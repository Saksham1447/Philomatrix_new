from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_db
from app.core.deps import get_current_user, require_roles
from app.core.docstore import Doc, DocStore
from app.core.q import group_by, ids, index_by, in_
from app.schemas.communication import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentSubmissionRequest,
    AuditLogResponse,
    FeedbackFormCreate,
    FeedbackFormResponse,
    FeedbackQuestionResponse,
    FeedbackSubmitRequest,
    NoticeCreate,
    NoticeResponse,
    NotificationResponse,
)

router = APIRouter(tags=["Communication, Assignments & Feedback"])


def _assignment_response(
    db: DocStore,
    assignment: Doc,
    submission: Doc | None = None,
    *,
    divisions: dict | None = None,
    classes: dict | None = None,
    subjects: dict | None = None,
    faculties: dict | None = None,
    users: dict | None = None,
) -> AssignmentResponse:
    division = divisions.get(assignment.division_id) if divisions is not None else db.get("divisions", assignment.division_id)
    cls = classes.get(division.class_id) if classes is not None and division else (
        db.get("classes", division.class_id) if division else None
    )
    subject = subjects.get(assignment.subject_id) if subjects is not None else db.get("subjects", assignment.subject_id)
    faculty = faculties.get(assignment.faculty_id) if faculties is not None else db.get("faculty_profiles", assignment.faculty_id)
    faculty_user = users.get(faculty.user_id) if users is not None and faculty else (
        db.get("users", faculty.user_id) if faculty else None
    )
    return AssignmentResponse(
        id=assignment.id,
        division_id=assignment.division_id,
        division_name=division.name if division else "",
        class_name=cls.name if cls else "",
        subject_id=assignment.subject_id,
        subject_name=subject.name if subject else "",
        faculty_name=faculty_user.full_name if faculty_user else "",
        title=assignment.title,
        description=assignment.description,
        due_date=assignment.due_date,
        attachment_url=assignment.attachment_url,
        created_at=assignment.created_at,
        is_submitted_by_student=submission is not None,
        submission_status=submission.status if submission else None,
    )


def _notice_response(
    db: DocStore,
    notice: Doc,
    publisher_name: str | None = None,
    publisher: Doc | None = None,
) -> NoticeResponse:
    if publisher is None and notice.published_by:
        publisher = db.get("users", notice.published_by)
    return NoticeResponse(
        id=notice.id,
        title=notice.title,
        content=notice.content,
        audience_role=notice.audience_role,
        target_class_id=notice.target_class_id,
        target_division_id=notice.target_division_id,
        priority=notice.priority,
        published_by_name=publisher_name if publisher_name is not None else (publisher.full_name if publisher else "Administration"),
        created_at=notice.created_at,
        expires_at=notice.expires_at,
    )


def _feedback_question_response(question: Doc) -> FeedbackQuestionResponse:
    return FeedbackQuestionResponse(
        id=question.id,
        question_text=question.question_text,
        question_type=question.question_type,
        display_order=question.display_order,
    )


def _feedback_form_response(form: Doc, questions: list[Doc]) -> FeedbackFormResponse:
    return FeedbackFormResponse(
        id=form.id,
        title=form.title,
        target_role=form.target_role,
        is_anonymous=form.is_anonymous,
        is_open=form.is_open,
        start_date=form.start_date,
        end_date=form.end_date,
        questions=[_feedback_question_response(question) for question in questions],
    )


# ASSIGNMENTS
@router.get("/assignments", response_model=List[AssignmentResponse])
def list_assignments(
    division_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """List assignments scoped to user division or faculty."""
    query = {"institution_id": current_user.institution_id}
    if current_user.student_profile:
        enrollment = db.find_one("enrollments", {"student_id": current_user.student_profile.id})
        if not enrollment:
            return []
        query["division_id"] = enrollment.division_id
    elif division_id:
        query["division_id"] = division_id
    elif current_user.faculty_profile:
        query["faculty_id"] = current_user.faculty_profile.id

    assignments = db.find("assignments", query, sort=[("due_date", -1)])
    divisions = index_by(db.get_many("divisions", ids(assignments, "division_id")).values())
    classes = index_by(db.get_many("classes", ids(divisions.values(), "class_id")).values())
    subjects = index_by(db.get_many("subjects", ids(assignments, "subject_id")).values())
    faculties = index_by(db.get_many("faculty_profiles", ids(assignments, "faculty_id")).values())
    users = index_by(db.get_many("users", ids(faculties.values(), "user_id")).values())
    results = []
    submissions_by_assignment = {}
    if current_user.student_profile and assignments:
        submissions = db.find(
            "assignment_submissions",
            {
                "assignment_id": in_(ids(assignments)),
                "student_id": current_user.student_profile.id,
            },
        )
        submissions_by_assignment = {
            assignment_id: items[0]
            for assignment_id, items in group_by(submissions, "assignment_id").items()
            if items
        }
    for assignment in assignments:
        submission = submissions_by_assignment.get(assignment.id)
        results.append(
            _assignment_response(
                db,
                assignment,
                submission,
                divisions=divisions,
                classes=classes,
                subjects=subjects,
                faculties=faculties,
                users=users,
            )
        )
    return results


@router.post("/assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    request: AssignmentCreate,
    current_user=Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """[FACULTY] Create an academic assignment for an assigned division."""
    if not current_user.faculty_profile:
        raise HTTPException(status_code=403, detail="Only faculty can publish assignments")

    assignment = db.insert(
        "assignments",
        {
            "institution_id": current_user.institution_id,
            "division_id": request.division_id,
            "subject_id": request.subject_id,
            "faculty_id": current_user.faculty_profile.id,
            "title": request.title,
            "description": request.description,
            "due_date": request.due_date,
            "attachment_url": request.attachment_url,
        },
    )
    return _assignment_response(db, assignment)


@router.post("/assignments/{id}/submit")
def submit_assignment(
    id: str,
    request: AssignmentSubmissionRequest,
    current_user=Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """[STUDENT] Submit homework or assignment."""
    if not current_user.student_profile:
        raise HTTPException(status_code=403, detail="Only students can submit assignments")

    assignment = db.get("assignments", id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    student_id = current_user.student_profile.id
    now = datetime.now(timezone.utc)
    is_late = now > assignment.due_date
    existing = db.find_one(
        "assignment_submissions",
        {"assignment_id": id, "student_id": student_id},
    )
    changes = {
        "submission_text": request.submission_text,
        "attachment_url": request.attachment_url,
        "submitted_at": now,
        "is_late": is_late,
        "status": "SUBMITTED",
    }
    if existing:
        db.update(existing, changes)
    else:
        db.insert("assignment_submissions", {"assignment_id": id, "student_id": student_id, **changes})
    return {"message": "Assignment submitted successfully", "is_late": is_late}


# NOTICES
@router.get("/notices", response_model=List[NoticeResponse])
def list_notices(
    current_user=Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """Fetch notices targeted to the caller's role and institution."""
    role_names = current_user.role_names
    query = {"institution_id": current_user.institution_id, "is_published": True}
    if "PRINCIPAL" not in role_names and "SUPER_ADMIN" not in role_names:
        allowed_audiences = ["ALL"]
        for role in ("FACULTY", "STUDENT", "PARENT"):
            if role in role_names:
                allowed_audiences.append(role)
        query["audience_role"] = in_(allowed_audiences)

    notices = db.find("notices", query, sort=[("created_at", -1)])
    publishers = index_by(
        db.get_many("users", ids(notices, "published_by")).values()
    )
    return [
        _notice_response(db, notice, publisher=publishers.get(notice.published_by))
        for notice in notices
    ]


@router.post("/notices", response_model=NoticeResponse, status_code=status.HTTP_201_CREATED)
def create_notice(
    request: NoticeCreate,
    current_user=Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY")),
    db: DocStore = Depends(get_db),
):
    """Publish a new academic or institutional notice."""
    notice = db.insert(
        "notices",
        {
            "institution_id": current_user.institution_id,
            "title": request.title,
            "content": request.content,
            "audience_role": request.audience_role,
            "target_class_id": request.target_class_id,
            "target_division_id": request.target_division_id,
            "priority": request.priority,
            "published_by": current_user.id,
            "is_published": True,
            "expires_at": request.expires_at,
        },
    )
    return _notice_response(db, notice, current_user.full_name)


# FEEDBACK
@router.get("/feedback/forms", response_model=List[FeedbackFormResponse])
def list_feedback_forms(
    current_user=Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """List open feedback forms available for the caller."""
    role_names = current_user.role_names
    query = {"institution_id": current_user.institution_id}
    if "PRINCIPAL" not in role_names and "SUPER_ADMIN" not in role_names:
        query["is_open"] = True
        if "STUDENT" in role_names:
            query["target_role"] = in_(["STUDENT", "ALL"])
        elif "FACULTY" in role_names:
            query["target_role"] = in_(["FACULTY", "ALL"])
        elif "PARENT" in role_names:
            query["target_role"] = in_(["PARENT", "ALL"])
        else:
            return []

    forms = db.find("feedback_forms", query, sort=[("created_at", -1)])
    questions = db.find(
        "feedback_questions",
        {"feedback_form_id": in_(ids(forms))},
        sort=[("display_order", 1)],
    ) if forms else []
    questions_by_form = group_by(questions, "feedback_form_id")
    return [_feedback_form_response(form, questions_by_form.get(form.id, [])) for form in forms]


@router.post("/feedback/forms", response_model=FeedbackFormResponse, status_code=status.HTTP_201_CREATED)
def create_feedback_form(
    request: FeedbackFormCreate,
    current_user=Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db),
):
    """[PRINCIPAL] Create an academic feedback form with rating questions."""
    form = db.insert(
        "feedback_forms",
        {
            "institution_id": current_user.institution_id,
            "title": request.title,
            "target_role": request.target_role,
            "is_anonymous": request.is_anonymous,
            "is_open": True,
            "start_date": request.start_date,
            "end_date": request.end_date,
        },
    )
    questions = db.insert_many(
        "feedback_questions",
        [
            {
                "feedback_form_id": form.id,
                "question_text": question.question_text,
                "question_type": question.question_type,
                "display_order": question.display_order,
            }
            for question in request.questions
        ],
    )
    return FeedbackFormResponse(
        id=form.id,
        title=form.title,
        target_role=form.target_role,
        is_anonymous=form.is_anonymous,
        is_open=form.is_open,
        start_date=form.start_date,
        end_date=form.end_date,
        questions=[_feedback_question_response(question) for question in questions],
    )


@router.post("/feedback/forms/{id}/respond")
def submit_feedback_response(
    id: str,
    request: FeedbackSubmitRequest,
    current_user=Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """Submit responses to a feedback form (anonymized where configured with duplicate protection)."""
    form = db.get("feedback_forms", id)
    if not form or not form.is_open:
        raise HTTPException(status_code=400, detail="Feedback form is not accepting responses")
    if current_user.institution_id != form.institution_id:
        raise HTTPException(status_code=403, detail="Cross-institution feedback submission denied")

    now = datetime.now(timezone.utc)
    if form.end_date and now.date() > form.end_date:
        raise HTTPException(status_code=400, detail="Feedback submission window has expired for this form")

    role_names = current_user.role_names
    if form.target_role == "STUDENT" and not current_user.student_profile:
        raise HTTPException(status_code=403, detail="Only enrolled students may submit responses to this form")
    if form.target_role == "FACULTY" and not current_user.faculty_profile:
        raise HTTPException(status_code=403, detail="Only faculty members may submit responses to this form")
    if "PARENT" in role_names and form.target_role != "PARENT":
        raise HTTPException(status_code=403, detail="Parents are not authorized to submit academic feedback for this form")

    if db.exists(
        "audit_logs",
        {
            "institution_id": form.institution_id,
            "user_id": current_user.id,
            "entity_id": form.id,
            "action": "FEEDBACK_SUBMITTED",
        },
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a response for this feedback form",
        )

    respondent_id = None if form.is_anonymous else current_user.id
    db.insert_many(
        "feedback_responses",
        [
            {
                "feedback_form_id": form.id,
                "question_id": answer.question_id,
                "respondent_user_id": respondent_id,
                "rating_value": answer.rating_value,
                "text_response": answer.text_response,
            }
            for answer in request.answers
        ],
    )
    db.insert(
        "audit_logs",
        {
            "institution_id": form.institution_id,
            "user_id": current_user.id,
            "action": "FEEDBACK_SUBMITTED",
            "entity_type": "feedback_forms",
            "entity_id": form.id,
            "new_state": {"is_anonymous": form.is_anonymous},
            "reason": "Feedback response submitted",
        },
    )
    return {"message": "Feedback submitted successfully. Thank you for helping improve academic standards!"}


@router.get("/feedback/forms/{id}/analytics")
def get_feedback_analytics(
    id: str,
    current_user=Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db),
):
    """[PRINCIPAL] Get aggregated analytics and ratings for a feedback form."""
    form = db.find_one(
        "feedback_forms",
        {"id": id, "institution_id": current_user.institution_id},
    )
    if not form:
        raise HTTPException(status_code=404, detail="Feedback form not found")

    total_submissions = db.count(
        "audit_logs",
        {"entity_id": form.id, "action": "FEEDBACK_SUBMITTED"},
    )
    questions = db.find("feedback_questions", {"feedback_form_id": form.id}, sort=[("display_order", 1)])
    responses = db.find("feedback_responses", {"feedback_form_id": form.id})
    responses_by_question = group_by(responses, "question_id")
    question_stats = []
    for question in questions:
        question_responses = responses_by_question.get(question.id, [])
        ratings = [response.rating_value for response in question_responses if response.rating_value is not None]
        average = round(sum(ratings) / len(ratings), 2) if ratings else None
        question_stats.append(
            {
                "question_id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type,
                "total_responses": len(question_responses),
                "average_rating": average,
                "rating_distribution": {str(value): ratings.count(value) for value in range(1, 6)},
                "comments": [response.text_response for response in question_responses if response.text_response],
            }
        )

    return {
        "form_id": form.id,
        "title": form.title,
        "target_role": form.target_role,
        "is_anonymous": form.is_anonymous,
        "is_open": form.is_open,
        "total_submissions": total_submissions,
        "questions": question_stats,
    }


# NOTIFICATIONS
@router.get("/notifications", response_model=List[NotificationResponse])
def get_my_notifications(
    current_user=Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """Fetch notifications for current user."""
    return db.find(
        "notifications",
        {"user_id": current_user.id},
        sort=[("created_at", -1)],
        limit=20,
    )


@router.put("/notifications/{id}/read")
def mark_notification_read(
    id: str,
    current_user=Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """Mark a notification as read."""
    notification = db.find_one("notifications", {"id": id, "user_id": current_user.id})
    if notification:
        db.update(notification, {"is_read": True})
    return {"message": "Notification marked as read"}


# AUDIT LOGS
@router.get("/audit/logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    current_user=Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db),
):
    """[PRINCIPAL | SUPER_ADMIN] Inspect audit trail for the institution."""
    logs = db.find(
        "audit_logs",
        {"institution_id": current_user.institution_id},
        sort=[("created_at", -1)],
        limit=50,
    )
    users = index_by(db.get_many("users", ids(logs, "user_id")).values())
    results = []
    for log in logs:
        user = users.get(log.user_id)
        results.append(
            AuditLogResponse(
                id=log.id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                user_name=user.full_name if user else "System",
                previous_state=log.previous_state,
                new_state=log.new_state,
                reason=log.reason,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
        )
    return results
