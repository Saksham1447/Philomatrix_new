from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, get_db, get_tenant_session_factory
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.core.deps import get_current_user
from app.models.user import User, Role, UserRoleAssignment, RefreshTokenRecord, UserPreference
from app.models.institution import Institution
from app.schemas.auth import (
    LoginRequest,
    Token,
    RefreshRequest,
    UserProfileResponse,
    PasswordChangeRequest,
    UserPreferenceSchema,
    UserPreferenceUpdate,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return access & refresh JWT tokens."""
    if request.institution_id:
        from app.core.database import get_tenant_session_factory
        control_db = SessionLocal()
        try:
            selected = control_db.query(Institution).filter(Institution.id == request.institution_id).first()
            if not selected or selected.status != "ACTIVE":
                raise HTTPException(status_code=403, detail="Selected institute is not available")
            if selected.database_url:
                db.close()
                db = get_tenant_session_factory(selected.database_url)()
        finally:
            control_db.close()
    identity = request.username_or_email.strip()
    user = (
        db.query(User)
        .filter((User.username == identity) | (User.email == identity))
        .first()
    )
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact your institution administrator."
        )
    if request.institution_id and user.institution_id != request.institution_id:
        raise HTTPException(status_code=401, detail="These credentials do not belong to the selected institute")

    # Fetch user roles
    roles = (
        db.query(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .filter(UserRoleAssignment.user_id == user.id)
        .all()
    )
    role_names = [r[0] for r in roles]

    claims = {
        "institution_id": user.institution_id,
        "roles": role_names,
        "username": user.username,
        "full_name": user.full_name,
    }

    access_token = create_access_token(subject=user.id, claims=claims)
    refresh_token = create_refresh_token(subject=user.id)

    # Store refresh token record
    token_record = RefreshTokenRecord(
        user_id=user.id,
        token_hash=get_password_hash(refresh_token[-20:]),  # store hash of suffix
        expires_at=datetime.now(timezone.utc),
        is_revoked=False
    )
    db.add(token_record)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    """Issue a new access token using a valid refresh token."""
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    roles = (
        db.query(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .filter(UserRoleAssignment.user_id == user.id)
        .all()
    )
    role_names = [r[0] for r in roles]

    claims = {
        "institution_id": user.institution_id,
        "roles": role_names,
        "username": user.username,
        "full_name": user.full_name,
    }

    access_token = create_access_token(subject=user.id, claims=claims)
    return Token(access_token=access_token, refresh_token=request.refresh_token)


@router.get("/me", response_model=UserProfileResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the profile, roles, and linked entities of current authenticated user."""
    roles = (
        db.query(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .filter(UserRoleAssignment.user_id == current_user.id)
        .all()
    )
    role_names = [r[0] for r in roles]

    inst_name = None
    if current_user.institution_id:
        inst = db.query(Institution).filter(Institution.id == current_user.institution_id).first()
        if inst:
            inst_name = inst.name

    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        full_name=current_user.full_name,
        phone_number=current_user.phone_number,
        institution_id=current_user.institution_id,
        institution_name=inst_name,
        roles=role_names,
        is_active=current_user.is_active,
        student_id=current_user.student_profile.id if current_user.student_profile else None,
        faculty_id=current_user.faculty_profile.id if current_user.faculty_profile else None,
        guardian_id=current_user.guardian_profile.id if current_user.guardian_profile else None,
    )


@router.put("/password")
def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change current user's password."""
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
    
    current_user.password_hash = get_password_hash(request.new_password)
    db.commit()
    return {"message": "Password updated successfully"}


@router.get("/preferences", response_model=UserPreferenceSchema)
def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve user-specific personal preferences."""
    pref = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    if not pref:
        pref = UserPreference(
            user_id=current_user.id,
            dashboard_layout="STANDARD",
            attendance_table_density="COMFORTABLE",
            notify_email=True,
            notify_in_app=True,
            theme_mode="LIGHT"
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


@router.put("/preferences", response_model=UserPreferenceSchema)
def update_user_preferences(
    update_data: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user-specific personal preferences."""
    pref = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    if not pref:
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(pref, field, value)

    db.commit()
    db.refresh(pref)
    return pref
