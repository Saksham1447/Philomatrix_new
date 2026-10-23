from sqlalchemy import Column, String, SmallInteger, Integer, Boolean, Text, DateTime, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Assignment(BaseModel):
    __tablename__ = "assignments"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    division_id = Column(String(36), ForeignKey("divisions.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    faculty_id = Column(String(36), ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=False)
    attachment_url = Column(Text, nullable=True)

    division = relationship("Division")
    subject = relationship("Subject")
    faculty = relationship("FacultyProfile")
    submissions = relationship("AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan")


class AssignmentSubmission(BaseModel):
    __tablename__ = "assignment_submissions"

    assignment_id = Column(String(36), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_text = Column(Text, nullable=True)
    attachment_url = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False)
    is_late = Column(Boolean, default=False, nullable=False)
    status = Column(String(20), default="SUBMITTED", nullable=False)  # SUBMITTED, REVIEWED
    grade_or_score = Column(String(20), nullable=True)
    feedback_remarks = Column(Text, nullable=True)

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("Student", back_populates="assignment_submissions")


class Notice(BaseModel):
    __tablename__ = "notices"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    audience_role = Column(String(50), default="ALL", nullable=False)  # ALL, FACULTY, STUDENT, PARENT
    target_class_id = Column(String(36), ForeignKey("classes.id", ondelete="SET NULL"), nullable=True)
    target_division_id = Column(String(36), ForeignKey("divisions.id", ondelete="SET NULL"), nullable=True)
    priority = Column(String(20), default="NORMAL", nullable=False)  # LOW, NORMAL, URGENT
    published_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_published = Column(Boolean, default=True, nullable=False)
    expires_at = Column(Date, nullable=True)

    publisher = relationship("User")


class FeedbackForm(BaseModel):
    __tablename__ = "feedback_forms"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    target_role = Column(String(50), default="STUDENT", nullable=False)
    is_anonymous = Column(Boolean, default=True, nullable=False)
    is_open = Column(Boolean, default=True, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    questions = relationship("FeedbackQuestion", back_populates="form", cascade="all, delete-orphan")
    responses = relationship("FeedbackResponse", back_populates="form", cascade="all, delete-orphan")


class FeedbackQuestion(BaseModel):
    __tablename__ = "feedback_questions"

    feedback_form_id = Column(String(36), ForeignKey("feedback_forms.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), default="RATING_1_5", nullable=False)  # RATING_1_5, TEXT
    display_order = Column(Integer, default=1, nullable=False)

    form = relationship("FeedbackForm", back_populates="questions")


class FeedbackResponse(BaseModel):
    __tablename__ = "feedback_responses"

    feedback_form_id = Column(String(36), ForeignKey("feedback_forms.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(String(36), ForeignKey("feedback_questions.id", ondelete="CASCADE"), nullable=False)
    respondent_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rating_value = Column(SmallInteger, nullable=True)
    text_response = Column(Text, nullable=True)

    form = relationship("FeedbackForm", back_populates="responses")


class Notification(BaseModel):
    __tablename__ = "notifications"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), default="GENERAL", nullable=False)  # ATTENDANCE, EXAM, NOTICE, TIMETABLE
    is_read = Column(Boolean, default=False, nullable=False)
    link_url = Column(String(255), nullable=True)


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False)  # e.g., "MARKS_APPROVED", "ATTENDANCE_CORRECTED", "RESULT_PUBLISHED"
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=False)
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)

    user = relationship("User")
