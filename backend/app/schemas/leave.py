from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class FacultyLeaveRequestCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date")
        return self


class FacultyLeaveRequestReview(BaseModel):
    status: str
    review_comments: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_review_status(self):
        if self.status not in {"APPROVED", "REJECTED"}:
            raise ValueError("Status must be APPROVED or REJECTED")
        return self


class FacultyLeaveRequestResponse(BaseModel):
    id: str
    faculty_id: str
    faculty_name: str
    employee_id: str
    start_date: date
    end_date: date
    reason: str
    status: str
    reviewed_by_name: Optional[str] = None
    review_comments: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True
