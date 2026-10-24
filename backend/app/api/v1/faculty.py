from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_password_hash
from app.core.deps import get_db, get_current_user, require_roles
from app.core.docstore import Conflict, DocStore, UserDoc
from app.core.institution_rules import resolve_faculty_department
from app.core.people import ensure_unique_person_id, normalize_gender
from app.core.q import ids
from app.schemas.academic import (
    FacultyCreate,
    FacultyResponse,
    FacultyAssignmentCreate,
    FacultyAssignmentResponse,
)

router = APIRouter(prefix="/faculty", tags=["Faculty Management"])


def _faculty_response(profile, user) -> FacultyResponse:
    return FacultyResponse(
        id=profile.id,
        user_id=user.id,
        employee_id=profile.employee_id,
        gender=profile.gender,
        first_name=user.first_name,
        middle_name=user.middle_name,
        last_name=user.last_name,
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        designation=profile.designation,
        department=profile.department,
        qualification=profile.qualification,
    )


def _assignment_responses(db: DocStore, assignments) -> List[FacultyAssignmentResponse]:
    """Resolve faculty/user/subject/division/class names with batched lookups."""
    faculty = db.get_many("faculty_profiles", ids(assignments, "faculty_id"))
    users = db.get_many("users", [f.user_id for f in faculty.values()])
    subjects = db.get_many("subjects", ids(assignments, "subject_id"))
    divisions = db.get_many("divisions", ids(assignments, "division_id"))
    classes = db.get_many("classes", [d.class_id for d in divisions.values()])
    results = []
    for a in assignments:
        fac = faculty[a.faculty_id]
        subject = subjects[a.subject_id]
        division = divisions[a.division_id]
        results.append(
            FacultyAssignmentResponse(
                id=a.id,
                academic_year_id=a.academic_year_id,
                faculty_id=a.faculty_id,
                faculty_name=users[fac.user_id].full_name,
                subject_id=a.subject_id,
                subject_name=subject.name,
                subject_code=subject.code,
                division_id=a.division_id,
                division_name=division.name,
                class_name=classes[division.class_id].name,
                is_class_teacher=a.is_class_teacher,
            )
        )
    return results


@router.get("", response_model=List[FacultyResponse])
def list_faculty(
    department: str = None,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """List all faculty members in the caller's institution."""
    query = {"institution_id": current_user.institution_id}
    if department:
        query["department"] = department
    faculties = db.find("faculty_profiles", query)
    users = db.get_many("users", ids(faculties, "user_id"))
    return [_faculty_response(f, users[f.user_id]) for f in faculties]


@router.post("", response_model=FacultyResponse, status_code=status.HTTP_201_CREATED)
def create_faculty(
    request: FacultyCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: DocStore = Depends(get_db)
):
    """Register a new faculty lecturer and user account."""
    existing_user = db.find_one(
        "users",
        {"$or": [{"username": request.email}, {"email": request.email}]},
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already in use")

    employee_id = ensure_unique_person_id(
        db, "faculty_profiles", "employee_id", request.employee_id, current_user.institution_id, "Faculty ID"
    )
    gender = normalize_gender(request.gender)
    department = resolve_faculty_department(db, current_user.institution_id, request.department)
    user = None
    try:
        # Create User
        user = db.insert("users", {
            "institution_id": current_user.institution_id,
            "username": request.email,
            "email": request.email,
            "password_hash": get_password_hash(request.password),
            "first_name": request.first_name,
            "middle_name": request.middle_name,
            "last_name": request.last_name,
            "phone_number": request.phone_number,
            "is_active": True,
            "is_verified": True,
        })

        # Assign FACULTY role
        faculty_role = db.find_one("roles", {"name": "FACULTY"})
        if not faculty_role:
            faculty_role = db.insert("roles", {"name": "FACULTY", "description": "Lecturer / Subject Teacher"})

        db.insert("user_role_assignments", {
            "user_id": user.id,
            "role_id": faculty_role.id,
            "institution_id": current_user.institution_id,
        })

        # Create Faculty Profile
        profile = db.insert("faculty_profiles", {
            "user_id": user.id,
            "institution_id": current_user.institution_id,
            "employee_id": employee_id,
            "gender": gender,
            "designation": request.designation,
            "department": department,
            "qualification": request.qualification,
        })
    except Conflict:
        # Best-effort rollback (no multi-document transaction): cascade-delete the new user
        if user is not None:
            db.delete("users", user)
        raise HTTPException(status_code=400, detail="Username, email, or employee ID already in use")
    except Exception:
        if user is not None:
            db.delete("users", user)
        raise

    return _faculty_response(profile, user)


@router.put("/{id}", response_model=FacultyResponse)
def update_faculty(
    id: str,
    request: FacultyCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db),
):
    profile = db.find_one("faculty_profiles", {"id": id, "institution_id": current_user.institution_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Faculty member not found")
    department = resolve_faculty_department(db, current_user.institution_id, request.department, profile.department)
    employee_id = ensure_unique_person_id(
        db, "faculty_profiles", "employee_id", request.employee_id, current_user.institution_id, "Faculty ID",
        exclude_id=profile.id,
    )
    gender = normalize_gender(request.gender, required=False) or profile.gender
    user = db.get("users", profile.user_id)
    try:
        user = db.update(user, {
            "first_name": request.first_name,
            "middle_name": request.middle_name,
            "last_name": request.last_name,
            "email": request.email,
            "phone_number": request.phone_number,
        })
        profile = db.update(profile, {
            "employee_id": employee_id,
            "gender": gender,
            "designation": request.designation,
            "department": department,
            "qualification": request.qualification,
        })
    except Conflict:
        raise HTTPException(status_code=400, detail="Email or employee ID already in use")
    return _faculty_response(profile, user)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty(
    id: str,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db),
):
    profile = db.find_one("faculty_profiles", {"id": id, "institution_id": current_user.institution_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Faculty member not found")
    db.delete("users", profile.user_id)
    return None


@router.get("/assignments", response_model=List[FacultyAssignmentResponse])
def list_assignments(
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """List teaching assignments."""
    query = {"institution_id": current_user.institution_id}
    # If faculty, scope to own assignments
    faculty_profile = current_user.faculty_profile
    if faculty_profile:
        query["faculty_id"] = faculty_profile.id

    return _assignment_responses(db, db.find("faculty_subject_assignments", query))


@router.post("/assignments", response_model=FacultyAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_faculty_subject(
    request: FacultyAssignmentCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db)
):
    """[PRINCIPAL] Assign a teacher to a subject and division."""
    existing = db.find_one(
        "faculty_subject_assignments",
        {
            "academic_year_id": request.academic_year_id,
            "faculty_id": request.faculty_id,
            "subject_id": request.subject_id,
            "division_id": request.division_id,
        },
    )
    if existing:
        raise HTTPException(status_code=400, detail="Assignment already exists for this teacher, subject, and division")

    assignment = db.insert("faculty_subject_assignments", {
        "institution_id": current_user.institution_id,
        "academic_year_id": request.academic_year_id,
        "faculty_id": request.faculty_id,
        "subject_id": request.subject_id,
        "division_id": request.division_id,
        "is_class_teacher": request.is_class_teacher,
    })

    return _assignment_responses(db, [assignment])[0]