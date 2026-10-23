from sqlalchemy import Column, String, Date, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Student(BaseModel):
    __tablename__ = "students"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    admission_number = Column(String(50), nullable=False, index=True)  # e.g., "ADM-2026-001"
    roll_number = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(20), nullable=False)  # MALE, FEMALE, OTHER
    blood_group = Column(String(10), nullable=True)
    admission_date = Column(Date, nullable=False)
    address = Column(Text, nullable=True)
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(30), nullable=True)
    status = Column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, INACTIVE, TRANSFERRED, GRADUATED

    __table_args__ = (
        UniqueConstraint("institution_id", "admission_number", name="uq_student_adm_no_institution"),
    )

    user = relationship("User", back_populates="student_profile")
    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    guardian_links = relationship("StudentGuardianLink", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="student", cascade="all, delete-orphan")
    marks_entries = relationship("MarksEntry", back_populates="student", cascade="all, delete-orphan")
    assignment_submissions = relationship("AssignmentSubmission", back_populates="student", cascade="all, delete-orphan")


class Guardian(BaseModel):
    __tablename__ = "guardians"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(50), nullable=False)  # FATHER, MOTHER, LEGAL_GUARDIAN
    occupation = Column(String(100), nullable=True)
    alternative_phone = Column(String(30), nullable=True)

    user = relationship("User", back_populates="guardian_profile")
    student_links = relationship("StudentGuardianLink", back_populates="guardian", cascade="all, delete-orphan")


class StudentGuardianLink(BaseModel):
    __tablename__ = "student_guardian_links"

    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    guardian_id = Column(String(36), ForeignKey("guardians.id", ondelete="CASCADE"), nullable=False, index=True)
    is_primary = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "guardian_id", name="uq_student_guardian"),
    )

    student = relationship("Student", back_populates="guardian_links")
    guardian = relationship("Guardian", back_populates="student_links")


class Enrollment(BaseModel):
    __tablename__ = "enrollments"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(String(36), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    division_id = Column(String(36), ForeignKey("divisions.id", ondelete="CASCADE"), nullable=False)
    roll_number = Column(String(20), nullable=True)
    status = Column(String(20), default="ENROLLED", nullable=False)  # ENROLLED, PROMOTED, DETAINED, WITHDRAWN

    __table_args__ = (
        UniqueConstraint("academic_year_id", "student_id", name="uq_enrollment_year_student"),
    )

    student = relationship("Student", back_populates="enrollments")
    academic_year = relationship("AcademicYear", back_populates="enrollments")
    division = relationship("Division", back_populates="enrollments")
