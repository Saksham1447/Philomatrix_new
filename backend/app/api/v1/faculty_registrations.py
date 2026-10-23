from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.deps import get_current_user, require_roles
from app.models.user import User, Role, UserRoleAssignment
from app.models.institution import Institution
from app.models.academic import FacultyProfile
from app.models.faculty_registration import FacultyRegistrationRequest
from app.schemas.faculty_registration import (
    FacultyRegistrationCreate,
    FacultyRegistrationReview,
    FacultyRegistrationResponse,
    PublicFacultyLoginOption,
)

router = APIRouter(prefix="/faculty-registrations", tags=["Faculty Registration"])


def _response(request: FacultyRegistrationRequest) -> FacultyRegistrationResponse:
    return FacultyRegistrationResponse(
        id=request.id,
        institution_id=request.institution_id,
        username=request.username,
        email=request.email,
        first_name=request.first_name,
        last_name=request.last_name,
        phone_number=request.phone_number,
        employee_id=request.employee_id,
        designation=request.designation,
        department=request.department,
        qualification=request.qualification,
        status=request.status,
        review_comments=request.review_comments,
        created_at=request.created_at.isoformat(),
    )


@router.get("/public/faculty-options", response_model=List[PublicFacultyLoginOption])
def public_faculty_options(db: Session = Depends(get_db)):
    faculties = (
        db.query(FacultyProfile)
        .join(User, User.id == FacultyProfile.user_id)
        .join(Institution, Institution.id == FacultyProfile.institution_id)
        .filter(User.is_active == True)
        .order_by(User.first_name.asc(), User.last_name.asc())
        .all()
    )
    return [
        PublicFacultyLoginOption(
            id=faculty.id,
            full_name=faculty.user.full_name,
            username=faculty.user.username,
            email=faculty.user.email,
            institution_id=faculty.institution_id,
            institution_name=faculty.user.institution.name,
        )
        for faculty in faculties
    ]


@router.get("/public/institutions")
def public_institutions(db: Session = Depends(get_db)):
    return [
        {"id": institution.id, "name": institution.name}
        for institution in db.query(Institution).filter(Institution.status == "ACTIVE").order_by(Institution.name.asc()).all()
    ]


@router.post("", response_model=FacultyRegistrationResponse, status_code=status.HTTP_201_CREATED)
def submit_registration(request: FacultyRegistrationCreate, db: Session = Depends(get_db)):
    if not db.query(Institution).filter(Institution.id == request.institution_id, Institution.status == "ACTIVE").first():
        raise HTTPException(status_code=400, detail="Selected institution is not available")
    if db.query(User).filter((User.username == request.username) | (User.email == request.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already in use")
    if db.query(FacultyRegistrationRequest).filter(
        FacultyRegistrationRequest.status == "PENDING",
        (FacultyRegistrationRequest.username == request.username) | (FacultyRegistrationRequest.email == request.email),
    ).first():
        raise HTTPException(status_code=409, detail="A pending registration already exists for this username or email")

    registration = FacultyRegistrationRequest(
        institution_id=request.institution_id,
        username=request.username,
        email=request.email,
        password_hash=get_password_hash(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        phone_number=request.phone_number,
        employee_id=request.employee_id,
        designation=request.designation,
        department=request.department,
        qualification=request.qualification,
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return _response(registration)


@router.get("", response_model=List[FacultyRegistrationResponse])
def list_registrations(
    current_user: User = Depends(require_roles("OFFICE_STAFF", "PRINCIPAL", "SUPER_ADMIN")),
    db: Session = Depends(get_db),
):
    query = db.query(FacultyRegistrationRequest).order_by(FacultyRegistrationRequest.created_at.desc())
    if "SUPER_ADMIN" not in [assignment.role.name for assignment in current_user.role_assignments]:
        query = query.filter(FacultyRegistrationRequest.institution_id == current_user.institution_id)
    return [_response(item) for item in query.all()]


@router.put("/{request_id}/review", response_model=FacultyRegistrationResponse)
def review_registration(
    request_id: str,
    review: FacultyRegistrationReview,
    current_user: User = Depends(require_roles("OFFICE_STAFF", "PRINCIPAL", "SUPER_ADMIN")),
    db: Session = Depends(get_db),
):
    if review.status not in {"APPROVED", "REJECTED"}:
        raise HTTPException(status_code=400, detail="Review status must be APPROVED or REJECTED")
    registration = db.query(FacultyRegistrationRequest).filter(FacultyRegistrationRequest.id == request_id).first()
    if not registration:
        raise HTTPException(status_code=404, detail="Faculty registration not found")
    if registration.status != "PENDING":
        raise HTTPException(status_code=409, detail="This registration has already been reviewed")
    if current_user.institution_id != registration.institution_id and "SUPER_ADMIN" not in [a.role.name for a in current_user.role_assignments]:
        raise HTTPException(status_code=403, detail="You cannot review registrations for another institution")

    if review.status == "APPROVED":
        if db.query(User).filter((User.username == registration.username) | (User.email == registration.email)).first():
            raise HTTPException(status_code=409, detail="Username or email is already in use")
        if db.query(FacultyProfile).filter(
            FacultyProfile.institution_id == registration.institution_id,
            FacultyProfile.employee_id == registration.employee_id,
        ).first():
            raise HTTPException(status_code=409, detail="Employee ID already exists in this institution")
        user = User(
            institution_id=registration.institution_id,
            username=registration.username,
            email=registration.email,
            password_hash=registration.password_hash,
            first_name=registration.first_name,
            last_name=registration.last_name,
            phone_number=registration.phone_number,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.flush()
        faculty_role = db.query(Role).filter(Role.name == "FACULTY").first()
        if not faculty_role:
            faculty_role = Role(name="FACULTY", description="Lecturer / Subject Teacher")
            db.add(faculty_role)
            db.flush()
        db.add(UserRoleAssignment(user_id=user.id, role_id=faculty_role.id, institution_id=registration.institution_id))
        db.add(FacultyProfile(
            user_id=user.id,
            institution_id=registration.institution_id,
            employee_id=registration.employee_id,
            designation=registration.designation,
            department=registration.department,
            qualification=registration.qualification,
        ))

    registration.status = review.status
    registration.reviewed_by_id = current_user.id
    registration.review_comments = review.review_comments
    db.commit()
    db.refresh(registration)
    return _response(registration)
