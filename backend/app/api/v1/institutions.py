from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db, get_tenant_session_factory, provision_tenant_database
from app.core.deps import get_current_user, require_roles
from app.models.user import User, Role, UserRoleAssignment
from app.models.institution import Institution, InstitutionSetting
from app.models.communication import AuditLog
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionUpdate,
    InstitutionResponse,
    InstitutionSettingResponse,
    InstitutionSettingUpdate,
)
from app.schemas.staff import StaffCreate, StaffResponse
from app.core.security import get_password_hash

router = APIRouter(prefix="/institutions", tags=["Institutions & Multi-Tenancy"])


@router.get("/{id}/staff", response_model=List[StaffResponse])
def list_institution_staff(
    id: str,
    current_user: User = Depends(require_roles("PRINCIPAL", "OFFICE_STAFF", "SUPER_ADMIN")),
    db: Session = Depends(get_db),
):
    """List office staff belonging to the caller's institute."""
    if "SUPER_ADMIN" not in [assignment.role.name for assignment in current_user.role_assignments] and current_user.institution_id != id:
        raise HTTPException(status_code=403, detail="Access denied to this institute")
    staff_role = db.query(Role).filter(Role.name == "OFFICE_STAFF").first()
    if not staff_role:
        return []
    users = (
        db.query(User)
        .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
        .filter(User.institution_id == id, UserRoleAssignment.role_id == staff_role.id)
        .order_by(User.first_name, User.last_name)
        .all()
    )
    return [StaffResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        phone_number=user.phone_number,
        is_active=user.is_active,
    ) for user in users]


@router.post("/{id}/staff", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
def create_institution_staff(
    id: str,
    request: StaffCreate,
    current_user: User = Depends(require_roles("PRINCIPAL", "SUPER_ADMIN")),
    db: Session = Depends(get_db),
):
    """Create an office staff account inside the selected institute database."""
    if "SUPER_ADMIN" not in [assignment.role.name for assignment in current_user.role_assignments] and current_user.institution_id != id:
        raise HTTPException(status_code=403, detail="Access denied to this institute")
    if db.query(User).filter((User.username == request.email) | (User.email == request.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already in use")
    role = db.query(Role).filter(Role.name == "OFFICE_STAFF").first()
    if not role:
        role = Role(name="OFFICE_STAFF", description="Institution office and admissions staff")
        db.add(role)
        db.flush()
    user = User(
        institution_id=id,
        username=request.email,
        email=request.email,
        password_hash=get_password_hash(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        phone_number=request.phone_number,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()
    db.add(UserRoleAssignment(user_id=user.id, role_id=role.id, institution_id=id))
    db.commit()
    db.refresh(user)
    return StaffResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        phone_number=user.phone_number,
        is_active=user.is_active,
    )

@router.get("/public", response_model=List[InstitutionResponse])
def list_public_institutions(db: Session = Depends(get_db)):
    """List active institutes available on the login screen."""
    return db.query(Institution).filter(Institution.status == "ACTIVE").order_by(Institution.name).all()


@router.get("", response_model=List[InstitutionResponse])
def list_institutions(
    current_user: User = Depends(require_roles("SUPER_ADMIN")),
    db: Session = Depends(get_db)
):
    """[SUPER_ADMIN] List all institution tenants."""
    return db.query(Institution).all()


@router.post("", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED)
def create_institution(
    request: InstitutionCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN")),
    db: Session = Depends(get_db)
):
    """[SUPER_ADMIN] Provision a new institution tenant."""
    existing_code = db.query(Institution).filter(Institution.code == request.code).first()
    if existing_code:
        raise HTTPException(status_code=400, detail="Institution code already exists")
    existing_slug = db.query(Institution).filter(Institution.slug == request.slug).first()
    if existing_slug:
        raise HTTPException(status_code=400, detail="Institution slug already exists")

    institution = Institution(
        name=request.name,
        code=request.code,
        slug=request.slug,
        address=request.address,
        city=request.city,
        state=request.state,
        pincode=request.pincode,
        phone=request.phone,
        email=request.email,
        logo_url=request.logo_url,
        institution_type=request.institution_type,
        status="ACTIVE"
    )
    db.add(institution)
    db.flush()

    # Create default settings
    settings = InstitutionSetting(
        institution_id=institution.id,
        min_attendance_threshold=75.00,
        allow_late_as_present=True,
        enable_parent_sms_alerts=False,
        report_card_template_id="STANDARD_V1",
        institution_type=request.institution_type
    )
    db.add(settings)
    db.commit()
    db.refresh(institution)
    try:
        institution.database_url = provision_tenant_database(
            institution,
            principal_email=request.principal_email,
            principal_password=request.principal_password,
            principal_first_name=request.principal_first_name,
            principal_last_name=request.principal_last_name,
        )
        db.commit()
        db.refresh(institution)
    except Exception as exc:
        db.delete(institution)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Unable to provision institute database: {exc}") from exc
    return institution


@router.get("/{id}", response_model=InstitutionResponse)
def get_institution(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get single institution profile (SUPER_ADMIN or member of institution)."""
    user_roles = (
        db.query(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .filter(UserRoleAssignment.user_id == current_user.id)
        .all()
    )
    role_names = [r[0] for r in user_roles]

    if "SUPER_ADMIN" not in role_names and current_user.institution_id != id:
        raise HTTPException(status_code=403, detail="Access denied to other institution's data")

    institution = db.query(Institution).filter(Institution.id == id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution


@router.put("/{id}", response_model=InstitutionResponse)
def update_institution(
    id: str,
    request: InstitutionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update institution profile and branding."""
    user_roles = (
        db.query(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .filter(UserRoleAssignment.user_id == current_user.id)
        .all()
    )
    role_names = [r[0] for r in user_roles]

    if "SUPER_ADMIN" not in role_names and ("PRINCIPAL" not in role_names or current_user.institution_id != id):
        raise HTTPException(status_code=403, detail="Unauthorized to update institution settings")

    institution = db.query(Institution).filter(Institution.id == id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(institution, field, value)

    db.commit()
    db.refresh(institution)
    if institution.database_url:
        tenant_db = get_tenant_session_factory(institution.database_url)()
        try:
            tenant_institution = tenant_db.query(Institution).filter(Institution.id == id).first()
            if tenant_institution:
                for field, value in request.model_dump(exclude_unset=True).items():
                    setattr(tenant_institution, field, value)
                tenant_db.commit()
        finally:
            tenant_db.close()
    return institution


@router.put("/{id}/status")
def set_institution_status(
    id: str,
    new_status: str,  # ACTIVE, SUSPENDED, DEACTIVATED
    current_user: User = Depends(require_roles("SUPER_ADMIN")),
    db: Session = Depends(get_db)
):
    """[SUPER_ADMIN] Toggle institution status (ACTIVE, SUSPENDED, DEACTIVATED)."""
    if new_status not in ["ACTIVE", "SUSPENDED", "DEACTIVATED"]:
        raise HTTPException(status_code=400, detail="Invalid status value")

    institution = db.query(Institution).filter(Institution.id == id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    institution.status = new_status
    db.commit()
    return {"message": f"Institution status changed to {new_status}"}


@router.get("/{id}/settings", response_model=InstitutionSettingResponse)
def get_institution_settings(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get operational settings for an institution."""
    user_roles = (
        db.query(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .filter(UserRoleAssignment.user_id == current_user.id)
        .all()
    )
    role_names = [r[0] for r in user_roles]

    if "SUPER_ADMIN" not in role_names and current_user.institution_id != id:
        raise HTTPException(status_code=403, detail="Access denied to other institution settings")

    settings = db.query(InstitutionSetting).filter(InstitutionSetting.institution_id == id).first()
    if not settings:
        settings = InstitutionSetting(
            institution_id=id,
            min_attendance_threshold=75.00,
            allow_late_as_present=True,
            enable_parent_sms_alerts=False,
            report_card_template_id="STANDARD_V1"
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


@router.put("/{id}/settings", response_model=InstitutionSettingResponse)
def update_institution_settings(
    id: str,
    request: InstitutionSettingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL | SUPER_ADMIN] Update institution operational policies (attendance threshold, report card layout, etc.)."""
    user_roles = (
        db.query(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .filter(UserRoleAssignment.user_id == current_user.id)
        .all()
    )
    role_names = [r[0] for r in user_roles]

    if "SUPER_ADMIN" not in role_names and ("PRINCIPAL" not in role_names or current_user.institution_id != id):
        raise HTTPException(status_code=403, detail="Unauthorized to modify institution settings")

    settings = db.query(InstitutionSetting).filter(InstitutionSetting.institution_id == id).first()
    if not settings:
        settings = InstitutionSetting(institution_id=id)
        db.add(settings)

    prev_state = {
        "min_attendance_threshold": float(settings.min_attendance_threshold),
        "allow_late_as_present": settings.allow_late_as_present,
        "enable_parent_sms_alerts": settings.enable_parent_sms_alerts,
        "report_card_template_id": settings.report_card_template_id
    }

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)

    new_state = {
        k: float(v) if isinstance(v, Decimal) else v
        for k, v in request.model_dump(exclude_unset=True).items()
    }

    # Log in audit
    audit = AuditLog(
        institution_id=id,
        user_id=current_user.id,
        action="INSTITUTION_SETTINGS_UPDATED",
        entity_type="institution_settings",
        entity_id=settings.id if hasattr(settings, 'id') and settings.id else id,
        previous_state=prev_state,
        new_state=new_state,
        reason="Administrative Policy Revision"
    )
    db.add(audit)
    db.commit()
    db.refresh(settings)
    return settings
