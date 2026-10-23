import io
from datetime import date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_token(username_or_email: str, password: str) -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username_or_email, "password": password}
    )
    assert res.status_code == 200, f"Login failed for {username_or_email}: {res.text}"
    return res.json()["access_token"]


def test_faculty_assigned_slots_and_roster():
    """Verify faculty can view assigned lecture slots and enrolled scholars with statutory status."""
    token = get_token("physics.prof@royalscience.edu", "Faculty@Pass2026")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Assigned slots (works on any day including weekend fallback)
    slots_res = client.get("/api/v1/attendance/today-slots", headers=headers)
    assert slots_res.status_code == 200
    slots = slots_res.json()
    assert len(slots) > 0
    slot = slots[0]
    assert "division_id" in slot
    assert "subject_id" in slot
    assert "period_number" in slot

    # 2. Roster for division
    div_id = slot["division_id"]
    roster_res = client.get(f"/api/v1/attendance/roster?division_id={div_id}", headers=headers)
    assert roster_res.status_code == 200
    roster = roster_res.json()
    assert len(roster) > 0

    first_scholar = roster[0]
    assert "sr_no" in first_scholar
    assert "roll_number" in first_scholar
    assert "full_name" in first_scholar
    assert "cumulative_attendance" in first_scholar
    assert first_scholar["statutory_status"] in ["ELIGIBLE", "SHORTAGE"]


def test_faculty_attendance_draft_and_commit_workflow(monkeypatch):
    """Verify draft saving, unmarked validation, submission persistence, and duplicate protection."""
    token = get_token("physics.prof@royalscience.edu", "Faculty@Pass2026")
    headers = {"Authorization": f"Bearer {token}"}

    slots_res = client.get("/api/v1/attendance/today-slots", headers=headers)
    assert slots_res.status_code == 200
    slot = slots_res.json()[0]
    div_id = slot["division_id"]
    subj_id = slot["subject_id"]

    roster_res = client.get(f"/api/v1/attendance/roster?division_id={div_id}", headers=headers)
    roster = roster_res.json()
    assert len(roster) >= 2

    import app.api.v1.attendance as attendance_api
    import uuid
    slot_day = slot["day_of_week"]
    candidate = date.today() + timedelta(days=7 * ((uuid.uuid4().int % 20) + 1))
    while candidate.weekday() + 1 != slot_day:
        candidate += timedelta(days=1)
    start = datetime.strptime(slot["start_time"], "%H:%M").time()
    fake_now = datetime.combine(candidate, start) + timedelta(minutes=1)
    monkeypatch.setattr(
        attendance_api,
        "_india_now",
        lambda: fake_now.replace(tzinfo=attendance_api.INDIA_TZ),
    )
    test_date = candidate.isoformat()
    period = slot["period_number"]


    # 1. Save draft with an unmarked student
    draft_records = [
        {"student_id": roster[0]["student_id"], "status": "PRESENT", "remarks": "On time"},
        {"student_id": roster[1]["student_id"], "status": "UNMARKED", "remarks": None}
    ]
    draft_payload = {
        "division_id": div_id,
        "subject_id": subj_id,
        "session_date": test_date,
        "period_number": period,
        "submission_status": "DRAFT",
        "records": draft_records
    }
    draft_res = client.post("/api/v1/attendance/submit", json=draft_payload, headers=headers)
    assert draft_res.status_code == 201
    draft_data = draft_res.json()
    assert draft_data["submission_status"] == "DRAFT"
    session_id = draft_data["id"]

    # 2. Attempt final commit while unmarked scholars exist (must be rejected)
    commit_payload_unmarked = {
        "division_id": div_id,
        "subject_id": subj_id,
        "session_date": test_date,
        "period_number": period,
        "submission_status": "SUBMITTED",
        "records": draft_records
    }
    unmarked_res = client.post("/api/v1/attendance/submit", json=commit_payload_unmarked, headers=headers)
    assert unmarked_res.status_code == 400
    assert "unmarked scholar" in unmarked_res.json()["detail"].lower()

    # 3. Commit with all scholars marked
    complete_records = [
        {"student_id": roster[0]["student_id"], "status": "PRESENT", "remarks": "On time"},
        {"student_id": roster[1]["student_id"], "status": "ABSENT", "remarks": "Unexcused"}
    ]
    commit_payload = {
        "division_id": div_id,
        "subject_id": subj_id,
        "session_date": test_date,
        "period_number": period,
        "submission_status": "SUBMITTED",
        "records": complete_records
    }
    commit_res = client.post("/api/v1/attendance/submit", json=commit_payload, headers=headers)
    assert commit_res.status_code == 201
    commit_data = commit_res.json()
    assert commit_data["submission_status"] == "SUBMITTED"
    assert commit_data["present_count"] == 1
    assert commit_data["absent_count"] == 1

    # 4. Duplicate submission attempt returns 409 Conflict
    dup_res = client.post("/api/v1/attendance/submit", json=commit_payload, headers=headers)
    assert dup_res.status_code == 409

    # 5. Reopen submitted session in read-only mode
    detail_res = client.get(f"/api/v1/attendance/sessions/{session_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["submission_status"] == "SUBMITTED"
    assert len(detail["records"]) == 2


def test_user_personal_preferences_persistence():
    """Verify Faculty and Office Staff can customize and persist personal preferences."""
    fac_token = get_token("physics.prof@royalscience.edu", "Faculty@Pass2026")
    fac_headers = {"Authorization": f"Bearer {fac_token}"}

    # Fetch initial preferences
    get_res = client.get("/api/v1/auth/preferences", headers=fac_headers)
    assert get_res.status_code == 200

    # Update preferences
    update_payload = {
        "dashboard_layout": "ANALYTICS",
        "attendance_table_density": "COMPACT",
        "notify_email": False,
        "notify_in_app": True
    }
    put_res = client.put("/api/v1/auth/preferences", json=update_payload, headers=fac_headers)
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["dashboard_layout"] == "ANALYTICS"
    assert updated["attendance_table_density"] == "COMPACT"
    assert updated["notify_email"] is False

    # Verify persistence
    verify_res = client.get("/api/v1/auth/preferences", headers=fac_headers)
    assert verify_res.status_code == 200
    assert verify_res.json()["attendance_table_density"] == "COMPACT"


def test_study_materials_upload_and_scoped_access():
    """Verify faculty can upload educational materials and students can download authorized notes."""
    fac_token = get_token("physics.prof@royalscience.edu", "Faculty@Pass2026")
    fac_headers = {"Authorization": f"Bearer {fac_token}"}

    # Find division and subject
    slots_res = client.get("/api/v1/attendance/today-slots", headers=fac_headers)
    slot = slots_res.json()[0]
    div_id = slot["division_id"]
    subj_id = slot["subject_id"]

    # 1. Invalid file rejection (.exe)
    invalid_file = ("bad.exe", io.BytesIO(b"MZ executable content"), "application/octet-stream")
    inv_res = client.post(
        "/api/v1/study-materials",
        data={
            "title": "Malicious File",
            "class_id": "none",
            "division_id": div_id,
            "subject_id": subj_id,
            "is_published": "true"
        },
        files={"file": invalid_file},
        headers=fac_headers
    )
    assert inv_res.status_code == 400

    # 2. Valid PDF upload
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< >>\n%%EOF"
    pdf_file = ("kinematics_notes.pdf", io.BytesIO(pdf_content), "application/pdf")
    upload_res = client.post(
        "/api/v1/study-materials",
        data={
            "title": "Chapter 1: Kinematics Lecture Notes",
            "description": "Comprehensive theory notes on motion in a straight line",
            "topic": "Kinematics",
            "class_id": "none",
            "division_id": div_id,
            "subject_id": subj_id,
            "is_published": "true"
        },
        files={"file": pdf_file},
        headers=fac_headers
    )
    assert upload_res.status_code == 201
    material = upload_res.json()
    material_id = material["id"]
    assert material["title"] == "Chapter 1: Kinematics Lecture Notes"
    assert material["file_name"] == "kinematics_notes.pdf"

    # 3. Authorized student can list and download
    student_token = get_token("arjun.sharma@royalscience.edu", "Student@Pass2026")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    list_res = client.get("/api/v1/study-materials", headers=student_headers)
    assert list_res.status_code == 200
    materials_list = list_res.json()
    found = any(m["id"] == material_id for m in materials_list)
    assert found, "Published study material should be accessible to enrolled student"

    # Download file content
    dl_res = client.get(f"/api/v1/study-materials/{material_id}/download", headers=student_headers)
    assert dl_res.status_code == 200
    assert dl_res.content == pdf_content
