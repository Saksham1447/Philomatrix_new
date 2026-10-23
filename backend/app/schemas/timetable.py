from datetime import time
from typing import Optional
from pydantic import BaseModel


class TimetableEntryCreate(BaseModel):
    timetable_version_id: Optional[str] = None
    division_id: str
    subject_id: str
    faculty_id: str
    day_of_week: int  # 1 to 6 (Mon to Sat)
    period_number: int  # 1 to 8
    start_time: time
    end_time: time
    room_number: Optional[str] = None
    is_practical_batch: bool = False
    batch_name: Optional[str] = None


class TimetableEntryResponse(BaseModel):
    id: str
    division_id: str
    division_name: str
    class_name: str
    subject_id: str
    subject_name: str
    subject_code: str
    faculty_id: str
    faculty_name: str
    day_of_week: int
    period_number: int
    start_time: time
    end_time: time
    room_number: Optional[str] = None
    is_practical_batch: bool
    batch_name: Optional[str] = None

    class Config:
        from_attributes = True
