from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.deps import get_current_user, get_db, require_roles, verify_student_access
from app.core.docstore import DocStore, UserDoc
from app.core.q import ids, index_by, group_by
from app.schemas.examination import (
    ExaminationCreate,
    ExaminationResponse,
    ExamSubjectResponse,
    MarksBatchSaveRequest,
    MarksEntryResponse,
    MarksApprovalResponse,
    MarksApprovalReviewRequest,
)

router = APIRouter(prefix="/examinations", tags=["Examinations & Marks Engine"])


def _exam_subject_progress(db: DocStore, exam_subject_id: str, division_id: str | None) -> str:
    approval_filter = {"exam_subject_id": exam_subject_id}
    marks_filter = {"exam_subject_id": exam_subject_id}
    if division_id:
        approval_filter["division_id"] = division_id
        marks_filter["division_id"] = division_id
    approvals = db.find("marks_approvals", approval_filter)
    if any(approval.status == "APPROVED" for approval in approvals):
        return "APPROVED"
    if any(approval.status == "PENDING" for approval in approvals):
        return "PENDING"
    if any(approval.status == "REJECTED" for approval in approvals):
        return "REJECTED"
    if db.count("marks_entries", marks_filter):
        return "DRAFT"
    return "NOT_STARTED"


def _exam_subject_response(
    db: DocStore,
    exam_subject,
    subjects_by_id=None,
    classes_by_id=None,
    divisions_by_id=None,
    faculty_by_id=None,
    users_by_id=None,
) -> ExamSubjectResponse:
    subject = (subjects_by_id or {}).get(exam_subject.subject_id) or db.get("subjects", exam_subject.subject_id)
    class_doc = (classes_by_id or {}).get(exam_subject.class_id) or db.get("classes", exam_subject.class_id)
    division_id = exam_subject.get("division_id")
    division = ((divisions_by_id or {}).get(division_id) or db.get("divisions", division_id)) if division_id else None
    faculty_id = exam_subject.get("faculty_id")
    faculty = ((faculty_by_id or {}).get(faculty_id) or db.get("faculty_profiles", faculty_id)) if faculty_id else None
    faculty_user = ((users_by_id or {}).get(faculty.user_id) or db.get("users", faculty.user_id)) if faculty else None
    return ExamSubjectResponse(
        id=exam_subject.id,
        subject_id=exam_subject.subject_id,
        subject_name=subject.name if subject else "Subject",
        subject_code=subject.code if subject else "",
        class_id=exam_subject.class_id,
        class_name=class_doc.name if class_doc else "",
        division_id=exam_subject.get("division_id"),
        division_name=division.name if division else None,
        faculty_id=exam_subject.get("faculty_id"),
        faculty_name=faculty_user.full_name if faculty_user else None,
        marks_status=_exam_subject_progress(db, exam_subject.id, exam_subject.get("division_id")),
        max_theory_marks=exam_subject.max_theory_marks,
        max_practical_marks=exam_subject.max_practical_marks,
        min_passing_marks=exam_subject.min_passing_marks,
        exam_date=exam_subject.exam_date,
        start_time=exam_subject.get("start_time"),
        end_time=exam_subject.get("end_time"),
    )


@router.get("", response_model=List[ExaminationResponse])
def list_examinations(
    academic_year_id: Optional[str] = None,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """List examinations for the active academic year."""
    flt = {"institution_id": current_user.institution_id}
    if academic_year_id:
        flt["academic_year_id"] = academic_year_id

    exams = db.find("examinations", flt, sort=[("start_date", -1)])
    visible_enrollments_by_year = {}
    visible_student_ids = []
    role_names = current_user.role_names
    cohort_restricted = "STUDENT" in role_names or "PARENT" in role_names
    if "STUDENT" in role_names and current_user.student_profile:
        visible_student_ids = [current_user.student_profile.id]
    elif "PARENT" in role_names and current_user.guardian_profile:
        links = db.find("student_guardian_links", {"guardian_id": current_user.guardian_profile.id})
        visible_student_ids = ids(links, "student_id")
    if cohort_restricted and not visible_student_ids:
        return []
    if visible_student_ids:
        for year_id in {exam.academic_year_id for exam in exams}:
            visible_enrollments_by_year[year_id] = db.find("enrollments", {
                "student_id": {"$in": visible_student_ids},
                "academic_year_id": year_id,
            })

    exam_ids = ids(exams)
    pubs_by_exam = group_by(db.find("result_publications", {"examination_id": {"$in": exam_ids}}), "examination_id") if exams else {}
    exam_subjects_by_exam = group_by(db.find("exam_subjects", {"examination_id": {"$in": exam_ids}}), "examination_id") if exams else {}
    all_exam_subjects = [es for group in exam_subjects_by_exam.values() for es in group]
    subjects_by_id = db.get_many("subjects", ids(all_exam_subjects, "subject_id"))
    classes_by_id = db.get_many("classes", ids(all_exam_subjects, "class_id"))
    divisions_by_id = db.get_many("divisions", ids(all_exam_subjects, "division_id"))
    faculty_by_id = db.get_many("faculty_profiles", ids(all_exam_subjects, "faculty_id"))
    users_by_id = db.get_many("users", [faculty.user_id for faculty in faculty_by_id.values()])
    results = []
    for ex in exams:
        is_published = len(pubs_by_exam.get(ex.id, [])) > 0
        if visible_student_ids:
            enrolled_classes = {
                enrollment.class_id
                for enrollment in visible_enrollments_by_year.get(ex.academic_year_id, [])
            }
            is_published = any(
                publication.class_id in enrolled_classes
                for publication in pubs_by_exam.get(ex.id, [])
            )
        subjects_out = []
        for es in exam_subjects_by_exam.get(ex.id, []):
            if visible_student_ids:
                enrollments = visible_enrollments_by_year.get(ex.academic_year_id, [])
                if not any(
                    enrollment.class_id == es.class_id and
                    (not es.get("division_id") or enrollment.division_id == es.division_id)
                    for enrollment in enrollments
                ):
                    continue
            subjects_out.append(_exam_subject_response(
                db, es, subjects_by_id, classes_by_id, divisions_by_id, faculty_by_id, users_by_id
            ))
        if visible_student_ids and not subjects_out:
            continue
        results.append(
            ExaminationResponse(
                id=ex.id,
                academic_year_id=ex.academic_year_id,
                name=ex.name,
                exam_type=ex.exam_type,
                start_date=ex.start_date,
                end_date=ex.end_date,
                status=ex.status,
                is_published=is_published,
                subjects=subjects_out
            )
        )
    return results


@router.post("", response_model=ExaminationResponse, status_code=status.HTTP_201_CREATED)
def create_examination(
    request: ExaminationCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: DocStore = Depends(get_db)
):
    """Schedule an examination and validate each division/teacher pairing."""
    if not request.subjects:
        raise HTTPException(status_code=400, detail="Add at least one subject to the examination")
    if request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="Examination end date must be on or after its start date")
    year = db.find_one("academic_years", {
        "id": request.academic_year_id,
        "institution_id": current_user.institution_id,
    })
    if not year:
        raise HTTPException(status_code=400, detail="Academic year not found in this institution")

    validated_subjects = []
    seen_subject_divisions = set()
    for subject_request in request.subjects:
        subject = db.find_one("subjects", {
            "id": subject_request.subject_id,
            "institution_id": current_user.institution_id,
        })
        class_doc = db.find_one("classes", {
            "id": subject_request.class_id,
            "institution_id": current_user.institution_id,
        })
        if not subject or not class_doc:
            raise HTTPException(status_code=400, detail="Every exam subject and class must belong to this institution")
        if not request.start_date <= subject_request.exam_date <= request.end_date:
            raise HTTPException(status_code=400, detail="Each subject exam date must be within the examination date range")
        if subject_request.end_time <= subject_request.start_time:
            raise HTTPException(status_code=400, detail="Each subject's end time must be later than its start time")
        key = (subject_request.subject_id, subject_request.division_id or subject_request.class_id)
        if key in seen_subject_divisions:
            raise HTTPException(status_code=400, detail="A subject can only be scheduled once per division in an examination")
        seen_subject_divisions.add(key)

        if subject_request.division_id or subject_request.faculty_id:
            division = db.find_one("divisions", {
                "id": subject_request.division_id,
                "institution_id": current_user.institution_id,
                "class_id": subject_request.class_id,
            })
            if not division or not subject_request.faculty_id:
                raise HTTPException(status_code=400, detail="Choose a division and its assigned teacher for each scheduled subject")
            assignment = db.find_one("faculty_subject_assignments", {
                "institution_id": current_user.institution_id,
                "academic_year_id": request.academic_year_id,
                "faculty_id": subject_request.faculty_id,
                "subject_id": subject_request.subject_id,
                "division_id": subject_request.division_id,
            })
            if not assignment:
                raise HTTPException(status_code=400, detail="The selected teacher is not assigned to this subject and division")
        for existing in validated_subjects:
            same_division = subject_request.division_id and existing.division_id == subject_request.division_id
            same_teacher = subject_request.faculty_id and existing.faculty_id == subject_request.faculty_id
            if (same_division or same_teacher) and existing.exam_date == subject_request.exam_date:
                if subject_request.start_time < existing.end_time and existing.start_time < subject_request.end_time:
                    raise HTTPException(status_code=400, detail="Exam times cannot overlap for the same division or teacher")
        validated_subjects.append(subject_request)

    exam = db.insert("examinations", {
        "institution_id": current_user.institution_id,
        "academic_year_id": request.academic_year_id,
        "name": request.name,
        "exam_type": request.exam_type,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "status": "SCHEDULED",
    })

    subjects_out = []
    for s in validated_subjects:
        es = db.insert("exam_subjects", {
            "examination_id": exam.id,
            "subject_id": s.subject_id,
            "class_id": s.class_id,
            "division_id": s.division_id,
            "faculty_id": s.faculty_id,
            "max_theory_marks": s.max_theory_marks,
            "max_practical_marks": s.max_practical_marks,
            "min_passing_marks": s.min_passing_marks,
            "exam_date": s.exam_date,
            "start_time": s.start_time,
            "end_time": s.end_time,
        })
        subjects_out.append(_exam_subject_response(db, es))

    return ExaminationResponse(
        id=exam.id,
        academic_year_id=exam.academic_year_id,
        name=exam.name,
        exam_type=exam.exam_type,
        start_date=exam.start_date,
        end_date=exam.end_date,
        status=exam.status,
        is_published=False,
        subjects=subjects_out
    )


def _ensure_exam_is_editable(exam, db: DocStore) -> list:
    if db.exists("result_publications", {"examination_id": exam.id}):
        raise HTTPException(status_code=409, detail="Published examinations cannot be edited or deleted")
    subjects = db.find("exam_subjects", {"examination_id": exam.id})
    subject_ids = ids(subjects)
    if subject_ids and (
        db.exists("marks_entries", {"exam_subject_id": {"$in": subject_ids}})
        or db.exists("marks_approvals", {"exam_subject_id": {"$in": subject_ids}})
    ):
        raise HTTPException(status_code=409, detail="Examinations with saved or submitted marks cannot be edited or deleted")
    return subjects


@router.put("/{id}", response_model=ExaminationResponse)
def update_examination(
    id: str,
    request: ExaminationCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: DocStore = Depends(get_db),
):
    exam = db.find_one("examinations", {"id": id, "institution_id": current_user.institution_id})
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")
    old_subjects = _ensure_exam_is_editable(exam, db)
    if not request.subjects:
        raise HTTPException(status_code=400, detail="An examination must include at least one subject")
    if request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="Examination end date must be on or after its start date")
    year = db.find_one("academic_years", {
        "id": request.academic_year_id,
        "institution_id": current_user.institution_id,
    })
    if not year:
        raise HTTPException(status_code=400, detail="Academic year not found in this institution")

    validated_subjects = []
    seen_subject_divisions = set()
    for subject_request in request.subjects:
        subject = db.find_one("subjects", {
            "id": subject_request.subject_id,
            "institution_id": current_user.institution_id,
        })
        class_doc = db.find_one("classes", {
            "id": subject_request.class_id,
            "institution_id": current_user.institution_id,
        })
        if not subject or not class_doc:
            raise HTTPException(status_code=400, detail="Every exam subject and class must belong to this institution")
        if not request.start_date <= subject_request.exam_date <= request.end_date:
            raise HTTPException(status_code=400, detail="Each subject exam date must be within the examination date range")
        if subject_request.end_time <= subject_request.start_time:
            raise HTTPException(status_code=400, detail="Each subject's end time must be later than its start time")
        key = (subject_request.subject_id, subject_request.division_id or subject_request.class_id)
        if key in seen_subject_divisions:
            raise HTTPException(status_code=400, detail="A subject can only be scheduled once per division in an examination")
        seen_subject_divisions.add(key)
        if subject_request.division_id or subject_request.faculty_id:
            division = db.find_one("divisions", {
                "id": subject_request.division_id,
                "institution_id": current_user.institution_id,
                "class_id": subject_request.class_id,
            })
            if not division or not subject_request.faculty_id:
                raise HTTPException(status_code=400, detail="Choose a division and its assigned teacher for each scheduled subject")
            assignment = db.find_one("faculty_subject_assignments", {
                "institution_id": current_user.institution_id,
                "academic_year_id": request.academic_year_id,
                "faculty_id": subject_request.faculty_id,
                "subject_id": subject_request.subject_id,
                "division_id": subject_request.division_id,
            })
            if not assignment:
                raise HTTPException(status_code=400, detail="The selected teacher is not assigned to this subject and division")
        for existing in validated_subjects:
            same_division = subject_request.division_id and existing.division_id == subject_request.division_id
            same_teacher = subject_request.faculty_id and existing.faculty_id == subject_request.faculty_id
            if (same_division or same_teacher) and existing.exam_date == subject_request.exam_date:
                if subject_request.start_time < existing.end_time and existing.start_time < subject_request.end_time:
                    raise HTTPException(status_code=400, detail="Exam times cannot overlap for the same division or teacher")
        validated_subjects.append(subject_request)

    exam = db.update(exam, {
        "academic_year_id": request.academic_year_id,
        "name": request.name,
        "exam_type": request.exam_type,
        "start_date": request.start_date,
        "end_date": request.end_date,
    })
    for exam_subject in old_subjects:
        db.delete("exam_subjects", exam_subject)
    subject_rows = []
    for subject_request in validated_subjects:
        subject_rows.append(db.insert("exam_subjects", {
            "examination_id": exam.id,
            "subject_id": subject_request.subject_id,
            "class_id": subject_request.class_id,
            "division_id": subject_request.division_id,
            "faculty_id": subject_request.faculty_id,
            "max_theory_marks": subject_request.max_theory_marks,
            "max_practical_marks": subject_request.max_practical_marks,
            "min_passing_marks": subject_request.min_passing_marks,
            "exam_date": subject_request.exam_date,
            "start_time": subject_request.start_time,
            "end_time": subject_request.end_time,
        }))
    return ExaminationResponse(
        id=exam.id,
        academic_year_id=exam.academic_year_id,
        name=exam.name,
        exam_type=exam.exam_type,
        start_date=exam.start_date,
        end_date=exam.end_date,
        status=exam.status,
        is_published=False,
        subjects=[_exam_subject_response(db, subject_row) for subject_row in subject_rows],
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_examination(
    id: str,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: DocStore = Depends(get_db),
):
    exam = db.find_one("examinations", {"id": id, "institution_id": current_user.institution_id})
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")
    _ensure_exam_is_editable(exam, db)
    db.delete("examinations", exam)
    return None


def _validate_faculty_exam_assignment(current_user: UserDoc, exam_subject, division_id: str, db: DocStore):
    if "FACULTY" not in current_user.role_names or not current_user.faculty_profile:
        raise HTTPException(status_code=403, detail="Only assigned teachers can access exam marks")
    exam = db.find_one("examinations", {
        "id": exam_subject.examination_id,
        "institution_id": current_user.institution_id,
    })
    division = db.find_one("divisions", {
        "id": division_id,
        "institution_id": current_user.institution_id,
        "class_id": exam_subject.class_id,
    })
    if not exam or not division:
        raise HTTPException(status_code=404, detail="Exam subject or division not found in this institution")
    if exam_subject.get("division_id") and exam_subject.division_id != division_id:
        raise HTTPException(status_code=403, detail="This exam subject is scheduled for a different division")
    assignment = db.find_one("faculty_subject_assignments", {
        "institution_id": current_user.institution_id,
        "academic_year_id": exam.academic_year_id,
        "faculty_id": current_user.faculty_profile.id,
        "subject_id": exam_subject.subject_id,
        "division_id": division_id,
    })
    if not assignment or (
        exam_subject.get("faculty_id") and exam_subject.faculty_id != current_user.faculty_profile.id
    ):
        raise HTTPException(status_code=403, detail="You are not assigned to this exam subject and division")
    return exam


@router.get("/marks/roster", response_model=List[MarksEntryResponse])
def get_marks_roster(
    exam_subject_id: str,
    division_id: str,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """[FACULTY] Get student roster with current marks/drafts for an exam subject & division."""
    es = db.get("exam_subjects", exam_subject_id)
    if not es:
        raise HTTPException(status_code=404, detail="Exam subject not found")
    exam = _validate_faculty_exam_assignment(current_user, es, division_id, db)

    division_enrollments = db.find("enrollments", {
        "division_id": division_id,
        "academic_year_id": exam.academic_year_id,
    })
    students_by_id = db.get_many("students", ids(division_enrollments, "student_id"))
    # Inner join with active students, ordered by roll number then admission number (NULL roll numbers last).
    roster_students = [
        students_by_id[enr.student_id]
        for enr in division_enrollments
        if enr.student_id in students_by_id and students_by_id[enr.student_id].status == "ACTIVE"
    ]
    roster_students.sort(key=lambda st: (st.roll_number is None, st.roll_number or "", st.admission_number or ""))
    users_by_id = db.get_many("users", ids(roster_students, "user_id"))

    entries = db.find("marks_entries", {"exam_subject_id": exam_subject_id, "division_id": division_id})
    existing_entries_map = index_by(entries, "student_id")

    roster = []
    for s in roster_students:
        e = existing_entries_map.get(s.id)
        student_name = users_by_id[s.user_id].full_name
        if e:
            roster.append(
                MarksEntryResponse(
                    id=e.id,
                    student_id=s.id,
                    student_name=student_name,
                    admission_number=s.admission_number,
                    roll_number=s.roll_number,
                    theory_marks_obtained=e.theory_marks_obtained,
                    practical_marks_obtained=e.practical_marks_obtained,
                    total_obtained=e.total_obtained,
                    is_absent=e.is_absent,
                    is_exempt=e.is_exempt,
                    status=e.status,
                    teacher_remarks=e.teacher_remarks
                )
            )
        else:
            roster.append(
                MarksEntryResponse(
                    id="",
                    student_id=s.id,
                    student_name=student_name,
                    admission_number=s.admission_number,
                    roll_number=s.roll_number,
                    theory_marks_obtained=None,
                    practical_marks_obtained=None,
                    total_obtained=None,
                    is_absent=False,
                    is_exempt=False,
                    status="NOT_STARTED",
                    teacher_remarks=None
                )
            )
    return roster


@router.post("/marks/save-draft")
def save_or_submit_marks(
    request: MarksBatchSaveRequest,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """[FACULTY] Save marks in DRAFT mode or SUBMIT for Principal moderation."""
    es = db.get("exam_subjects", request.exam_subject_id)
    if not es:
        raise HTTPException(status_code=404, detail="Exam subject not found")
    exam = _validate_faculty_exam_assignment(current_user, es, request.division_id, db)

    requested_student_ids = [entry.student_id for entry in request.entries]
    enrollments = db.find("enrollments", {
        "division_id": request.division_id,
        "academic_year_id": exam.academic_year_id,
        "student_id": {"$in": requested_student_ids},
    }) if requested_student_ids else []
    if len({enrollment.student_id for enrollment in enrollments}) != len(set(requested_student_ids)):
        raise HTTPException(status_code=400, detail="Every marks entry must belong to the selected division")

    target_status = "SUBMITTED" if request.submit_for_approval else "DRAFT"

    # Validate every entry before persisting anything so a bad row cannot leave a partial batch
    # (the SQL version rolled the whole request back on validation errors).
    for entry_in in request.entries:
        if entry_in.theory_marks_obtained is not None:
            if entry_in.theory_marks_obtained < 0 or entry_in.theory_marks_obtained > es.max_theory_marks:
                raise HTTPException(
                    status_code=400,
                    detail=f"Theory marks must be between 0 and {es.max_theory_marks}"
                )
        if entry_in.practical_marks_obtained is not None:
            if entry_in.practical_marks_obtained < 0 or entry_in.practical_marks_obtained > es.max_practical_marks:
                raise HTTPException(
                    status_code=400,
                    detail=f"Practical marks must be between 0 and {es.max_practical_marks}"
                )

    if not request.entries:
        raise HTTPException(status_code=400, detail="At least one student mark entry is required")
    if len(set(requested_student_ids)) != len(requested_student_ids):
        raise HTTPException(status_code=400, detail="A student can only be included once in a marks batch")
    enrolled_students = db.find("students", {
        "id": {"$in": requested_student_ids},
        "institution_id": current_user.institution_id,
        "status": "ACTIVE",
    })
    if len(enrolled_students) != len(set(requested_student_ids)):
        raise HTTPException(status_code=400, detail="Marks can only be entered for active students in this institution")

    existing_by_student = index_by(
        db.find("marks_entries", {
            "exam_subject_id": request.exam_subject_id,
            "division_id": request.division_id,
            "student_id": {"$in": [e.student_id for e in request.entries]},
        }) if request.entries else [],
        "student_id",
    )
    for entry_in in request.entries:
        total = None
        if not entry_in.is_absent and not entry_in.is_exempt:
            th = entry_in.theory_marks_obtained or Decimal("0.00")
            pr = entry_in.practical_marks_obtained or Decimal("0.00")
            total = th + pr

        existing = existing_by_student.get(entry_in.student_id)
        if existing:
            db.update(existing, {
                "theory_marks_obtained": entry_in.theory_marks_obtained,
                "practical_marks_obtained": entry_in.practical_marks_obtained,
                "total_obtained": total,
                "is_absent": entry_in.is_absent,
                "is_exempt": entry_in.is_exempt,
                "status": target_status,
                "teacher_remarks": entry_in.teacher_remarks,
                "entered_by": current_user.id,
            })
        else:
            existing_by_student[entry_in.student_id] = db.insert("marks_entries", {
                "exam_subject_id": request.exam_subject_id,
                "student_id": entry_in.student_id,
                "division_id": request.division_id,
                "theory_marks_obtained": entry_in.theory_marks_obtained,
                "practical_marks_obtained": entry_in.practical_marks_obtained,
                "total_obtained": total,
                "is_absent": entry_in.is_absent,
                "is_exempt": entry_in.is_exempt,
                "entered_by": current_user.id,
                "status": target_status,
                "teacher_remarks": entry_in.teacher_remarks,
            })

    # If submitted for approval, create/update MarksApproval record
    if request.submit_for_approval:
        now = datetime.now(timezone.utc)
        approval = db.find_one("marks_approvals", {
            "exam_subject_id": request.exam_subject_id,
            "division_id": request.division_id,
        })
        if not approval:
            db.insert("marks_approvals", {
                "exam_subject_id": request.exam_subject_id,
                "division_id": request.division_id,
                "submitted_by": current_user.id,
                "submitted_at": now,
                "status": "PENDING",
            })
        else:
            db.update(approval, {
                "status": "PENDING",
                "submitted_at": now,
                "submitted_by": current_user.id,
            })

    msg = "Marks submitted for Principal review" if request.submit_for_approval else "Marks saved as draft"
    return {"message": msg, "status": target_status}

@router.get("/marks/approvals/pending", response_model=List[MarksApprovalResponse])
def list_pending_approvals(
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db)
):
    """[PRINCIPAL] List marks submissions pending review."""
    institution_exams = db.find("examinations", {"institution_id": current_user.institution_id})
    exams_by_id = index_by(institution_exams)
    exam_subjects = db.find("exam_subjects", {"examination_id": {"$in": ids(institution_exams)}}) if institution_exams else []
    exam_subjects_by_id = index_by(exam_subjects)
    approvals = db.find(
        "marks_approvals",
        {"exam_subject_id": {"$in": ids(exam_subjects)}, "status": "PENDING"},
        sort=[("submitted_at", -1)],
    ) if exam_subjects else []

    subjects_by_id = db.get_many("subjects", ids(exam_subjects, "subject_id"))
    divisions_by_id = db.get_many("divisions", ids(approvals, "division_id"))
    classes_by_id = db.get_many("classes", ids(divisions_by_id.values(), "class_id"))
    users_by_id = db.get_many("users", ids(approvals, "submitted_by") + [a.reviewed_by for a in approvals if a.reviewed_by])

    results = []
    for a in approvals:
        exam_subject = exam_subjects_by_id[a.exam_subject_id]
        division = divisions_by_id[a.division_id]
        reviewer = users_by_id.get(a.reviewed_by) if a.reviewed_by else None
        results.append(
            MarksApprovalResponse(
                id=a.id,
                exam_subject_id=a.exam_subject_id,
                examination_name=exams_by_id[exam_subject.examination_id].name,
                subject_name=subjects_by_id[exam_subject.subject_id].name,
                subject_code=subjects_by_id[exam_subject.subject_id].code,
                division_id=a.division_id,
                division_name=division.name,
                class_name=classes_by_id[division.class_id].name,
                submitted_by_name=users_by_id[a.submitted_by].full_name,
                submitted_at=a.submitted_at,
                status=a.status,
                reviewed_by_name=reviewer.full_name if reviewer else None,
                reviewed_at=a.reviewed_at,
                review_comments=a.review_comments
            )
        )
    return results


@router.put("/marks/approvals/{id}/review")
def review_marks_batch(
    id: str,
    review: MarksApprovalReviewRequest,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db)
):
    """[PRINCIPAL] Review, approve, or reject a submitted marks batch."""
    approval = db.get("marks_approvals", id)
    if not approval:
        raise HTTPException(status_code=404, detail="Marks approval request not found")

    # Prevent unauthorized self-approval
    role_names = current_user.role_names
    if approval.submitted_by == current_user.id and "SUPER_ADMIN" not in role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-Approval Violation: You cannot approve a marks submission that you entered"
        )

    now = datetime.now(timezone.utc)
    new_marks_status = "APPROVED" if review.approved else "REJECTED"
    db.update(approval, {
        "reviewed_by": current_user.id,
        "reviewed_at": now,
        "review_comments": review.review_comments,
        "status": new_marks_status,
    })

    # Update all marks entries in this batch
    db.update_many(
        "marks_entries",
        {"exam_subject_id": approval.exam_subject_id, "division_id": approval.division_id},
        {"status": new_marks_status},
    )

    # Log action in audit logs
    db.insert("audit_logs", {
        "institution_id": current_user.institution_id,
        "user_id": current_user.id,
        "action": f"MARKS_BATCH_{new_marks_status}",
        "entity_type": "marks_approvals",
        "entity_id": approval.id,
        "previous_state": {"status": "PENDING"},
        "new_state": {"status": new_marks_status},
        "reason": review.review_comments,
    })

    return {"message": f"Marks batch {new_marks_status.lower()} successfully"}


@router.post("/{id}/publish")
def publish_examination_results(
    id: str,
    class_id: Optional[str] = None,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db)
):
    """[PRINCIPAL] Formally publish exam results to students and parents."""
    exam = db.find_one("examinations", {"id": id, "institution_id": current_user.institution_id})
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")

    # If class_id not specified, publish for all classes in this institution
    if class_id:
        target_classes = [class_id]
    else:
        inst_classes = db.find("classes", {"institution_id": exam.institution_id})
        target_classes = ids(inst_classes)

    now = datetime.now(timezone.utc)
    for cid in target_classes:
        existing = db.find_one("result_publications", {"examination_id": exam.id, "class_id": cid})
        if not existing:
            db.insert("result_publications", {
                "examination_id": exam.id,
                "class_id": cid,
                "published_by": current_user.id,
                "published_at": now,
                "is_active": True,
            })

    db.update(exam, {"status": "PUBLISHED"})
    # Log in audit
    db.insert("audit_logs", {
        "institution_id": current_user.institution_id,
        "user_id": current_user.id,
        "action": "EXAMINATION_RESULTS_PUBLISHED",
        "entity_type": "examinations",
        "entity_id": exam.id,
        "new_state": {"status": "PUBLISHED", "published_classes": target_classes},
    })

    return {"message": f"Examination '{exam.name}' results published successfully"}


@router.get("/marks/student/{student_id}", response_model=List[dict])
def get_student_marks(
    student_id: str,
    examination_id: Optional[str] = None,
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """Fetch student marks (only published examinations are visible to students and parents)."""
    # Re-validate student access, tenant isolation, and guardian-child relationship server-side
    student = verify_student_access(student_id, current_user, db)

    marks = db.find("marks_entries", {"student_id": student_id})
    exam_subjects_by_id = db.get_many("exam_subjects", ids(marks, "exam_subject_id"))
    exams_by_id = db.get_many("examinations", ids(exam_subjects_by_id.values(), "examination_id"))

    # Inner joins: drop entries whose exam subject/examination no longer exists.
    entries = [
        e for e in marks
        if e.exam_subject_id in exam_subjects_by_id
        and exam_subjects_by_id[e.exam_subject_id].examination_id in exams_by_id
    ]

    # If student or parent, restrict to published examinations
    if current_user.student_profile or current_user.guardian_profile:
        published_exam_ids = {
            p.examination_id
            for p in db.find("result_publications", {"examination_id": {"$in": list(exams_by_id)}, "is_active": True})
        } if exams_by_id else set()
        entries = [e for e in entries if exam_subjects_by_id[e.exam_subject_id].examination_id in published_exam_ids]

    if examination_id:
        entries = [e for e in entries if exam_subjects_by_id[e.exam_subject_id].examination_id == examination_id]

    subjects_by_id = db.get_many("subjects", ids(exam_subjects_by_id.values(), "subject_id"))
    results = []
    for e in entries:
        exam_subject = exam_subjects_by_id[e.exam_subject_id]
        exam = exams_by_id[exam_subject.examination_id]
        subject = subjects_by_id[exam_subject.subject_id]
        results.append({
            "examination_id": exam.id,
            "examination_name": exam.name,
            "subject_id": subject.id,
            "subject_code": subject.code,
            "subject_name": subject.name,
            "max_theory": float(exam_subject.max_theory_marks),
            "max_practical": float(exam_subject.max_practical_marks),
            "max_total": float(exam_subject.max_theory_marks + exam_subject.max_practical_marks),
            "theory_obtained": float(e.theory_marks_obtained) if e.theory_marks_obtained is not None else None,
            "practical_obtained": float(e.practical_marks_obtained) if e.practical_marks_obtained is not None else None,
            "total_obtained": float(e.total_obtained) if e.total_obtained is not None else None,
            "is_absent": e.is_absent,
            "is_exempt": e.is_exempt,
            "status": e.status,
            "teacher_remarks": e.teacher_remarks
        })
    return results