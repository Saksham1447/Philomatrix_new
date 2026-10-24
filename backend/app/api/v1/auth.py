from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_control_store, get_tenant_store
from app.core.deps import get_current_user, get_db
from app.core.docstore import DocStore, UserDoc
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    RefreshRequest,
    Token,
    UserPreferenceSchema,
    UserPreferenceUpdate,
    UserProfileResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: DocStore = Depends(get_db)):
    """Authenticate user and return access & refresh JWT tokens."""
    if request.institution_id:
        selected = get_control_store().find_one(
            "institutions",
            {"id": request.institution_id, "status": "ACTIVE"},
        )
        if not selected:
            raise HTTPException(status_code=403, detail="Selected institute is not available")
        if selected.database_url:
            db = get_tenant_store(selected.database_url)

    identity = request.username_or_email.strip()
    user = db.find_one("users", {"$or": [{"username": identity}, {"email": identity}]})
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact your institution administrator.",
        )
    if request.institution_id and user.institution_id != request.institution_id:
        raise HTTPException(status_code=401, detail="These credentials do not belong to the selected institute")

    role_names = user.role_names
    claims = {
        "institution_id": user.institution_id,
        "roles": role_names,
        "username": user.username,
        "full_name": user.full_name,
    }
    access_token = create_access_token(subject=user.id, claims=claims)
    refresh_token = create_refresh_token(subject=user.id)

    with db.transaction():
        db.insert("refresh_token_records", {
            "user_id": user.id,
            "token_hash": get_password_hash(refresh_token[-20:]),
            "expires_at": datetime.now(timezone.utc),
            "is_revoked": False,
        })
        db.update(user, {"last_login_at": datetime.now(timezone.utc)})
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
def refresh(request: RefreshRequest, db: DocStore = Depends(get_db)):
    """Issue a new access token using a valid refresh token."""
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.find_one("users", {"id": user_id, "is_active": True})
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    claims = {
        "institution_id": user.institution_id,
        "roles": user.role_names,
        "username": user.username,
        "full_name": user.full_name,
    }
    access_token = create_access_token(subject=user.id, claims=claims)
    return Token(access_token=access_token, refresh_token=request.refresh_token)


@router.get("/me", response_model=UserProfileResponse)
def get_me(current_user: UserDoc = Depends(get_current_user), db: DocStore = Depends(get_db)):
    """Return the profile, roles, and linked entities of current authenticated user."""
    institution_name = None
    if current_user.institution_id:
        institution = db.get("institutions", current_user.institution_id)
        if institution:
            institution_name = institution.name

    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        middle_name=current_user.middle_name,
        last_name=current_user.last_name,
        full_name=current_user.full_name,
        phone_number=current_user.phone_number,
        institution_id=current_user.institution_id,
        institution_name=institution_name,
        roles=current_user.role_names,
        is_active=current_user.is_active,
        student_id=current_user.student_profile.id if current_user.student_profile else None,
        faculty_id=current_user.faculty_profile.id if current_user.faculty_profile else None,
        guardian_id=current_user.guardian_profile.id if current_user.guardian_profile else None,
    )


@router.put("/password")
def change_password(
    request: PasswordChangeRequest,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """Change current user's password."""
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    db.update(current_user, {"password_hash": get_password_hash(request.new_password)})
    return {"message": "Password updated successfully"}


@router.get("/preferences", response_model=UserPreferenceSchema)
def get_user_preferences(
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """Retrieve user-specific personal preferences."""
    preference = current_user.preferences
    if not preference:
        preference = db.insert("user_preferences", {"user_id": current_user.id})
    return preference


@router.put("/preferences", response_model=UserPreferenceSchema)
def update_user_preferences(
    update_data: UserPreferenceUpdate,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """Update user-specific personal preferences."""
    preference = db.find_one("user_preferences", {"user_id": current_user.id})
    changes = update_data.model_dump(exclude_unset=True)
    if not preference:
        return db.insert("user_preferences", {"user_id": current_user.id, **changes})
    return db.update(preference, changes) if changes else preference
