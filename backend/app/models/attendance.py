from sqlalchemy import Column, String, SmallInteger, Date, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class AttendanceSession(BaseModel):
    __tablename__ = "attendance_sessions"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(String(36), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False)
    timetable_entry_id = Column(String(36), ForeignKey("timetable_entries.id", ondelete="SET NULL"), nullable=True)
    division_id = Column(String(36), ForeignKey("divisions.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    faculty_id = Column(String(36), ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False)
    session_date = Column(Date, nullable=False, index=True)
    period_number = Column(SmallInteger, nullable=False)
    submission_status = Column(String(20), default="SUBMITTED", nullable=False)  # SUBMITTED, CANCELLED

    __table_args__ = (
        UniqueConstraint("division_id", "subject_id", "session_date", "period_number", name="uq_att_session_slot"),
    )

    timetable_entry = relationship("TimetableEntry", back_populates="attendance_sessions")
    division = relationship("Division")
    subject = relationship("Subject")
    faculty = relationship("FacultyProfile")
    records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")


class AttendanceRecord(BaseModel):
    __tablename__ = "attendance_records"

    attendance_session_id = Column(String(36), ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # PRESENT, ABSENT, LATE, EXCUSED
    remarks = Column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("attendance_session_id", "student_id", name="uq_att_session_student"),
    )

    session = relationship("AttendanceSession", back_populates="records")
    student = relationship("Student", back_populates="attendance_records")
    correction_requests = relationship("AttendanceCorrectionRequest", back_populates="record", cascade="all, delete-orphan")


class AttendanceCorrectionRequest(BaseModel):
    __tablename__ = "attendance_correction_requests"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_record_id = Column(String(36), ForeignKey("attendance_records.id", ondelete="CASCADE"), nullable=False)
    requested_by = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    previous_status = Column(String(20), nullable=False)
    requested_status = Column(String(20), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    record = relationship("AttendanceRecord", back_populates="correction_requests")
    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
