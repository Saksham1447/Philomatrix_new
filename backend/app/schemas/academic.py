from datetime import date
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, EmailStr


class AcademicYearCreate(BaseModel):
    name: str  # e.g., "2026-2027"
    start_date: date
    end_date: date
    is_current: bool = False


class AcademicYearResponse(BaseModel):
    id: str
    name: str
    start_date: date
    end_date: date
    is_current: bool
    is_archived: bool

    class Config:
        from_attributes = True


class DivisionResponse(BaseModel):
    id: str
    class_id: str
    name: str
    room_number: Optional[str] = None
    capacity: int

    class Config:
        from_attributes = True


class DivisionCreate(BaseModel):
    class_id: str
    name: str
    room_number: Optional[str] = None
    capacity: int = 60


class ClassCreate(BaseModel):
    name: str
    stream: str = "GENERAL"
    display_order: int = 1
    divisions: List[str] = []


class ClassResponse(BaseModel):
    id: str
    name: str
    stream: str
    display_order: int
    divisions: List[DivisionResponse] = []

    class Config:
        from_attributes = True


class SubjectCreate(BaseModel):
    code: str
    name: str
    stream: str = "GENERAL"
    has_practical: bool = True
    max_theory_marks: Decimal = Decimal("70.00")
    max_practical_marks: Decimal = Decimal("30.00")
    min_pass_percentage: Decimal = Decimal("35.00")


class SubjectResponse(BaseModel):
    id: str
    code: str
    name: str
    stream: str
    has_practical: bool
    max_theory_marks: Decimal
    max_practical_marks: Decimal
    min_pass_percentage: Decimal

    class Config:
        from_attributes = True


class FacultyCreate(BaseModel):
    username: Optional[str] = None
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    employee_id: str
    designation: str = "Lecturer"
    department: str = "General"
    qualification: Optional[str] = None


class FacultyResponse(BaseModel):
    id: str
    user_id: str
    employee_id: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone_number: Optional[str] = None
    designation: str
    department: str
    qualification: Optional[str] = None

    class Config:
        from_attributes = True


class FacultyAssignmentCreate(BaseModel):
    academic_year_id: str
    faculty_id: str
    subject_id: str
    division_id: str
    is_class_teacher: bool = False


class FacultyAssignmentResponse(BaseModel):
    id: str
    academic_year_id: str
    faculty_id: str
    faculty_name: str
    subject_id: str
    subject_name: str
    subject_code: str
    division_id: str
    division_name: str
    class_name: str
    is_class_teacher: bool

    class Config:
        from_attributes = True
