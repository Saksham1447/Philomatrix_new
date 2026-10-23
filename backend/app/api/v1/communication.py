from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, Role, UserRoleAssignment
from app.models.communication import (
    Assignment,
    AssignmentSubmission,
    Notice,
    FeedbackForm,
    FeedbackQuestion,
    FeedbackResponse,
    Notification,
    AuditLog,
)
from app.models.student import Enrollment
from app.schemas.communication import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentSubmissionRequest,
    NoticeCreate,
    NoticeResponse,
    FeedbackFormCreate,
    FeedbackFormResponse,
    FeedbackQuestionResponse,
    FeedbackSubmitRequest,
    NotificationResponse,
    AuditLogResponse,
)

router = APIRouter(tags=["Communication, Assignments & Feedback"])


# ASSIGNMENTS
@router.get("/assignments", response_model=List[AssignmentResponse])
def list_assignments(
    division_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List assignments scoped to user division or faculty."""
    query = (
        db.query(Assignment)
        .filter(Assignment.institution_id == current_user.institution_id)
    )

    if current_user.student_profile:
        enr = db.query(Enrollment).filter(Enrollment.student_id == current_user.student_profile.id).first()
        if enr:
            query = query.filter(Assignment.division_id == enr.division_id)
        else:
            return []
    elif division_id:
        query = query.filter(Assignment.division_id == division_id)
    elif current_user.faculty_profile:
        query = query.filter(Assignment.faculty_id == current_user.faculty_profile.id)

    assignments = query.order_by(Assignment.due_date.desc()).all()
    results = []
    for a in assignments:
        is_sub = False
        sub_status = None
        if current_user.student_profile:
            sub = (
                db.query(AssignmentSubmission)
                .filter(AssignmentSubmission.assignment_id == a.id, AssignmentSubmission.student_id == current_user.student_profile.id)
                .first()
            )
            if sub:
                is_sub = True
                sub_status = sub.status

        results.append(
            AssignmentResponse(
                id=a.id,
                division_id=a.division_id,
                division_name=a.division.name,
                class_name=a.division.class_model.name,
                subject_id=a.subject_id,
                subject_name=a.subject.name,
                faculty_name=a.faculty.user.full_name,
                title=a.title,
                description=a.description,
                due_date=a.due_date,
                attachment_url=a.attachment_url,
                created_at=a.created_at,
                is_submitted_by_student=is_sub,
                submission_status=sub_status
            )
        )
    return results


@router.post("/assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    request: AssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """[FACULTY] Create an academic assignment for an assigned division."""
    if not current_user.faculty_profile:
        raise HTTPException(status_code=403, detail="Only faculty can publish assignments")

    assignment = Assignment(
        institution_id=current_user.institution_id,
        division_id=request.division_id,
        subject_id=request.subject_id,
        faculty_id=current_user.faculty_profile.id,
        title=request.title,
        description=request.description,
        due_date=request.due_date,
        attachment_url=request.attachment_url
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return AssignmentResponse(
        id=assignment.id,
        division_id=assignment.division_id,
        division_name=assignment.division.name,
        class_name=assignment.division.class_model.name,
        subject_id=assignment.subject_id,
        subject_name=assignment.subject.name,
        faculty_name=current_user.full_name,
        title=assignment.title,
        description=assignment.description,
        due_date=assignment.due_date,
        attachment_url=assignment.attachment_url,
        created_at=assignment.created_at,
        is_submitted_by_student=False,
        submission_status=None
    )


@router.post("/assignments/{id}/submit")
def submit_assignment(
    id: str,
    request: AssignmentSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """[STUDENT] Submit homework or assignment."""
    if not current_user.student_profile:
        raise HTTPException(status_code=403, detail="Only students can submit assignments")

    assignment = db.query(Assignment).filter(Assignment.id == id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    student_id = current_user.student_profile.id
    now = datetime.now(timezone.utc)
    is_late = now > assignment.due_date

    existing = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.assignment_id == id, AssignmentSubmission.student_id == student_id)
        .first()
    )
    if existing:
        existing.submission_text = request.submission_text
        existing.attachment_url = request.attachment_url
        existing.submitted_at = now
        existing.is_late = is_late
        existing.status = "SUBMITTED"
    else:
        sub = AssignmentSubmission(
            assignment_id=id,
            student_id=student_id,
            submission_text=request.submission_text,
            attachment_url=request.attachment_url,
            submitted_at=now,
            is_late=is_late,
            status="SUBMITTED"
        )
        db.add(sub)

    db.commit()
    return {"message": "Assignment submitted successfully", "is_late": is_late}


# NOTICES
@router.get("/notices", response_model=List[NoticeResponse])
def list_notices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch notices targeted to the caller's role and institution."""
    user_roles = (
        db.query(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .filter(UserRoleAssignment.user_id == current_user.id)
        .all()
    )
    role_names = [r[0] for r in user_roles]

    query = (
        db.query(Notice)
        .filter(Notice.institution_id == current_user.institution_id, Notice.is_published == True)
    )

    # Scoping: if not Principal/SuperAdmin, filter by audience
    if "PRINCIPAL" not in role_names and "SUPER_ADMIN" not in role_names:
        allowed_audiences = ["ALL"]
        if "FACULTY" in role_names:
            allowed_audiences.append("FACULTY")
        if "STUDENT" in role_names:
            allowed_audiences.append("STUDENT")
        if "PARENT" in role_names:
            allowed_audiences.append("PARENT")
        query = query.filter(Notice.audience_role.in_(allowed_audiences))

    notices = query.order_by(Notice.created_at.desc()).all()
    results = []
    for n in notices:
        results.append(
            NoticeResponse(
                id=n.id,
                title=n.title,
                content=n.content,
                audience_role=n.audience_role,
                target_class_id=n.target_class_id,
                target_division_id=n.target_division_id,
                priority=n.priority,
                published_by_name=n.publisher.full_name if n.publisher else "Administration",
                created_at=n.created_at,
                expires_at=n.expires_at
            )
        )
    return results


@router.post("/notices", response_model=NoticeResponse, status_code=status.HTTP_201_CREATED)
def create_notice(
    request: NoticeCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY")),
    db: Session = Depends(get_db)
):
    """Publish a new academic or institutional notice."""
    notice = Notice(
        institution_id=current_user.institution_id,
        title=request.title,
        content=request.content,
        audience_role=request.audience_role,
        target_class_id=request.target_class_id,
        target_division_id=request.target_division_id,
        priority=request.priority,
        published_by=current_user.id,
        is_published=True,
        expires_at=request.expires_at
    )
    db.add(notice)
    db.commit()
    db.refresh(notice)

    return NoticeResponse(
        id=notice.id,
        title=notice.title,
        content=notice.content,
        audience_role=notice.audience_role,
        target_class_id=notice.target_class_id,
        target_division_id=notice.target_division_id,
        priority=notice.priority,
        published_by_name=current_user.full_name,
        created_at=notice.created_at,
        expires_at=notice.expires_at
    )


# FEEDBACK
@router.get("/feedback/forms", response_model=List[FeedbackFormResponse])
def list_feedback_forms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List open feedback forms available for the caller."""
    user_roles = (
        db.query(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .filter(UserRoleAssignment.user_id == current_user.id)
        .all()
    )
    role_names = [r[0] for r in user_roles]

    query = db.query(FeedbackForm).filter(FeedbackForm.institution_id == current_user.institution_id)

    # Scoping by role:
    if "PRINCIPAL" not in role_names and "SUPER_ADMIN" not in role_names:
        query = query.filter(FeedbackForm.is_open == True)
        if "STUDENT" in role_names:
            query = query.filter(FeedbackForm.target_role.in_(["STUDENT", "ALL"]))
        elif "FACULTY" in role_names:
            query = query.filter(FeedbackForm.target_role.in_(["FACULTY", "ALL"]))
        elif "PARENT" in role_names:
            query = query.filter(FeedbackForm.target_role.in_(["PARENT", "ALL"]))
        else:
            return []

    forms = query.order_by(FeedbackForm.created_at.desc()).all()
    results = []
    for f in forms:
        q_out = [
            FeedbackQuestionResponse(
                id=q.id,
                question_text=q.question_text,
                question_type=q.question_type,
                display_order=q.display_order
            )
            for q in f.questions
        ]
        results.append(
            FeedbackFormResponse(
                id=f.id,
                title=f.title,
                target_role=f.target_role,
                is_anonymous=f.is_anonymous,
                is_open=f.is_open,
                start_date=f.start_date,
                end_date=f.end_date,
                questions=q_out
            )
        )
    return results


@router.post("/feedback/forms", response_model=FeedbackFormResponse, status_code=status.HTTP_201_CREATED)
def create_feedback_form(
    request: FeedbackFormCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL] Create an academic feedback form with rating questions."""
    form = FeedbackForm(
        institution_id=current_user.institution_id,
        title=request.title,
        target_role=request.target_role,
        is_anonymous=request.is_anonymous,
        is_open=True,
        start_date=request.start_date,
        end_date=request.end_date
    )
    db.add(form)
    db.flush()

    q_out = []
    for q in request.questions:
        fq = FeedbackQuestion(
            feedback_form_id=form.id,
            question_text=q.question_text,
            question_type=q.question_type,
            display_order=q.display_order
        )
        db.add(fq)
        db.flush()
        q_out.append(
            FeedbackQuestionResponse(
                id=fq.id,
                question_text=fq.question_text,
                question_type=fq.question_type,
                display_order=fq.display_order
            )
        )

    db.commit()
    db.refresh(form)

    return FeedbackFormResponse(
        id=form.id,
        title=form.title,
        target_role=form.target_role,
        is_anonymous=form.is_anonymous,
        is_open=form.is_open,
        start_date=form.start_date,
        end_date=form.end_date,
        questions=q_out
    )


@router.post("/feedback/forms/{id}/respond")
def submit_feedback_response(
    id: str,
    request: FeedbackSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit responses to a feedback form (anonymized where configured with duplicate protection)."""
    form = db.query(FeedbackForm).filter(FeedbackForm.id == id).first()
    if not form or not form.is_open:
        raise HTTPException(status_code=400, detail="Feedback form is not accepting responses")

    # Cross-tenant check
    if current_user.institution_id != form.institution_id:
        raise HTTPException(status_code=403, detail="Cross-institution feedback submission denied")

    # Deadline check
    now = datetime.now(timezone.utc)
    if form.end_date and now.date() > form.end_date:
        raise HTTPException(status_code=400, detail="Feedback submission window has expired for this form")

    # Role eligibility check (Section 13.3 & 13.4: Parent cannot submit feedback on student's behalf by default)
    user_roles = (
        db.query(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .filter(UserRoleAssignment.user_id == current_user.id)
        .all()
    )
    role_names = [r[0] for r in user_roles]

    if form.target_role == "STUDENT" and not current_user.student_profile:
        raise HTTPException(status_code=403, detail="Only enrolled students may submit responses to this form")
    elif form.target_role == "FACULTY" and not current_user.faculty_profile:
        raise HTTPException(status_code=403, detail="Only faculty members may submit responses to this form")
    elif "PARENT" in role_names and form.target_role != "PARENT":
        raise HTTPException(status_code=403, detail="Parents are not authorized to submit academic feedback for this form")

    # Duplicate submission prevention
    existing_submission = (
        db.query(AuditLog)
        .filter(
            AuditLog.institution_id == form.institution_id,
            AuditLog.user_id == current_user.id,
            AuditLog.entity_id == form.id,
            AuditLog.action == "FEEDBACK_SUBMITTED"
        )
        .first()
    )
    if existing_submission:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a response for this feedback form"
        )

    respondent_id = None if form.is_anonymous else current_user.id

    for a in request.answers:
        resp = FeedbackResponse(
            feedback_form_id=form.id,
            question_id=a.question_id,
            respondent_user_id=respondent_id,
            rating_value=a.rating_value,
            text_response=a.text_response
        )
        db.add(resp)

    # Record submission token in audit log without response mapping to guarantee privacy
    sub_audit = AuditLog(
        institution_id=form.institution_id,
        user_id=current_user.id,
        action="FEEDBACK_SUBMITTED",
        entity_type="feedback_forms",
        entity_id=form.id,
        new_state={"is_anonymous": form.is_anonymous},
        reason="Feedback response submitted"
    )
    db.add(sub_audit)
    db.commit()
    return {"message": "Feedback submitted successfully. Thank you for helping improve academic standards!"}


@router.get("/feedback/forms/{id}/analytics")
def get_feedback_analytics(
    id: str,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL] Get aggregated analytics and ratings for a feedback form."""
    form = db.query(FeedbackForm).filter(FeedbackForm.id == id, FeedbackForm.institution_id == current_user.institution_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Feedback form not found")

    total_submissions = (
        db.query(AuditLog)
        .filter(AuditLog.entity_id == form.id, AuditLog.action == "FEEDBACK_SUBMITTED")
        .count()
    )

    question_stats = []
    for q in form.questions:
        responses = db.query(FeedbackResponse).filter(FeedbackResponse.question_id == q.id).all()
        ratings = [r.rating_value for r in responses if r.rating_value is not None]
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

        dist = {str(i): ratings.count(i) for i in range(1, 6)}
        comments = [r.text_response for r in responses if r.text_response]

        question_stats.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "total_responses": len(responses),
            "average_rating": avg_rating,
            "rating_distribution": dist,
            "comments": comments
        })

    return {
        "form_id": form.id,
        "title": form.title,
        "target_role": form.target_role,
        "is_anonymous": form.is_anonymous,
        "is_open": form.is_open,
        "total_submissions": total_submissions,
        "questions": question_stats
    }



# NOTIFICATIONS
@router.get("/notifications", response_model=List[NotificationResponse])
def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch notifications for current user."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )


@router.put("/notifications/{id}/read")
def mark_notification_read(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read."""
    notif = db.query(Notification).filter(Notification.id == id, Notification.user_id == current_user.id).first()
    if notif:
        notif.is_read = True
        db.commit()
    return {"message": "Notification marked as read"}


# AUDIT LOGS
@router.get("/audit/logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: Session = Depends(get_db)
):
    """[PRINCIPAL | SUPER_ADMIN] Inspect audit trail for the institution."""
    query = (
        db.query(AuditLog)
        .filter(AuditLog.institution_id == current_user.institution_id)
        .order_by(AuditLog.created_at.desc())
        .limit(50)
    )
    logs = query.all()
    results = []
    for l in logs:
        results.append(
            AuditLogResponse(
                id=l.id,
                action=l.action,
                entity_type=l.entity_type,
                entity_id=l.entity_id,
                user_name=l.user.full_name if l.user else "System",
                previous_state=l.previous_state,
                new_state=l.new_state,
                reason=l.reason,
                ip_address=l.ip_address,
                created_at=l.created_at
            )
        )
    return results
