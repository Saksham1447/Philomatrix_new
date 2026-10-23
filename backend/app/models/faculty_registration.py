from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class FacultyRegistrationRequest(BaseModel):
    __tablename__ = "faculty_registration_requests"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone_number = Column(String(30), nullable=True)
    employee_id = Column(String(50), nullable=False)
    designation = Column(String(100), default="Lecturer", nullable=False)
    department = Column(String(100), default="Science", nullable=False)
    qualification = Column(String(200), nullable=True)
    status = Column(String(20), default="PENDING", nullable=False, index=True)
    reviewed_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_comments = Column(Text, nullable=True)

    institution = relationship("Institution")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
