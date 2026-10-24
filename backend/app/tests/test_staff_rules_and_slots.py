from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth(username: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"username_or_email": username, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": "Bearer " + res.json()["access_token"]}


PRINCIPAL = ("principal@royalscience.edu", "Royal@Principal2026")
OFFICE = ("admissions@royalscience.edu", "Staff@Pass2026")
FACULTY = ("physics.prof@royalscience.edu", "Faculty@Pass2026")


def faculty_payload(**overrides) -> dict:
    return {
        "email": "new.teacher@royalscience.edu",
        "password": "Teacher@2026",
        "first_name": "New",
        "last_name": "Teacher",
        "employee_id": "FAC-NEW-01",
        "gender": "FEMALE",
        **overrides,
    }


def class_11_and_division(headers: dict) -> tuple[dict, dict]:
    classes = client.get("/api/v1/academics/classes", headers=headers).json()
    class_11 = next(item for item in classes if item["name"] == "Class 11")
    return class_11, next(item for item in class_11["divisions"] if item["name"] == "A")


def test_office_staff_can_add_but_not_change_students_faculty_or_academic_structure():
    office = auth(*OFFICE)

    created = client.post("/api/v1/faculty", json=faculty_payload(department="Physics"), headers=office)
    assert created.status_code == 201, created.text
    # Not an engineering college: faculty are not tied to a department.
    assert created.json()["department"] == "General"

    faculty_id = created.json()["id"]
    assert client.put(f"/api/v1/faculty/{faculty_id}", json=faculty_payload(), headers=office).status_code == 403
    assert client.delete(f"/api/v1/faculty/{faculty_id}", headers=office).status_code == 403

    students = client.get("/api/v1/students", headers=office).json()
    assert client.delete(f"/api/v1/students/{students[0]['id']}", headers=office).status_code == 403
    assert client.post("/api/v1/academics/classes", json={"name": "Class 13", "divisions": ["A"]}, headers=office).status_code == 403

    principal = auth(*PRINCIPAL)
    assert client.delete(f"/api/v1/faculty/{faculty_id}", headers=principal).status_code == 204


def test_engineering_college_requires_an_existing_department_for_faculty(isolated_mongo_store):
    store = isolated_mongo_store
    for institution in store.find("institutions", {"code": "RJCS-001"}):
        store.update(institution, {"institution_type": "ENGINEERING_COLLEGE"})
    office = auth(*OFFICE)
    classes = client.post(
        "/api/v1/academics/classes",
        json={"name": "Data Science", "stream": "Engineering", "divisions": ["A"]},
        headers=auth(*PRINCIPAL),
    )
    assert classes.status_code == 201, classes.text

    assert client.post("/api/v1/faculty", json=faculty_payload(), headers=office).status_code == 400
    unknown = client.post("/api/v1/faculty", json=faculty_payload(department="Astrology"), headers=office)
    assert unknown.status_code == 400
    created = client.post("/api/v1/faculty", json=faculty_payload(department="data science"), headers=office)
    assert created.status_code == 201, created.text
    assert created.json()["department"] == "Data Science"
    listed = client.get("/api/v1/faculty?department=Data Science", headers=office).json()
    assert [item["employee_id"] for item in listed] == ["FAC-NEW-01"]


def test_slot_template_drives_how_faculty_build_their_timetable():
    principal = auth(*PRINCIPAL)
    office = auth(*OFFICE)
    faculty = auth(*FACULTY)
    class_11, division_a = class_11_and_division(principal)
    me = client.get("/api/v1/auth/me", headers=faculty).json()
    subjects = {item["code"]: item["id"] for item in client.get("/api/v1/academics/subjects", headers=principal).json()}

    # Faculty cannot define slots; principals and office staff can, for several days at once.
    slot = {"class_id": class_11["id"], "days_of_week": [3], "period_number": 1, "start_time": "09:00:00", "end_time": "10:00:00"}
    assert client.post("/api/v1/timetable/slots", json=slot, headers=faculty).status_code == 403
    created = client.post("/api/v1/timetable/slots", json=slot, headers=office)
    assert created.status_code == 201, created.text
    reserved = client.post(
        "/api/v1/timetable/slots",
        json={**slot, "days_of_week": [3], "period_number": 2, "start_time": "10:00:00", "end_time": "11:00:00", "subject_id": subjects["CHEM-101"]},
        headers=principal,
    )
    assert reserved.status_code == 201, reserved.text

    # Duplicate period and overlapping times are rejected.
    assert client.post("/api/v1/timetable/slots", json=slot, headers=principal).status_code == 409
    overlap = {**slot, "period_number": 3, "start_time": "09:30:00", "end_time": "10:30:00"}
    assert client.post("/api/v1/timetable/slots", json=overlap, headers=principal).status_code == 409

    available = client.get(
        f"/api/v1/timetable/available-slots?division_id={division_a['id']}", headers=faculty
    ).json()
    by_period = {(item["day_of_week"], item["period_number"]): item for item in available}
    assert by_period[(3, 1)]["status"] == "OPEN"
    assert [item["subject_code"] for item in by_period[(3, 1)]["allowed_subjects"]] == ["PHY-101"]
    # Slot reserved for Chemistry offers a Physics teacher nothing to claim.
    assert by_period[(3, 2)]["allowed_subjects"] == []

    entry = {
        "division_id": division_a["id"],
        "subject_id": subjects["PHY-101"],
        "faculty_id": me["faculty_id"],
        "day_of_week": 3,
        "period_number": 1,
        "start_time": "08:00:00",
        "end_time": "08:30:00",
    }
    claimed = client.post("/api/v1/timetable/entries", json=entry, headers=faculty)
    assert claimed.status_code == 201, claimed.text
    # Times come from the slot, not from the request.
    assert claimed.json()["start_time"] == "09:00:00" and claimed.json()["end_time"] == "10:00:00"

    wrong_subject = {**entry, "day_of_week": 3, "period_number": 2}
    assert client.post("/api/v1/timetable/entries", json=wrong_subject, headers=faculty).status_code in (400, 403)
    no_slot = {**entry, "day_of_week": 4, "period_number": 5}
    assert client.post("/api/v1/timetable/entries", json=no_slot, headers=faculty).status_code == 400

    taken = client.get(f"/api/v1/timetable/available-slots?division_id={division_a['id']}", headers=faculty).json()
    assert {(i["day_of_week"], i["period_number"]): i["status"] for i in taken}[(3, 1)] == "TAKEN"

    # A used slot cannot be deleted; its times propagate to scheduled lectures.
    slot_id = created.json()[0]["id"]
    assert client.delete(f"/api/v1/timetable/slots/{slot_id}", headers=principal).status_code == 400
    moved = client.put(
        f"/api/v1/timetable/slots/{slot_id}", json={"start_time": "09:05:00", "end_time": "10:00:00"}, headers=principal
    )
    assert moved.status_code == 200, moved.text
    entries = client.get(f"/api/v1/timetable?division_id={division_a['id']}", headers=principal).json()
    assert next(e for e in entries if (e["day_of_week"], e["period_number"]) == (3, 1))["start_time"] == "09:05:00"

    free_slot_id = reserved.json()[0]["id"]
    assert client.delete(f"/api/v1/timetable/slots/{free_slot_id}", headers=office).status_code == 200


def test_full_name_includes_middle_name_everywhere_a_person_is_added():
    office = auth(*OFFICE)
    principal = auth(*PRINCIPAL)

    faculty = client.post(
        "/api/v1/faculty", json=faculty_payload(middle_name="Kumar"), headers=office
    )
    assert faculty.status_code == 201, faculty.text
    assert faculty.json()["middle_name"] == "Kumar"
    assert faculty.json()["full_name"] == "New Kumar Teacher"

    # The new teacher can log in and sees the complete name on their profile.
    teacher = auth("new.teacher@royalscience.edu", "Teacher@2026")
    me = client.get("/api/v1/auth/me", headers=teacher).json()
    assert me["middle_name"] == "Kumar" and me["full_name"] == "New Kumar Teacher"

    staff = client.post(
        f"/api/v1/institutions/{me['institution_id']}/staff",
        json={"email": "clerk@royalscience.edu", "password": "Clerk@2026", "first_name": "Asha", "middle_name": "Ravi", "last_name": "Patil"},
        headers=principal,
    )
    assert staff.status_code == 201, staff.text
    assert staff.json()["full_name"] == "Asha Ravi Patil"

    # Records created before middle names existed keep working.
    assert client.get("/api/v1/auth/me", headers=principal).json()["full_name"] == "Dr. Arvind Kulkarni"


def test_faculty_and_student_ids_must_be_unique_and_gender_is_required():
    office = auth(*OFFICE)

    missing_gender = faculty_payload()
    del missing_gender["gender"]
    assert client.post("/api/v1/faculty", json=missing_gender, headers=office).status_code == 400
    assert client.post("/api/v1/faculty", json=faculty_payload(gender="robot"), headers=office).status_code == 400

    created = client.post("/api/v1/faculty", json=faculty_payload(gender="female"), headers=office)
    assert created.status_code == 201, created.text
    assert created.json()["gender"] == "FEMALE"

    # Same ID (ignoring case and surrounding spaces) is rejected, even with a different email.
    duplicate = client.post(
        "/api/v1/faculty",
        json=faculty_payload(email="other.teacher@royalscience.edu", employee_id=" fac-new-01 "),
        headers=office,
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Faculty ID 'fac-new-01' already exists"
    assert [item["employee_id"] for item in client.get("/api/v1/faculty", headers=office).json()].count("FAC-NEW-01") == 1

    principal = auth(*PRINCIPAL)
    year = client.get("/api/v1/academics/years", headers=principal).json()[0]
    class_11, division_a = class_11_and_division(principal)
    student = {
        "email": "new.student@royalscience.edu",
        "password": "Student@2026",
        "first_name": "New",
        "middle_name": "Kumar",
        "last_name": "Student",
        "admission_number": "adm-2026-001",
        "date_of_birth": "2009-02-02",
        "gender": "MALE",
        "admission_date": "2026-06-15",
        "academic_year_id": year["id"],
        "class_id": class_11["id"],
        "division_id": division_a["id"],
    }
    clash = client.post("/api/v1/students", json=student, headers=office)
    assert clash.status_code == 400
    assert clash.json()["detail"] == "Student ID 'adm-2026-001' already exists"
    assert client.post("/api/v1/students", json={**student, "gender": "unknown", "admission_number": "ADM-NEW-9"}, headers=office).status_code == 400

    ok = client.post("/api/v1/students", json={**student, "admission_number": "ADM-NEW-9"}, headers=office)
    assert ok.status_code == 201, ok.text
    assert ok.json()["gender"] == "MALE"


def test_each_division_of_a_class_has_its_own_timetable():
    principal = auth(*PRINCIPAL)
    physics_teacher = auth("physics.prof@royalscience.edu", "Faculty@Pass2026")
    chem_teacher = auth("chem.prof@royalscience.edu", "Faculty@Pass2026")
    class_11, division_a = class_11_and_division(principal)
    division_b = next(item for item in class_11["divisions"] if item["name"] == "B")
    year = client.get("/api/v1/academics/years", headers=principal).json()[0]
    subjects = {item["code"]: item["id"] for item in client.get("/api/v1/academics/subjects", headers=principal).json()}
    chem_faculty = client.get("/api/v1/auth/me", headers=chem_teacher).json()["faculty_id"]
    physics_faculty = client.get("/api/v1/auth/me", headers=physics_teacher).json()["faculty_id"]

    slot = {"class_id": class_11["id"], "days_of_week": [5], "period_number": 1, "start_time": "09:00:00", "end_time": "10:00:00"}
    assert client.post("/api/v1/timetable/slots", json=slot, headers=principal).status_code == 201
    assigned = client.post(
        "/api/v1/faculty/assignments",
        json={"academic_year_id": year["id"], "faculty_id": chem_faculty, "subject_id": subjects["CHEM-101"], "division_id": division_b["id"]},
        headers=principal,
    )
    assert assigned.status_code == 201, assigned.text

    def entry(division, subject, faculty):
        return {
            "division_id": division["id"], "subject_id": subjects[subject], "faculty_id": faculty,
            "day_of_week": 5, "period_number": 1, "start_time": "09:00:00", "end_time": "10:00:00",
        }

    assert client.post("/api/v1/timetable/entries", json=entry(division_a, "PHY-101", physics_faculty), headers=physics_teacher).status_code == 201
    # The same slot is still open for division B, which gets a different subject and teacher.
    open_for_b = client.get(f"/api/v1/timetable/available-slots?division_id={division_b['id']}", headers=chem_teacher).json()
    assert next(i for i in open_for_b if (i["day_of_week"], i["period_number"]) == (5, 1))["status"] == "OPEN"
    assert client.post("/api/v1/timetable/entries", json=entry(division_b, "CHEM-101", chem_faculty), headers=chem_teacher).status_code == 201

    def at_friday_first_period(division):
        rows = client.get(f"/api/v1/timetable?division_id={division['id']}", headers=principal).json()
        return [row["subject_code"] for row in rows if (row["day_of_week"], row["period_number"]) == (5, 1)]

    assert at_friday_first_period(division_a) == ["PHY-101"]
    assert at_friday_first_period(division_b) == ["CHEM-101"]


def test_existing_institute_gets_missing_standard_subjects_without_duplicates(isolated_mongo_store):
    from app.core.default_subjects import ensure_default_subjects

    store = isolated_mongo_store
    royal = store.find_one("institutions", {"code": "RJCS-001"})
    assert ensure_default_subjects(store, royal.id) == 4  # Information Technology, Marathi, Hindi, Environmental Education
    assert ensure_default_subjects(store, royal.id) == 0
    names = [item["name"] for item in client.get("/api/v1/academics/subjects", headers=auth(*PRINCIPAL)).json()]
    assert {"Marathi", "Hindi", "Environmental Education", "Information Technology"} <= set(names)
    assert names.count("Physics") == 1
