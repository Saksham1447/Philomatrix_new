from types import SimpleNamespace
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_password_hash
from app.core.deps import get_db, get_current_user, require_roles
from app.core.people import ensure_unique_person_id, normalize_gender
from app.core.docstore import Conflict, DocStore, UserDoc
from app.core.q import group_by, ids, in_, regex_contains
from app.schemas.student import (
    StudentCreate,
    StudentResponse,
    GuardianResponse,
    LinkGuardianRequest,
)

router = APIRouter(prefix="/students", tags=["Student Management"])


class _Refs:
    """Batched division/class/academic-year lookups for enrollment display fields."""

    def __init__(self, db: DocStore, enrollments):
        enrollments = [e for e in enrollments if e]
        self.divisions = db.get_many("divisions", ids(enrollments, "division_id"))
        self.classes = db.get_many("classes", [d.class_id for d in self.divisions.values()])
        self.years = db.get_many("academic_years", ids(enrollments, "academic_year_id"))


def _student_response(student, user, enrollment, refs: _Refs, guardians=None) -> StudentResponse:
    division = refs.divisions.get(enrollment.division_id) if enrollment else None
    cls = refs.classes.get(division.class_id) if division else None
    year = refs.years.get(enrollment.academic_year_id) if enrollment else None
    return StudentResponse(
        id=student.id,
        user_id=student.user_id,
        admission_number=student.admission_number,
        roll_number=student.roll_number,
        first_name=user.first_name,
        middle_name=user.middle_name,
        last_name=user.last_name,
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        date_of_birth=student.date_of_birth,
        gender=student.gender,
        blood_group=student.blood_group,
        admission_date=student.admission_date,
        address=student.address,
        status=student.status,
        class_name=cls.name if enrollment and cls else None,
        division_name=division.name if enrollment and division else None,
        division_id=enrollment.division_id if enrollment else None,
        academic_year_name=year.name if year else None,
        guardians=guardians or [],
    )


def _guardian_response(guardian, user) -> GuardianResponse:
    return GuardianResponse(
        id=guardian.id,
        user_id=guardian.user_id,
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        relationship_type=guardian.relationship_type,
        occupation=guardian.occupation,
    )


@router.get("", response_model=List[StudentResponse])
def list_students(
    class_id: Optional[str] = None,
    division_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY", "OFFICE_STAFF")),
    db: DocStore = Depends(get_db)
):
    """List and search enrolled students within caller's institution."""
    query = {"institution_id": current_user.institution_id}

    if division_id or class_id:
        enrollment_filter = {"division_id": division_id} if division_id else {"class_id": class_id}
        enrolled = db.find("enrollments", enrollment_filter)
        query["id"] = in_(set(ids(enrolled, "student_id")))

    if search:
        pattern = regex_contains(search)
        matching_users = db.find(
            "users",
            {
                "institution_id": current_user.institution_id,
                "$or": [{"first_name": pattern}, {"middle_name": pattern}, {"last_name": pattern}, {"email": pattern}],
            },
        )
        query["$or"] = [
            {"admission_number": pattern},
            {"user_id": in_(ids(matching_users))},
        ]

    students = db.find("students", query)
    student_ids = ids(students)
    users = db.get_many("users", ids(students, "user_id"))

    all_enrollments = db.find("enrollments", {"student_id": in_(student_ids)}) if student_ids else []
    enrollments_by_student = group_by(all_enrollments, "student_id")
    refs = _Refs(db, all_enrollments)

    links = db.find("student_guardian_links", {"student_id": in_(student_ids)}) if student_ids else []
    links_by_student = group_by(links, "student_id")
    guardians = db.get_many("guardians", ids(links, "guardian_id"))
    guardian_users = db.get_many("users", [g.user_id for g in guardians.values()])

    results = []
    for s in students:
        # Prefer enrollment in the current academic year, else any enrollment
        student_enrollments = enrollments_by_student.get(s.id, [])
        enrollment = next(
            (e for e in student_enrollments if getattr(refs.years.get(e.academic_year_id), "is_current", False)),
            None,
        ) or (student_enrollments[0] if student_enrollments else None)

        guardian_out = []
        for link in links_by_student.get(s.id, []):
            g = guardians.get(link.guardian_id)
            if g:
                guardian_out.append(_guardian_response(g, guardian_users[g.user_id]))

        results.append(_student_response(s, users[s.user_id], enrollment, refs, guardian_out))
    return results


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def admit_student(
    request: StudentCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: DocStore = Depends(get_db)
):
    """[PRINCIPAL | STAFF] Admit a new student with login credentials, enrollment, and optional parent."""
    # Check duplicate user
    if db.find_one("users", {"$or": [{"username": request.email}, {"email": request.email}]}):
        raise HTTPException(status_code=400, detail="Student username or email already registered")

    # Student ID (admission number) must be unique within the institution
    admission_number = ensure_unique_person_id(
        db, "students", "admission_number", request.admission_number, current_user.institution_id, "Student ID"
    )
    gender = normalize_gender(request.gender)

    created_users = []  # best-effort rollback targets (cascade-deleted on failure)

    def _get_or_create_role(name: str, description: str):
        role = db.find_one("roles", {"name": name})
        return role or db.insert("roles", {"name": name, "description": description})

    try:
        # 1. Create User
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
        created_users.append(user)

        # 2. Assign STUDENT role
        student_role = _get_or_create_role("STUDENT", "Enrolled Student")
        db.insert("user_role_assignments", {
            "user_id": user.id,
            "role_id": student_role.id,
            "institution_id": current_user.institution_id,
        })

        # 3. Create Student profile
        student = db.insert("students", {
            "user_id": user.id,
            "institution_id": current_user.institution_id,
            "admission_number": admission_number,
            "roll_number": request.roll_number,
            "date_of_birth": request.date_of_birth,
            "gender": gender,
            "blood_group": request.blood_group,
            "admission_date": request.admission_date,
            "address": request.address,
            "emergency_contact_name": request.emergency_contact_name,
            "emergency_contact_phone": request.emergency_contact_phone,
            "status": "ACTIVE",
        })

        # 4. Enroll in academic year, class, and division
        db.insert("enrollments", {
            "institution_id": current_user.institution_id,
            "student_id": student.id,
            "academic_year_id": request.academic_year_id,
            "class_id": request.class_id,
            "division_id": request.division_id,
            "roll_number": request.roll_number,
            "status": "ENROLLED",
        })

        # 5. Optional Guardian creation & linking
        guardians_out = []
        if request.guardian:
            g_user = db.find_one("users", {"$or": [
                {"username": request.guardian.username},
                {"email": request.guardian.email},
            ]})

            if not g_user:
                g_user = db.insert("users", {
                    "institution_id": current_user.institution_id,
                    "username": request.guardian.username,
                    "email": request.guardian.email,
                    "password_hash": get_password_hash(request.guardian.password),
                    "first_name": request.guardian.first_name,
                    "middle_name": request.guardian.middle_name,
                    "last_name": request.guardian.last_name,
                    "phone_number": request.guardian.phone_number,
                    "is_active": True,
                    "is_verified": True,
                })
                created_users.append(g_user)

                parent_role = _get_or_create_role("PARENT", "Parent / Legal Guardian")
                db.insert("user_role_assignments", {
                    "user_id": g_user.id,
                    "role_id": parent_role.id,
                    "institution_id": current_user.institution_id,
                })

                guardian_profile = db.insert("guardians", {
                    "user_id": g_user.id,
                    "institution_id": current_user.institution_id,
                    "relationship_type": request.guardian.relationship_type,
                    "occupation": request.guardian.occupation,
                })
            else:
                guardian_profile = g_user.guardian_profile
                if guardian_profile is None:
                    raise HTTPException(status_code=400, detail="Existing guardian user has no guardian profile")

            # Link student to guardian
            db.insert("student_guardian_links", {
                "student_id": student.id,
                "guardian_id": guardian_profile.id,
                "is_primary": True,
                "is_verified": True,
            })
            guardians_out.append(_guardian_response(guardian_profile, g_user))
    except Conflict:
        for created in reversed(created_users):
            db.delete("users", created)
        raise HTTPException(status_code=400, detail="Student or guardian details conflict with an existing record")
    except Exception:
        for created in reversed(created_users):
            db.delete("users", created)
        raise

    # Names are resolved from the requested division/year ids (as before the migration)
    enrollment = SimpleNamespace(division_id=request.division_id, academic_year_id=request.academic_year_id)
    refs = _Refs(db, [enrollment])
    if request.division_id not in refs.divisions:
        enrollment = None
    return _student_response(student, user, enrollment, refs, guardians_out)


@router.put("/{id}", response_model=StudentResponse)
def update_student(
    id: str,
    request: StudentCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db),
):
    student = db.find_one("students", {"id": id, "institution_id": current_user.institution_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    admission_number = ensure_unique_person_id(
        db, "students", "admission_number", request.admission_number, current_user.institution_id, "Student ID",
        exclude_id=student.id,
    )
    gender = normalize_gender(request.gender)
    user = db.get("users", student.user_id)
    try:
        user = db.update(user, {
            "first_name": request.first_name,
            "middle_name": request.middle_name,
            "last_name": request.last_name,
            "email": request.email,
            "phone_number": request.phone_number,
        })
        student = db.update(student, {
            "admission_number": admission_number,
            "roll_number": request.roll_number,
            "date_of_birth": request.date_of_birth,
            "gender": gender,
            "admission_date": request.admission_date,
            "address": request.address,
            "blood_group": request.blood_group,
        })
        enrollment = db.find_one("enrollments", {
            "student_id": student.id,
            "academic_year_id": request.academic_year_id,
        })
        if enrollment:
            enrollment = db.update(enrollment, {
                "class_id": request.class_id,
                "division_id": request.division_id,
                "roll_number": request.roll_number,
            })
    except Conflict:
        raise HTTPException(status_code=400, detail="Email or admission number already in use")
    return _student_response(student, user, enrollment, _Refs(db, [enrollment]))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    id: str,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db),
):
    student = db.find_one("students", {"id": id, "institution_id": current_user.institution_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete("users", student.user_id)
    return None


@router.get("/my-profile", response_model=StudentResponse)
def get_my_student_profile(
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """[STUDENT] Return own student record."""
    s = current_user.student_profile
    if not s:
        raise HTTPException(status_code=404, detail="Student profile not found for this user")

    enrollment = db.find_one("enrollments", {"student_id": s.id})
    return _student_response(s, current_user, enrollment, _Refs(db, [enrollment]))


@router.get("/my-children", response_model=List[StudentResponse])
def get_my_children(
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """[PARENT] List verified linked children for multi-child switcher."""
    guardian = current_user.guardian_profile
    if not guardian:
        raise HTTPException(status_code=403, detail="Current user is not a registered guardian")

    links = db.find("student_guardian_links", {"guardian_id": guardian.id})
    students = db.get_many("students", ids(links, "student_id"))
    users = db.get_many("users", [s.user_id for s in students.values()])
    enrollments = db.find("enrollments", {"student_id": in_(students.keys())}) if students else []
    enrollments_by_student = group_by(enrollments, "student_id")
    refs = _Refs(db, enrollments)

    results = []
    for link in links:
        s = students.get(link.student_id)
        if not s:
            continue
        student_enrollments = enrollments_by_student.get(s.id, [])
        enrollment = student_enrollments[0] if student_enrollments else None
        results.append(_student_response(s, users[s.user_id], enrollment, refs))
    return results
