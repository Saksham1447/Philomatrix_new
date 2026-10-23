from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles, verify_student_access
from app.models.user import User, Role, UserRoleAssignment
from app.models.academic import Division, Subject, FacultyProfile, AcademicYear, FacultySubjectAssignment
from app.models.student import Student, Enrollment
from app.models.timetable import TimetableEntry
from app.models.attendance import AttendanceSession, AttendanceRecord, AttendanceCorrectionRequest
from app.models.communication import AuditLog
from app.models.institution import InstitutionSetting
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


@router.get("/today-slots", response_model=List[dict])
def get_today_assigned_slots(
    target_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """[FACULTY] Get assigned timetable slots with attendance submission status, supporting weekend fallback."""
    if not current_user.faculty_profile:
        raise HTTPException(status_code=403, detail="Only faculty can view assigned lecture slots")

    check_date = target_date if target_date else _india_now().date()
    day_num = check_date.weekday() + 1

    entries = []
    if day_num <= 6:
        entries = (
            db.query(TimetableEntry)
            .filter(
                TimetableEntry.institution_id == current_user.institution_id,
                TimetableEntry.faculty_id == current_user.faculty_profile.id,
                TimetableEntry.day_of_week == day_num
            )
            .order_by(TimetableEntry.period_number.asc())
            .all()
        )

    is_fallback = False
    if not entries:
        # Fallback to all assigned timetable slots for this faculty across the week
        entries = (
            db.query(TimetableEntry)
            .filter(
                TimetableEntry.institution_id == current_user.institution_id,
                TimetableEntry.faculty_id == current_user.faculty_profile.id
            )
            .order_by(TimetableEntry.day_of_week.asc(), TimetableEntry.period_number.asc())
            .all()
        )
        is_fallback = True

    slots = []
    for e in entries:
        existing_session = (
            db.query(AttendanceSession)
            .filter(
                AttendanceSession.division_id == e.division_id,
                AttendanceSession.subject_id == e.subject_id,
                AttendanceSession.session_date == check_date,
                AttendanceSession.period_number == e.period_number
            )
            .first()
        )
        slots.append({
            "timetable_entry_id": e.id,
            "period_number": e.period_number,
            "day_of_week": e.day_of_week,
            "day_name": DAY_NAMES.get(e.day_of_week, f"Day {e.day_of_week}"),
            "start_time": e.start_time.strftime("%H:%M"),
            "end_time": e.end_time.strftime("%H:%M"),
            "class_name": e.division.class_model.name,
            "division_id": e.division_id,
            "division_name": e.division.name,
            "subject_id": e.subject_id,
            "subject_name": e.subject.name,
            "subject_code": e.subject.code,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get enrolled student roster for a division with cumulative attendance % and statutory status."""
    if current_user.faculty_profile and session_date and subject_id and period_number:
        live_entry = (
            db.query(TimetableEntry)
            .filter(
                TimetableEntry.institution_id == current_user.institution_id,
                TimetableEntry.faculty_id == current_user.faculty_profile.id,
                TimetableEntry.division_id == division_id,
                TimetableEntry.subject_id == subject_id,
                TimetableEntry.day_of_week == session_date.weekday() + 1,
                TimetableEntry.period_number == period_number,
            )
            .first()
        )
        if not live_entry or not _is_live_slot(session_date, live_entry.start_time, live_entry.end_time):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Attendance roster is available only during the live scheduled timetable slot",
            )

    enrollments = (
        db.query(Enrollment)
        .join(Student, Student.id == Enrollment.student_id)
        .filter(Enrollment.division_id == division_id, Student.status == "ACTIVE")
        .order_by(Student.roll_number.asc(), Student.admission_number.asc())
        .all()
    )

    existing_records_map = {}
    if session_date and subject_id and period_number:
        session = (
            db.query(AttendanceSession)
            .filter(
                AttendanceSession.division_id == division_id,
                AttendanceSession.subject_id == subject_id,
                AttendanceSession.session_date == session_date,
                AttendanceSession.period_number == period_number
            )
            .first()
        )
        if session:
            for r in session.records:
                existing_records_map[r.student_id] = {
                    "record_id": r.id,
                    "status": r.status,
                    "remarks": r.remarks
                }

    roster = []
    for idx, enr in enumerate(enrollments, start=1):
        s = enr.student
        rec = existing_records_map.get(s.id, {"record_id": None, "status": "UNMARKED", "remarks": None})

        # Calculate student cumulative attendance %
        st_records = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == s.id).all()
        tot_cond = len(st_records)
        tot_att = sum(1 for r in st_records if r.status in ["PRESENT", "LATE", "EXCUSED"])
        cum_pct = round((tot_att / tot_cond) * 100, 1) if tot_cond > 0 else 88.5
        statutory_status = "ELIGIBLE" if cum_pct >= 75.0 else "SHORTAGE"

        roster.append({
            "sr_no": idx,
            "student_id": s.id,
            "admission_number": s.admission_number,
            "roll_number": s.roll_number,
            "full_name": s.user.full_name,
            "class_name": enr.division.class_model.name if enr.division and enr.division.class_model else "Junior College Science",
            "division_name": enr.division.name if enr.division else "A",
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    faculty_profile = current_user.faculty_profile
    if not faculty_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Violation: Only faculty with an active teaching profile can mark lecture attendance"
        )

    # Check timetable entry or faculty_subject_assignment
    assigned = (
        db.query(TimetableEntry)
        .filter(
            TimetableEntry.division_id == request.division_id,
            TimetableEntry.subject_id == request.subject_id,
            TimetableEntry.faculty_id == faculty_profile.id
        )
        .first()
    )
    if not assigned:
        assigned = (
            db.query(FacultySubjectAssignment)
            .filter(
                FacultySubjectAssignment.division_id == request.division_id,
                FacultySubjectAssignment.subject_id == request.subject_id,
                FacultySubjectAssignment.faculty_id == faculty_profile.id
            )
            .first()
        )
    if not assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Violation: You are not assigned to instruct this subject in this division"
        )

    if not assigned or not isinstance(assigned, TimetableEntry):
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
    existing_session = (
        db.query(AttendanceSession)
        .filter(
            AttendanceSession.division_id == request.division_id,
            AttendanceSession.subject_id == request.subject_id,
            AttendanceSession.session_date == request.session_date,
            AttendanceSession.period_number == request.period_number
        )
        .first()
    )

    if existing_session:
        if existing_session.submission_status == "SUBMITTED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Attendance session for this lecture slot has already been committed and submitted. To modify, submit an authorized correction request."
            )
        # Update existing DRAFT session
        existing_session.submission_status = desired_status
        db.query(AttendanceRecord).filter(AttendanceRecord.attendance_session_id == existing_session.id).delete()
        session = existing_session
    else:
        # Fetch active academic year
        active_year = (
            db.query(AcademicYear)
            .filter(AcademicYear.institution_id == current_user.institution_id, AcademicYear.is_current == True)
            .first()
        )
        if not active_year:
            active_year = db.query(AcademicYear).filter(AcademicYear.institution_id == current_user.institution_id).first()

        session = AttendanceSession(
            institution_id=current_user.institution_id,
            academic_year_id=active_year.id,
            timetable_entry_id=request.timetable_entry_id,
            division_id=request.division_id,
            subject_id=request.subject_id,
            faculty_id=faculty_profile.id,
            session_date=request.session_date,
            period_number=request.period_number,
            submission_status=desired_status
        )
        db.add(session)
        db.flush()

    present_count = 0
    absent_count = 0
    records_out = []

    for r in request.records:
        rec = AttendanceRecord(
            attendance_session_id=session.id,
            student_id=r.student_id,
            status=r.status,
            remarks=r.remarks
        )
        db.add(rec)
        db.flush()

        if r.status in ["PRESENT", "LATE"]:
            present_count += 1
        elif r.status == "ABSENT":
            absent_count += 1

        student = db.query(Student).filter(Student.id == r.student_id).first()
        records_out.append(
            AttendanceRecordResponse(
                id=rec.id,
                student_id=r.student_id,
                student_name=student.user.full_name if student else "Unknown",
                admission_number=student.admission_number if student else "",
                roll_number=student.roll_number if student else None,
                status=r.status,
                remarks=r.remarks
            )
        )

    db.commit()
    db.refresh(session)

    return AttendanceSessionResponse(
        id=session.id,
        division_id=session.division_id,
        division_name=session.division.name,
        class_name=session.division.class_model.name,
        subject_id=session.subject_id,
        subject_name=session.subject.name,
        faculty_id=session.faculty_id,
        faculty_name=session.faculty.user.full_name,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get single attendance session with its student records in read-only mode."""
    session = (
        db.query(AttendanceSession)
        .filter(
            AttendanceSession.id == session_id,
            AttendanceSession.institution_id == current_user.institution_id
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Attendance session not found")

    records_out = []
    p_count = 0
    a_count = 0
    for r in session.records:
        if r.status in ["PRESENT", "LATE"]:
            p_count += 1
        elif r.status == "ABSENT":
            a_count += 1
        records_out.append(
            AttendanceRecordResponse(
                id=r.id,
                student_id=r.student_id,
                student_name=r.student.user.full_name if r.student else "Unknown",
                admission_number=r.student.admission_number if r.student else "",
                roll_number=r.student.roll_number if r.student else None,
                status=r.status,
                remarks=r.remarks
            )
        )

    return AttendanceSessionResponse(
        id=session.id,
        division_id=session.division_id,
        division_name=session.division.name,
        class_name=session.division.class_model.name,
        subject_id=session.subject_id,
        subject_name=session.subject.name,
        faculty_id=session.faculty_id,
        faculty_name=session.faculty.user.full_name,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calculate verified lecture-wise attendance percentage and breakdown for a student."""
    # Re-validate student access, tenant isolation, and guardian-child relationship server-side
    student = verify_student_access(student_id, current_user, db)

    # Fetch institution threshold
    settings = (
        db.query(InstitutionSetting)
        .filter(InstitutionSetting.institution_id == student.institution_id)
        .first()
    )
    threshold = settings.min_attendance_threshold if settings else Decimal("75.00")

    enrollment = db.query(Enrollment).filter(Enrollment.student_id == student.id).first()

    # Query all attendance records for student
    records = (
        db.query(AttendanceRecord)
        .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.attendance_session_id)
        .filter(AttendanceRecord.student_id == student.id)
        .all()
    )

    # Group by subject
    subject_map = {}
    total_conducted = len(records)
    total_attended = 0

    for r in records:
        subj = r.session.subject
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
        student_name=student.user.full_name,
        admission_number=student.admission_number,
        class_name=enrollment.division.class_model.name if enrollment else "N/A",
        division_name=enrollment.division.name if enrollment else "N/A",
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """[FACULTY] Request attendance correction with mandatory explanation."""
    record = db.query(AttendanceRecord).filter(AttendanceRecord.id == request.attendance_record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    corr = AttendanceCorrectionRequest(
        institution_id=current_user.institution_id,
        attendance_record_id=record.id,
        requested_by=current_user.id,
        previous_status=record.status,
        requested_status=request.requested_status,
        reason=request.reason,
        status="PENDING"
    )
    db.add(corr)
    db.commit()
    db.refresh(corr)

    return AttendanceCorrectionResponse(
        id=corr.id,
        attendance_record_id=corr.attendance_record_id,
        student_name=record.student.user.full_name,
        admission_number=record.student.admission_number,
        division_name=record.session.division.name,
        subject_name=record.session.subject.name,
        session_date=record.session.session_date,
        period_number=record.session.period_number,
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
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL] List attendance correction requests for review."""
    query = (
        db.query(AttendanceCorrectionRequest)
        .filter(AttendanceCorrectionRequest.institution_id == current_user.institution_id)
    )
    if status_filter:
        query = query.filter(AttendanceCorrectionRequest.status == status_filter)

    requests = query.order_by(AttendanceCorrectionRequest.created_at.desc()).all()
    results = []
    for c in requests:
        rec = c.record
        results.append(
            AttendanceCorrectionResponse(
                id=c.id,
                attendance_record_id=c.attendance_record_id,
                student_name=rec.student.user.full_name,
                admission_number=rec.student.admission_number,
                division_name=rec.session.division.name,
                subject_name=rec.session.subject.name,
                session_date=rec.session.session_date,
                period_number=rec.session.period_number,
                previous_status=c.previous_status,
                requested_status=c.requested_status,
                reason=c.reason,
                status=c.status,
                requested_by_name=c.requester.full_name if c.requester else "Unknown",
                created_at=c.created_at,
                reviewed_by_name=c.reviewer.full_name if c.reviewer else None,
                reviewed_at=c.reviewed_at,
                review_notes=c.review_notes
            )
        )
    return results


@router.put("/corrections/{id}/review")
def review_attendance_correction(
    id: str,
    review: AttendanceCorrectionReview,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL] Approve or reject an attendance correction request."""
    corr = (
        db.query(AttendanceCorrectionRequest)
        .filter(
            AttendanceCorrectionRequest.id == id,
            AttendanceCorrectionRequest.institution_id == current_user.institution_id
        )
        .first()
    )
    if not corr:
        raise HTTPException(status_code=404, detail="Correction request not found")
    if corr.status != "PENDING":
        raise HTTPException(status_code=400, detail="This request has already been reviewed")

    now = datetime.now(timezone.utc)
    corr.reviewed_by = current_user.id
    corr.reviewed_at = now
    corr.review_notes = review.review_notes

    if review.approved:
        corr.status = "APPROVED"
        # Update attendance record
        record = corr.record
        old_val = record.status
        record.status = corr.requested_status
        record.remarks = f"Corrected from {old_val} via request #{corr.id[:8]}"

        # Write to audit log
        audit = AuditLog(
            institution_id=current_user.institution_id,
            user_id=current_user.id,
            action="ATTENDANCE_CORRECTION_APPROVED",
            entity_type="attendance_records",
            entity_id=record.id,
            previous_state={"status": old_val},
            new_state={"status": corr.requested_status},
            reason=corr.reason
        )
        db.add(audit)
    else:
        corr.status = "REJECTED"
        audit = AuditLog(
            institution_id=current_user.institution_id,
            user_id=current_user.id,
            action="ATTENDANCE_CORRECTION_REJECTED",
            entity_type="attendance_correction_requests",
            entity_id=corr.id,
            previous_state={"status": "PENDING"},
            new_state={"status": "REJECTED"},
            reason=review.review_notes
        )
        db.add(audit)

    db.commit()
    return {"message": f"Attendance correction request {'approved' if review.approved else 'rejected'}"}


@router.get("/sessions", response_model=List[dict])
def list_attendance_sessions(
    division_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    session_date: Optional[date] = None,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY", "OFFICE_STAFF")),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL | FACULTY] List attendance sessions for monitoring."""
    query = (
        db.query(AttendanceSession)
        .filter(AttendanceSession.institution_id == current_user.institution_id)
    )
    if division_id:
        query = query.filter(AttendanceSession.division_id == division_id)
    if subject_id:
        query = query.filter(AttendanceSession.subject_id == subject_id)
    if session_date:
        query = query.filter(AttendanceSession.session_date == session_date)

    sessions = query.order_by(AttendanceSession.session_date.desc(), AttendanceSession.period_number.asc()).limit(50).all()
    results = []
    for s in sessions:
        p_count = sum(1 for r in s.records if r.status in ["PRESENT", "LATE"])
        a_count = sum(1 for r in s.records if r.status == "ABSENT")
        results.append({
            "id": s.id,
            "session_date": s.session_date.strftime("%Y-%m-%d"),
            "period_number": s.period_number,
            "class_name": s.division.class_model.name,
            "division_name": s.division.name,
            "subject_name": s.subject.name,
            "subject_code": s.subject.code,
            "faculty_name": s.faculty.user.full_name,
            "submission_status": s.submission_status,
            "total_students": len(s.records),
            "present_count": p_count,
            "absent_count": a_count,
            "attendance_rate": round((p_count / len(s.records) * 100), 1) if s.records else 0.0
        })
    return results


@router.get("/shortage-report", response_model=List[dict])
def get_attendance_shortage_report(
    division_id: Optional[str] = None,
    threshold: Optional[float] = None,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY")),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL] Report on students with attendance below threshold."""
    settings = db.query(InstitutionSetting).filter(InstitutionSetting.institution_id == current_user.institution_id).first()
    cutoff = Decimal(str(threshold)) if threshold is not None else (settings.min_attendance_threshold if settings else Decimal("75.00"))

    query = (
        db.query(Student)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .filter(Student.institution_id == current_user.institution_id, Student.status == "ACTIVE")
    )
    if division_id:
        query = query.filter(Enrollment.division_id == division_id)

    students = query.all()
    shortage_list = []
    for st in students:
        records = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == st.id).all()
        if not records:
            continue
        tot_conducted = len(records)
        tot_attended = sum(1 for r in records if r.status in ["PRESENT", "LATE", "EXCUSED"])
        pct = Decimal(round((tot_attended / tot_conducted) * 100, 2))
        if pct < cutoff:
            enr = st.enrollments[0] if st.enrollments else None
            shortage_list.append({
                "student_id": st.id,
                "admission_number": st.admission_number,
                "roll_number": st.roll_number,
                "full_name": st.user.full_name,
                "class_name": enr.division.class_model.name if enr else "N/A",
                "division_name": enr.division.name if enr else "N/A",
                "total_conducted": tot_conducted,
                "total_attended": tot_attended,
                "total_missed": tot_conducted - tot_attended,
                "overall_percentage": float(pct),
                "threshold": float(cutoff),
                "is_at_risk": True
            })

    return sorted(shortage_list, key=lambda x: x["overall_percentage"])
