from datetime import date, datetime
from typing import List, Optional, Any, Dict
from decimal import Decimal
from pydantic import BaseModel


class ExamSubjectCreate(BaseModel):
    subject_id: str
    class_id: str
    max_theory_marks: Decimal = Decimal("70.00")
    max_practical_marks: Decimal = Decimal("30.00")
    min_passing_marks: Decimal = Decimal("35.00")
    exam_date: Optional[date] = None


class ExamSubjectResponse(BaseModel):
    id: str
    subject_id: str
    subject_name: str
    subject_code: str
    class_id: str
    class_name: str
    max_theory_marks: Decimal
    max_practical_marks: Decimal
    min_passing_marks: Decimal
    exam_date: Optional[date] = None

    class Config:
        from_attributes = True


class ExaminationCreate(BaseModel):
    academic_year_id: str
    name: str  # e.g., "Unit Test 1"
    exam_type: str = "UNIT_TEST"  # UNIT_TEST, TERMINAL, PRACTICAL, PRELIM, FINAL
    start_date: date
    end_date: date
    subjects: List[ExamSubjectCreate] = []


class ExaminationResponse(BaseModel):
    id: str
    academic_year_id: str
    name: str
    exam_type: str
    start_date: date
    end_date: date
    status: str
    is_published: bool = False
    subjects: List[ExamSubjectResponse] = []

    class Config:
        from_attributes = True


class MarksEntryInput(BaseModel):
    student_id: str
    theory_marks_obtained: Optional[Decimal] = None
    practical_marks_obtained: Optional[Decimal] = None
    is_absent: bool = False
    is_exempt: bool = False
    teacher_remarks: Optional[str] = None


class MarksBatchSaveRequest(BaseModel):
    exam_subject_id: str
    division_id: str
    entries: List[MarksEntryInput]
    submit_for_approval: bool = False  # False = save draft, True = submit


class MarksEntryResponse(BaseModel):
    id: str
    student_id: str
    student_name: str
    admission_number: str
    roll_number: Optional[str] = None
    theory_marks_obtained: Optional[Decimal] = None
    practical_marks_obtained: Optional[Decimal] = None
    total_obtained: Optional[Decimal] = None
    is_absent: bool
    is_exempt: bool
    status: str
    teacher_remarks: Optional[str] = None

    class Config:
        from_attributes = True


class MarksApprovalResponse(BaseModel):
    id: str
    exam_subject_id: str
    examination_name: str
    subject_name: str
    subject_code: str
    division_id: str
    division_name: str
    class_name: str
    submitted_by_name: str
    submitted_at: datetime
    status: str  # PENDING, APPROVED, REJECTED
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comments: Optional[str] = None

    class Config:
        from_attributes = True


class MarksApprovalReviewRequest(BaseModel):
    approved: bool
    review_comments: Optional[str] = None


class ReportCardSubjectScore(BaseModel):
    subject_code: str
    subject_name: str
    theory_max: Decimal
    theory_obtained: Optional[Decimal] = None
    practical_max: Decimal
    practical_obtained: Optional[Decimal] = None
    total_max: Decimal
    total_obtained: Optional[Decimal] = None
    percentage: Decimal
    grade: str
    status: str  # PASS, FAIL, ABSENT, EXEMPT


class ReportCardData(BaseModel):
    institution_name: str
    institution_address: Optional[str] = None
    institution_code: str
    institution_logo_url: Optional[str] = None
    academic_year: str
    examination_name: str
    examination_type: str
    student_name: str
    admission_number: str
    roll_number: Optional[str] = None
    class_name: str
    division_name: str
    stream: str
    attendance_percentage: Decimal
    total_conducted_lectures: int
    total_attended_lectures: int
    subjects: List[ReportCardSubjectScore]
    grand_total_max: Decimal
    grand_total_obtained: Decimal
    overall_percentage: Decimal
    overall_grade: str
    final_result: str
    teacher_remarks: Optional[str] = None
    principal_remarks: Optional[str] = None
    published_date: Optional[date] = None
