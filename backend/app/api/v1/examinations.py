from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles, verify_student_access
from app.models.user import User, Role, UserRoleAssignment
from app.models.academic import Subject, Division, ClassModel, AcademicYear
from app.models.student import Student, Enrollment
from app.models.examination import (
    Examination,
    ExamSubject,
    MarksEntry,
    MarksApproval,
    ResultPublication,
)
from app.models.communication import AuditLog
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List examinations for the active academic year."""
    query = (
        db.query(Examination)
        .filter(Examination.institution_id == current_user.institution_id)
    )
    if academic_year_id:
        query = query.filter(Examination.academic_year_id == academic_year_id)

    exams = query.order_by(Examination.start_date.desc()).all()
    results = []
    for ex in exams:
        is_published = len(ex.result_publications) > 0
        subjects_out = []
        for es in ex.exam_subjects:
            subjects_out.append(
                ExamSubjectResponse(
                    id=es.id,
                    subject_id=es.subject_id,
                    subject_name=es.subject.name,
                    subject_code=es.subject.code,
                    class_id=es.class_id,
                    class_name=es.subject.institution.classes[0].name if es.subject.institution.classes else "Class 11",
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
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL] Schedule a new examination with subjects, max marks, and dates."""
    exam = Examination(
        institution_id=current_user.institution_id,
        academic_year_id=request.academic_year_id,
        name=request.name,
        exam_type=request.exam_type,
        start_date=request.start_date,
        end_date=request.end_date,
        status="SCHEDULED"
    )
    db.add(exam)
    db.flush()

    subjects_out = []
    for s in request.subjects:
        es = ExamSubject(
            examination_id=exam.id,
            subject_id=s.subject_id,
            class_id=s.class_id,
            max_theory_marks=s.max_theory_marks,
            max_practical_marks=s.max_practical_marks,
            min_passing_marks=s.min_passing_marks,
            exam_date=s.exam_date
        )
        db.add(es)
        db.flush()
        subj = db.query(Subject).filter(Subject.id == s.subject_id).first()
        cls = db.query(ClassModel).filter(ClassModel.id == s.class_id).first()
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

    db.commit()
    db.refresh(exam)

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """[FACULTY] Get student roster with current marks/drafts for an exam subject & division."""
    es = db.query(ExamSubject).filter(ExamSubject.id == exam_subject_id).first()
    if not es:
        raise HTTPException(status_code=404, detail="Exam subject not found")

    enrollments = (
        db.query(Enrollment)
        .join(Student, Student.id == Enrollment.student_id)
        .filter(Enrollment.division_id == division_id, Student.status == "ACTIVE")
        .order_by(Student.roll_number.asc(), Student.admission_number.asc())
        .all()
    )

    existing_entries_map = {}
    entries = (
        db.query(MarksEntry)
        .filter(MarksEntry.exam_subject_id == exam_subject_id, MarksEntry.division_id == division_id)
        .all()
    )
    for entry in entries:
        existing_entries_map[entry.student_id] = entry

    roster = []
    for enr in enrollments:
        s = enr.student
        e = existing_entries_map.get(s.id)
        if e:
            roster.append(
                MarksEntryResponse(
                    id=e.id,
                    student_id=s.id,
                    student_name=s.user.full_name,
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
                    student_name=s.user.full_name,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """[FACULTY] Save marks in DRAFT mode or SUBMIT for Principal moderation."""
    es = db.query(ExamSubject).filter(ExamSubject.id == request.exam_subject_id).first()
    if not es:
        raise HTTPException(status_code=404, detail="Exam subject not found")

    target_status = "SUBMITTED" if request.submit_for_approval else "DRAFT"

    for entry_in in request.entries:
        # Validate bounds
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

        total = None
        if not entry_in.is_absent and not entry_in.is_exempt:
            th = entry_in.theory_marks_obtained or Decimal("0.00")
            pr = entry_in.practical_marks_obtained or Decimal("0.00")
            total = th + pr

        existing = (
            db.query(MarksEntry)
            .filter(MarksEntry.exam_subject_id == request.exam_subject_id, MarksEntry.student_id == entry_in.student_id)
            .first()
        )
        if existing:
            # Cannot modify if already published
            if existing.status == "APPROVED" and not request.submit_for_approval:
                pass  # Skip overwrite of approved marks unless correction workflow
            existing.theory_marks_obtained = entry_in.theory_marks_obtained
            existing.practical_marks_obtained = entry_in.practical_marks_obtained
            existing.total_obtained = total
            existing.is_absent = entry_in.is_absent
            existing.is_exempt = entry_in.is_exempt
            existing.status = target_status
            existing.teacher_remarks = entry_in.teacher_remarks
            existing.entered_by = current_user.id
        else:
            new_entry = MarksEntry(
                exam_subject_id=request.exam_subject_id,
                student_id=entry_in.student_id,
                division_id=request.division_id,
                theory_marks_obtained=entry_in.theory_marks_obtained,
                practical_marks_obtained=entry_in.practical_marks_obtained,
                total_obtained=total,
                is_absent=entry_in.is_absent,
                is_exempt=entry_in.is_exempt,
                entered_by=current_user.id,
                status=target_status,
                teacher_remarks=entry_in.teacher_remarks
            )
            db.add(new_entry)

    # If submitted for approval, create/update MarksApproval record
    if request.submit_for_approval:
        now = datetime.now(timezone.utc)
        approval = (
            db.query(MarksApproval)
            .filter(MarksApproval.exam_subject_id == request.exam_subject_id, MarksApproval.division_id == request.division_id)
            .first()
        )
        if not approval:
            approval = MarksApproval(
                exam_subject_id=request.exam_subject_id,
                division_id=request.division_id,
                submitted_by=current_user.id,
                submitted_at=now,
                status="PENDING"
            )
            db.add(approval)
        else:
            approval.status = "PENDING"
            approval.submitted_at = now
            approval.submitted_by = current_user.id

    db.commit()
    msg = "Marks submitted for Principal review" if request.submit_for_approval else "Marks saved as draft"
    return {"message": msg, "status": target_status}


@router.get("/marks/approvals/pending", response_model=List[MarksApprovalResponse])
def list_pending_approvals(
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL] List marks submissions pending review."""
    approvals = (
        db.query(MarksApproval)
        .join(ExamSubject, ExamSubject.id == MarksApproval.exam_subject_id)
        .join(Examination, Examination.id == ExamSubject.examination_id)
        .filter(Examination.institution_id == current_user.institution_id, MarksApproval.status == "PENDING")
        .order_by(MarksApproval.submitted_at.desc())
        .all()
    )

    results = []
    for a in approvals:
        results.append(
            MarksApprovalResponse(
                id=a.id,
                exam_subject_id=a.exam_subject_id,
                examination_name=a.exam_subject.examination.name,
                subject_name=a.exam_subject.subject.name,
                subject_code=a.exam_subject.subject.code,
                division_id=a.division_id,
                division_name=a.division.name,
                class_name=a.division.class_model.name,
                submitted_by_name=a.submitter.full_name,
                submitted_at=a.submitted_at,
                status=a.status,
                reviewed_by_name=a.reviewer.full_name if a.reviewer else None,
                reviewed_at=a.reviewed_at,
                review_comments=a.review_comments
            )
        )
    return results


@router.put("/marks/approvals/{id}/review")
def review_marks_batch(
    id: str,
    review: MarksApprovalReviewRequest,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL] Review, approve, or reject a submitted marks batch."""
    approval = db.query(MarksApproval).filter(MarksApproval.id == id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Marks approval request not found")

    # Prevent unauthorized self-approval
    user_roles = (
        db.query(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .filter(UserRoleAssignment.user_id == current_user.id)
        .all()
    )
    role_names = [r[0] for r in user_roles]
    if approval.submitted_by == current_user.id and "SUPER_ADMIN" not in role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-Approval Violation: You cannot approve a marks submission that you entered"
        )

    now = datetime.now(timezone.utc)
    approval.reviewed_by = current_user.id
    approval.reviewed_at = now
    approval.review_comments = review.review_comments

    new_marks_status = "APPROVED" if review.approved else "REJECTED"
    approval.status = new_marks_status

    # Update all marks entries in this batch
    db.query(MarksEntry).filter(
        MarksEntry.exam_subject_id == approval.exam_subject_id,
        MarksEntry.division_id == approval.division_id
    ).update({"status": new_marks_status})

    # Log action in audit logs
    audit = AuditLog(
        institution_id=current_user.institution_id,
        user_id=current_user.id,
        action=f"MARKS_BATCH_{new_marks_status}",
        entity_type="marks_approvals",
        entity_id=approval.id,
        previous_state={"status": "PENDING"},
        new_state={"status": new_marks_status},
        reason=review.review_comments
    )
    db.add(audit)
    db.commit()

    return {"message": f"Marks batch {new_marks_status.lower()} successfully"}


@router.post("/{id}/publish")
def publish_examination_results(
    id: str,
    class_id: Optional[str] = None,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL] Formally publish exam results to students and parents."""
    exam = db.query(Examination).filter(Examination.id == id, Examination.institution_id == current_user.institution_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")

    # If class_id not specified, publish for all classes in this institution
    if class_id:
        target_classes = [class_id]
    else:
        inst_classes = db.query(ClassModel).filter(ClassModel.institution_id == exam.institution_id).all()
        target_classes = [c.id for c in inst_classes]

    now = datetime.now(timezone.utc)
    for cid in target_classes:
        existing = db.query(ResultPublication).filter(ResultPublication.examination_id == exam.id, ResultPublication.class_id == cid).first()
        if not existing:
            pub = ResultPublication(
                examination_id=exam.id,
                class_id=cid,
                published_by=current_user.id,
                published_at=now,
                is_active=True
            )
            db.add(pub)

    exam.status = "PUBLISHED"
    # Log in audit
    audit = AuditLog(
        institution_id=current_user.institution_id,
        user_id=current_user.id,
        action="EXAMINATION_RESULTS_PUBLISHED",
        entity_type="examinations",
        entity_id=exam.id,
        new_state={"status": "PUBLISHED", "published_classes": target_classes}
    )
    db.add(audit)
    db.commit()

    return {"message": f"Examination '{exam.name}' results published successfully"}


@router.get("/marks/student/{student_id}", response_model=List[dict])
def get_student_marks(
    student_id: str,
    examination_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch student marks (only published examinations are visible to students and parents)."""
    # Re-validate student access, tenant isolation, and guardian-child relationship server-side
    student = verify_student_access(student_id, current_user, db)

    query = (
        db.query(MarksEntry)
        .join(ExamSubject, ExamSubject.id == MarksEntry.exam_subject_id)
        .join(Examination, Examination.id == ExamSubject.examination_id)
        .filter(MarksEntry.student_id == student_id)
    )

    # If student or parent, restrict to published examinations
    if current_user.student_profile or current_user.guardian_profile:
        query = query.join(ResultPublication, ResultPublication.examination_id == Examination.id).filter(ResultPublication.is_active == True)

    if examination_id:
        query = query.filter(Examination.id == examination_id)

    entries = query.all()
    results = []
    for e in entries:
        results.append({
            "examination_id": e.exam_subject.examination.id,
            "examination_name": e.exam_subject.examination.name,
            "subject_id": e.exam_subject.subject.id,
            "subject_code": e.exam_subject.subject.code,
            "subject_name": e.exam_subject.subject.name,
            "max_theory": float(e.exam_subject.max_theory_marks),
            "max_practical": float(e.exam_subject.max_practical_marks),
            "max_total": float(e.exam_subject.max_theory_marks + e.exam_subject.max_practical_marks),
            "theory_obtained": float(e.theory_marks_obtained) if e.theory_marks_obtained is not None else None,
            "practical_obtained": float(e.practical_marks_obtained) if e.practical_marks_obtained is not None else None,
            "total_obtained": float(e.total_obtained) if e.total_obtained is not None else None,
            "is_absent": e.is_absent,
            "is_exempt": e.is_exempt,
            "status": e.status,
            "teacher_remarks": e.teacher_remarks
        })
    return results
