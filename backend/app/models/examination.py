from sqlalchemy import Column, String, Integer, Date, DateTime, Numeric, Boolean, Text, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Examination(BaseModel):
    __tablename__ = "examinations"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(String(36), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g., "Unit Test 1", "First Terminal Exam"
    exam_type = Column(String(50), nullable=False)  # UNIT_TEST, TERMINAL, PRACTICAL, PRELIM, FINAL
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), default="SCHEDULED", nullable=False)  # SCHEDULED, MARKS_ENTRY, UNDER_REVIEW, PUBLISHED

    exam_subjects = relationship("ExamSubject", back_populates="examination", cascade="all, delete-orphan")
    result_publications = relationship("ResultPublication", back_populates="examination", cascade="all, delete-orphan")
    report_cards = relationship("ReportCardVersion", back_populates="examination", cascade="all, delete-orphan")


class ExamSubject(BaseModel):
    __tablename__ = "exam_subjects"

    examination_id = Column(String(36), ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    max_theory_marks = Column(Numeric(5, 2), default=70.00, nullable=False)
    max_practical_marks = Column(Numeric(5, 2), default=30.00, nullable=False)
    min_passing_marks = Column(Numeric(5, 2), default=35.00, nullable=False)
    exam_date = Column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("examination_id", "subject_id", "class_id", name="uq_exam_subject_class"),
    )

    examination = relationship("Examination", back_populates="exam_subjects")
    subject = relationship("Subject")
    marks_entries = relationship("MarksEntry", back_populates="exam_subject", cascade="all, delete-orphan")
    marks_approvals = relationship("MarksApproval", back_populates="exam_subject", cascade="all, delete-orphan")


class MarksEntry(BaseModel):
    __tablename__ = "marks_entries"

    exam_subject_id = Column(String(36), ForeignKey("exam_subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    division_id = Column(String(36), ForeignKey("divisions.id", ondelete="CASCADE"), nullable=False)
    theory_marks_obtained = Column(Numeric(5, 2), nullable=True)
    practical_marks_obtained = Column(Numeric(5, 2), nullable=True)
    total_obtained = Column(Numeric(5, 2), nullable=True)
    is_absent = Column(Boolean, default=False, nullable=False)
    is_exempt = Column(Boolean, default=False, nullable=False)
    entered_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), default="DRAFT", nullable=False)  # DRAFT, SUBMITTED, APPROVED, REJECTED
    teacher_remarks = Column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("exam_subject_id", "student_id", name="uq_marks_exam_subject_student"),
    )

    exam_subject = relationship("ExamSubject", back_populates="marks_entries")
    student = relationship("Student", back_populates="marks_entries")
    division = relationship("Division")


class MarksApproval(BaseModel):
    __tablename__ = "marks_approvals"

    exam_subject_id = Column(String(36), ForeignKey("exam_subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    division_id = Column(String(36), ForeignKey("divisions.id", ondelete="CASCADE"), nullable=False, index=True)
    submitted_by = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_comments = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("exam_subject_id", "division_id", name="uq_marks_approval_subject_div"),
    )

    exam_subject = relationship("ExamSubject", back_populates="marks_approvals")
    division = relationship("Division")
    submitter = relationship("User", foreign_keys=[submitted_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class ResultPublication(BaseModel):
    __tablename__ = "result_publications"

    examination_id = Column(String(36), ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    published_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("examination_id", "class_id", name="uq_result_publication_exam_class"),
    )

    examination = relationship("Examination", back_populates="result_publications")
    publisher = relationship("User", foreign_keys=[published_by])


class ReportCardVersion(BaseModel):
    __tablename__ = "report_card_versions"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    examination_id = Column(String(36), ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    summary_data = Column(JSON, nullable=False)  # Stores snapshot of subject scores, totals, %, attendance
    generated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        UniqueConstraint("examination_id", "student_id", "version", name="uq_report_card_exam_student_ver"),
    )

    examination = relationship("Examination", back_populates="report_cards")
    student = relationship("Student")
