from sqlalchemy import Column, String, Integer, Boolean, Numeric, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class AcademicYear(BaseModel):
    __tablename__ = "academic_years"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(50), nullable=False)  # e.g., "2026-2027"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_current = Column(Boolean, default=False, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("institution_id", "name", name="uq_academic_year_institution_name"),
    )

    institution = relationship("Institution", back_populates="academic_years")
    enrollments = relationship("Enrollment", back_populates="academic_year", cascade="all, delete-orphan")
    faculty_assignments = relationship("FacultySubjectAssignment", back_populates="academic_year", cascade="all, delete-orphan")


class ClassModel(BaseModel):
    __tablename__ = "classes"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(50), nullable=False)  # e.g., "Class 11", "Class 12"
    stream = Column(String(50), default="GENERAL", nullable=False)
    display_order = Column(Integer, default=1, nullable=False)

    __table_args__ = (
        UniqueConstraint("institution_id", "name", "stream", name="uq_class_name_stream"),
    )

    institution = relationship("Institution", back_populates="classes")
    divisions = relationship("Division", back_populates="class_model", cascade="all, delete-orphan")


class Division(BaseModel):
    __tablename__ = "divisions"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(20), nullable=False)  # e.g., "A", "B", "C"
    room_number = Column(String(50), nullable=True)
    capacity = Column(Integer, default=60, nullable=False)

    __table_args__ = (
        UniqueConstraint("class_id", "name", name="uq_division_class_name"),
    )

    class_model = relationship("ClassModel", back_populates="divisions")
    enrollments = relationship("Enrollment", back_populates="division", cascade="all, delete-orphan")
    faculty_assignments = relationship("FacultySubjectAssignment", back_populates="division", cascade="all, delete-orphan")
    timetable_entries = relationship("TimetableEntry", back_populates="division", cascade="all, delete-orphan")


class Subject(BaseModel):
    __tablename__ = "subjects"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(30), nullable=False)  # e.g., "PHY-101", "CHEM-101", "MATH-101"
    name = Column(String(100), nullable=False)  # e.g., "Physics", "Chemistry"
    stream = Column(String(50), default="GENERAL", nullable=False)
    has_practical = Column(Boolean, default=True, nullable=False)
    max_theory_marks = Column(Numeric(5, 2), default=70.00, nullable=False)
    max_practical_marks = Column(Numeric(5, 2), default=30.00, nullable=False)
    min_pass_percentage = Column(Numeric(5, 2), default=35.00, nullable=False)

    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_subject_code_institution"),
    )

    institution = relationship("Institution", back_populates="subjects")
    faculty_assignments = relationship("FacultySubjectAssignment", back_populates="subject", cascade="all, delete-orphan")


class FacultyProfile(BaseModel):
    __tablename__ = "faculty_profiles"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(String(50), nullable=False)
    designation = Column(String(100), default="Lecturer", nullable=False)
    department = Column(String(100), default="General", nullable=False)
    qualification = Column(String(200), nullable=True)
    joining_date = Column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("institution_id", "employee_id", name="uq_faculty_emp_id_institution"),
    )

    user = relationship("User", back_populates="faculty_profile")
    assignments = relationship("FacultySubjectAssignment", back_populates="faculty", cascade="all, delete-orphan")
    timetable_entries = relationship("TimetableEntry", back_populates="faculty", cascade="all, delete-orphan")


class FacultySubjectAssignment(BaseModel):
    __tablename__ = "faculty_subject_assignments"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(String(36), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False)
    faculty_id = Column(String(36), ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    division_id = Column(String(36), ForeignKey("divisions.id", ondelete="CASCADE"), nullable=False)
    is_class_teacher = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("academic_year_id", "faculty_id", "subject_id", "division_id", name="uq_fac_sub_div_year"),
    )

    academic_year = relationship("AcademicYear", back_populates="faculty_assignments")
    faculty = relationship("FacultyProfile", back_populates="assignments")
    subject = relationship("Subject", back_populates="faculty_assignments")
    division = relationship("Division", back_populates="faculty_assignments")
