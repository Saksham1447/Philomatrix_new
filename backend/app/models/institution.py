from sqlalchemy import Column, String, Text, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Institution(BaseModel):
    __tablename__ = "institutions"

    slug = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(32), unique=True, index=True, nullable=False)
    status = Column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, SUSPENDED, DEACTIVATED
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(20), nullable=True)
    phone = Column(String(30), nullable=True)
    email = Column(String(255), nullable=True)
    logo_url = Column(Text, nullable=True)
    database_url = Column(Text, nullable=True)
    institution_type = Column(String(40), default="OTHER", nullable=False)

    # Relationships
    settings = relationship("InstitutionSetting", back_populates="institution", uselist=False, cascade="all, delete-orphan")
    users = relationship("User", back_populates="institution", cascade="all, delete-orphan")
    academic_years = relationship("AcademicYear", back_populates="institution", cascade="all, delete-orphan")
    classes = relationship("ClassModel", back_populates="institution", cascade="all, delete-orphan")
    subjects = relationship("Subject", back_populates="institution", cascade="all, delete-orphan")


class InstitutionSetting(BaseModel):
    __tablename__ = "institution_settings"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), unique=True, nullable=False)
    min_attendance_threshold = Column(Numeric(5, 2), default=75.00, nullable=False)
    allow_late_as_present = Column(Boolean, default=True, nullable=False)
    enable_parent_sms_alerts = Column(Boolean, default=False, nullable=False)
    report_card_template_id = Column(String(50), default="STANDARD_V1", nullable=False)
    institution_type = Column(String(40), default="OTHER", nullable=False)
    academic_unit_label = Column(String(80), default="Department / Class", nullable=False)
    educator_label = Column(String(80), default="Faculty / Teacher", nullable=False)
    learner_label = Column(String(80), default="Student", nullable=False)
    head_role_label = Column(String(80), default="Head / Principal", nullable=False)

    institution = relationship("Institution", back_populates="settings")
