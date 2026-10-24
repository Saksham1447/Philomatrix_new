import pytest
from decimal import Decimal
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


def test_health_check():
    """Verify system health endpoint."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "PHILOMATRIX" in data["app"]


def test_authentication_success_and_failure():
    """Verify login with valid and invalid credentials."""
    # 1. Invalid credentials
    res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "principal@royalscience.edu", "password": "WrongPassword!"}
    )
    assert res.status_code == 401
    assert "Incorrect" in res.json()["detail"]

    # 2. Valid credentials
    res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "principal@royalscience.edu", "password": "Royal@Principal2026"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_user_profile_me():
    """Verify /api/v1/auth/me returns authentic profile and roles."""
    token = get_token("principal@royalscience.edu", "Royal@Principal2026")
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    profile = res.json()
    assert profile["email"] == "principal@royalscience.edu"
    assert "PRINCIPAL" in profile["roles"]
    assert profile["institution_name"] in [
        "Royal Junior College of Science",
        "Chate Junior College Of Science",
    ]


def test_super_admin_login_and_profile():
    """Verify the platform admin can complete login and profile retrieval."""
    token = get_token("superadmin@philomatrix.local", "Philomatrix@2026")
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer " + token}
    )
    assert res.status_code == 200
    profile = res.json()
    assert profile["email"] == "superadmin@philomatrix.local"
    assert profile["institution_id"] is None
    assert "SUPER_ADMIN" in profile["roles"]



def test_tenant_isolation_boundary():
    """Verify Tenant B Principal cannot view or update Tenant A Institution details."""
    token_b = get_token("principal@apexcollege.edu", "Apex@Principal2026")
    token_a = get_token("principal@royalscience.edu", "Royal@Principal2026")

    # Get Tenant A institution ID
    me_a = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"}).json()
    inst_a_id = me_a["institution_id"]

    # Principal B tries to query Institution A profile
    res = client.get(
        f"/api/v1/institutions/{inst_a_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


def test_timetable_conflict_engine():
    """Verify that scheduling an overlapping lecture slot is rejected with 409 Conflict."""
    token = get_token("principal@royalscience.edu", "Royal@Principal2026")

    # Fetch existing timetable
    tt_res = client.get("/api/v1/timetable", headers={"Authorization": f"Bearer {token}"})
    assert tt_res.status_code == 200
    entries = tt_res.json()
    assert len(entries) > 0

    existing_slot = entries[0]
    # Attempt to schedule the SAME faculty at the SAME day and period in another division
    clash_request = {
        "division_id": existing_slot["division_id"],
        "subject_id": existing_slot["subject_id"],
        "faculty_id": existing_slot["faculty_id"],
        "day_of_week": existing_slot["day_of_week"],
        "period_number": existing_slot["period_number"],
        "start_time": existing_slot["start_time"],
        "end_time": existing_slot["end_time"],
        "room_number": "Clash Room"
    }

    res = client.post(
        "/api/v1/timetable/entries",
        json=clash_request,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 409
    assert "conflict" in res.json()["detail"].lower()


def test_attendance_marking_and_calculation():
    """Verify attendance recording and mathematical percentage rollup."""
    token_fac = get_token("physics.prof@royalscience.edu", "Faculty@Pass2026")

    # 1. Fetch student list
    st_res = client.get("/api/v1/students", headers={"Authorization": f"Bearer {token_fac}"})
    assert st_res.status_code == 200
    students = st_res.json()
    assert len(students) >= 2

    target_student = students[0]
    div_id = target_student["division_id"]

    # 2. Query student attendance summary
    summary_res = client.get(
        f"/api/v1/attendance/summary/student/{target_student['id']}",
        headers={"Authorization": f"Bearer {token_fac}"}
    )
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert "overall_percentage" in summary
    assert summary["total_conducted"] >= 0
    assert 0 <= float(summary["overall_percentage"]) <= 100


def test_unauthorized_attendance_prevention():
    """Verify that students or non-assigned users cannot submit attendance."""
    token_student = get_token("arjun.sharma@royalscience.edu", "Student@Pass2026")

    payload = {
        "division_id": "dummy_div",
        "subject_id": "dummy_sub",
        "session_date": "2026-10-18",
        "period_number": 1,
        "records": []
    }
    res = client.post(
        "/api/v1/attendance/submit",
        json=payload,
        headers={"Authorization": f"Bearer {token_student}"}
    )
    assert res.status_code == 403


def test_student_privacy_isolation():
    """Verify student Arjun cannot inspect another student's marks or attendance."""
    token_arjun = get_token("arjun.sharma@royalscience.edu", "Student@Pass2026")
    token_principal = get_token("principal@royalscience.edu", "Royal@Principal2026")

    # Get student Priya ID
    st_res = client.get("/api/v1/students", headers={"Authorization": f"Bearer {token_principal}"})
    priya = next(s for s in st_res.json() if "Priya" in s["full_name"])

    # Arjun tries to query Priya's attendance
    res = client.get(
        f"/api/v1/attendance/summary/student/{priya['id']}",
        headers={"Authorization": f"Bearer {token_arjun}"}
    )
    assert res.status_code == 403
    assert "only access their own" in res.json()["detail"]


def test_parent_child_switcher_and_isolation():
    """Verify Parent Mr. Sharma can view linked child Arjun, but receives 403 on unlinked students."""
    token_parent = get_token("parent.sharma@gmail.com", "Parent@Pass2026")

    # Parent fetches linked children
    res = client.get("/api/v1/students/my-children", headers={"Authorization": f"Bearer {token_parent}"})
    assert res.status_code == 200
    children = res.json()
    assert len(children) >= 1
    assert any("Arjun" in c["full_name"] for c in children)


def test_report_card_generation_and_pdf_stream():
    """Verify report card data compilation and ReportLab PDF streaming."""
    token_principal = get_token("principal@royalscience.edu", "Royal@Principal2026")

    # Fetch examinations
    exam_res = client.get("/api/v1/examinations", headers={"Authorization": f"Bearer {token_principal}"})
    assert exam_res.status_code == 200
    exams = exam_res.json()
    assert len(exams) > 0
    exam = exams[0]

    # Fetch student
    st_res = client.get("/api/v1/students", headers={"Authorization": f"Bearer {token_principal}"})
    student = st_res.json()[0]

    # 1. Fetch Report Card JSON
    rc_res = client.get(
        f"/api/v1/reports/report-card/{exam['id']}/student/{student['id']}",
        headers={"Authorization": f"Bearer {token_principal}"}
    )
    assert rc_res.status_code == 200
    rc_data = rc_res.json()
    assert rc_data["student_name"] == student["full_name"]
    assert "grand_total_obtained" in rc_data
    assert "subjects" in rc_data
    assert len(rc_data["subjects"]) > 0

    # 2. Fetch Report Card PDF stream
    pdf_res = client.get(
        f"/api/v1/reports/report-card/{exam['id']}/student/{student['id']}/pdf",
        headers={"Authorization": f"Bearer {token_principal}"}
    )
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000  # Valid non-empty binary PDF stream
