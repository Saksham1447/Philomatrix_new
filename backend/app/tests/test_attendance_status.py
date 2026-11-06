import pytest
from pydantic import ValidationError

from app.schemas.attendance import AttendanceCorrectionCreate, AttendanceRecordInput


def test_late_is_not_a_valid_attendance_record_status():
    with pytest.raises(ValidationError):
        AttendanceRecordInput(student_id="student-1", status="LATE")


def test_late_is_not_a_valid_attendance_correction_status():
    with pytest.raises(ValidationError):
        AttendanceCorrectionCreate(
            attendance_record_id="record-1",
            requested_status="LATE",
            reason="Correction requested",
        )
