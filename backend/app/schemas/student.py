from datetime import date
from typing import List, Optional
from pydantic import BaseModel, EmailStr


class GuardianCreate(BaseModel):
    username: Optional[str] = None
    email: EmailStr
    password: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    phone_number: str
    relationship_type: str = "FATHER"  # FATHER, MOTHER, LEGAL_GUARDIAN
    occupation: Optional[str] = None


class GuardianResponse(BaseModel):
    id: str
    user_id: str
    full_name: str
    email: str
    phone_number: Optional[str] = None
    relationship_type: str
    occupation: Optional[str] = None

    class Config:
        from_attributes = True


class StudentCreate(BaseModel):
    # User fields
    username: Optional[str] = None
    email: EmailStr
    password: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    phone_number: Optional[str] = None

    # Student specific fields
    admission_number: str
    date_of_birth: date
    gender: str
    blood_group: Optional[str] = None
    admission_date: date
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    # Initial enrollment
    academic_year_id: str
    class_id: str
    division_id: str
    roll_number: Optional[str] = None

    # Optional guardian to create & link simultaneously
    guardian: Optional[GuardianCreate] = None


class StudentResponse(BaseModel):
    id: str
    user_id: str
    admission_number: str
    roll_number: Optional[str] = None
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    full_name: str
    email: str
    phone_number: Optional[str] = None
    date_of_birth: date
    gender: str
    blood_group: Optional[str] = None
    admission_date: date
    address: Optional[str] = None
    status: str
    class_name: Optional[str] = None
    division_name: Optional[str] = None
    division_id: Optional[str] = None
    academic_year_name: Optional[str] = None
    guardians: List[GuardianResponse] = []

    class Config:
        from_attributes = True


class LinkGuardianRequest(BaseModel):
    guardian_id: str
    is_primary: bool = True
