from sqlalchemy import Column, Date, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class FacultyLeaveRequest(BaseModel):
    __tablename__ = "faculty_leave_requests"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    faculty_id = Column(String(36), ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    reviewed_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_comments = Column(Text, nullable=True)

    institution = relationship("Institution")
    faculty = relationship("FacultyProfile")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
