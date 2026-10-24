from typing import List, Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class LoginRequest(BaseModel):
    username_or_email: str
    password: str
    institution_id: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfileResponse(BaseModel):
    id: str
    username: str
    # Local platform accounts may intentionally use reserved development domains
    # such as .local, so profile responses must preserve the stored address.
    email: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    full_name: str
    phone_number: Optional[str] = None
    profile_photo_url: Optional[str] = None
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    roles: List[str]
    is_active: bool
    student_id: Optional[str] = None
    faculty_id: Optional[str] = None
    guardian_id: Optional[str] = None

    class Config:
        from_attributes = True


class ProfileUpdateRequest(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    email: str
    phone_number: Optional[str] = None
    profile_photo_url: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class UserPreferenceSchema(BaseModel):
    dashboard_layout: str = "STANDARD"
    default_division_id: Optional[str] = None
    default_subject_id: Optional[str] = None
    attendance_table_density: str = "COMFORTABLE"
    notify_email: bool = True
    notify_in_app: bool = True
    theme_mode: str = "LIGHT"

    class Config:
        from_attributes = True


class UserPreferenceUpdate(BaseModel):
    dashboard_layout: Optional[str] = None
    default_division_id: Optional[str] = None
    default_subject_id: Optional[str] = None
    attendance_table_density: Optional[str] = None
    notify_email: Optional[bool] = None
    notify_in_app: Optional[bool] = None
    theme_mode: Optional[str] = None
