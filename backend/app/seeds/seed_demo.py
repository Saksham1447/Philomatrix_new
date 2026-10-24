"""Idempotently populate the demo institution data through the shared DocStore."""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from app.core.database import (
    get_control_store,
    get_tenant_store,
    invalidate_institution_cache,
    provision_tenant_database,
)
from app.core.docstore import DocStore
from app.core.security import get_password_hash

_PASSWORD_HASHES: dict[str, str] = {}


def _ensure(store: DocStore, collection: str, identity: dict, values: dict):
    """Return the existing record or create it without overwriting user changes."""
    return store.find_one(collection, identity) or store.insert(collection, values)


def run_seed(store: DocStore | None = None, isolate_institutions: bool = False) -> None:
    """Seed the system/demo identities and the complete academic demo lifecycle.

    ``store`` is injectable so tests and local tooling can use mongomock.  When
    omitted, the configured control store is used; this function never opens a
    SQLAlchemy session or reads database credentials itself.
    """
    db = store or get_control_store()
    print("[SEED] Commencing PHILOMATRIX Seed Data Generation...")

    # System roles and platform accounts.
    role_names = ("SUPER_ADMIN", "PRINCIPAL", "FACULTY", "STUDENT", "PARENT", "OFFICE_STAFF")
    roles = {
        name: _ensure(db, "roles", {"name": name}, {"name": name, "description": f"{name} role permissions"})
        for name in role_names
    }

    def user(username, email, password, first_name, last_name, phone, institution_id=None):
        record = db.find_one("users", {"email": email})
        if record:
            return record
        if email not in _PASSWORD_HASHES:
            _PASSWORD_HASHES[email] = get_password_hash(password)
        return db.insert(
            "users",
            {
                "institution_id": institution_id,
                "username": username,
                "email": email,
                "password_hash": _PASSWORD_HASHES[email],
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone,
                "is_active": True,
                "is_verified": True,
            },
        )

    def assign_role(account, role_name, institution_id=None):
        _ensure(
            db,
            "user_role_assignments",
            {
                "user_id": account.id,
                "role_id": roles[role_name].id,
                "institution_id": institution_id,
            },
            {
                "user_id": account.id,
                "role_id": roles[role_name].id,
                "institution_id": institution_id,
            },
        )

    platform_admin = user(
        "superadmin", "superadmin@philomatrix.local", "Philomatrix@2026",
        "Platform", "SuperAdmin", "+91 9999900000",
    )
    assign_role(platform_admin, "SUPER_ADMIN")
    named_admin = user(
        "SuperAdmin", "superadmin.admin@philomatrix.local", "SuperAdmin@123",
        "Platform", "Administrator", "+91 9999900000",
    )
    assign_role(named_admin, "SUPER_ADMIN")

    # Demo institutions are registered in the control store. With isolate_institutions,
    # each college's data lives in its own collection namespace; otherwise (tests) one store is used.
    control = db

    def use_store(target: DocStore) -> None:
        nonlocal db, roles
        db = target
        roles = {role.name: role for role in db.find("roles")}

    def tenant_store(institution) -> DocStore:
        if not isolate_institutions:
            return control
        if institution.database_url:
            return get_tenant_store(institution.database_url)
        database_name = provision_tenant_database(institution)
        control.update(institution, {"database_url": database_name})
        invalidate_institution_cache(institution.id)
        return get_tenant_store(database_name)
    inst_a = _ensure(
        db,
        "institutions",
        {"code": "RJCS-001"},
        {
            "name": "Royal Junior College of Science",
            "slug": "royal-science-jc",
            "code": "RJCS-001",
            "status": "ACTIVE",
            "address": "Plot 42, Academic Boulevard, Shivajinagar",
            "city": "Pune",
            "state": "Maharashtra",
            "pincode": "411005",
            "phone": "+91 20 25501234",
            "email": "contact@royalscience.edu",
            "logo_url": "https://images.unsplash.com/photo-1592280771190-3e2e4d571952?w=150",
        },
    )
    inst_b = _ensure(
        db,
        "institutions",
        {"code": "APEX-002"},
        {
            "name": "Apex Science Junior College",
            "slug": "apex-science-jc",
            "code": "APEX-002",
            "status": "ACTIVE",
            "address": "Sector 18, Vashi",
            "city": "Navi Mumbai",
            "state": "Maharashtra",
            "pincode": "400703",
            "phone": "+91 22 27805678",
            "email": "admin@apexcollege.edu",
        },
    )
    _ensure(
        db,
        "institution_settings",
        {"institution_id": inst_a.id},
        {
            "institution_id": inst_a.id,
            "min_attendance_threshold": Decimal("75.00"),
            "allow_late_as_present": True,
            "enable_parent_sms_alerts": False,
            "report_card_template_id": "STANDARD_V1",
        },
    )
    _ensure(
        db,
        "institution_settings",
        {"institution_id": inst_b.id},
        {
            "institution_id": inst_b.id,
            "min_attendance_threshold": Decimal("75.00"),
            "allow_late_as_present": True,
        },
    )

    principal_b_store = tenant_store(inst_b)
    use_store(principal_b_store)
    principal_b = user(
        "principal_apex", "principal@apexcollege.edu", "Apex@Principal2026",
        "Dr. Meenakshi", "Sundaram", "+91 9822099887", inst_b.id,
    )
    assign_role(principal_b, "PRINCIPAL", inst_b.id)

    # Everything below belongs to Royal Junior College of Science.
    use_store(tenant_store(inst_a))
    principal_a = user(
        "principal_rjcs", "principal@royalscience.edu", "Royal@Principal2026",
        "Dr. Arvind", "Kulkarni", "+91 9822011223", inst_a.id,
    )
    assign_role(principal_a, "PRINCIPAL", inst_a.id)
    staff_a = user(
        "admissions_rjcs", "admissions@royalscience.edu", "Staff@Pass2026",
        "Ramesh", "Joshi", "+91 9822044556", inst_a.id,
    )
    assign_role(staff_a, "OFFICE_STAFF", inst_a.id)

    # Academic year, classes, divisions, and subjects.
    year = _ensure(
        db,
        "academic_years",
        {"institution_id": inst_a.id, "name": "2026-2027"},
        {
            "institution_id": inst_a.id,
            "name": "2026-2027",
            "start_date": date(2026, 6, 15),
            "end_date": date(2027, 4, 30),
            "is_current": True,
            "is_archived": False,
        },
    )
    classes = {
        name: _ensure(
            db,
            "classes",
            {"institution_id": inst_a.id, "name": name, "stream": "SCIENCE"},
            {
                "institution_id": inst_a.id,
                "name": name,
                "stream": "SCIENCE",
                "display_order": order,
            },
        )
        for name, order in (("Class 11", 1), ("Class 12", 2))
    }
    div_11a = _ensure(
        db,
        "divisions",
        {"class_id": classes["Class 11"].id, "name": "A"},
        {
            "institution_id": inst_a.id,
            "class_id": classes["Class 11"].id,
            "name": "A",
            "room_number": "Lab-Hall 101",
            "capacity": 60,
        },
    )
    div_11b = _ensure(
        db,
        "divisions",
        {"class_id": classes["Class 11"].id, "name": "B"},
        {
            "institution_id": inst_a.id,
            "class_id": classes["Class 11"].id,
            "name": "B",
            "room_number": "Lab-Hall 102",
            "capacity": 60,
        },
    )
    subject_specs = (
        ("PHY-101", "Physics", True, 70, 30),
        ("CHEM-101", "Chemistry", True, 70, 30),
        ("MATH-101", "Mathematics & Statistics", True, 80, 20),
        ("BIO-101", "Biology", True, 70, 30),
        ("ENG-101", "English", False, 80, 20),
        ("CS-101", "Computer Science", True, 50, 50),
    )
    subjects = {}
    for code, name, practical, theory, lab in subject_specs:
        subjects[code] = _ensure(
            db,
            "subjects",
            {"institution_id": inst_a.id, "code": code},
            {
                "institution_id": inst_a.id,
                "code": code,
                "name": name,
                "stream": "SCIENCE",
                "has_practical": practical,
                "max_theory_marks": Decimal(str(theory)),
                "max_practical_marks": Decimal(str(lab)),
                "min_pass_percentage": Decimal("35.00"),
            },
        )

    # Faculty identities, profiles, and teaching assignments.
    faculty_specs = (
        ("prof_verma", "physics.prof@royalscience.edu", "Rajesh", "Verma", "FAC-PHY-01", "Physics", "M.Sc. Physics (Gold Medalist), B.Ed.", "PHY-101"),
        ("prof_kulkarni", "chem.prof@royalscience.edu", "Sunita", "Kulkarni", "FAC-CHM-02", "Chemistry", "Ph.D. Organic Chemistry", "CHEM-101"),
        ("prof_deshmukh", "math.prof@royalscience.edu", "Amit", "Deshmukh", "FAC-MTH-03", "Mathematics", "M.Sc. Applied Mathematics", "MATH-101"),
    )
    faculty = {}
    for username, email, first, last, employee_id, department, qualification, subject_code in faculty_specs:
        account = user(
            username, email, "Faculty@Pass2026", first, last,
            "+91 9823000111", inst_a.id,
        )
        assign_role(account, "FACULTY", inst_a.id)
        profile = _ensure(
            db,
            "faculty_profiles",
            {"user_id": account.id},
            {
                "user_id": account.id,
                "institution_id": inst_a.id,
                "employee_id": employee_id,
                "gender": {"FAC-PHY-01": "MALE", "FAC-CHM-02": "FEMALE", "FAC-MTH-03": "MALE"}[employee_id],
                "designation": "Senior Lecturer",
                "department": department,
                "qualification": qualification,
            },
        )
        faculty[subject_code] = profile
        _ensure(
            db,
            "faculty_subject_assignments",
            {
                "academic_year_id": year.id,
                "faculty_id": profile.id,
                "subject_id": subjects[subject_code].id,
                "division_id": div_11a.id,
            },
            {
                "institution_id": inst_a.id,
                "academic_year_id": year.id,
                "faculty_id": profile.id,
                "subject_id": subjects[subject_code].id,
                "division_id": div_11a.id,
                "is_class_teacher": subject_code == "PHY-101",
            },
        )

    # Timetable for class 11-A: Monday and Tuesday morning periods.
    timetable = _ensure(
        db,
        "timetable_versions",
        {"institution_id": inst_a.id, "is_active": True},
        {
            "institution_id": inst_a.id,
            "academic_year_id": year.id,
            "version_number": 1,
            "is_active": True,
        },
    )
    timetable_specs = (
        (1, 1, time(9, 0), time(10, 0), "PHY-101"),
        (1, 2, time(10, 0), time(11, 0), "CHEM-101"),
        (1, 3, time(11, 15), time(12, 15), "MATH-101"),
        (2, 1, time(9, 0), time(10, 0), "CHEM-101"),
        (2, 2, time(10, 0), time(11, 0), "PHY-101"),
    )
    for day, period, starts, ends, subject_code in timetable_specs:
        _ensure(
            db,
            "timetable_entries",
            {
                "timetable_version_id": timetable.id,
                "division_id": div_11a.id,
                "day_of_week": day,
                "period_number": period,
            },
            {
                "timetable_version_id": timetable.id,
                "institution_id": inst_a.id,
                "division_id": div_11a.id,
                "subject_id": subjects[subject_code].id,
                "faculty_id": faculty[subject_code].id,
                "day_of_week": day,
                "period_number": period,
                "start_time": starts,
                "end_time": ends,
                "room_number": "Hall 101",
            },
        )

    # Division slot templates, used by faculty to build their own timetable.
    # Only seeded when each college has its own namespace; the shared-store test seed
    # leaves classes free-form so tests can schedule arbitrary periods.
    if isolate_institutions:
        slot_periods = (
            (1, time(9, 0), time(10, 0)),
            (2, time(10, 0), time(11, 0)),
            (3, time(11, 15), time(12, 15)),
            (4, time(12, 15), time(13, 15)),
            (5, time(13, 50), time(14, 50)),
            (6, time(14, 50), time(15, 50)),
        )
        for division in (div_11a, div_11b):
            for day in range(1, 7):
                for period, starts, ends in slot_periods:
                    _ensure(
                        db,
                        "timetable_slots",
                        {"division_id": division.id, "day_of_week": day, "period_number": period},
                        {
                            "institution_id": inst_a.id,
                            "division_id": division.id,
                            "day_of_week": day,
                            "period_number": period,
                            "start_time": starts,
                            "end_time": ends,
                        },
                    )

    # Students, accounts, enrollments, and the one linked guardian.
    students_specs = (
        ("arjun_sharma", "arjun.sharma@royalscience.edu", "Arjun", "Sharma", "ADM-2026-001", "101", "MALE", date(2009, 5, 14), "+91 9822112233"),
        ("priya_patel", "priya.patel@royalscience.edu", "Priya", "Patel", "ADM-2026-002", "102", "FEMALE", date(2009, 8, 22), "+91 9822112244"),
        ("rohan_gupta", "rohan.gupta@royalscience.edu", "Rohan", "Gupta", "ADM-2026-003", "103", "MALE", date(2009, 11, 5), "+91 9822112255"),
        ("ananya_iyer", "ananya.iyer@royalscience.edu", "Ananya", "Iyer", "ADM-2026-004", "104", "FEMALE", date(2009, 3, 19), "+91 9822112266"),
    )
    students = []
    for username, email, first, last, admission_no, roll, gender, dob, phone in students_specs:
        account = user(username, email, "Student@Pass2026", first, last, phone, inst_a.id)
        assign_role(account, "STUDENT", inst_a.id)
        student = _ensure(
            db,
            "students",
            {"user_id": account.id},
            {
                "user_id": account.id,
                "institution_id": inst_a.id,
                "admission_number": admission_no,
                "roll_number": roll,
                "date_of_birth": dob,
                "gender": gender,
                "blood_group": "O+",
                "admission_date": date(2026, 6, 18),
                "address": "Lane 7, Kothrud, Pune",
                "emergency_contact_name": "Family Emergency",
                "emergency_contact_phone": "+91 9822998877",
                "status": "ACTIVE",
            },
        )
        students.append(student)
        _ensure(
            db,
            "enrollments",
            {"academic_year_id": year.id, "student_id": student.id},
            {
                "institution_id": inst_a.id,
                "student_id": student.id,
                "academic_year_id": year.id,
                "class_id": classes["Class 11"].id,
                "division_id": div_11a.id,
                "roll_number": roll,
                "status": "ENROLLED",
            },
        )

    arjun_account = db.find_one("users", {"email": "arjun.sharma@royalscience.edu"})
    guardian_account = user(
        "parent_vikram", "parent.sharma@gmail.com", "Parent@Pass2026",
        "Vikram", "Sharma", "+91 9822119900", inst_a.id,
    )
    assign_role(guardian_account, "PARENT", inst_a.id)
    guardian = _ensure(
        db,
        "guardians",
        {"user_id": guardian_account.id},
        {
            "user_id": guardian_account.id,
            "institution_id": inst_a.id,
            "relationship_type": "FATHER",
            "occupation": "Architect",
            "alternative_phone": "+91 9822119901",
        },
    )
    arjun = db.find_one("students", {"user_id": arjun_account.id})
    _ensure(
        db,
        "student_guardian_links",
        {"student_id": arjun.id, "guardian_id": guardian.id},
        {
            "student_id": arjun.id,
            "guardian_id": guardian.id,
            "is_primary": True,
            "is_verified": True,
        },
    )

    # Historical submitted Physics attendance, including seeded absence/excused cases.
    for offset in range(1, 6):
        session_date = date.today() - timedelta(days=offset)
        if session_date.weekday() >= 6:
            continue
        session = _ensure(
            db,
            "attendance_sessions",
            {
                "division_id": div_11a.id,
                "subject_id": subjects["PHY-101"].id,
                "session_date": session_date,
                "period_number": 1,
            },
            {
                "institution_id": inst_a.id,
                "academic_year_id": year.id,
                "division_id": div_11a.id,
                "subject_id": subjects["PHY-101"].id,
                "faculty_id": faculty["PHY-101"].id,
                "session_date": session_date,
                "period_number": 1,
                "submission_status": "SUBMITTED",
            },
        )
        for student in students:
            status = "PRESENT"
            if student.admission_number == "ADM-2026-003" and offset in (1, 2, 4):
                status = "ABSENT"
            elif student.admission_number == "ADM-2026-002" and offset == 3:
                status = "EXCUSED"
            _ensure(
                db,
                "attendance_records",
                {"attendance_session_id": session.id, "student_id": student.id},
                {
                    "attendance_session_id": session.id,
                    "student_id": student.id,
                    "status": status,
                },
            )

    # Unit Test 1, subjects, marks, approval, and published results.
    exam = _ensure(
        db,
        "examinations",
        {"institution_id": inst_a.id, "name": "Unit Test 1 (Term 1)"},
        {
            "institution_id": inst_a.id,
            "academic_year_id": year.id,
            "name": "Unit Test 1 (Term 1)",
            "exam_type": "UNIT_TEST",
            "start_date": date(2026, 8, 10),
            "end_date": date(2026, 8, 16),
            "status": "PUBLISHED",
        },
    )
    exam_subjects = {}
    for code, exam_day in (("PHY-101", date(2026, 8, 10)), ("CHEM-101", date(2026, 8, 12))):
        exam_subjects[code] = _ensure(
            db,
            "exam_subjects",
            {
                "examination_id": exam.id,
                "subject_id": subjects[code].id,
                "class_id": classes["Class 11"].id,
            },
            {
                "examination_id": exam.id,
                "subject_id": subjects[code].id,
                "class_id": classes["Class 11"].id,
                "max_theory_marks": Decimal("70.00"),
                "max_practical_marks": Decimal("30.00"),
                "min_passing_marks": Decimal("35.00"),
                "exam_date": exam_day,
            },
        )
    marks = {
        "ADM-2026-001": (Decimal("62.50"), Decimal("28.00")),
        "ADM-2026-002": (Decimal("58.00"), Decimal("27.50")),
        "ADM-2026-003": (Decimal("40.00"), Decimal("22.00")),
        "ADM-2026-004": (Decimal("65.00"), Decimal("29.00")),
    }
    for student in students:
        theory, practical = marks.get(student.admission_number, (Decimal("50.00"), Decimal("25.00")))
        _ensure(
            db,
            "marks_entries",
            {"exam_subject_id": exam_subjects["PHY-101"].id, "student_id": student.id},
            {
                "exam_subject_id": exam_subjects["PHY-101"].id,
                "student_id": student.id,
                "division_id": div_11a.id,
                "theory_marks_obtained": theory,
                "practical_marks_obtained": practical,
                "total_obtained": theory + practical,
                "is_absent": False,
                "is_exempt": False,
                "entered_by": faculty["PHY-101"].user_id,
                "status": "APPROVED",
                "teacher_remarks": "Exceptional problem solving in mechanics.",
            },
        )
    now = datetime.now(timezone.utc)
    _ensure(
        db,
        "marks_approvals",
        {"exam_subject_id": exam_subjects["PHY-101"].id, "division_id": div_11a.id},
        {
            "exam_subject_id": exam_subjects["PHY-101"].id,
            "division_id": div_11a.id,
            "submitted_by": faculty["PHY-101"].user_id,
            "submitted_at": now - timedelta(days=10),
            "status": "APPROVED",
            "reviewed_by": principal_a.id,
            "reviewed_at": now - timedelta(days=9),
            "review_comments": "Marks verified and approved.",
        },
    )
    _ensure(
        db,
        "result_publications",
        {"examination_id": exam.id, "class_id": classes["Class 11"].id},
        {
            "examination_id": exam.id,
            "class_id": classes["Class 11"].id,
            "published_by": principal_a.id,
            "published_at": now - timedelta(days=8),
            "is_active": True,
        },
    )

    # Notices, assignments, and feedback content.
    for title, content, priority in (
        (
            "Class 11 Science Laboratory Practical Orientation",
            "All Class 11 Science students of Division A & B are instructed to attend mandatory safety protocols orientation in the Chemistry Lab on Monday at 09:00 AM.",
            "URGENT",
        ),
        (
            "Term-1 Board Model Examination Notification",
            "The timetable for the upcoming Term-1 Preliminary Board assessments will be released next week. Parents are advised to monitor progress via portal.",
            "NORMAL",
        ),
    ):
        _ensure(
            db,
            "notices",
            {"institution_id": inst_a.id, "title": title},
            {
                "institution_id": inst_a.id,
                "title": title,
                "content": content,
                "audience_role": "ALL",
                "priority": priority,
                "published_by": principal_a.id,
                "is_published": True,
            },
        )
    _ensure(
        db,
        "assignments",
        {"institution_id": inst_a.id, "title": "Physics Numerical Problems: Projectile Motion"},
        {
            "institution_id": inst_a.id,
            "division_id": div_11a.id,
            "subject_id": subjects["PHY-101"].id,
            "faculty_id": faculty["PHY-101"].id,
            "title": "Physics Numerical Problems: Projectile Motion",
            "description": "Complete textbook problems 4.1 through 4.15 from Chapter 4. Include clear vector diagrams and units.",
            "due_date": now + timedelta(days=5),
        },
    )
    feedback_form = _ensure(
        db,
        "feedback_forms",
        {"institution_id": inst_a.id, "title": "First Month Science Laboratory & Academic Experience"},
        {
            "institution_id": inst_a.id,
            "title": "First Month Science Laboratory & Academic Experience",
            "target_role": "STUDENT",
            "is_anonymous": True,
            "is_open": True,
        },
    )
    for index, question, kind in (
        (1, "How would you rate the clarity of Physics theory lectures?", "RATING_1_5"),
        (2, "Are the science laboratory instruments and equipment well maintained?", "RATING_1_5"),
        (3, "What additional academic support or doubt sessions would you recommend?", "TEXT"),
    ):
        _ensure(
            db,
            "feedback_questions",
            {"feedback_form_id": feedback_form.id, "display_order": index},
            {
                "feedback_form_id": feedback_form.id,
                "question_text": question,
                "question_type": kind,
                "display_order": index,
            },
        )

    print("[SUCCESS] PHILOMATRIX Seed Data Generation Completed Successfully!")


if __name__ == "__main__":
    run_seed(isolate_institutions=True)
