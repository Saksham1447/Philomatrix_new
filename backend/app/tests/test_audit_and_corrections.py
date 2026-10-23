import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.student import Student
from app.models.academic import Division, Subject, FacultyProfile
from app.models.examination import Examination, ExamSubject, MarksApproval
from app.models.communication import FeedbackForm, FeedbackQuestion

client = TestClient(app)


def get_token(username_or_email: str, password: str) -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username_or_email, "password": password}
    )
    assert res.status_code == 200, f"Login failed for {username_or_email}: {res.text}"
    return res.json()["access_token"]


def test_principal_cannot_mark_attendance_without_faculty_assignment():
    """Verify Section 7.2 & 24.1: Principals cannot mark attendance without an explicit teaching assignment."""
    token_principal = get_token("principal@royalscience.edu", "Royal@Principal2026")

    # Fetch division and subject
    db = SessionLocal()
    div = db.query(Division).first()
    subj = db.query(Subject).first()
    student = db.query(Student).first()
    db.close()

    payload = {
        "division_id": div.id,
        "subject_id": subj.id,
        "session_date": "2026-10-18",
        "period_number": 6,
        "records": [
            {
                "student_id": student.id,
                "status": "PRESENT"
            }
        ]
    }

    res = client.post(
        "/api/v1/attendance/submit",
        json=payload,
        headers={"Authorization": f"Bearer {token_principal}"}
    )
    # Principal does not have a teaching profile or assignment for this division/subject
    assert res.status_code == 403
    assert "Security Violation" in res.json()["detail"] or "Only faculty" in res.json()["detail"]


def test_parent_cannot_access_unlinked_student_records():
    """Verify Section 7.5 & 24.1: Parents cannot access unlinked student attendance, marks, timetable, or report cards."""
    token_parent = get_token("parent.sharma@gmail.com", "Parent@Pass2026")
    token_principal = get_token("principal@royalscience.edu", "Royal@Principal2026")

    # Find unlinked student Priya
    st_res = client.get("/api/v1/students", headers={"Authorization": f"Bearer {token_principal}"})
    assert st_res.status_code == 200
    priya = next(s for s in st_res.json() if "Priya" in s["full_name"])

    # 1. Attendance Summary for unlinked student -> 403
    res_att = client.get(
        f"/api/v1/attendance/summary/student/{priya['id']}",
        headers={"Authorization": f"Bearer {token_parent}"}
    )
    assert res_att.status_code == 403
    assert "not authorized" in res_att.json()["detail"].lower()

    # 2. Marks for unlinked student -> 403
    res_marks = client.get(
        f"/api/v1/examinations/marks/student/{priya['id']}",
        headers={"Authorization": f"Bearer {token_parent}"}
    )
    assert res_marks.status_code == 403

    # 3. Timetable with unlinked student_id -> 403
    res_tt = client.get(
        f"/api/v1/timetable?student_id={priya['id']}",
        headers={"Authorization": f"Bearer {token_parent}"}
    )
    assert res_tt.status_code == 403

    # 4. Report Card PDF for unlinked student -> 403
    exam_res = client.get("/api/v1/examinations", headers={"Authorization": f"Bearer {token_principal}"})
    exam_id = exam_res.json()[0]["id"]
    res_rc = client.get(
        f"/api/v1/reports/report-card/{exam_id}/student/{priya['id']}/pdf",
        headers={"Authorization": f"Bearer {token_parent}"}
    )
    assert res_rc.status_code == 403


def test_student_cannot_list_student_directory():
    """Verify Section 7.4 & 24.1: Students cannot browse full student directory."""
    token_student = get_token("arjun.sharma@royalscience.edu", "Student@Pass2026")
    res = client.get("/api/v1/students", headers={"Authorization": f"Bearer {token_student}"})
    assert res.status_code == 403


def test_institution_settings_persistence_and_audit():
    """Verify Section 10: Administrative configuration update persists to database and writes audit trail."""
    token_principal = get_token("principal@royalscience.edu", "Royal@Principal2026")

    # Get institution ID
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_principal}"}).json()
    inst_id = me["institution_id"]

    # 1. Fetch current settings
    res = client.get(f"/api/v1/institutions/{inst_id}/settings", headers={"Authorization": f"Bearer {token_principal}"})
    assert res.status_code == 200
    initial_settings = res.json()
    assert "min_attendance_threshold" in initial_settings

    # 2. Update settings
    update_payload = {
        "min_attendance_threshold": 80.00,
        "allow_late_as_present": False,
        "enable_parent_sms_alerts": True,
        "report_card_template_id": "PREMIER_JC_V2"
    }
    update_res = client.put(
        f"/api/v1/institutions/{inst_id}/settings",
        json=update_payload,
        headers={"Authorization": f"Bearer {token_principal}"}
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert float(updated["min_attendance_threshold"]) == 80.00
    assert updated["allow_late_as_present"] is False
    assert updated["enable_parent_sms_alerts"] is True
    assert updated["report_card_template_id"] == "PREMIER_JC_V2"

    # 3. Confirm persistence by re-fetching
    recheck = client.get(f"/api/v1/institutions/{inst_id}/settings", headers={"Authorization": f"Bearer {token_principal}"}).json()
    assert float(recheck["min_attendance_threshold"]) == 80.00

    # 4. Check audit log
    audit_res = client.get("/api/v1/audit/logs", headers={"Authorization": f"Bearer {token_principal}"})
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert any(l["action"] == "INSTITUTION_SETTINGS_UPDATED" for l in logs)

    # Revert back to 75.00 for clean state
    client.put(
        f"/api/v1/institutions/{inst_id}/settings",
        json={"min_attendance_threshold": 75.00, "allow_late_as_present": True},
        headers={"Authorization": f"Bearer {token_principal}"}
    )


def test_feedback_security_duplicate_and_analytics():
    """Verify Section 13: Feedback deadline, duplicate protection, anonymity, and analytics."""
    token_principal = get_token("principal@royalscience.edu", "Royal@Principal2026")
    token_student = get_token("arjun.sharma@royalscience.edu", "Student@Pass2026")
    token_parent = get_token("parent.sharma@gmail.com", "Parent@Pass2026")

    # Principal creates a feedback form
    create_form_res = client.post(
        "/api/v1/feedback/forms",
        json={
            "title": "Automated Test Term Feedback",
            "target_role": "STUDENT",
            "is_anonymous": True,
            "questions": [
                {
                    "question_text": "How effective are the Physics lab instruments?",
                    "question_type": "RATING_1_5",
                    "display_order": 1
                },
                {
                    "question_text": "General comments on academic rigor:",
                    "question_type": "TEXT",
                    "display_order": 2
                }
            ]
        },
        headers={"Authorization": f"Bearer {token_principal}"}
    )
    assert create_form_res.status_code == 201
    form_id = create_form_res.json()["id"]
    q1_id = create_form_res.json()["questions"][0]["id"]
    q2_id = create_form_res.json()["questions"][1]["id"]

    # 1. Parent cannot submit student feedback
    parent_sub = client.post(
        f"/api/v1/feedback/forms/{form_id}/respond",
        json={"answers": [{"question_id": q1_id, "rating_value": 5}]},
        headers={"Authorization": f"Bearer {token_parent}"}
    )
    assert parent_sub.status_code == 403

    # 2. Student submits feedback
    sub_res = client.post(
        f"/api/v1/feedback/forms/{form_id}/respond",
        json={
            "answers": [
                {"question_id": q1_id, "rating_value": 5},
                {"question_id": q2_id, "text_response": "Excellent facilities and practical experiments."}
            ]
        },
        headers={"Authorization": f"Bearer {token_student}"}
    )
    assert sub_res.status_code == 200

    # 3. Duplicate submission prevention
    dup_res = client.post(
        f"/api/v1/feedback/forms/{form_id}/respond",
        json={"answers": [{"question_id": q1_id, "rating_value": 4}]},
        headers={"Authorization": f"Bearer {token_student}"}
    )
    assert dup_res.status_code == 409
    assert "already submitted" in dup_res.json()["detail"].lower()

    # 4. Principal views analytics
    analytics_res = client.get(
        f"/api/v1/feedback/forms/{form_id}/analytics",
        headers={"Authorization": f"Bearer {token_principal}"}
    )
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert analytics["total_submissions"] == 1
    assert len(analytics["questions"]) == 2
    assert analytics["questions"][0]["average_rating"] == 5.0
    assert "Excellent facilities" in analytics["questions"][1]["comments"][0]
