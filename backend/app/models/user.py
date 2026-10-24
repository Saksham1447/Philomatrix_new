from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Role(BaseModel):
    __tablename__ = "roles"

    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)

    user_assignments = relationship("UserRoleAssignment", back_populates="role", cascade="all, delete-orphan")


class User(BaseModel):
    __tablename__ = "users"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=False)
    phone_number = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    institution = relationship("Institution", back_populates="users")
    role_assignments = relationship("UserRoleAssignment", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshTokenRecord", back_populates="user", cascade="all, delete-orphan")
    faculty_profile = relationship("FacultyProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    student_profile = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    guardian_profile = relationship("Guardian", back_populates="user", uselist=False, cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        return " ".join(part for part in (self.first_name, self.middle_name, self.last_name) if part)


class UserRoleAssignment(BaseModel):
    __tablename__ = "user_role_assignments"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "institution_id", name="uq_user_role_institution"),
    )

    user = relationship("User", back_populates="role_assignments")
    role = relationship("Role", back_populates="user_assignments")


class RefreshTokenRecord(BaseModel):
    __tablename__ = "refresh_token_records"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    user = relationship("User", back_populates="refresh_tokens")



class UserPreference(BaseModel):
    __tablename__ = "user_preferences"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    dashboard_layout = Column(String(50), default="STANDARD", nullable=False)
    default_division_id = Column(String(36), nullable=True)
    default_subject_id = Column(String(36), nullable=True)
    attendance_table_density = Column(String(20), default="COMFORTABLE", nullable=False)  # COMFORTABLE, COMPACT
    notify_email = Column(Boolean, default=True, nullable=False)
    notify_in_app = Column(Boolean, default=True, nullable=False)
    theme_mode = Column(String(20), default="LIGHT", nullable=False)

    user = relationship("User", back_populates="preferences")

