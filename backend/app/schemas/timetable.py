from datetime import time
from typing import List, Optional
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


class TimetableSlotCreate(BaseModel):
    class_id: str
    days_of_week: List[int]  # 1 to 6 (Mon to Sat); one slot is created per day
    period_number: int  # 1 to 8
    start_time: time
    end_time: time
    subject_id: Optional[str] = None


class TimetableSlotUpdate(BaseModel):
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    subject_id: Optional[str] = None


class TimetableSlotResponse(BaseModel):
    id: str
    class_id: str
    class_name: str
    day_of_week: int
    period_number: int
    start_time: time
    end_time: time
    subject_id: Optional[str] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None


class SlotSubjectOption(BaseModel):
    subject_id: str
    subject_name: str
    subject_code: str


class AvailableSlotResponse(BaseModel):
    slot_id: str
    day_of_week: int
    period_number: int
    start_time: time
    end_time: time
    # OPEN, TAKEN (division already has a lecture) or FACULTY_BUSY (teacher teaches elsewhere)
    status: str
    taken_by: Optional[str] = None
    taken_subject: Optional[str] = None
    allowed_subjects: List[SlotSubjectOption] = []
