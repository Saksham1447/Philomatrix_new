from typing import List, Optional, Generator
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.database import get_db as get_database_session
from app.core.security import decode_token
from app.models.user import User, Role, UserRoleAssignment
from app.models.institution import Institution

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db(request: Request) -> Generator[Session, None, None]:
    """Dependency that provides a thread-local database session."""
    yield from get_database_session(request)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Validate access token and return the authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: Optional[str] = payload.get("sub")
        token_type: Optional[str] = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    return user


class RoleChecker:
    """Dependency for server-side role-based authorization."""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        user_roles = (
            db.query(Role.name)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .filter(UserRoleAssignment.user_id == current_user.id)
            .all()
        )
        role_names = [r[0] for r in user_roles]

        # SUPER_ADMIN has access to administrative endpoints unless tenant-restricted
        if "SUPER_ADMIN" in role_names and "SUPER_ADMIN" in self.allowed_roles:
            return current_user

        has_permission = any(role in self.allowed_roles for role in role_names)
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {', '.join(self.allowed_roles)}"
            )
        return current_user


def require_roles(*roles: str) -> RoleChecker:
    return RoleChecker(list(roles))


from app.models.student import Student, StudentGuardianLink


def verify_institution_access(
    institution_id: str,
    current_user: User,
    db: Session
) -> Institution:
    """Ensure that the user belongs to the institution or is a SUPER_ADMIN."""
    # Check if SUPER_ADMIN
    is_super = (
        db.query(UserRoleAssignment)
        .join(Role)
        .filter(UserRoleAssignment.user_id == current_user.id, Role.name == "SUPER_ADMIN")
        .first()
    )
    if is_super:
        inst = db.query(Institution).filter(Institution.id == institution_id).first()
        if not inst:
            raise HTTPException(status_code=404, detail="Institution not found")
        return inst

    if current_user.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cross-institution data access is strictly forbidden"
        )

    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    if inst.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Institution is currently {inst.status.lower()}"
        )
    return inst


def verify_student_access(
    student_id: str,
    current_user: User,
    db: Session
) -> Student:
    """
    Validate server-side access to a specific student record:
    1. Cross-tenant isolation
    2. Student self-access check
    3. Guardian-child verified link check
    4. Staff/Faculty/Principal institution membership check
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Super admin platform check
    is_super = (
        db.query(UserRoleAssignment)
        .join(Role)
        .filter(UserRoleAssignment.user_id == current_user.id, Role.name == "SUPER_ADMIN")
        .first()
    )
    if not is_super and current_user.institution_id != student.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cross-institution student record access is strictly forbidden"
        )

    # 1. Student can only access their own record
    if current_user.student_profile:
        if current_user.student_profile.id != student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security Violation: Students can only access their own records"
            )
        return student

    # 2. Guardian must have a verified link with this student
    if current_user.guardian_profile:
        link = (
            db.query(StudentGuardianLink)
            .filter(
                StudentGuardianLink.guardian_id == current_user.guardian_profile.id,
                StudentGuardianLink.student_id == student_id,
                StudentGuardianLink.is_verified == True
            )
            .first()
        )
        if not link:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security Violation: You are not authorized to view this student's records"
            )
        return student

    # 3. Faculty / Principal / Office Staff
    return student
