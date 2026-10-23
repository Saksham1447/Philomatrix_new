from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class StudyMaterial(BaseModel):
    __tablename__ = "study_materials"

    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(String(36), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False)
    faculty_id = Column(String(36), ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    division_id = Column(String(36), ForeignKey("divisions.id", ondelete="CASCADE"), nullable=True, index=True)
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    topic = Column(String(255), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(String(100), nullable=False)  # MIME type or extension
    is_published = Column(Boolean, default=True, nullable=False)
    download_count = Column(Integer, default=0, nullable=False)

    # Relationships
    faculty = relationship("FacultyProfile")
    class_model = relationship("ClassModel")
    division = relationship("Division")
    subject = relationship("Subject")
    academic_year = relationship("AcademicYear")
