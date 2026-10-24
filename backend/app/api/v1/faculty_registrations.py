from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_db
from app.core.deps import get_current_user, require_roles
from app.core.docstore import Doc, DocStore, UserDoc
from app.core.security import get_password_hash
from app.schemas.faculty_registration import (
    FacultyRegistrationCreate,
    FacultyRegistrationResponse,
    FacultyRegistrationReview,
    PublicFacultyLoginOption,
)

router = APIRouter(prefix="/faculty-registrations", tags=["Faculty Registration"])


def _response(request: Doc) -> FacultyRegistrationResponse:
    return FacultyRegistrationResponse(
        id=request.id,
        institution_id=request.institution_id,
        username=request.username,
        email=request.email,
        first_name=request.first_name,
        middle_name=request.middle_name,
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
def public_faculty_options(db: DocStore = Depends(get_db)):
    profiles = db.find("faculty_profiles")
    faculties = []
    for profile in profiles:
        user = db.get("users", profile.user_id)
        institution = db.get("institutions", profile.institution_id)
        if not user or not user.is_active or not institution:
            continue
        user_institution = db.get("institutions", user.institution_id) if user.institution_id else None
        if not user_institution:
            continue
        faculties.append((profile, user, user_institution))

    faculties.sort(key=lambda item: (
        item[1].first_name or "",
        item[1].last_name or "",
    ))
    return [
        PublicFacultyLoginOption(
            id=profile.id,
            full_name=user.full_name,
            username=user.username,
            email=user.email,
            institution_id=profile.institution_id,
            institution_name=institution.name,
        )
        for profile, user, institution in faculties
    ]


@router.get("/public/institutions")
def public_institutions(db: DocStore = Depends(get_db)):
    return [
        {"id": institution.id, "name": institution.name}
        for institution in db.find("institutions", {"status": "ACTIVE"}, sort=[("name", 1)])
    ]


@router.post("", response_model=FacultyRegistrationResponse, status_code=status.HTTP_201_CREATED)
def submit_registration(request: FacultyRegistrationCreate, db: DocStore = Depends(get_db)):
    if not db.find_one("institutions", {"id": request.institution_id, "status": "ACTIVE"}):
        raise HTTPException(status_code=400, detail="Selected institution is not available")
    if db.find_one("users", {"$or": [{"username": request.username}, {"email": request.email}]}):
        raise HTTPException(status_code=400, detail="Username or email already in use")
    if db.find_one(
        "faculty_registration_requests",
        {
            "status": "PENDING",
            "$or": [{"username": request.username}, {"email": request.email}],
        },
    ):
        raise HTTPException(
            status_code=409,
            detail="A pending registration already exists for this username or email",
        )

    registration = db.insert("faculty_registration_requests", {
        "institution_id": request.institution_id,
        "username": request.username,
        "email": request.email,
        "password_hash": get_password_hash(request.password),
        "first_name": request.first_name,
        "middle_name": request.middle_name,
        "last_name": request.last_name,
        "phone_number": request.phone_number,
        "employee_id": request.employee_id,
        "designation": request.designation,
        "department": request.department,
        "qualification": request.qualification,
    })
    return _response(registration)


@router.get("", response_model=List[FacultyRegistrationResponse])
def list_registrations(
    current_user: UserDoc = Depends(require_roles("OFFICE_STAFF", "PRINCIPAL", "SUPER_ADMIN")),
    db: DocStore = Depends(get_db),
):
    filter_doc = {}
    if "SUPER_ADMIN" not in current_user.role_names:
        filter_doc["institution_id"] = current_user.institution_id
    requests = db.find(
        "faculty_registration_requests",
        filter_doc,
        sort=[("created_at", -1)],
    )
    return [_response(item) for item in requests]


@router.put("/{request_id}/review", response_model=FacultyRegistrationResponse)
def review_registration(
    request_id: str,
    review: FacultyRegistrationReview,
    current_user: UserDoc = Depends(require_roles("OFFICE_STAFF", "PRINCIPAL", "SUPER_ADMIN")),
    db: DocStore = Depends(get_db),
):
    if review.status not in {"APPROVED", "REJECTED"}:
        raise HTTPException(status_code=400, detail="Review status must be APPROVED or REJECTED")
    registration = db.get("faculty_registration_requests", request_id)
    if not registration:
        raise HTTPException(status_code=404, detail="Faculty registration not found")
    if registration.status != "PENDING":
        raise HTTPException(status_code=409, detail="This registration has already been reviewed")
    if (
        current_user.institution_id != registration.institution_id
        and "SUPER_ADMIN" not in current_user.role_names
    ):
        raise HTTPException(status_code=403, detail="You cannot review registrations for another institution")

    if review.status == "APPROVED":
        if db.find_one(
            "users",
            {"$or": [{"username": registration.username}, {"email": registration.email}]},
        ):
            raise HTTPException(status_code=409, detail="Username or email is already in use")
        if db.find_one(
            "faculty_profiles",
            {
                "institution_id": registration.institution_id,
                "employee_id": registration.employee_id,
            },
        ):
            raise HTTPException(status_code=409, detail="Employee ID already exists in this institution")

        user = db.insert("users", {
            "institution_id": registration.institution_id,
            "username": registration.username,
            "email": registration.email,
            "password_hash": registration.password_hash,
            "first_name": registration.first_name,
            "middle_name": registration.middle_name,
            "last_name": registration.last_name,
            "phone_number": registration.phone_number,
            "is_active": True,
            "is_verified": True,
        })
        faculty_role = db.find_one("roles", {"name": "FACULTY"})
        if not faculty_role:
            faculty_role = db.insert("roles", {
                "name": "FACULTY",
                "description": "Lecturer / Subject Teacher",
            })
        db.insert("user_role_assignments", {
            "user_id": user.id,
            "role_id": faculty_role.id,
            "institution_id": registration.institution_id,
        })
        db.insert("faculty_profiles", {
            "user_id": user.id,
            "institution_id": registration.institution_id,
            "employee_id": registration.employee_id,
            "designation": registration.designation,
            "department": registration.department,
            "qualification": registration.qualification,
        })

    registration = db.update(registration, {
        "status": review.status,
        "reviewed_by_id": current_user.id,
        "review_comments": review.review_comments,
    })
    return _response(registration)
