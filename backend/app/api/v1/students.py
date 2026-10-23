from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.deps import get_current_user, require_roles
from app.models.user import User, Role, UserRoleAssignment
from app.models.student import Student, Guardian, StudentGuardianLink, Enrollment
from app.models.academic import Division, ClassModel, AcademicYear
from app.schemas.student import (
    StudentCreate,
    StudentResponse,
    GuardianResponse,
    LinkGuardianRequest,
)

router = APIRouter(prefix="/students", tags=["Student Management"])


@router.get("", response_model=List[StudentResponse])
def list_students(
    class_id: Optional[str] = None,
    division_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY", "OFFICE_STAFF")),
    db: Session = Depends(get_db)
):
    """List and search enrolled students within caller's institution."""
    query = (
        db.query(Student)
        .join(User, User.id == Student.user_id)
        .filter(Student.institution_id == current_user.institution_id)
    )

    if division_id:
        query = query.join(Enrollment, Enrollment.student_id == Student.id).filter(Enrollment.division_id == division_id)
    elif class_id:
        query = query.join(Enrollment, Enrollment.student_id == Student.id).filter(Enrollment.class_id == class_id)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Student.admission_number.ilike(search_filter)) |
            (User.first_name.ilike(search_filter)) |
            (User.last_name.ilike(search_filter)) |
            (User.email.ilike(search_filter))
        )

    students = query.all()
    results = []
    for s in students:
        # Get active enrollment
        enrollment = (
            db.query(Enrollment)
            .join(AcademicYear, AcademicYear.id == Enrollment.academic_year_id)
            .filter(Enrollment.student_id == s.id, AcademicYear.is_current == True)
            .first()
        )
        if not enrollment:
            enrollment = db.query(Enrollment).filter(Enrollment.student_id == s.id).first()

        guardians = []
        for link in s.guardian_links:
            g = link.guardian
            guardians.append(
                GuardianResponse(
                    id=g.id,
                    user_id=g.user_id,
                    full_name=g.user.full_name,
                    email=g.user.email,
                    phone_number=g.user.phone_number,
                    relationship_type=g.relationship_type,
                    occupation=g.occupation
                )
            )

        results.append(
            StudentResponse(
                id=s.id,
                user_id=s.user_id,
                admission_number=s.admission_number,
                roll_number=s.roll_number,
                first_name=s.user.first_name,
                last_name=s.user.last_name,
                full_name=s.user.full_name,
                email=s.user.email,
                phone_number=s.user.phone_number,
                date_of_birth=s.date_of_birth,
                gender=s.gender,
                blood_group=s.blood_group,
                admission_date=s.admission_date,
                address=s.address,
                status=s.status,
                class_name=enrollment.division.class_model.name if enrollment else None,
                division_name=enrollment.division.name if enrollment else None,
                division_id=enrollment.division_id if enrollment else None,
                academic_year_name=enrollment.academic_year.name if enrollment else None,
                guardians=guardians
            )
        )
    return results


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def admit_student(
    request: StudentCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL | STAFF] Admit a new student with login credentials, enrollment, and optional parent."""
    # Check duplicate user
    if db.query(User).filter((User.username == request.email) | (User.email == request.email)).first():
        raise HTTPException(status_code=400, detail="Student username or email already registered")

    # Check duplicate admission number in institution
    if db.query(Student).filter(
        Student.institution_id == current_user.institution_id,
        Student.admission_number == request.admission_number
    ).first():
        raise HTTPException(status_code=400, detail="Admission number already in use in this institution")

    # 1. Create User
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

    # 2. Assign STUDENT role
    student_role = db.query(Role).filter(Role.name == "STUDENT").first()
    if not student_role:
        student_role = Role(name="STUDENT", description="Enrolled Student")
        db.add(student_role)
        db.flush()

    role_assign = UserRoleAssignment(
        user_id=user.id,
        role_id=student_role.id,
        institution_id=current_user.institution_id
    )
    db.add(role_assign)

    # 3. Create Student profile
    student = Student(
        user_id=user.id,
        institution_id=current_user.institution_id,
        admission_number=request.admission_number,
        roll_number=request.roll_number,
        date_of_birth=request.date_of_birth,
        gender=request.gender,
        blood_group=request.blood_group,
        admission_date=request.admission_date,
        address=request.address,
        emergency_contact_name=request.emergency_contact_name,
        emergency_contact_phone=request.emergency_contact_phone,
        status="ACTIVE"
    )
    db.add(student)
    db.flush()

    # 4. Enroll in academic year, class, and division
    enrollment = Enrollment(
        institution_id=current_user.institution_id,
        student_id=student.id,
        academic_year_id=request.academic_year_id,
        class_id=request.class_id,
        division_id=request.division_id,
        roll_number=request.roll_number,
        status="ENROLLED"
    )
    db.add(enrollment)

    # 5. Optional Guardian creation & linking
    guardians_out = []
    if request.guardian:
        g_user = db.query(User).filter(
            (User.username == request.guardian.username) | (User.email == request.guardian.email)
        ).first()

        if not g_user:
            g_user = User(
                institution_id=current_user.institution_id,
                username=request.guardian.username,
                email=request.guardian.email,
                password_hash=get_password_hash(request.guardian.password),
                first_name=request.guardian.first_name,
                last_name=request.guardian.last_name,
                phone_number=request.guardian.phone_number,
                is_active=True,
                is_verified=True
            )
            db.add(g_user)
            db.flush()

            parent_role = db.query(Role).filter(Role.name == "PARENT").first()
            if not parent_role:
                parent_role = Role(name="PARENT", description="Parent / Legal Guardian")
                db.add(parent_role)
                db.flush()

            db.add(UserRoleAssignment(
                user_id=g_user.id,
                role_id=parent_role.id,
                institution_id=current_user.institution_id
            ))

            guardian_profile = Guardian(
                user_id=g_user.id,
                institution_id=current_user.institution_id,
                relationship_type=request.guardian.relationship_type,
                occupation=request.guardian.occupation
            )
            db.add(guardian_profile)
            db.flush()
        else:
            guardian_profile = g_user.guardian_profile

        # Link student to guardian
        link = StudentGuardianLink(
            student_id=student.id,
            guardian_id=guardian_profile.id,
            is_primary=True,
            is_verified=True
        )
        db.add(link)

        guardians_out.append(
            GuardianResponse(
                id=guardian_profile.id,
                user_id=g_user.id,
                full_name=g_user.full_name,
                email=g_user.email,
                phone_number=g_user.phone_number,
                relationship_type=guardian_profile.relationship_type,
                occupation=guardian_profile.occupation
            )
        )

    db.commit()
    db.refresh(student)

    # Get division and class names
    div = db.query(Division).filter(Division.id == request.division_id).first()
    year = db.query(AcademicYear).filter(AcademicYear.id == request.academic_year_id).first()

    return StudentResponse(
        id=student.id,
        user_id=user.id,
        admission_number=student.admission_number,
        roll_number=student.roll_number,
        first_name=user.first_name,
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
        class_name=div.class_model.name if div else None,
        division_name=div.name if div else None,
        division_id=div.id if div else None,
        academic_year_name=year.name if year else None,
        guardians=guardians_out
    )


@router.put("/{id}", response_model=StudentResponse)
def update_student(
    id: str,
    request: StudentCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == id, Student.institution_id == current_user.institution_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    user = student.user
    user.first_name, user.last_name, user.email = request.first_name, request.last_name, request.email
    user.phone_number = request.phone_number
    student.admission_number, student.roll_number = request.admission_number, request.roll_number
    student.date_of_birth, student.gender = request.date_of_birth, request.gender
    student.admission_date, student.address = request.admission_date, request.address
    student.blood_group = request.blood_group
    enrollment = db.query(Enrollment).filter(Enrollment.student_id == student.id, Enrollment.academic_year_id == request.academic_year_id).first()
    if enrollment:
        enrollment.class_id, enrollment.division_id, enrollment.roll_number = request.class_id, request.division_id, request.roll_number
    db.commit()
    db.refresh(student)
    enrollment = db.query(Enrollment).filter(Enrollment.student_id == student.id, Enrollment.academic_year_id == request.academic_year_id).first()
    return StudentResponse(
        id=student.id, user_id=user.id, admission_number=student.admission_number,
        roll_number=student.roll_number, first_name=user.first_name, last_name=user.last_name,
        full_name=user.full_name, email=user.email, phone_number=user.phone_number,
        date_of_birth=student.date_of_birth, gender=student.gender, blood_group=student.blood_group,
        admission_date=student.admission_date, address=student.address, status=student.status,
        class_name=enrollment.division.class_model.name if enrollment else None,
        division_name=enrollment.division.name if enrollment else None,
        division_id=enrollment.division_id if enrollment else None,
        academic_year_name=enrollment.academic_year.name if enrollment else None,
        guardians=[],
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    id: str,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == id, Student.institution_id == current_user.institution_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student.user)
    db.commit()
    return None


@router.get("/my-profile", response_model=StudentResponse)
def get_my_student_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """[STUDENT] Return own student record."""
    if not current_user.student_profile:
        raise HTTPException(status_code=404, detail="Student profile not found for this user")

    s = current_user.student_profile
    enrollment = db.query(Enrollment).filter(Enrollment.student_id == s.id).first()

    return StudentResponse(
        id=s.id,
        user_id=s.user_id,
        admission_number=s.admission_number,
        roll_number=s.roll_number,
        first_name=s.user.first_name,
        last_name=s.user.last_name,
        full_name=s.user.full_name,
        email=s.user.email,
        phone_number=s.user.phone_number,
        date_of_birth=s.date_of_birth,
        gender=s.gender,
        blood_group=s.blood_group,
        admission_date=s.admission_date,
        address=s.address,
        status=s.status,
        class_name=enrollment.division.class_model.name if enrollment else None,
        division_name=enrollment.division.name if enrollment else None,
        division_id=enrollment.division_id if enrollment else None,
        academic_year_name=enrollment.academic_year.name if enrollment else None,
        guardians=[]
    )


@router.get("/my-children", response_model=List[StudentResponse])
def get_my_children(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """[PARENT] List verified linked children for multi-child switcher."""
    if not current_user.guardian_profile:
        raise HTTPException(status_code=403, detail="Current user is not a registered guardian")

    guardian = current_user.guardian_profile
    results = []
    for link in guardian.student_links:
        s = link.student
        enrollment = db.query(Enrollment).filter(Enrollment.student_id == s.id).first()
        results.append(
            StudentResponse(
                id=s.id,
                user_id=s.user_id,
                admission_number=s.admission_number,
                roll_number=s.roll_number,
                first_name=s.user.first_name,
                last_name=s.user.last_name,
                full_name=s.user.full_name,
                email=s.user.email,
                phone_number=s.user.phone_number,
                date_of_birth=s.date_of_birth,
                gender=s.gender,
                blood_group=s.blood_group,
                admission_date=s.admission_date,
                address=s.address,
                status=s.status,
                class_name=enrollment.division.class_model.name if enrollment else None,
                division_name=enrollment.division.name if enrollment else None,
                division_id=enrollment.division_id if enrollment else None,
                academic_year_name=enrollment.academic_year.name if enrollment else None,
                guardians=[]
            )
        )
    return results
