from typing import Optional
from pydantic import BaseModel, EmailStr


class StaffCreate(BaseModel):
    username: Optional[str] = None
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone_number: Optional[str] = None


class StaffResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    full_name: str
    phone_number: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True
