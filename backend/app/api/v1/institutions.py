from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import (
    get_tenant_store,
    invalidate_institution_cache,
    provision_tenant_database,
)
from app.core.deps import get_current_user, get_db, require_roles
from app.core.docstore import Doc, DocStore, UserDoc
from app.core.security import get_password_hash
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionResponse,
    InstitutionSettingResponse,
    InstitutionSettingUpdate,
    InstitutionUpdate,
)
from app.schemas.staff import StaffCreate, StaffResponse

router = APIRouter(prefix="/institutions", tags=["Institutions & Multi-Tenancy"])


def _with_settings(db: DocStore, institution: Doc) -> dict:
    """Include the SQL-era one-to-one settings relationship in API responses."""
    result = dict(institution)
    result["settings"] = db.find_one("institution_settings", {"institution_id": institution.id})
    return result


@router.get("/{id}/staff", response_model=List[StaffResponse])
def list_institution_staff(
    id: str,
    current_user: UserDoc = Depends(require_roles("PRINCIPAL", "OFFICE_STAFF", "SUPER_ADMIN")),
    db: DocStore = Depends(get_db),
):
    """List office staff belonging to the caller's institute."""
    if "SUPER_ADMIN" not in current_user.role_names and current_user.institution_id != id:
        raise HTTPException(status_code=403, detail="Access denied to this institute")
    staff_role = db.find_one("roles", {"name": "OFFICE_STAFF"})
    if not staff_role:
        return []
    assignments = db.find("user_role_assignments", {"role_id": staff_role.id})
    users = db.find(
        "users",
        {
            "institution_id": id,
            "id": {"$in": [assignment.user_id for assignment in assignments]},
        },
        sort=[("first_name", 1), ("last_name", 1)],
    )
    return [
        StaffResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            middle_name=user.middle_name,
            last_name=user.last_name,
            full_name=user.full_name,
            phone_number=user.phone_number,
            is_active=user.is_active,
        )
        for user in users
    ]


@router.post("/{id}/staff", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
def create_institution_staff(
    id: str,
    request: StaffCreate,
    current_user: UserDoc = Depends(require_roles("PRINCIPAL", "SUPER_ADMIN")),
    db: DocStore = Depends(get_db),
):
    """Create an office staff account inside the selected institute database."""
    if "SUPER_ADMIN" not in current_user.role_names and current_user.institution_id != id:
        raise HTTPException(status_code=403, detail="Access denied to this institute")
    if db.find_one("users", {"$or": [{"username": request.email}, {"email": request.email}]}):
        raise HTTPException(status_code=400, detail="Username or email already in use")
    role = db.find_one("roles", {"name": "OFFICE_STAFF"})
    if not role:
        role = db.insert("roles", {
            "name": "OFFICE_STAFF",
            "description": "Institution office and admissions staff",
        })

    user = db.insert("users", {
        "institution_id": id,
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
    db.insert("user_role_assignments", {
        "user_id": user.id,
        "role_id": role.id,
        "institution_id": id,
    })
    return StaffResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        middle_name=user.middle_name,
        last_name=user.last_name,
        full_name=user.full_name,
        phone_number=user.phone_number,
        is_active=user.is_active,
    )


@router.get("/public", response_model=List[InstitutionResponse])
def list_public_institutions(db: DocStore = Depends(get_db)):
    """List active institutes available on the login screen."""
    institutions = db.find("institutions", {"status": "ACTIVE"}, sort=[("name", 1)])
    return [_with_settings(db, institution) for institution in institutions]


@router.get("", response_model=List[InstitutionResponse])
def list_institutions(
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN")),
    db: DocStore = Depends(get_db),
):
    """[SUPER_ADMIN] List all institution tenants."""
    return [_with_settings(db, institution) for institution in db.find("institutions")]


@router.post("", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED)
def create_institution(
    request: InstitutionCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN")),
    db: DocStore = Depends(get_db),
):
    """[SUPER_ADMIN] Provision a new institution tenant."""
    if db.find_one("institutions", {"code": request.code}):
        raise HTTPException(status_code=400, detail="Institution code already exists")
    if db.find_one("institutions", {"slug": request.slug}):
        raise HTTPException(status_code=400, detail="Institution slug already exists")

    institution = db.insert("institutions", {
        "name": request.name,
        "code": request.code,
        "slug": request.slug,
        "address": request.address,
        "city": request.city,
        "state": request.state,
        "pincode": request.pincode,
        "phone": request.phone,
        "email": request.email,
        "logo_url": request.logo_url,
        "institution_type": request.institution_type,
        "status": "ACTIVE",
    })
    db.insert("institution_settings", {
        "institution_id": institution.id,
        "min_attendance_threshold": 75.00,
        "allow_late_as_present": True,
        "enable_parent_sms_alerts": False,
        "report_card_template_id": "STANDARD_V1",
        "institution_type": request.institution_type,
    })
    try:
        database_name = provision_tenant_database(
            institution,
            principal_email=request.principal_email,
            principal_password=request.principal_password,
            principal_first_name=request.principal_first_name,
            principal_middle_name=request.principal_middle_name,
            principal_last_name=request.principal_last_name,
        )
        institution = db.update(institution, {"database_url": database_name})
        invalidate_institution_cache(institution.id)
    except Exception as exc:
        db.delete("institutions", institution)
        invalidate_institution_cache(institution.id)
        raise HTTPException(status_code=500, detail=f"Unable to provision institute database: {exc}") from exc
    return _with_settings(db, institution)


@router.get("/{id}", response_model=InstitutionResponse)
def get_institution(
    id: str,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """Get single institution profile (SUPER_ADMIN or member of institution)."""
    if "SUPER_ADMIN" not in current_user.role_names and current_user.institution_id != id:
        raise HTTPException(status_code=403, detail="Access denied to other institution's data")

    institution = db.get("institutions", id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    return _with_settings(db, institution)


@router.put("/{id}", response_model=InstitutionResponse)
def update_institution(
    id: str,
    request: InstitutionUpdate,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """Update institution profile and branding."""
    is_super_admin = "SUPER_ADMIN" in current_user.role_names
    if not is_super_admin and ("PRINCIPAL" not in current_user.role_names or current_user.institution_id != id):
        raise HTTPException(status_code=403, detail="Unauthorized to update institution settings")

    institution = db.get("institutions", id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    changes = request.model_dump(exclude_unset=True)
    if changes:
        institution = db.update(institution, changes)
        invalidate_institution_cache(id)
    if institution.database_url:
        tenant_db = get_tenant_store(institution.database_url)
        tenant_institution = tenant_db.get("institutions", id)
        if tenant_institution and changes:
            tenant_db.update(tenant_institution, changes)
    return _with_settings(db, institution)


@router.put("/{id}/status")
def set_institution_status(
    id: str,
    new_status: str,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN")),
    db: DocStore = Depends(get_db),
):
    """[SUPER_ADMIN] Toggle institution status (ACTIVE, SUSPENDED, DEACTIVATED)."""
    if new_status not in ["ACTIVE", "SUSPENDED", "DEACTIVATED"]:
        raise HTTPException(status_code=400, detail="Invalid status value")

    institution = db.get("institutions", id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    db.update(institution, {"status": new_status})
    invalidate_institution_cache(id)
    return {"message": f"Institution status changed to {new_status}"}


@router.get("/{id}/settings", response_model=InstitutionSettingResponse)
def get_institution_settings(
    id: str,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """Get operational settings for an institution."""
    if "SUPER_ADMIN" not in current_user.role_names and current_user.institution_id != id:
        raise HTTPException(status_code=403, detail="Access denied to other institution settings")

    settings_doc = db.find_one("institution_settings", {"institution_id": id})
    if not settings_doc:
        settings_doc = db.insert("institution_settings", {
            "institution_id": id,
            "min_attendance_threshold": 75.00,
            "allow_late_as_present": True,
            "enable_parent_sms_alerts": False,
            "report_card_template_id": "STANDARD_V1",
        })
    return settings_doc


@router.put("/{id}/settings", response_model=InstitutionSettingResponse)
def update_institution_settings(
    id: str,
    request: InstitutionSettingUpdate,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """[PRINCIPAL | SUPER_ADMIN] Update institution operational policies."""
    role_names = current_user.role_names
    if "SUPER_ADMIN" not in role_names and ("PRINCIPAL" not in role_names or current_user.institution_id != id):
        raise HTTPException(status_code=403, detail="Unauthorized to modify institution settings")

    settings_doc = db.find_one("institution_settings", {"institution_id": id})
    if not settings_doc:
        settings_doc = db.insert("institution_settings", {"institution_id": id})

    previous_state = {
        "min_attendance_threshold": float(settings_doc.min_attendance_threshold),
        "allow_late_as_present": settings_doc.allow_late_as_present,
        "enable_parent_sms_alerts": settings_doc.enable_parent_sms_alerts,
        "report_card_template_id": settings_doc.report_card_template_id,
    }
    changes = request.model_dump(exclude_unset=True)
    if changes:
        settings_doc = db.update(settings_doc, changes)
    new_state = {
        key: float(value) if isinstance(value, Decimal) else value
        for key, value in changes.items()
    }

    db.insert("audit_logs", {
        "institution_id": id,
        "user_id": current_user.id,
        "action": "INSTITUTION_SETTINGS_UPDATED",
        "entity_type": "institution_settings",
        "entity_id": settings_doc.id if settings_doc.id else id,
        "previous_state": previous_state,
        "new_state": new_state,
        "reason": "Administrative Policy Revision",
    })
    return settings_doc
