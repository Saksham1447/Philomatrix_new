from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel


class AttendanceRecordInput(BaseModel):
    student_id: str
    status: str  # PRESENT, ABSENT, LATE, EXCUSED
    remarks: Optional[str] = None


class AttendanceSessionSubmit(BaseModel):
    timetable_entry_id: Optional[str] = None
    division_id: str
    subject_id: str
    session_date: date
    period_number: int
    submission_status: Optional[str] = "SUBMITTED"  # "DRAFT" or "SUBMITTED"
    records: List[AttendanceRecordInput]



class AttendanceRecordResponse(BaseModel):
    id: str
    student_id: str
    student_name: str
    admission_number: str
    roll_number: Optional[str] = None
    status: str
    remarks: Optional[str] = None

    class Config:
        from_attributes = True


class AttendanceSessionResponse(BaseModel):
    id: str
    division_id: str
    division_name: str
    class_name: str
    subject_id: str
    subject_name: str
    faculty_id: str
    faculty_name: str
    session_date: date
    period_number: int
    submission_status: str
    total_students: int
    present_count: int
    absent_count: int
    records: List[AttendanceRecordResponse] = []

    class Config:
        from_attributes = True


class SubjectAttendanceStat(BaseModel):
    subject_id: str
    subject_code: str
    subject_name: str
    total_conducted: int
    total_attended: int
    percentage: Decimal


class StudentAttendanceSummary(BaseModel):
    student_id: str
    student_name: str
    admission_number: str
    class_name: str
    division_name: str
    total_conducted: int
    total_attended: int
    overall_percentage: Decimal
    is_below_threshold: bool
    subject_breakdown: List[SubjectAttendanceStat]


class AttendanceCorrectionCreate(BaseModel):
    attendance_record_id: str
    requested_status: str
    reason: str


class AttendanceCorrectionResponse(BaseModel):
    id: str
    attendance_record_id: str
    student_name: str
    admission_number: str
    division_name: str
    subject_name: str
    session_date: date
    period_number: int
    previous_status: str
    requested_status: str
    reason: str
    status: str  # PENDING, APPROVED, REJECTED
    requested_by_name: str
    created_at: datetime
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None

    class Config:
        from_attributes = True


class AttendanceCorrectionReview(BaseModel):
    approved: bool
    review_notes: Optional[str] = None
