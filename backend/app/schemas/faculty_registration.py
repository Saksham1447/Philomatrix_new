from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class FacultyRegistrationCreate(BaseModel):
    institution_id: str
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone_number: Optional[str] = None
    employee_id: str = Field(min_length=1, max_length=50)
    designation: str = "Lecturer"
    department: str = "Science"
    qualification: Optional[str] = None


class FacultyRegistrationReview(BaseModel):
    status: str
    review_comments: Optional[str] = None


class FacultyRegistrationResponse(BaseModel):
    id: str
    institution_id: str
    username: str
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    employee_id: str
    designation: str
    department: str
    qualification: Optional[str] = None
    status: str
    review_comments: Optional[str] = None
    created_at: str


class PublicFacultyLoginOption(BaseModel):
    id: str
    full_name: str
    username: str
    email: str
    institution_id: str
    institution_name: str
