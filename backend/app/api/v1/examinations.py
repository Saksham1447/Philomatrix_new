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
    exam_ids = ids(exams)
    pubs_by_exam = group_by(db.find("result_publications", {"examination_id": {"$in": exam_ids}}), "examination_id") if exams else {}
    exam_subjects_by_exam = group_by(db.find("exam_subjects", {"examination_id": {"$in": exam_ids}}), "examination_id") if exams else {}
    all_exam_subjects = [es for group in exam_subjects_by_exam.values() for es in group]
    subjects_by_id = db.get_many("subjects", ids(all_exam_subjects, "subject_id"))
    first_class_name_by_institution = {}

    def first_class_name(institution_id):
        # Mirrors the former `subject.institution.classes[0]` lookup (unordered first class).
        if institution_id not in first_class_name_by_institution:
            first_class = db.find_one("classes", {"institution_id": institution_id})
            first_class_name_by_institution[institution_id] = first_class.name if first_class else "Class 11"
        return first_class_name_by_institution[institution_id]

    results = []
    for ex in exams:
        is_published = len(pubs_by_exam.get(ex.id, [])) > 0
        subjects_out = []
        for es in exam_subjects_by_exam.get(ex.id, []):
            subject = subjects_by_id[es.subject_id]
            subjects_out.append(
                ExamSubjectResponse(
                    id=es.id,
                    subject_id=es.subject_id,
                    subject_name=subject.name,
                    subject_code=subject.code,
                    class_id=es.class_id,
                    class_name=first_class_name(subject.institution_id),
                    max_theory_marks=es.max_theory_marks,
                    max_practical_marks=es.max_practical_marks,
                    min_passing_marks=es.min_passing_marks,
                    exam_date=es.exam_date
                )
            )
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
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db)
):
    """[PRINCIPAL] Schedule a new examination with subjects, max marks, and dates."""
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
    for s in request.subjects:
        es = db.insert("exam_subjects", {
            "examination_id": exam.id,
            "subject_id": s.subject_id,
            "class_id": s.class_id,
            "max_theory_marks": s.max_theory_marks,
            "max_practical_marks": s.max_practical_marks,
            "min_passing_marks": s.min_passing_marks,
            "exam_date": s.exam_date,
        })
        subj = db.get("subjects", s.subject_id)
        cls = db.get("classes", s.class_id)
        subjects_out.append(
            ExamSubjectResponse(
                id=es.id,
                subject_id=es.subject_id,
                subject_name=subj.name if subj else "Subject",
                subject_code=subj.code if subj else "",
                class_id=es.class_id,
                class_name=cls.name if cls else "",
                max_theory_marks=es.max_theory_marks,
                max_practical_marks=es.max_practical_marks,
                min_passing_marks=es.min_passing_marks,
                exam_date=es.exam_date
            )
        )

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

    division_enrollments = db.find("enrollments", {"division_id": division_id})
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

    existing_by_student = index_by(
        db.find("marks_entries", {
            "exam_subject_id": request.exam_subject_id,
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
            # Cannot modify if already published
            if existing.status == "APPROVED" and not request.submit_for_approval:
                pass  # Skip overwrite of approved marks unless correction workflow
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