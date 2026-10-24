"""FastAPI dependencies for database access and authorization."""
from typing import Generator, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.core.database import get_db as get_database_store
from app.core.docstore import Doc, DocStore, UserDoc
from app.core.security import decode_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db(request: Request) -> Generator[DocStore, None, None]:
    yield from get_database_store(request)


def get_current_user(token: str = Depends(oauth2_scheme), db: DocStore = Depends(get_db)) -> UserDoc:
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

    user = db.get("users", user_id)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated")
    return user


class RoleChecker:
    """Role authorization using the user's lazy, cached role-name helper."""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: UserDoc = Depends(get_current_user), db: DocStore = Depends(get_db)) -> UserDoc:
        role_names = current_user.role_names
        if "SUPER_ADMIN" in role_names and "SUPER_ADMIN" in self.allowed_roles:
            return current_user
        if not any(role in self.allowed_roles for role in role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {', '.join(self.allowed_roles)}",
            )
        return current_user


def require_roles(*roles: str) -> RoleChecker:
    return RoleChecker(list(roles))


def verify_institution_access(institution_id: str, current_user: UserDoc, db: DocStore) -> Doc:
    """Ensure user belongs to the institution or is a SUPER_ADMIN."""
    is_super = "SUPER_ADMIN" in current_user.role_names
    institution = db.get("institutions", institution_id)
    if is_super:
        if institution is None:
            raise HTTPException(status_code=404, detail="Institution not found")
        return institution
    if current_user.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cross-institution data access is strictly forbidden",
        )
    if institution is None:
        raise HTTPException(status_code=404, detail="Institution not found")
    if institution.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Institution is currently {institution.status.lower()}")
    return institution


def verify_student_access(student_id: str, current_user: UserDoc, db: DocStore) -> Doc:
    """Enforce tenant, student-self, guardian-link, and student-existence checks."""
    student = db.get("students", student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    is_super = "SUPER_ADMIN" in current_user.role_names
    if not is_super and current_user.institution_id != student.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cross-institution student record access is strictly forbidden",
        )
    if current_user.student_profile:
        if current_user.student_profile.id != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Security Violation: Students can only access their own records")
        return student
    if current_user.guardian_profile:
        link = db.find_one("student_guardian_links", {
            "guardian_id": current_user.guardian_profile.id,
            "student_id": student_id,
            "is_verified": True,
        })
        if link is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Security Violation: You are not authorized to view this student's records")
    return student
