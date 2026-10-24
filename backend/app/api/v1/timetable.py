from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.deps import get_db, get_current_user, require_roles, verify_student_access
from app.core.docstore import Conflict, DocStore, UserDoc
from app.core.q import ids
from app.schemas.timetable import (
    AvailableSlotResponse,
    SlotSubjectOption,
    TimetableEntryCreate,
    TimetableEntryResponse,
    TimetableSlotCreate,
    TimetableSlotResponse,
    TimetableSlotUpdate,
)

router = APIRouter(prefix="/timetable", tags=["Timetable & Scheduling"])


def _entry_responses(db: DocStore, entries) -> List[TimetableEntryResponse]:
    """Resolve division/class/subject/faculty names with batched lookups."""
    divisions = db.get_many("divisions", ids(entries, "division_id"))
    classes = db.get_many("classes", [d.class_id for d in divisions.values()])
    subjects = db.get_many("subjects", ids(entries, "subject_id"))
    faculty = db.get_many("faculty_profiles", ids(entries, "faculty_id"))
    users = db.get_many("users", [f.user_id for f in faculty.values()])
    results = []
    for e in entries:
        division = divisions[e.division_id]
        subject = subjects[e.subject_id]
        results.append(
            TimetableEntryResponse(
                id=e.id,
                division_id=e.division_id,
                division_name=division.name,
                class_name=classes[division.class_id].name,
                subject_id=e.subject_id,
                subject_name=subject.name,
                subject_code=subject.code,
                faculty_id=e.faculty_id,
                faculty_name=users[faculty[e.faculty_id].user_id].full_name,
                day_of_week=e.day_of_week,
                period_number=e.period_number,
                start_time=e.start_time,
                end_time=e.end_time,
                room_number=e.room_number,
                is_practical_batch=e.is_practical_batch,
                batch_name=e.batch_name,
            )
        )
    return results


@router.get("", response_model=List[TimetableEntryResponse])
def get_timetable(
    division_id: Optional[str] = None,
    faculty_id: Optional[str] = None,
    student_id: Optional[str] = None,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """Fetch timetable slots by division, faculty, or student."""
    query = {"institution_id": current_user.institution_id}

    if division_id:
        query["division_id"] = division_id
    elif faculty_id:
        query["faculty_id"] = faculty_id
    elif current_user.faculty_profile:
        query["faculty_id"] = current_user.faculty_profile.id
    elif current_user.student_profile:
        sid = current_user.student_profile.id
        enrollment = db.find_one("enrollments", {"student_id": sid})
        if enrollment:
            query["division_id"] = enrollment.division_id
        else:
            return []
    elif student_id:
        # Re-validate student identity or guardian-child link server-side
        student = verify_student_access(student_id, current_user, db)
        enrollment = db.find_one("enrollments", {"student_id": student.id})
        if enrollment:
            query["division_id"] = enrollment.division_id
        else:
            return []
    elif current_user.guardian_profile:
        # If parent called without student_id, find first verified linked child
        link = db.find_one(
            "student_guardian_links",
            {"guardian_id": current_user.guardian_profile.id, "is_verified": True},
        )
        if link:
            enrollment = db.find_one("enrollments", {"student_id": link.student_id})
            if enrollment:
                query["division_id"] = enrollment.division_id
            else:
                return []
        else:
            return []

    entries = db.find("timetable_entries", query, sort=[("day_of_week", 1), ("period_number", 1)])
    return _entry_responses(db, entries)


@router.post("/entries", response_model=TimetableEntryResponse, status_code=status.HTTP_201_CREATED)
def create_timetable_entry(
    request: TimetableEntryCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY", "OFFICE_STAFF")),
    db: DocStore = Depends(get_db)
):
    """Add a lecture slot with automatic conflict detection."""
    faculty_profile = current_user.faculty_profile
    if faculty_profile:
        if request.faculty_id != faculty_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Faculty can only schedule their own teaching slots",
            )
    elif not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A faculty or institution context is required to schedule a slot",
        )

    division = db.find_one(
        "divisions",
        {"id": request.division_id, "institution_id": current_user.institution_id},
    )
    subject = db.find_one(
        "subjects",
        {"id": request.subject_id, "institution_id": current_user.institution_id},
    )
    faculty = db.find_one(
        "faculty_profiles",
        {"id": request.faculty_id, "institution_id": current_user.institution_id},
    )
    if not division or not subject or not faculty:
        raise HTTPException(status_code=404, detail="Division, subject, or faculty profile not found")

    if faculty_profile:
        assignment = db.find_one(
            "faculty_subject_assignments",
            {
                "faculty_id": faculty_profile.id,
                "division_id": request.division_id,
                "subject_id": request.subject_id,
                "institution_id": current_user.institution_id,
            },
        )
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Faculty can only schedule assigned subjects and divisions",
            )
    # When the department/class has a slot template, only its slots (with its times and
    # reserved subject) can be scheduled; classes without a template keep free scheduling.
    start_time, end_time = request.start_time, request.end_time
    if db.count("timetable_slots", {"division_id": request.division_id}):
        template_slot = db.find_one(
            "timetable_slots",
            {"division_id": request.division_id, "day_of_week": request.day_of_week, "period_number": request.period_number},
        )
        if not template_slot:
            raise HTTPException(
                status_code=400,
                detail="No slot is defined for this division on that day and period",
            )
        if template_slot.subject_id and template_slot.subject_id != request.subject_id:
            reserved = db.get("subjects", template_slot.subject_id)
            raise HTTPException(
                status_code=400,
                detail=f"This slot is reserved for {reserved.name if reserved else 'another subject'}",
            )
        start_time, end_time = template_slot.start_time, template_slot.end_time

    # Find or create active timetable version
    version_id = request.timetable_version_id
    if not version_id:
        active_year = db.find_one(
            "academic_years",
            {"institution_id": current_user.institution_id, "is_current": True},
        )
        if not active_year:
            active_year = db.find_one("academic_years", {"institution_id": current_user.institution_id})
        if not active_year:
            current_year = date.today().year
            active_year = db.insert("academic_years", {
                "institution_id": current_user.institution_id,
                "name": f"{current_year}-{current_year + 1}",
                "start_date": date(current_year, 6, 1),
                "end_date": date(current_year + 1, 5, 31),
                "is_current": True,
                "is_archived": False,
            })

        tt_version = db.find_one(
            "timetable_versions",
            {"institution_id": current_user.institution_id, "is_active": True},
        )
        if not tt_version:
            tt_version = db.insert("timetable_versions", {
                "institution_id": current_user.institution_id,
                "academic_year_id": active_year.id,
                "version_number": 1,
                "is_active": True,
            })
        version_id = tt_version.id

    slot = {
        "timetable_version_id": version_id,
        "day_of_week": request.day_of_week,
        "period_number": request.period_number,
    }

    # 1. Faculty conflict check: Is faculty already booked at this day & period?
    faculty_clash = db.find_one("timetable_entries", {**slot, "faculty_id": request.faculty_id})
    if faculty_clash:
        clash_division = db.get("divisions", faculty_clash.division_id)
        clash_class = db.get("classes", clash_division.class_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Faculty schedule conflict: Lecturer is already scheduled in {clash_class.name} - Division {clash_division.name} for Period {request.period_number}"
        )

    # 2. Division conflict check: Is division already attending a lecture at this day & period?
    division_clash = db.find_one("timetable_entries", {**slot, "division_id": request.division_id})
    if division_clash and not (request.is_practical_batch and division_clash.is_practical_batch):
        clash_subject = db.get("subjects", division_clash.subject_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Division schedule conflict: Division already has lecture '{clash_subject.name}' scheduled for Period {request.period_number}"
        )

    # 3. Room conflict check (if room is assigned)
    if request.room_number:
        room_clash = db.find_one("timetable_entries", {**slot, "room_number": request.room_number})
        if room_clash:
            clash_division = db.get("divisions", room_clash.division_id)
            clash_subject = db.get("subjects", room_clash.subject_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Room conflict: Room {request.room_number} is already occupied by {clash_division.name} ({clash_subject.name})"
            )

    try:
        entry = db.insert("timetable_entries", {
            "timetable_version_id": version_id,
            "institution_id": current_user.institution_id,
            "division_id": request.division_id,
            "subject_id": request.subject_id,
            "faculty_id": request.faculty_id,
            "day_of_week": request.day_of_week,
            "period_number": request.period_number,
            "start_time": start_time,
            "end_time": end_time,
            "room_number": request.room_number,
            "is_practical_batch": request.is_practical_batch,
            "batch_name": request.batch_name,
        })
    except Conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Schedule conflict: this slot is already taken for the faculty or division",
        )

    return _entry_responses(db, [entry])[0]


@router.delete("/entries/{id}")
def delete_timetable_entry(
    id: str,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: DocStore = Depends(get_db)
):
    """Delete a timetable period."""
    entry = db.find_one(
        "timetable_entries",
        {"id": id, "institution_id": current_user.institution_id},
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Timetable entry not found")

    db.delete("timetable_entries", entry)
    return {"message": "Timetable entry deleted successfully"}

# ---------------------------------------------------------------------------
# Slot templates: the periods (and optionally the subject) of each weekday, per
# department/class. Divisions are scheduled from these slots.
# ---------------------------------------------------------------------------
SLOT_MANAGERS = ("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")


def _require_institution(current_user: UserDoc) -> str:
    if not current_user.institution_id:
        raise HTTPException(status_code=403, detail="An institution context is required")
    return current_user.institution_id


def _slot_responses(db: DocStore, slots) -> List[TimetableSlotResponse]:
    divisions = db.get_many("divisions", ids(slots, "division_id"))
    classes = db.get_many("classes", ids(divisions.values(), "class_id"))
    subjects = db.get_many("subjects", ids(slots, "subject_id"))
    results = []
    for slot in slots:
        division = divisions[slot.division_id]
        subject = subjects.get(slot.subject_id) if slot.subject_id else None
        results.append(TimetableSlotResponse(
            id=slot.id,
            class_id=division.class_id,
            class_name=classes[division.class_id].name,
            division_id=division.id,
            division_name=division.name,
            day_of_week=slot.day_of_week,
            period_number=slot.period_number,
            start_time=slot.start_time,
            end_time=slot.end_time,
            subject_id=slot.subject_id,
            subject_name=subject.name if subject else None,
            subject_code=subject.code if subject else None,
        ))
    return results


def _check_slot_times(start, end) -> None:
    if start >= end:
        raise HTTPException(status_code=400, detail="Slot end time must be after its start time")


def _check_no_overlap(db: DocStore, division_id: str, day: int, start, end, ignore_id: Optional[str] = None) -> None:
    for other in db.find("timetable_slots", {"division_id": division_id, "day_of_week": day}):
        if other.id != ignore_id and start < other.end_time and other.start_time < end:
            raise HTTPException(
                status_code=409,
                detail=f"Time overlaps period {other.period_number} on day {day} for this division",
            )


def _check_subject(db: DocStore, subject_id: Optional[str], institution_id: str) -> None:
    if subject_id and not db.find_one("subjects", {"id": subject_id, "institution_id": institution_id}):
        raise HTTPException(status_code=404, detail="Subject not found")


def _slot_entries(db: DocStore, slot) -> list:
    return db.find("timetable_entries", {
        "division_id": slot.division_id,
        "day_of_week": slot.day_of_week,
        "period_number": slot.period_number,
    })


@router.get("/slots", response_model=List[TimetableSlotResponse])
def list_slots(
    class_id: Optional[str] = None,
    division_id: Optional[str] = None,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """List slot templates, optionally for one department/class or the class of a division."""
    query = {"institution_id": current_user.institution_id}
    if division_id:
        division = db.find_one("divisions", {"id": division_id, "institution_id": current_user.institution_id})
        if not division:
            raise HTTPException(status_code=404, detail="Division not found")
        query["division_id"] = division_id
    elif class_id:
        divisions = db.find("divisions", {"class_id": class_id, "institution_id": current_user.institution_id})
        query["division_id"] = {"$in": ids(divisions, "id")}
    slots = db.find("timetable_slots", query, sort=[("day_of_week", 1), ("period_number", 1)])
    return _slot_responses(db, slots)


@router.post("/slots", response_model=List[TimetableSlotResponse], status_code=status.HTTP_201_CREATED)
def create_slots(
    request: TimetableSlotCreate,
    current_user: UserDoc = Depends(require_roles(*SLOT_MANAGERS)),
    db: DocStore = Depends(get_db),
):
    """Define one period of a department/class for the chosen weekdays."""
    institution_id = _require_institution(current_user)
    division = db.find_one("divisions", {"id": request.division_id, "institution_id": institution_id})
    if not division:
        raise HTTPException(status_code=404, detail="Division not found")
    days = sorted(set(request.days_of_week))
    if not days or any(day < 1 or day > 6 for day in days):
        raise HTTPException(status_code=400, detail="Choose weekdays between 1 (Monday) and 6 (Saturday)")
    if not 1 <= request.period_number <= 8:
        raise HTTPException(status_code=400, detail="Period number must be between 1 and 8")
    _check_slot_times(request.start_time, request.end_time)
    _check_subject(db, request.subject_id, institution_id)

    for day in days:
        if db.find_one("timetable_slots", {"division_id": request.division_id, "day_of_week": day, "period_number": request.period_number}):
            raise HTTPException(status_code=409, detail=f"Period {request.period_number} already exists on day {day}")
        _check_no_overlap(db, request.division_id, day, request.start_time, request.end_time)

    try:
        with db.transaction():
            created = [
                db.insert("timetable_slots", {
                    "institution_id": institution_id,
                    "division_id": request.division_id,
                    "subject_id": request.subject_id,
                    "day_of_week": day,
                    "period_number": request.period_number,
                    "start_time": request.start_time,
                    "end_time": request.end_time,
                })
                for day in days
            ]
    except Conflict:
        raise HTTPException(status_code=409, detail="This period already exists for the department/class")
    return _slot_responses(db, created)


@router.put("/slots/{id}", response_model=TimetableSlotResponse)
def update_slot(
    id: str,
    request: TimetableSlotUpdate,
    current_user: UserDoc = Depends(require_roles(*SLOT_MANAGERS)),
    db: DocStore = Depends(get_db),
):
    """Change a slot's times or reserved subject; day and period stay fixed."""
    institution_id = _require_institution(current_user)
    slot = db.find_one("timetable_slots", {"id": id, "institution_id": institution_id})
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    changes = {}
    start = request.start_time or slot.start_time
    end = request.end_time or slot.end_time
    _check_slot_times(start, end)
    if "start_time" in request.model_fields_set and request.start_time:
        changes["start_time"] = request.start_time
    if "end_time" in request.model_fields_set and request.end_time:
        changes["end_time"] = request.end_time
    if "start_time" in changes or "end_time" in changes:
        _check_no_overlap(db, slot.division_id, slot.day_of_week, start, end, ignore_id=slot.id)
    entries = _slot_entries(db, slot)
    if "subject_id" in request.model_fields_set:
        _check_subject(db, request.subject_id, institution_id)
        if request.subject_id and any(entry.subject_id != request.subject_id for entry in entries):
            raise HTTPException(status_code=400, detail="Lectures with another subject are already scheduled in this slot")
        changes["subject_id"] = request.subject_id
    with db.transaction():
        slot = db.update(slot, changes) if changes else slot
        if "start_time" in changes or "end_time" in changes:
            for entry in entries:
                db.update(entry, {"start_time": start, "end_time": end})
    return _slot_responses(db, [slot])[0]


@router.delete("/slots/{id}")
def delete_slot(
    id: str,
    current_user: UserDoc = Depends(require_roles(*SLOT_MANAGERS)),
    db: DocStore = Depends(get_db),
):
    """Remove an unused slot from a department/class template."""
    institution_id = _require_institution(current_user)
    slot = db.find_one("timetable_slots", {"id": id, "institution_id": institution_id})
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    if _slot_entries(db, slot):
        raise HTTPException(status_code=400, detail="Lectures are already scheduled in this slot; remove them first")
    db.delete("timetable_slots", slot)
    return {"message": "Slot deleted successfully"}


@router.get("/available-slots", response_model=List[AvailableSlotResponse])
def list_available_slots(
    division_id: str,
    faculty_id: Optional[str] = None,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY")),
    db: DocStore = Depends(get_db),
):
    """Slots of a division's department/class that a teacher can take, with the subjects they may teach there."""
    institution_id = _require_institution(current_user)
    division = db.find_one("divisions", {"id": division_id, "institution_id": institution_id})
    if not division:
        raise HTTPException(status_code=404, detail="Division not found")
    teacher_id = current_user.faculty_profile.id if current_user.faculty_profile else faculty_id
    if not teacher_id:
        raise HTTPException(status_code=400, detail="faculty_id is required")

    assigned = db.find("faculty_subject_assignments", {"faculty_id": teacher_id, "division_id": division_id})
    subjects = db.get_many("subjects", ids(assigned, "subject_id"))

    entry_scope = {"institution_id": institution_id}
    active_version = db.find_one("timetable_versions", {"institution_id": institution_id, "is_active": True})
    if active_version:
        entry_scope["timetable_version_id"] = active_version.id
    division_entries = {
        (entry.day_of_week, entry.period_number): entry
        for entry in db.find("timetable_entries", {**entry_scope, "division_id": division_id})
    }
    busy = {
        (entry.day_of_week, entry.period_number)
        for entry in db.find("timetable_entries", {**entry_scope, "faculty_id": teacher_id})
    }
    taken_faculty = db.get_many("faculty_profiles", ids(division_entries.values(), "faculty_id"))
    taken_users = db.get_many("users", [profile.user_id for profile in taken_faculty.values()])
    taken_subjects = db.get_many("subjects", ids(division_entries.values(), "subject_id"))

    results = []
    slots = db.find("timetable_slots", {"division_id": division_id}, sort=[("day_of_week", 1), ("period_number", 1)])
    for slot in slots:
        key = (slot.day_of_week, slot.period_number)
        taken = division_entries.get(key)
        state = "TAKEN" if taken else "FACULTY_BUSY" if key in busy else "OPEN"
        results.append(AvailableSlotResponse(
            slot_id=slot.id,
            day_of_week=slot.day_of_week,
            period_number=slot.period_number,
            start_time=slot.start_time,
            end_time=slot.end_time,
            status=state,
            taken_by=taken_users[taken_faculty[taken.faculty_id].user_id].full_name if taken else None,
            taken_subject=taken_subjects[taken.subject_id].name if taken else None,
            allowed_subjects=[
                SlotSubjectOption(subject_id=item.id, subject_name=item.name, subject_code=item.code)
                for item in subjects.values()
                if not slot.subject_id or slot.subject_id == item.id
            ],
        ))
    return results
