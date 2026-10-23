from datetime import date, datetime, time, timezone, timedelta
from decimal import Decimal
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.institution import Institution, InstitutionSetting
from app.models.user import User, Role, UserRoleAssignment
from app.models.academic import (
    AcademicYear,
    ClassModel,
    Division,
    Subject,
    FacultyProfile,
    FacultySubjectAssignment,
)
from app.models.student import Student, Guardian, StudentGuardianLink, Enrollment
from app.models.timetable import TimetableVersion, TimetableEntry
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.examination import (
    Examination,
    ExamSubject,
    MarksEntry,
    MarksApproval,
    ResultPublication,
)
from app.models.communication import Assignment, Notice, FeedbackForm, FeedbackQuestion, Notification, AuditLog


def run_seed():
    db = SessionLocal()
    print("[SEED] Commencing PHILOMATRIX Seed Data Generation...")

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    # 1. System Roles
    role_names = ["SUPER_ADMIN", "PRINCIPAL", "FACULTY", "STUDENT", "PARENT", "OFFICE_STAFF"]
    roles_map = {}
    for r_name in role_names:
        r = db.query(Role).filter(Role.name == r_name).first()
        if not r:
            r = Role(name=r_name, description=f"{r_name} role permissions")
            db.add(r)
            db.flush()
        roles_map[r_name] = r

    # 2. SaaS Super Admin
    super_admin = db.query(User).filter(User.email == "superadmin@philomatrix.local").first()
    if not super_admin:
        super_admin = User(
            username="superadmin",
            email="superadmin@philomatrix.local",
            password_hash=get_password_hash("Philomatrix@2026"),
            first_name="Platform",
            last_name="SuperAdmin",
            phone_number="+91 9999900000",
            is_active=True,
            is_verified=True
        )
        db.add(super_admin)
        db.flush()
        db.add(UserRoleAssignment(user_id=super_admin.id, role_id=roles_map["SUPER_ADMIN"].id))

    # Additional platform administrator login
    named_super_admin = db.query(User).filter(User.username == "SuperAdmin").first()
    if not named_super_admin:
        named_super_admin = User(
            username="SuperAdmin",
            email="superadmin.admin@philomatrix.local",
            password_hash=get_password_hash("SuperAdmin@123"),
            first_name="Platform",
            last_name="Administrator",
            phone_number="+91 9999900000",
            is_active=True,
            is_verified=True
        )
        db.add(named_super_admin)
        db.flush()
        db.add(UserRoleAssignment(
            user_id=named_super_admin.id,
            role_id=roles_map["SUPER_ADMIN"].id
        ))

    # 3. Demo Institution A (Royal Junior College of Science)
    inst_a = db.query(Institution).filter(Institution.code == "RJCS-001").first()
    if not inst_a:
        inst_a = Institution(
            name="Royal Junior College of Science",
            slug="royal-science-jc",
            code="RJCS-001",
            status="ACTIVE",
            address="Plot 42, Academic Boulevard, Shivajinagar",
            city="Pune",
            state="Maharashtra",
            pincode="411005",
            phone="+91 20 25501234",
            email="contact@royalscience.edu",
            logo_url="https://images.unsplash.com/photo-1592280771190-3e2e4d571952?w=150"
        )
        db.add(inst_a)
        db.flush()

        db.add(InstitutionSetting(
            institution_id=inst_a.id,
            min_attendance_threshold=Decimal("75.00"),
            allow_late_as_present=True,
            enable_parent_sms_alerts=False,
            report_card_template_id="STANDARD_V1"
        ))

    # 4. Demo Institution B (Apex Science Junior College - for isolation testing)
    inst_b = db.query(Institution).filter(Institution.code == "APEX-002").first()
    if not inst_b:
        inst_b = Institution(
            name="Apex Science Junior College",
            slug="apex-science-jc",
            code="APEX-002",
            status="ACTIVE",
            address="Sector 18, Vashi",
            city="Navi Mumbai",
            state="Maharashtra",
            pincode="400703",
            phone="+91 22 27805678",
            email="admin@apexcollege.edu"
        )
        db.add(inst_b)
        db.flush()

        db.add(InstitutionSetting(
            institution_id=inst_b.id,
            min_attendance_threshold=Decimal("75.00"),
            allow_late_as_present=True
        ))

    # 5. Principal for Institution A
    principal_a = db.query(User).filter(User.email == "principal@royalscience.edu").first()
    if not principal_a:
        principal_a = User(
            institution_id=inst_a.id,
            username="principal_rjcs",
            email="principal@royalscience.edu",
            password_hash=get_password_hash("Royal@Principal2026"),
            first_name="Dr. Arvind",
            last_name="Kulkarni",
            phone_number="+91 9822011223",
            is_active=True,
            is_verified=True
        )
        db.add(principal_a)
        db.flush()
        db.add(UserRoleAssignment(user_id=principal_a.id, role_id=roles_map["PRINCIPAL"].id, institution_id=inst_a.id))

    # Principal for Institution B (Tenant B)
    principal_b = db.query(User).filter(User.email == "principal@apexcollege.edu").first()
    if not principal_b:
        principal_b = User(
            institution_id=inst_b.id,
            username="principal_apex",
            email="principal@apexcollege.edu",
            password_hash=get_password_hash("Apex@Principal2026"),
            first_name="Dr. Meenakshi",
            last_name="Sundaram",
            phone_number="+91 9822099887",
            is_active=True,
            is_verified=True
        )
        db.add(principal_b)
        db.flush()
        db.add(UserRoleAssignment(user_id=principal_b.id, role_id=roles_map["PRINCIPAL"].id, institution_id=inst_b.id))

    # 6. Office Staff for Institution A
    staff_a = db.query(User).filter(User.email == "admissions@royalscience.edu").first()
    if not staff_a:
        staff_a = User(
            institution_id=inst_a.id,
            username="admissions_rjcs",
            email="admissions@royalscience.edu",
            password_hash=get_password_hash("Staff@Pass2026"),
            first_name="Ramesh",
            last_name="Joshi",
            phone_number="+91 9822044556",
            is_active=True,
            is_verified=True
        )
        db.add(staff_a)
        db.flush()
        db.add(UserRoleAssignment(user_id=staff_a.id, role_id=roles_map["OFFICE_STAFF"].id, institution_id=inst_a.id))

    # 7. Academic Year for Institution A
    acad_year = db.query(AcademicYear).filter(AcademicYear.institution_id == inst_a.id, AcademicYear.name == "2026-2027").first()
    if not acad_year:
        acad_year = AcademicYear(
            institution_id=inst_a.id,
            name="2026-2027",
            start_date=date(2026, 6, 15),
            end_date=date(2027, 4, 30),
            is_current=True,
            is_archived=False
        )
        db.add(acad_year)
        db.flush()

    # 8. Classes & Divisions for Institution A
    class_11 = db.query(ClassModel).filter(ClassModel.institution_id == inst_a.id, ClassModel.name == "Class 11").first()
    if not class_11:
        class_11 = ClassModel(
            institution_id=inst_a.id,
            name="Class 11",
            stream="SCIENCE",
            display_order=1
        )
        db.add(class_11)
        db.flush()

    class_12 = db.query(ClassModel).filter(ClassModel.institution_id == inst_a.id, ClassModel.name == "Class 12").first()
    if not class_12:
        class_12 = ClassModel(
            institution_id=inst_a.id,
            name="Class 12",
            stream="SCIENCE",
            display_order=2
        )
        db.add(class_12)
        db.flush()

    div_11a = db.query(Division).filter(Division.class_id == class_11.id, Division.name == "A").first()
    if not div_11a:
        div_11a = Division(
            institution_id=inst_a.id,
            class_id=class_11.id,
            name="A",
            room_number="Lab-Hall 101",
            capacity=60
        )
        db.add(div_11a)
        db.flush()

    div_11b = db.query(Division).filter(Division.class_id == class_11.id, Division.name == "B").first()
    if not div_11b:
        div_11b = Division(
            institution_id=inst_a.id,
            class_id=class_11.id,
            name="B",
            room_number="Lab-Hall 102",
            capacity=60
        )
        db.add(div_11b)
        db.flush()

    # 9. Subjects for Junior College Science
    subjects_spec = [
        {"code": "PHY-101", "name": "Physics", "has_practical": True, "theory": 70, "practical": 30},
        {"code": "CHEM-101", "name": "Chemistry", "has_practical": True, "theory": 70, "practical": 30},
        {"code": "MATH-101", "name": "Mathematics & Statistics", "has_practical": True, "theory": 80, "practical": 20},
        {"code": "BIO-101", "name": "Biology", "has_practical": True, "theory": 70, "practical": 30},
        {"code": "ENG-101", "name": "English", "has_practical": False, "theory": 80, "practical": 20},
        {"code": "CS-101", "name": "Computer Science", "has_practical": True, "theory": 50, "practical": 50},
    ]
    subjects_map = {}
    for s_info in subjects_spec:
        sub = db.query(Subject).filter(Subject.institution_id == inst_a.id, Subject.code == s_info["code"]).first()
        if not sub:
            sub = Subject(
                institution_id=inst_a.id,
                code=s_info["code"],
                name=s_info["name"],
                stream="SCIENCE",
                has_practical=s_info["has_practical"],
                max_theory_marks=Decimal(str(s_info["theory"])),
                max_practical_marks=Decimal(str(s_info["practical"])),
                min_pass_percentage=Decimal("35.00")
            )
            db.add(sub)
            db.flush()
        subjects_map[s_info["code"]] = sub

    # 10. Faculty Members
    faculty_spec = [
        {
            "username": "prof_verma",
            "email": "physics.prof@royalscience.edu",
            "first": "Rajesh",
            "last": "Verma",
            "emp_id": "FAC-PHY-01",
            "dept": "Physics",
            "qual": "M.Sc. Physics (Gold Medalist), B.Ed.",
            "subject_code": "PHY-101"
        },
        {
            "username": "prof_kulkarni",
            "email": "chem.prof@royalscience.edu",
            "first": "Sunita",
            "last": "Kulkarni",
            "emp_id": "FAC-CHM-02",
            "dept": "Chemistry",
            "qual": "Ph.D. Organic Chemistry",
            "subject_code": "CHEM-101"
        },
        {
            "username": "prof_deshmukh",
            "email": "math.prof@royalscience.edu",
            "first": "Amit",
            "last": "Deshmukh",
            "emp_id": "FAC-MTH-03",
            "dept": "Mathematics",
            "qual": "M.Sc. Applied Mathematics",
            "subject_code": "MATH-101"
        }
    ]
    faculty_map = {}
    for f in faculty_spec:
        u = db.query(User).filter(User.email == f["email"]).first()
        if not u:
            u = User(
                institution_id=inst_a.id,
                username=f["username"],
                email=f["email"],
                password_hash=get_password_hash("Faculty@Pass2026"),
                first_name=f["first"],
                last_name=f["last"],
                phone_number="+91 9823000111",
                is_active=True,
                is_verified=True
            )
            db.add(u)
            db.flush()
            db.add(UserRoleAssignment(user_id=u.id, role_id=roles_map["FACULTY"].id, institution_id=inst_a.id))

            fp = FacultyProfile(
                user_id=u.id,
                institution_id=inst_a.id,
                employee_id=f["emp_id"],
                designation="Senior Lecturer",
                department=f["dept"],
                qualification=f["qual"]
            )
            db.add(fp)
            db.flush()

            # Assign to Division A
            db.add(FacultySubjectAssignment(
                institution_id=inst_a.id,
                academic_year_id=acad_year.id,
                faculty_id=fp.id,
                subject_id=subjects_map[f["subject_code"]].id,
                division_id=div_11a.id,
                is_class_teacher=(f["subject_code"] == "PHY-101")
            ))
            faculty_map[f["subject_code"]] = fp
        else:
            faculty_map[f["subject_code"]] = u.faculty_profile

    # 11. Timetable Setup (Class 11-A)
    tt_ver = db.query(TimetableVersion).filter(TimetableVersion.institution_id == inst_a.id, TimetableVersion.is_active == True).first()
    if not tt_ver:
        tt_ver = TimetableVersion(
            institution_id=inst_a.id,
            academic_year_id=acad_year.id,
            version_number=1,
            is_active=True
        )
        db.add(tt_ver)
        db.flush()

    # Schedule: Monday Periods 1, 2, 3 for 11-A
    entries_spec = [
        {"day": 1, "period": 1, "start": time(9, 0), "end": time(10, 0), "code": "PHY-101", "room": "Hall 101"},
        {"day": 1, "period": 2, "start": time(10, 0), "end": time(11, 0), "code": "CHEM-101", "room": "Hall 101"},
        {"day": 1, "period": 3, "start": time(11, 15), "end": time(12, 15), "code": "MATH-101", "room": "Hall 101"},
        {"day": 2, "period": 1, "start": time(9, 0), "end": time(10, 0), "code": "CHEM-101", "room": "Hall 101"},
        {"day": 2, "period": 2, "start": time(10, 0), "end": time(11, 0), "code": "PHY-101", "room": "Hall 101"},
    ]
    timetable_slots = []
    for es in entries_spec:
        sub = subjects_map[es["code"]]
        fac = faculty_map[es["code"]]
        tte = (
            db.query(TimetableEntry)
            .filter(
                TimetableEntry.timetable_version_id == tt_ver.id,
                TimetableEntry.division_id == div_11a.id,
                TimetableEntry.day_of_week == es["day"],
                TimetableEntry.period_number == es["period"]
            )
            .first()
        )
        if not tte:
            tte = TimetableEntry(
                timetable_version_id=tt_ver.id,
                institution_id=inst_a.id,
                division_id=div_11a.id,
                subject_id=sub.id,
                faculty_id=fac.id,
                day_of_week=es["day"],
                period_number=es["period"],
                start_time=es["start"],
                end_time=es["end"],
                room_number=es["room"]
            )
            db.add(tte)
            db.flush()
        timetable_slots.append(tte)

    # 12. Students & Guardians
    students_spec = [
        {
            "username": "arjun_sharma",
            "email": "arjun.sharma@royalscience.edu",
            "first": "Arjun",
            "last": "Sharma",
            "adm_no": "ADM-2026-001",
            "roll": "101",
            "gender": "MALE",
            "dob": date(2009, 5, 14),
            "guardian_email": "parent.sharma@gmail.com",
            "guardian_name": "Vikram Sharma",
            "relation": "FATHER",
            "phone": "+91 9822112233"
        },
        {
            "username": "priya_patel",
            "email": "priya.patel@royalscience.edu",
            "first": "Priya",
            "last": "Patel",
            "adm_no": "ADM-2026-002",
            "roll": "102",
            "gender": "FEMALE",
            "dob": date(2009, 8, 22),
            "guardian_email": None,
            "guardian_name": None,
            "relation": None,
            "phone": "+91 9822112244"
        },
        {
            "username": "rohan_gupta",
            "email": "rohan.gupta@royalscience.edu",
            "first": "Rohan",
            "last": "Gupta",
            "adm_no": "ADM-2026-003",
            "roll": "103",
            "gender": "MALE",
            "dob": date(2009, 11, 5),
            "guardian_email": None,
            "guardian_name": None,
            "relation": None,
            "phone": "+91 9822112255"
        },
        {
            "username": "ananya_iyer",
            "email": "ananya.iyer@royalscience.edu",
            "first": "Ananya",
            "last": "Iyer",
            "adm_no": "ADM-2026-004",
            "roll": "104",
            "gender": "FEMALE",
            "dob": date(2009, 3, 19),
            "guardian_email": None,
            "guardian_name": None,
            "relation": None,
            "phone": "+91 9822112266"
        }
    ]

    students_list = []
    for s_info in students_spec:
        u = db.query(User).filter(User.email == s_info["email"]).first()
        if not u:
            u = User(
                institution_id=inst_a.id,
                username=s_info["username"],
                email=s_info["email"],
                password_hash=get_password_hash("Student@Pass2026"),
                first_name=s_info["first"],
                last_name=s_info["last"],
                phone_number=s_info["phone"],
                is_active=True,
                is_verified=True
            )
            db.add(u)
            db.flush()
            db.add(UserRoleAssignment(user_id=u.id, role_id=roles_map["STUDENT"].id, institution_id=inst_a.id))

            st = Student(
                user_id=u.id,
                institution_id=inst_a.id,
                admission_number=s_info["adm_no"],
                roll_number=s_info["roll"],
                date_of_birth=s_info["dob"],
                gender=s_info["gender"],
                blood_group="O+",
                admission_date=date(2026, 6, 18),
                address="Lane 7, Kothrud, Pune",
                emergency_contact_name="Family Emergency",
                emergency_contact_phone="+91 9822998877",
                status="ACTIVE"
            )
            db.add(st)
            db.flush()

            # Enroll into Class 11-A
            db.add(Enrollment(
                institution_id=inst_a.id,
                student_id=st.id,
                academic_year_id=acad_year.id,
                class_id=class_11.id,
                division_id=div_11a.id,
                roll_number=s_info["roll"],
                status="ENROLLED"
            ))

            # Optional Parent Creation & Linking
            if s_info["guardian_email"]:
                gu = db.query(User).filter(User.email == s_info["guardian_email"]).first()
                if not gu:
                    names = s_info["guardian_name"].split(" ")
                    gu = User(
                        institution_id=inst_a.id,
                        username="parent_vikram",
                        email=s_info["guardian_email"],
                        password_hash=get_password_hash("Parent@Pass2026"),
                        first_name=names[0],
                        last_name=names[1] if len(names) > 1 else "Guardian",
                        phone_number="+91 9822119900",
                        is_active=True,
                        is_verified=True
                    )
                    db.add(gu)
                    db.flush()
                    db.add(UserRoleAssignment(user_id=gu.id, role_id=roles_map["PARENT"].id, institution_id=inst_a.id))

                    gp = Guardian(
                        user_id=gu.id,
                        institution_id=inst_a.id,
                        relationship_type=s_info["relation"],
                        occupation="Architect",
                        alternative_phone="+91 9822119901"
                    )
                    db.add(gp)
                    db.flush()
                else:
                    gp = gu.guardian_profile

                db.add(StudentGuardianLink(
                    student_id=st.id,
                    guardian_id=gp.id,
                    is_primary=True,
                    is_verified=True
                ))
            students_list.append(st)
        else:
            students_list.append(u.student_profile)

    # 13. Attendance History Generation
    # Create 5 historical sessions for Physics, Chemistry & Math to show realistic percentages
    phy_fac = faculty_map["PHY-101"]
    phy_sub = subjects_map["PHY-101"]

    for day_offset in range(1, 6):
        sess_date = date.today() - timedelta(days=day_offset)
        if sess_date.weekday() >= 6:
            continue
        existing_sess = (
            db.query(AttendanceSession)
            .filter(
                AttendanceSession.division_id == div_11a.id,
                AttendanceSession.subject_id == phy_sub.id,
                AttendanceSession.session_date == sess_date,
                AttendanceSession.period_number == 1
            )
            .first()
        )
        if not existing_sess:
            sess = AttendanceSession(
                institution_id=inst_a.id,
                academic_year_id=acad_year.id,
                division_id=div_11a.id,
                subject_id=phy_sub.id,
                faculty_id=phy_fac.id,
                session_date=sess_date,
                period_number=1,
                submission_status="SUBMITTED"
            )
            db.add(sess)
            db.flush()

            for st in students_list:
                # Rohan has lower attendance
                st_status = "PRESENT"
                if st.admission_number == "ADM-2026-003" and day_offset in [1, 2, 4]:
                    st_status = "ABSENT"
                elif st.admission_number == "ADM-2026-002" and day_offset == 3:
                    st_status = "EXCUSED"

                db.add(AttendanceRecord(
                    attendance_session_id=sess.id,
                    student_id=st.id,
                    status=st_status
                ))

    # 14. Examination, Marks Entry & Approved Publication
    exam_ut1 = db.query(Examination).filter(Examination.institution_id == inst_a.id, Examination.name == "Unit Test 1 (Term 1)").first()
    if not exam_ut1:
        exam_ut1 = Examination(
            institution_id=inst_a.id,
            academic_year_id=acad_year.id,
            name="Unit Test 1 (Term 1)",
            exam_type="UNIT_TEST",
            start_date=date(2026, 8, 10),
            end_date=date(2026, 8, 16),
            status="PUBLISHED"
        )
        db.add(exam_ut1)
        db.flush()

        # Exam Subjects: Physics & Chemistry
        es_phy = ExamSubject(
            examination_id=exam_ut1.id,
            subject_id=subjects_map["PHY-101"].id,
            class_id=class_11.id,
            max_theory_marks=Decimal("70.00"),
            max_practical_marks=Decimal("30.00"),
            min_passing_marks=Decimal("35.00"),
            exam_date=date(2026, 8, 10)
        )
        es_chem = ExamSubject(
            examination_id=exam_ut1.id,
            subject_id=subjects_map["CHEM-101"].id,
            class_id=class_11.id,
            max_theory_marks=Decimal("70.00"),
            max_practical_marks=Decimal("30.00"),
            min_passing_marks=Decimal("35.00"),
            exam_date=date(2026, 8, 12)
        )
        db.add(es_phy)
        db.add(es_chem)
        db.flush()

        # Seed Marks for Students in Physics
        marks_data_phy = {
            "ADM-2026-001": (Decimal("62.50"), Decimal("28.00")),  # Arjun: 90.5/100
            "ADM-2026-002": (Decimal("58.00"), Decimal("27.50")),  # Priya: 85.5/100
            "ADM-2026-003": (Decimal("40.00"), Decimal("22.00")),  # Rohan: 62.0/100
            "ADM-2026-004": (Decimal("65.00"), Decimal("29.00")),  # Ananya: 94.0/100
        }
        for st in students_list:
            th, pr = marks_data_phy.get(st.admission_number, (Decimal("50.00"), Decimal("25.00")))
            db.add(MarksEntry(
                exam_subject_id=es_phy.id,
                student_id=st.id,
                division_id=div_11a.id,
                theory_marks_obtained=th,
                practical_marks_obtained=pr,
                total_obtained=th + pr,
                is_absent=False,
                is_exempt=False,
                entered_by=phy_fac.user_id,
                status="APPROVED",
                teacher_remarks="Exceptional problem solving in mechanics."
            ))

        # Marks Approval
        db.add(MarksApproval(
            exam_subject_id=es_phy.id,
            division_id=div_11a.id,
            submitted_by=phy_fac.user_id,
            submitted_at=datetime.now(timezone.utc) - timedelta(days=10),
            status="APPROVED",
            reviewed_by=principal_a.id,
            reviewed_at=datetime.now(timezone.utc) - timedelta(days=9),
            review_comments="Marks verified and approved."
        ))

        # Result Publication
        db.add(ResultPublication(
            examination_id=exam_ut1.id,
            class_id=class_11.id,
            published_by=principal_a.id,
            published_at=datetime.now(timezone.utc) - timedelta(days=8),
            is_active=True
        ))

    # 15. Notices, Assignments & Feedback
    notice_exist = db.query(Notice).filter(Notice.institution_id == inst_a.id).first()
    if not notice_exist:
        db.add(Notice(
            institution_id=inst_a.id,
            title="Class 11 Science Laboratory Practical Orientation",
            content="All Class 11 Science students of Division A & B are instructed to attend mandatory safety protocols orientation in the Chemistry Lab on Monday at 09:00 AM.",
            audience_role="ALL",
            priority="URGENT",
            published_by=principal_a.id,
            is_published=True
        ))
        db.add(Notice(
            institution_id=inst_a.id,
            title="Term-1 Board Model Examination Notification",
            content="The timetable for the upcoming Term-1 Preliminary Board assessments will be released next week. Parents are advised to monitor progress via portal.",
            audience_role="ALL",
            priority="NORMAL",
            published_by=principal_a.id,
            is_published=True
        ))

    assignment_exist = db.query(Assignment).filter(Assignment.institution_id == inst_a.id).first()
    if not assignment_exist:
        db.add(Assignment(
            institution_id=inst_a.id,
            division_id=div_11a.id,
            subject_id=subjects_map["PHY-101"].id,
            faculty_id=faculty_map["PHY-101"].id,
            title="Physics Numerical Problems: Projectile Motion",
            description="Complete textbook problems 4.1 through 4.15 from Chapter 4. Include clear vector diagrams and units.",
            due_date=datetime.now(timezone.utc) + timedelta(days=5)
        ))

    feedback_exist = db.query(FeedbackForm).filter(FeedbackForm.institution_id == inst_a.id).first()
    if not feedback_exist:
        fb_form = FeedbackForm(
            institution_id=inst_a.id,
            title="First Month Science Laboratory & Academic Experience",
            target_role="STUDENT",
            is_anonymous=True,
            is_open=True
        )
        db.add(fb_form)
        db.flush()

        db.add(FeedbackQuestion(
            feedback_form_id=fb_form.id,
            question_text="How would you rate the clarity of Physics theory lectures?",
            question_type="RATING_1_5",
            display_order=1
        ))
        db.add(FeedbackQuestion(
            feedback_form_id=fb_form.id,
            question_text="Are the science laboratory instruments and equipment well maintained?",
            question_type="RATING_1_5",
            display_order=2
        ))
        db.add(FeedbackQuestion(
            feedback_form_id=fb_form.id,
            question_text="What additional academic support or doubt sessions would you recommend?",
            question_type="TEXT",
            display_order=3
        ))

    db.commit()
    db.close()
    print("[SUCCESS] PHILOMATRIX Seed Data Generation Completed Successfully!")


if __name__ == "__main__":
    run_seed()
