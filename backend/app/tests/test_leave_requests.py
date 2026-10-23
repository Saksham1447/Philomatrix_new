from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.leave import FacultyLeaveRequest


client = TestClient(app)


def login(username_or_email: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username_or_email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_faculty_can_submit_and_office_staff_can_review_leave_request():
    db = SessionLocal()
    db.query(FacultyLeaveRequest).filter(
        FacultyLeaveRequest.start_date == "2099-01-10",
        FacultyLeaveRequest.end_date == "2099-01-12",
    ).delete(synchronize_session=False)
    db.commit()
    db.close()

    faculty_token = login("physics.prof@royalscience.edu", "Faculty@Pass2026")
    office_token = login("admissions@royalscience.edu", "Staff@Pass2026")

    create_response = client.post(
        "/api/v1/leave-requests",
        json={
            "start_date": "2099-01-10",
            "end_date": "2099-01-12",
            "reason": "Family function",
        },
        headers={"Authorization": f"Bearer {faculty_token}"},
    )
    assert create_response.status_code == 201, create_response.text
    request_id = create_response.json()["id"]
    assert create_response.json()["status"] == "PENDING"

    office_list = client.get(
        "/api/v1/leave-requests",
        headers={"Authorization": f"Bearer {office_token}"},
    )
    assert office_list.status_code == 200
    assert any(item["id"] == request_id for item in office_list.json())

    review_response = client.put(
        f"/api/v1/leave-requests/{request_id}/review",
        json={"status": "APPROVED", "review_comments": "Approved for the requested dates"},
        headers={"Authorization": f"Bearer {office_token}"},
    )
    assert review_response.status_code == 200, review_response.text
    assert review_response.json()["status"] == "APPROVED"
    assert review_response.json()["review_comments"] == "Approved for the requested dates"

    faculty_list = client.get(
        "/api/v1/leave-requests",
        headers={"Authorization": f"Bearer {faculty_token}"},
    )
    assert faculty_list.status_code == 200
    faculty_request = next(item for item in faculty_list.json() if item["id"] == request_id)
    assert faculty_request["status"] == "APPROVED"


def test_non_faculty_cannot_submit_leave_request():
    principal_token = login("principal@royalscience.edu", "Royal@Principal2026")
    response = client.post(
        "/api/v1/leave-requests",
        json={
            "start_date": "2099-02-01",
            "end_date": "2099-02-01",
            "reason": "Should not be permitted",
        },
        headers={"Authorization": f"Bearer {principal_token}"},
    )
    assert response.status_code == 403
