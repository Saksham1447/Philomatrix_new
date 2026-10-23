from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class StudyMaterialBase(BaseModel):
    title: str
    description: Optional[str] = None
    topic: Optional[str] = None
    class_id: str
    division_id: Optional[str] = None
    subject_id: str
    is_published: bool = True


class StudyMaterialCreate(StudyMaterialBase):
    pass


class StudyMaterialUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    topic: Optional[str] = None
    is_published: Optional[bool] = None


class StudyMaterialResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    topic: Optional[str] = None
    file_name: str
    file_size: int
    file_type: str
    is_published: bool
    download_count: int
    created_at: datetime
    class_id: str
    class_name: str
    division_id: Optional[str] = None
    division_name: Optional[str] = None
    subject_id: str
    subject_name: str
    subject_code: str
    faculty_id: str
    faculty_name: str

    class Config:
        from_attributes = True
