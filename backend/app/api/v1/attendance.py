from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.deps import get_current_user, get_db, require_roles, verify_student_access
from app.core.docstore import DocStore, UserDoc
from app.core.q import ids, index_by, group_by
from app.schemas.attendance import (
    AttendanceSessionSubmit,
    AttendanceSessionResponse,
    AttendanceRecordResponse,
    StudentAttendanceSummary,
    SubjectAttendanceStat,
    AttendanceCorrectionCreate,
    AttendanceCorrectionResponse,
    AttendanceCorrectionReview,
)

router = APIRouter(prefix="/attendance", tags=["Lecture-Wise Attendance"])


DAY_NAMES = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}
INDIA_TZ = ZoneInfo("Asia/Kolkata")


def _india_now() -> datetime:
    return datetime.now(INDIA_TZ)


def _is_live_slot(check_date: date, start_time, end_time) -> bool:
    now = _india_now()
    if check_date != now.date():
        return False
    start = datetime.combine(check_date, start_time, tzinfo=INDIA_TZ)
    end = datetime.combine(check_date, end_time, tzinfo=INDIA_TZ)
    return start <= now < end


def _roll_sort_key(student):
    """Roll number asc (NULLs last), then admission number asc."""
    return (student.roll_number is None, student.roll_number or "", student.admission_number or "")


@router.get("/today-slots", response_model=List[dict])
def get_today_assigned_slots(
    target_date: Optional[date] = None,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """[FACULTY] Get assigned timetable slots with attendance submission status, supporting weekend fallback."""
    if not current_user.faculty_profile:
        raise HTTPException(status_code=403, detail="Only faculty can view assigned lecture slots")

    check_date = target_date if target_date else _india_now().date()
    day_num = check_date.weekday() + 1

    entries = []
    if day_num <= 6:
        entries = db.find(
            "timetable_entries",
            {
                "institution_id": current_user.institution_id,
                "faculty_id": current_user.faculty_profile.id,
                "day_of_week": day_num,
            },
            sort=[("period_number", 1)],
        )

    is_fallback = False
    if not entries:
        # Fallback to all assigned timetable slots for this faculty across the week
        entries = db.find(
            "timetable_entries",
            {
                "institution_id": current_user.institution_id,
                "faculty_id": current_user.faculty_profile.id,
            },
            sort=[("day_of_week", 1), ("period_number", 1)],
        )
        is_fallback = True

    divisions_by_id = db.get_many("divisions", ids(entries, "division_id"))
    classes_by_id = db.get_many("classes", ids(divisions_by_id.values(), "class_id"))
    subjects_by_id = db.get_many("subjects", ids(entries, "subject_id"))

    slots = []
    for e in entries:
        existing_session = db.find_one("attendance_sessions", {
            "division_id": e.division_id,
            "subject_id": e.subject_id,
            "session_date": check_date,
            "period_number": e.period_number,
        })
        division = divisions_by_id[e.division_id]
        subject = subjects_by_id[e.subject_id]
        slots.append({
            "timetable_entry_id": e.id,
            "period_number": e.period_number,
            "day_of_week": e.day_of_week,
            "day_name": DAY_NAMES.get(e.day_of_week, f"Day {e.day_of_week}"),
            "start_time": e.start_time.strftime("%H:%M"),
            "end_time": e.end_time.strftime("%H:%M"),
            "class_name": classes_by_id[division.class_id].name,
            "division_id": e.division_id,
            "division_name": division.name,
            "subject_id": e.subject_id,
            "subject_name": subject.name,
            "subject_code": subject.code,
            "room_number": e.room_number,
            "is_submitted": existing_session is not None and existing_session.submission_status == "SUBMITTED",
            "is_draft": existing_session is not None and existing_session.submission_status == "DRAFT",
            "submission_status": existing_session.submission_status if existing_session else None,
            "session_id": existing_session.id if existing_session else None,
            "is_fallback": is_fallback,
            "is_live": _is_live_slot(check_date, e.start_time, e.end_time),
        })
    return slots


@router.get("/roster", response_model=List[dict])
def get_attendance_roster(
    division_id: str,
    subject_id: Optional[str] = None,
    session_date: Optional[date] = None,
    period_number: Optional[int] = None,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """Get enrolled student roster for a division with cumulative attendance % and statutory status."""
    if current_user.faculty_profile and session_date and subject_id and period_number:
        live_entry = db.find_one("timetable_entries", {
            "institution_id": current_user.institution_id,
            "faculty_id": current_user.faculty_profile.id,
            "division_id": division_id,
            "subject_id": subject_id,
            "day_of_week": session_date.weekday() + 1,
            "period_number": period_number,
        })
        if not live_entry or not _is_live_slot(session_date, live_entry.start_time, live_entry.end_time):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Attendance roster is available only during the live scheduled timetable slot",
            )

    enrollments = db.find("enrollments", {"division_id": division_id})
    students_by_id = db.get_many("students", ids(enrollments, "student_id"))
    # Inner join with ACTIVE students, ordered by roll number then admission number.
    enrolled = [
        (enr, students_by_id[enr.student_id])
        for enr in enrollments
        if enr.student_id in students_by_id and students_by_id[enr.student_id].status == "ACTIVE"
    ]
    enrolled.sort(key=lambda pair: _roll_sort_key(pair[1]))

    division = db.get("divisions", division_id)
    division_class = db.get("classes", division.class_id) if division else None
    users_by_id = db.get_many("users", ids([s for _, s in enrolled], "user_id"))

    existing_records_map = {}
    if session_date and subject_id and period_number:
        session = db.find_one("attendance_sessions", {
            "division_id": division_id,
            "subject_id": subject_id,
            "session_date": session_date,
            "period_number": period_number,
        })
        if session:
            for r in db.find("attendance_records", {"attendance_session_id": session.id}):
                existing_records_map[r.student_id] = {
                    "record_id": r.id,
                    "status": r.status,
                    "remarks": r.remarks
                }

    student_ids = ids([s for _, s in enrolled])
    records_by_student = group_by(
        db.find("attendance_records", {"student_id": {"$in": student_ids}}) if student_ids else [],
        "student_id",
    )

    roster = []
    for idx, (enr, s) in enumerate(enrolled, start=1):
        rec = existing_records_map.get(s.id, {"record_id": None, "status": "UNMARKED", "remarks": None})

        # Calculate student cumulative attendance %
        st_records = records_by_student.get(s.id, [])
        tot_cond = len(st_records)
        tot_att = sum(1 for r in st_records if r.status in ["PRESENT", "LATE", "EXCUSED"])
        cum_pct = round((tot_att / tot_cond) * 100, 1) if tot_cond > 0 else 88.5
        statutory_status = "ELIGIBLE" if cum_pct >= 75.0 else "SHORTAGE"

        roster.append({
            "sr_no": idx,
            "student_id": s.id,
            "admission_number": s.admission_number,
            "roll_number": s.roll_number,
            "full_name": users_by_id[s.user_id].full_name,
            "class_name": division_class.name if division and division_class else "Junior College Science",
            "division_name": division.name if division else "A",
            "current_status": rec["status"],
            "cumulative_attendance": cum_pct,
            "statutory_status": statutory_status,
            "record_id": rec["record_id"],
            "remarks": rec["remarks"]
        })
    return roster

@router.post("/submit", response_model=AttendanceSessionResponse, status_code=status.HTTP_201_CREATED)
def submit_attendance(
    request: AttendanceSessionSubmit,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    faculty_profile = current_user.faculty_profile
    if not faculty_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Violation: Only faculty with an active teaching profile can mark lecture attendance"
        )

    # Check timetable entry or faculty_subject_assignment
    assigned = db.find_one("timetable_entries", {
        "division_id": request.division_id,
        "subject_id": request.subject_id,
        "faculty_id": faculty_profile.id,
    })
    assigned_is_timetable_entry = assigned is not None
    if not assigned:
        assigned = db.find_one("faculty_subject_assignments", {
            "division_id": request.division_id,
            "subject_id": request.subject_id,
            "faculty_id": faculty_profile.id,
        })
    if not assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Violation: You are not assigned to instruct this subject in this division"
        )

    if not assigned or not assigned_is_timetable_entry:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Attendance can only be marked during the live scheduled timetable slot",
        )

    if not _is_live_slot(request.session_date, assigned.start_time, assigned.end_time):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Attendance is available only during the live slot "
                f"{assigned.start_time.strftime('%I:%M %p')} - {assigned.end_time.strftime('%I:%M %p')} "
                "on the scheduled date"
            ),
        )

    desired_status = (request.submission_status or "SUBMITTED").upper()

    # If submitting final attendance, prevent unmarked students
    if desired_status == "SUBMITTED":
        unmarked = [r for r in request.records if r.status not in ["PRESENT", "ABSENT", "LATE", "EXCUSED"]]
        if unmarked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit attendance session with {len(unmarked)} unmarked scholar(s). All scholars must be marked Present, Absent, or Late."
            )

    # Check existing session
    existing_session = db.find_one("attendance_sessions", {
        "division_id": request.division_id,
        "subject_id": request.subject_id,
        "session_date": request.session_date,
        "period_number": request.period_number,
    })

    if existing_session:
        if existing_session.submission_status == "SUBMITTED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Attendance session for this lecture slot has already been committed and submitted. To modify, submit an authorized correction request."
            )
        # Update existing DRAFT session
        session = db.update(existing_session, {"submission_status": desired_status})
        db.delete_many("attendance_records", {"attendance_session_id": session.id})
    else:
        # Fetch active academic year
        active_year = db.find_one("academic_years", {"institution_id": current_user.institution_id, "is_current": True})
        if not active_year:
            active_year = db.find_one("academic_years", {"institution_id": current_user.institution_id})

        session = db.insert("attendance_sessions", {
            "institution_id": current_user.institution_id,
            "academic_year_id": active_year.id,
            "timetable_entry_id": request.timetable_entry_id,
            "division_id": request.division_id,
            "subject_id": request.subject_id,
            "faculty_id": faculty_profile.id,
            "session_date": request.session_date,
            "period_number": request.period_number,
            "submission_status": desired_status,
        })

    present_count = 0
    absent_count = 0
    records_out = []

    students_by_id = db.get_many("students", [r.student_id for r in request.records])
    users_by_id = db.get_many("users", ids(students_by_id.values(), "user_id"))

    for r in request.records:
        rec = db.insert("attendance_records", {
            "attendance_session_id": session.id,
            "student_id": r.student_id,
            "status": r.status,
            "remarks": r.remarks,
        })

        if r.status in ["PRESENT", "LATE"]:
            present_count += 1
        elif r.status == "ABSENT":
            absent_count += 1

        student = students_by_id.get(r.student_id)
        records_out.append(
            AttendanceRecordResponse(
                id=rec.id,
                student_id=r.student_id,
                student_name=users_by_id[student.user_id].full_name if student else "Unknown",
                admission_number=student.admission_number if student else "",
                roll_number=student.roll_number if student else None,
                status=r.status,
                remarks=r.remarks
            )
        )

    division = db.get("divisions", session.division_id)
    division_class = db.get("classes", division.class_id)
    subject = db.get("subjects", session.subject_id)
    faculty = db.get("faculty_profiles", session.faculty_id)
    faculty_user = db.get("users", faculty.user_id)

    return AttendanceSessionResponse(
        id=session.id,
        division_id=session.division_id,
        division_name=division.name,
        class_name=division_class.name,
        subject_id=session.subject_id,
        subject_name=subject.name,
        faculty_id=session.faculty_id,
        faculty_name=faculty_user.full_name,
        session_date=session.session_date,
        period_number=session.period_number,
        submission_status=session.submission_status,
        total_students=len(records_out),
        present_count=present_count,
        absent_count=absent_count,
        records=records_out
    )


@router.get("/sessions/{session_id}", response_model=AttendanceSessionResponse)
def get_attendance_session_detail(
    session_id: str,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """Get single attendance session with its student records in read-only mode."""
    session = db.find_one("attendance_sessions", {
        "id": session_id,
        "institution_id": current_user.institution_id,
    })
    if not session:
        raise HTTPException(status_code=404, detail="Attendance session not found")

    records = db.find("attendance_records", {"attendance_session_id": session.id})
    students_by_id = db.get_many("students", ids(records, "student_id"))
    users_by_id = db.get_many("users", ids(students_by_id.values(), "user_id"))

    records_out = []
    p_count = 0
    a_count = 0
    for r in records:
        if r.status in ["PRESENT", "LATE"]:
            p_count += 1
        elif r.status == "ABSENT":
            a_count += 1
        student = students_by_id.get(r.student_id)
        records_out.append(
            AttendanceRecordResponse(
                id=r.id,
                student_id=r.student_id,
                student_name=users_by_id[student.user_id].full_name if student else "Unknown",
                admission_number=student.admission_number if student else "",
                roll_number=student.roll_number if student else None,
                status=r.status,
                remarks=r.remarks
            )
        )

    division = db.get("divisions", session.division_id)
    division_class = db.get("classes", division.class_id)
    subject = db.get("subjects", session.subject_id)
    faculty = db.get("faculty_profiles", session.faculty_id)
    faculty_user = db.get("users", faculty.user_id)

    return AttendanceSessionResponse(
        id=session.id,
        division_id=session.division_id,
        division_name=division.name,
        class_name=division_class.name,
        subject_id=session.subject_id,
        subject_name=subject.name,
        faculty_id=session.faculty_id,
        faculty_name=faculty_user.full_name,
        session_date=session.session_date,
        period_number=session.period_number,
        submission_status=session.submission_status,
        total_students=len(records_out),
        present_count=p_count,
        absent_count=a_count,
        records=records_out
    )



@router.get("/summary/student/{student_id}", response_model=StudentAttendanceSummary)
def get_student_attendance_summary(
    student_id: str,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """Calculate verified lecture-wise attendance percentage and breakdown for a student."""
    # Re-validate student access, tenant isolation, and guardian-child relationship server-side
    student = verify_student_access(student_id, current_user, db)

    # Fetch institution threshold
    settings = db.find_one("institution_settings", {"institution_id": student.institution_id})
    threshold = settings.min_attendance_threshold if settings else Decimal("75.00")

    enrollment = db.find_one("enrollments", {"student_id": student.id})
    enrollment_division = db.get("divisions", enrollment.division_id) if enrollment else None
    enrollment_class = db.get("classes", enrollment_division.class_id) if enrollment_division else None
    student_user = db.get("users", student.user_id)

    # Query all attendance records for student (inner join with sessions)
    all_records = db.find("attendance_records", {"student_id": student.id})
    sessions_by_id = db.get_many("attendance_sessions", ids(all_records, "attendance_session_id"))
    records = [r for r in all_records if r.attendance_session_id in sessions_by_id]
    subjects_by_id = db.get_many("subjects", ids(sessions_by_id.values(), "subject_id"))

    # Group by subject
    subject_map = {}
    total_conducted = len(records)
    total_attended = 0

    for r in records:
        subj = subjects_by_id[sessions_by_id[r.attendance_session_id].subject_id]
        if subj.id not in subject_map:
            subject_map[subj.id] = {
                "id": subj.id,
                "code": subj.code,
                "name": subj.name,
                "conducted": 0,
                "attended": 0
            }
        subject_map[subj.id]["conducted"] += 1
        if r.status in ["PRESENT", "LATE"]:
            subject_map[subj.id]["attended"] += 1
            total_attended += 1
        elif r.status == "EXCUSED":
            # Excused leave does not penalize student: counts as attended or excused
            subject_map[subj.id]["attended"] += 1
            total_attended += 1

    overall_pct = (
        Decimal(round((total_attended / total_conducted) * 100, 2))
        if total_conducted > 0 else Decimal("100.00")
    )

    breakdown = []
    for s_info in subject_map.values():
        c = s_info["conducted"]
        a = s_info["attended"]
        pct = Decimal(round((a / c) * 100, 2)) if c > 0 else Decimal("100.00")
        breakdown.append(
            SubjectAttendanceStat(
                subject_id=s_info["id"],
                subject_code=s_info["code"],
                subject_name=s_info["name"],
                total_conducted=c,
                total_attended=a,
                percentage=pct
            )
        )

    return StudentAttendanceSummary(
        student_id=student.id,
        student_name=student_user.full_name,
        admission_number=student.admission_number,
        class_name=enrollment_class.name if enrollment else "N/A",
        division_name=enrollment_division.name if enrollment else "N/A",
        total_conducted=total_conducted,
        total_attended=total_attended,
        overall_percentage=overall_pct,
        is_below_threshold=overall_pct < threshold,
        subject_breakdown=breakdown
    )

# Correction Workflow
@router.post("/corrections", response_model=AttendanceCorrectionResponse, status_code=status.HTTP_201_CREATED)
def request_attendance_correction(
    request: AttendanceCorrectionCreate,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """[FACULTY] Request attendance correction with mandatory explanation."""
    record = db.get("attendance_records", request.attendance_record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    corr = db.insert("attendance_correction_requests", {
        "institution_id": current_user.institution_id,
        "attendance_record_id": record.id,
        "requested_by": current_user.id,
        "previous_status": record.status,
        "requested_status": request.requested_status,
        "reason": request.reason,
        "status": "PENDING",
    })

    student = db.get("students", record.student_id)
    student_user = db.get("users", student.user_id)
    session = db.get("attendance_sessions", record.attendance_session_id)
    division = db.get("divisions", session.division_id)
    subject = db.get("subjects", session.subject_id)

    return AttendanceCorrectionResponse(
        id=corr.id,
        attendance_record_id=corr.attendance_record_id,
        student_name=student_user.full_name,
        admission_number=student.admission_number,
        division_name=division.name,
        subject_name=subject.name,
        session_date=session.session_date,
        period_number=session.period_number,
        previous_status=corr.previous_status,
        requested_status=corr.requested_status,
        reason=corr.reason,
        status=corr.status,
        requested_by_name=current_user.full_name,
        created_at=corr.created_at,
        reviewed_by_name=None,
        reviewed_at=None,
        review_notes=None
    )


@router.get("/corrections", response_model=List[AttendanceCorrectionResponse])
def list_attendance_corrections(
    status_filter: Optional[str] = None,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db)
):
    """[PRINCIPAL] List attendance correction requests for review."""
    flt = {"institution_id": current_user.institution_id}
    if status_filter:
        flt["status"] = status_filter

    requests = db.find("attendance_correction_requests", flt, sort=[("created_at", -1)])

    records_by_id = db.get_many("attendance_records", ids(requests, "attendance_record_id"))
    students_by_id = db.get_many("students", ids(records_by_id.values(), "student_id"))
    sessions_by_id = db.get_many("attendance_sessions", ids(records_by_id.values(), "attendance_session_id"))
    divisions_by_id = db.get_many("divisions", ids(sessions_by_id.values(), "division_id"))
    subjects_by_id = db.get_many("subjects", ids(sessions_by_id.values(), "subject_id"))
    user_ids = ids(students_by_id.values(), "user_id") + [c.requested_by for c in requests] + [c.reviewed_by for c in requests if c.reviewed_by]
    users_by_id = db.get_many("users", user_ids)

    results = []
    for c in requests:
        rec = records_by_id[c.attendance_record_id]
        student = students_by_id[rec.student_id]
        session = sessions_by_id[rec.attendance_session_id]
        requester = users_by_id.get(c.requested_by)
        reviewer = users_by_id.get(c.reviewed_by) if c.reviewed_by else None
        results.append(
            AttendanceCorrectionResponse(
                id=c.id,
                attendance_record_id=c.attendance_record_id,
                student_name=users_by_id[student.user_id].full_name,
                admission_number=student.admission_number,
                division_name=divisions_by_id[session.division_id].name,
                subject_name=subjects_by_id[session.subject_id].name,
                session_date=session.session_date,
                period_number=session.period_number,
                previous_status=c.previous_status,
                requested_status=c.requested_status,
                reason=c.reason,
                status=c.status,
                requested_by_name=requester.full_name if requester else "Unknown",
                created_at=c.created_at,
                reviewed_by_name=reviewer.full_name if reviewer else None,
                reviewed_at=c.reviewed_at,
                review_notes=c.review_notes
            )
        )
    return results


@router.put("/corrections/{id}/review")
def review_attendance_correction(
    id: str,
    review: AttendanceCorrectionReview,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db)
):
    """[PRINCIPAL] Approve or reject an attendance correction request."""
    corr = db.find_one("attendance_correction_requests", {
        "id": id,
        "institution_id": current_user.institution_id,
    })
    if not corr:
        raise HTTPException(status_code=404, detail="Correction request not found")
    if corr.status != "PENDING":
        raise HTTPException(status_code=400, detail="This request has already been reviewed")

    now = datetime.now(timezone.utc)
    changes = {
        "reviewed_by": current_user.id,
        "reviewed_at": now,
        "review_notes": review.review_notes,
    }

    if review.approved:
        changes["status"] = "APPROVED"
        db.update(corr, changes)
        # Update attendance record
        record = db.get("attendance_records", corr.attendance_record_id)
        old_val = record.status
        db.update(record, {
            "status": corr.requested_status,
            "remarks": f"Corrected from {old_val} via request #{corr.id[:8]}",
        })

        # Write to audit log
        db.insert("audit_logs", {
            "institution_id": current_user.institution_id,
            "user_id": current_user.id,
            "action": "ATTENDANCE_CORRECTION_APPROVED",
            "entity_type": "attendance_records",
            "entity_id": record.id,
            "previous_state": {"status": old_val},
            "new_state": {"status": corr.requested_status},
            "reason": corr.reason,
        })
    else:
        changes["status"] = "REJECTED"
        db.update(corr, changes)
        db.insert("audit_logs", {
            "institution_id": current_user.institution_id,
            "user_id": current_user.id,
            "action": "ATTENDANCE_CORRECTION_REJECTED",
            "entity_type": "attendance_correction_requests",
            "entity_id": corr.id,
            "previous_state": {"status": "PENDING"},
            "new_state": {"status": "REJECTED"},
            "reason": review.review_notes,
        })

    return {"message": f"Attendance correction request {'approved' if review.approved else 'rejected'}"}


@router.get("/sessions", response_model=List[dict])
def list_attendance_sessions(
    division_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    session_date: Optional[date] = None,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY", "OFFICE_STAFF")),
    db: DocStore = Depends(get_db)
):
    """[PRINCIPAL | FACULTY] List attendance sessions for monitoring."""
    flt = {"institution_id": current_user.institution_id}
    if division_id:
        flt["division_id"] = division_id
    if subject_id:
        flt["subject_id"] = subject_id
    if session_date:
        flt["session_date"] = session_date

    sessions = db.find("attendance_sessions", flt, sort=[("session_date", -1), ("period_number", 1)], limit=50)

    records_by_session = group_by(
        db.find("attendance_records", {"attendance_session_id": {"$in": ids(sessions)}}) if sessions else [],
        "attendance_session_id",
    )
    divisions_by_id = db.get_many("divisions", ids(sessions, "division_id"))
    classes_by_id = db.get_many("classes", ids(divisions_by_id.values(), "class_id"))
    subjects_by_id = db.get_many("subjects", ids(sessions, "subject_id"))
    faculty_by_id = db.get_many("faculty_profiles", ids(sessions, "faculty_id"))
    users_by_id = db.get_many("users", ids(faculty_by_id.values(), "user_id"))

    results = []
    for s in sessions:
        s_records = records_by_session.get(s.id, [])
        p_count = sum(1 for r in s_records if r.status in ["PRESENT", "LATE"])
        a_count = sum(1 for r in s_records if r.status == "ABSENT")
        division = divisions_by_id[s.division_id]
        subject = subjects_by_id[s.subject_id]
        results.append({
            "id": s.id,
            "session_date": s.session_date.strftime("%Y-%m-%d"),
            "period_number": s.period_number,
            "class_name": classes_by_id[division.class_id].name,
            "division_name": division.name,
            "subject_name": subject.name,
            "subject_code": subject.code,
            "faculty_name": users_by_id[faculty_by_id[s.faculty_id].user_id].full_name,
            "submission_status": s.submission_status,
            "total_students": len(s_records),
            "present_count": p_count,
            "absent_count": a_count,
            "attendance_rate": round((p_count / len(s_records) * 100), 1) if s_records else 0.0
        })
    return results


@router.get("/shortage-report", response_model=List[dict])
def get_attendance_shortage_report(
    division_id: Optional[str] = None,
    threshold: Optional[float] = None,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY")),
    db: DocStore = Depends(get_db)
):
    """[PRINCIPAL] Report on students with attendance below threshold."""
    settings = db.find_one("institution_settings", {"institution_id": current_user.institution_id})
    cutoff = Decimal(str(threshold)) if threshold is not None else (settings.min_attendance_threshold if settings else Decimal("75.00"))

    students = db.find("students", {"institution_id": current_user.institution_id, "status": "ACTIVE"})
    enrollments_by_student = group_by(
        db.find("enrollments", {"student_id": {"$in": ids(students)}}) if students else [],
        "student_id",
    )
    # Inner join with enrollments (optionally restricted to a division); one row per student.
    if division_id:
        students = [
            st for st in students
            if any(e.division_id == division_id for e in enrollments_by_student.get(st.id, []))
        ]
    else:
        students = [st for st in students if enrollments_by_student.get(st.id)]

    records_by_student = group_by(
        db.find("attendance_records", {"student_id": {"$in": ids(students)}}) if students else [],
        "student_id",
    )
    users_by_id = db.get_many("users", ids(students, "user_id"))

    shortage_list = []
    for st in students:
        records = records_by_student.get(st.id, [])
        if not records:
            continue
        tot_conducted = len(records)
        tot_attended = sum(1 for r in records if r.status in ["PRESENT", "LATE", "EXCUSED"])
        pct = Decimal(round((tot_attended / tot_conducted) * 100, 2))
        if pct < cutoff:
            enr = enrollments_by_student[st.id][0]
            division = db.get("divisions", enr.division_id)
            division_class = db.get("classes", division.class_id) if division else None
            shortage_list.append({
                "student_id": st.id,
                "admission_number": st.admission_number,
                "roll_number": st.roll_number,
                "full_name": users_by_id[st.user_id].full_name,
                "class_name": division_class.name if division_class else "N/A",
                "division_name": division.name if division else "N/A",
                "total_conducted": tot_conducted,
                "total_attended": tot_attended,
                "total_missed": tot_conducted - tot_attended,
                "overall_percentage": float(pct),
                "threshold": float(cutoff),
                "is_at_risk": True
            })

    return sorted(shortage_list, key=lambda x: x["overall_percentage"])