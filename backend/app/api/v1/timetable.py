from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles, verify_student_access
from app.models.user import User
from app.models.timetable import TimetableVersion, TimetableEntry
from app.models.academic import Division, Subject, FacultyProfile, AcademicYear, FacultySubjectAssignment
from app.models.student import Enrollment, StudentGuardianLink
from app.schemas.timetable import TimetableEntryCreate, TimetableEntryResponse

router = APIRouter(prefix="/timetable", tags=["Timetable & Scheduling"])


@router.get("", response_model=List[TimetableEntryResponse])
def get_timetable(
    division_id: Optional[str] = None,
    faculty_id: Optional[str] = None,
    student_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch timetable slots by division, faculty, or student."""
    query = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.institution_id == current_user.institution_id)
    )

    if division_id:
        query = query.filter(TimetableEntry.division_id == division_id)
    elif faculty_id:
        query = query.filter(TimetableEntry.faculty_id == faculty_id)
    elif current_user.faculty_profile:
        query = query.filter(TimetableEntry.faculty_id == current_user.faculty_profile.id)
    elif current_user.student_profile:
        sid = current_user.student_profile.id
        enrollment = db.query(Enrollment).filter(Enrollment.student_id == sid).first()
        if enrollment:
            query = query.filter(TimetableEntry.division_id == enrollment.division_id)
        else:
            return []
    elif student_id:
        # Re-validate student identity or guardian-child link server-side
        student = verify_student_access(student_id, current_user, db)
        enrollment = db.query(Enrollment).filter(Enrollment.student_id == student.id).first()
        if enrollment:
            query = query.filter(TimetableEntry.division_id == enrollment.division_id)
        else:
            return []
    elif current_user.guardian_profile:
        # If parent called without student_id, find first verified linked child
        link = (
            db.query(StudentGuardianLink)
            .filter(
                StudentGuardianLink.guardian_id == current_user.guardian_profile.id,
                StudentGuardianLink.is_verified == True
            )
            .first()
        )
        if link:
            enrollment = db.query(Enrollment).filter(Enrollment.student_id == link.student_id).first()
            if enrollment:
                query = query.filter(TimetableEntry.division_id == enrollment.division_id)
            else:
                return []
        else:
            return []

    entries = query.order_by(TimetableEntry.day_of_week.asc(), TimetableEntry.period_number.asc()).all()
    results = []
    for e in entries:
        results.append(
            TimetableEntryResponse(
                id=e.id,
                division_id=e.division_id,
                division_name=e.division.name,
                class_name=e.division.class_model.name,
                subject_id=e.subject_id,
                subject_name=e.subject.name,
                subject_code=e.subject.code,
                faculty_id=e.faculty_id,
                faculty_name=e.faculty.user.full_name,
                day_of_week=e.day_of_week,
                period_number=e.period_number,
                start_time=e.start_time,
                end_time=e.end_time,
                room_number=e.room_number,
                is_practical_batch=e.is_practical_batch,
                batch_name=e.batch_name
            )
        )
    return results


@router.post("/entries", response_model=TimetableEntryResponse, status_code=status.HTTP_201_CREATED)
def create_timetable_entry(
    request: TimetableEntryCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY")),
    db: Session = Depends(get_db)
):
    """Add a lecture slot with automatic conflict detection."""
    if current_user.faculty_profile:
        if request.faculty_id != current_user.faculty_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Faculty can only schedule their own teaching slots",
            )
    elif not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A faculty or institution context is required to schedule a slot",
        )

    division = (
        db.query(Division)
        .filter(
            Division.id == request.division_id,
            Division.institution_id == current_user.institution_id,
        )
        .first()
    )
    subject = (
        db.query(Subject)
        .filter(
            Subject.id == request.subject_id,
            Subject.institution_id == current_user.institution_id,
        )
        .first()
    )
    faculty = (
        db.query(FacultyProfile)
        .filter(
            FacultyProfile.id == request.faculty_id,
            FacultyProfile.institution_id == current_user.institution_id,
        )
        .first()
    )
    if not division or not subject or not faculty:
        raise HTTPException(status_code=404, detail="Division, subject, or faculty profile not found")

    if current_user.faculty_profile:
        assignment = (
            db.query(FacultySubjectAssignment)
            .filter(
                FacultySubjectAssignment.faculty_id == current_user.faculty_profile.id,
                FacultySubjectAssignment.division_id == request.division_id,
                FacultySubjectAssignment.subject_id == request.subject_id,
                FacultySubjectAssignment.institution_id == current_user.institution_id,
            )
            .first()
        )
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Faculty can only schedule assigned subjects and divisions",
            )
    # Find or create active timetable version
    version_id = request.timetable_version_id
    if not version_id:
        active_year = (
            db.query(AcademicYear)
            .filter(AcademicYear.institution_id == current_user.institution_id, AcademicYear.is_current == True)
            .first()
        )
        if not active_year:
            active_year = db.query(AcademicYear).filter(AcademicYear.institution_id == current_user.institution_id).first()
        if not active_year:
            raise HTTPException(status_code=400, detail="No academic year found")

        tt_version = (
            db.query(TimetableVersion)
            .filter(TimetableVersion.institution_id == current_user.institution_id, TimetableVersion.is_active == True)
            .first()
        )
        if not tt_version:
            tt_version = TimetableVersion(
                institution_id=current_user.institution_id,
                academic_year_id=active_year.id,
                version_number=1,
                is_active=True
            )
            db.add(tt_version)
            db.flush()
        version_id = tt_version.id

    # 1. Faculty conflict check: Is faculty already booked at this day & period?
    faculty_clash = (
        db.query(TimetableEntry)
        .filter(
            TimetableEntry.timetable_version_id == version_id,
            TimetableEntry.faculty_id == request.faculty_id,
            TimetableEntry.day_of_week == request.day_of_week,
            TimetableEntry.period_number == request.period_number
        )
        .first()
    )
    if faculty_clash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Faculty schedule conflict: Lecturer is already scheduled in {faculty_clash.division.class_model.name} - Division {faculty_clash.division.name} for Period {request.period_number}"
        )

    # 2. Division conflict check: Is division already attending a lecture at this day & period?
    division_clash = (
        db.query(TimetableEntry)
        .filter(
            TimetableEntry.timetable_version_id == version_id,
            TimetableEntry.division_id == request.division_id,
            TimetableEntry.day_of_week == request.day_of_week,
            TimetableEntry.period_number == request.period_number
        )
        .first()
    )
    if division_clash and not (request.is_practical_batch and division_clash.is_practical_batch):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Division schedule conflict: Division already has lecture '{division_clash.subject.name}' scheduled for Period {request.period_number}"
        )

    # 3. Room conflict check (if room is assigned)
    if request.room_number:
        room_clash = (
            db.query(TimetableEntry)
            .filter(
                TimetableEntry.timetable_version_id == version_id,
                TimetableEntry.room_number == request.room_number,
                TimetableEntry.day_of_week == request.day_of_week,
                TimetableEntry.period_number == request.period_number
            )
            .first()
        )
        if room_clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Room conflict: Room {request.room_number} is already occupied by {room_clash.division.name} ({room_clash.subject.name})"
            )

    entry = TimetableEntry(
        timetable_version_id=version_id,
        institution_id=current_user.institution_id,
        division_id=request.division_id,
        subject_id=request.subject_id,
        faculty_id=request.faculty_id,
        day_of_week=request.day_of_week,
        period_number=request.period_number,
        start_time=request.start_time,
        end_time=request.end_time,
        room_number=request.room_number,
        is_practical_batch=request.is_practical_batch,
        batch_name=request.batch_name
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return TimetableEntryResponse(
        id=entry.id,
        division_id=entry.division_id,
        division_name=entry.division.name,
        class_name=entry.division.class_model.name,
        subject_id=entry.subject_id,
        subject_name=entry.subject.name,
        subject_code=entry.subject.code,
        faculty_id=entry.faculty_id,
        faculty_name=entry.faculty.user.full_name,
        day_of_week=entry.day_of_week,
        period_number=entry.period_number,
        start_time=entry.start_time,
        end_time=entry.end_time,
        room_number=entry.room_number,
        is_practical_batch=entry.is_practical_batch,
        batch_name=entry.batch_name
    )


@router.delete("/entries/{id}")
def delete_timetable_entry(
    id: str,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: Session = Depends(get_db)
):
    """Delete a timetable period."""
    entry = (
        db.query(TimetableEntry)
        .filter(TimetableEntry.id == id, TimetableEntry.institution_id == current_user.institution_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Timetable entry not found")

    db.delete(entry)
    db.commit()
    return {"message": "Timetable entry deleted successfully"}
