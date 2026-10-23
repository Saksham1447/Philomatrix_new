from datetime import date, datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel


class AssignmentCreate(BaseModel):
    division_id: str
    subject_id: str
    title: str
    description: Optional[str] = None
    due_date: datetime
    attachment_url: Optional[str] = None


class AssignmentResponse(BaseModel):
    id: str
    division_id: str
    division_name: str
    class_name: str
    subject_id: str
    subject_name: str
    faculty_name: str
    title: str
    description: Optional[str] = None
    due_date: datetime
    attachment_url: Optional[str] = None
    created_at: datetime
    is_submitted_by_student: bool = False
    submission_status: Optional[str] = None

    class Config:
        from_attributes = True


class AssignmentSubmissionRequest(BaseModel):
    submission_text: Optional[str] = None
    attachment_url: Optional[str] = None


class NoticeCreate(BaseModel):
    title: str
    content: str
    audience_role: str = "ALL"  # ALL, FACULTY, STUDENT, PARENT
    target_class_id: Optional[str] = None
    target_division_id: Optional[str] = None
    priority: str = "NORMAL"  # LOW, NORMAL, URGENT
    expires_at: Optional[date] = None


class NoticeResponse(BaseModel):
    id: str
    title: str
    content: str
    audience_role: str
    target_class_id: Optional[str] = None
    target_division_id: Optional[str] = None
    priority: str
    published_by_name: Optional[str] = None
    created_at: datetime
    expires_at: Optional[date] = None

    class Config:
        from_attributes = True


class FeedbackQuestionCreate(BaseModel):
    question_text: str
    question_type: str = "RATING_1_5"  # RATING_1_5, TEXT
    display_order: int = 1


class FeedbackQuestionResponse(BaseModel):
    id: str
    question_text: str
    question_type: str
    display_order: int

    class Config:
        from_attributes = True


class FeedbackFormCreate(BaseModel):
    title: str
    target_role: str = "STUDENT"
    is_anonymous: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    questions: List[FeedbackQuestionCreate] = []


class FeedbackFormResponse(BaseModel):
    id: str
    title: str
    target_role: str
    is_anonymous: bool
    is_open: bool
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    questions: List[FeedbackQuestionResponse] = []

    class Config:
        from_attributes = True


class FeedbackAnswerInput(BaseModel):
    question_id: str
    rating_value: Optional[int] = None
    text_response: Optional[str] = None


class FeedbackSubmitRequest(BaseModel):
    answers: List[FeedbackAnswerInput]


class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    notification_type: str
    is_read: bool
    link_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str
    user_name: Optional[str] = None
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
