from sqlalchemy import Column, String, Integer, SmallInteger, Time, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class TimetableVersion(BaseModel):
    __tablename__ = "timetable_versions"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(String(36), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    entries = relationship("TimetableEntry", back_populates="version", cascade="all, delete-orphan")


class TimetableEntry(BaseModel):
    __tablename__ = "timetable_entries"

    timetable_version_id = Column(String(36), ForeignKey("timetable_versions.id", ondelete="CASCADE"), nullable=False)
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    division_id = Column(String(36), ForeignKey("divisions.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    faculty_id = Column(String(36), ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(SmallInteger, nullable=False)  # 1 (Monday) - 6 (Saturday)
    period_number = Column(SmallInteger, nullable=False)  # 1 to 8
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    room_number = Column(String(50), nullable=True)
    is_practical_batch = Column(Boolean, default=False, nullable=False)
    batch_name = Column(String(20), nullable=True)

    __table_args__ = (
        UniqueConstraint("timetable_version_id", "faculty_id", "day_of_week", "period_number", name="uq_tt_faculty_day_period"),
        UniqueConstraint("timetable_version_id", "division_id", "day_of_week", "period_number", name="uq_tt_division_day_period"),
    )

    version = relationship("TimetableVersion", back_populates="entries")
    division = relationship("Division", back_populates="timetable_entries")
    subject = relationship("Subject")
    faculty = relationship("FacultyProfile", back_populates="timetable_entries")
    attendance_sessions = relationship("AttendanceSession", back_populates="timetable_entry")


class TimetableSlot(BaseModel):
    """Per-division slot template: the periods (and optionally subject) of each weekday."""
    __tablename__ = "timetable_slots"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    division_id = Column(String(36), ForeignKey("divisions.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    day_of_week = Column(SmallInteger, nullable=False)  # 1 (Monday) - 6 (Saturday)
    period_number = Column(SmallInteger, nullable=False)  # 1 to 8
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    __table_args__ = (
        UniqueConstraint("division_id", "day_of_week", "period_number", name="uq_slot_division_day_period"),
    )
