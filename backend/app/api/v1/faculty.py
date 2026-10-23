from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.deps import get_current_user, require_roles
from app.models.user import User, Role, UserRoleAssignment
from app.models.academic import FacultyProfile, FacultySubjectAssignment, Subject, Division, ClassModel, AcademicYear
from app.schemas.academic import (
    FacultyCreate,
    FacultyResponse,
    FacultyAssignmentCreate,
    FacultyAssignmentResponse,
)

router = APIRouter(prefix="/faculty", tags=["Faculty Management"])


@router.get("", response_model=List[FacultyResponse])
def list_faculty(
    department: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all faculty members in the caller's institution."""
    query = (
        db.query(FacultyProfile)
        .filter(FacultyProfile.institution_id == current_user.institution_id)
    )
    if department:
        query = query.filter(FacultyProfile.department == department)
    faculties = query.all()
    result = []
    for f in faculties:
        result.append(
            FacultyResponse(
                id=f.id,
                user_id=f.user_id,
                employee_id=f.employee_id,
                first_name=f.user.first_name,
                last_name=f.user.last_name,
                full_name=f.user.full_name,
                email=f.user.email,
                phone_number=f.user.phone_number,
                designation=f.designation,
                department=f.department,
                qualification=f.qualification
            )
        )
    return result


@router.post("", response_model=FacultyResponse, status_code=status.HTTP_201_CREATED)
def create_faculty(
    request: FacultyCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: Session = Depends(get_db)
):
    """Register a new faculty lecturer and user account."""
    existing_user = (
        db.query(User)
        .filter((User.username == request.email) | (User.email == request.email))
        .first()
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already in use")

    existing_emp = (
        db.query(FacultyProfile)
        .filter(
            FacultyProfile.institution_id == current_user.institution_id,
            FacultyProfile.employee_id == request.employee_id
        )
        .first()
    )
    if existing_emp:
        raise HTTPException(status_code=400, detail="Employee ID already exists in institution")

    # Create User
    user = User(
        institution_id=current_user.institution_id,
        username=request.email,
        email=request.email,
        password_hash=get_password_hash(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        phone_number=request.phone_number,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    db.flush()

    # Assign FACULTY role
    faculty_role = db.query(Role).filter(Role.name == "FACULTY").first()
    if not faculty_role:
        faculty_role = Role(name="FACULTY", description="Lecturer / Subject Teacher")
        db.add(faculty_role)
        db.flush()

    role_assign = UserRoleAssignment(
        user_id=user.id,
        role_id=faculty_role.id,
        institution_id=current_user.institution_id
    )
    db.add(role_assign)

    # Create Faculty Profile
    profile = FacultyProfile(
        user_id=user.id,
        institution_id=current_user.institution_id,
        employee_id=request.employee_id,
        designation=request.designation,
        department=request.department,
        qualification=request.qualification
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return FacultyResponse(
        id=profile.id,
        user_id=user.id,
        employee_id=profile.employee_id,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        designation=profile.designation,
        department=profile.department,
        qualification=profile.qualification
    )


@router.put("/{id}", response_model=FacultyResponse)
def update_faculty(
    id: str,
    request: FacultyCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: Session = Depends(get_db),
):
    profile = db.query(FacultyProfile).filter(FacultyProfile.id == id, FacultyProfile.institution_id == current_user.institution_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Faculty member not found")
    user = profile.user
    user.first_name, user.last_name, user.email = request.first_name, request.last_name, request.email
    user.phone_number = request.phone_number
    profile.employee_id, profile.designation = request.employee_id, request.designation
    profile.department, profile.qualification = request.department, request.qualification
    db.commit()
    db.refresh(profile)
    return FacultyResponse(id=profile.id, user_id=user.id, employee_id=profile.employee_id, first_name=user.first_name, last_name=user.last_name, full_name=user.full_name, email=user.email, phone_number=user.phone_number, designation=profile.designation, department=profile.department, qualification=profile.qualification)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty(
    id: str,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: Session = Depends(get_db),
):
    profile = db.query(FacultyProfile).filter(FacultyProfile.id == id, FacultyProfile.institution_id == current_user.institution_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Faculty member not found")
    db.delete(profile.user)
    db.commit()
    return None


@router.get("/assignments", response_model=List[FacultyAssignmentResponse])
def list_assignments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List teaching assignments."""
    query = (
        db.query(FacultySubjectAssignment)
        .filter(FacultySubjectAssignment.institution_id == current_user.institution_id)
    )
    # If faculty, scope to own assignments
    if current_user.faculty_profile:
        query = query.filter(FacultySubjectAssignment.faculty_id == current_user.faculty_profile.id)

    assignments = query.all()
    results = []
    for a in assignments:
        results.append(
            FacultyAssignmentResponse(
                id=a.id,
                academic_year_id=a.academic_year_id,
                faculty_id=a.faculty_id,
                faculty_name=a.faculty.user.full_name,
                subject_id=a.subject_id,
                subject_name=a.subject.name,
                subject_code=a.subject.code,
                division_id=a.division_id,
                division_name=a.division.name,
                class_name=a.division.class_model.name,
                is_class_teacher=a.is_class_teacher
            )
        )
    return results


@router.post("/assignments", response_model=FacultyAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_faculty_subject(
    request: FacultyAssignmentCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL] Assign a teacher to a subject and division."""
    existing = (
        db.query(FacultySubjectAssignment)
        .filter(
            FacultySubjectAssignment.academic_year_id == request.academic_year_id,
            FacultySubjectAssignment.faculty_id == request.faculty_id,
            FacultySubjectAssignment.subject_id == request.subject_id,
            FacultySubjectAssignment.division_id == request.division_id
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Assignment already exists for this teacher, subject, and division")

    assignment = FacultySubjectAssignment(
        institution_id=current_user.institution_id,
        academic_year_id=request.academic_year_id,
        faculty_id=request.faculty_id,
        subject_id=request.subject_id,
        division_id=request.division_id,
        is_class_teacher=request.is_class_teacher
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return FacultyAssignmentResponse(
        id=assignment.id,
        academic_year_id=assignment.academic_year_id,
        faculty_id=assignment.faculty_id,
        faculty_name=assignment.faculty.user.full_name,
        subject_id=assignment.subject_id,
        subject_name=assignment.subject.name,
        subject_code=assignment.subject.code,
        division_id=assignment.division_id,
        division_name=assignment.division.name,
        class_name=assignment.division.class_model.name,
        is_class_teacher=assignment.is_class_teacher
    )
