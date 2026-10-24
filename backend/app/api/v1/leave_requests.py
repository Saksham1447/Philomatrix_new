from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_db
from app.core.deps import get_current_user, require_roles
from app.core.docstore import Doc, DocStore
from app.core.q import ids, in_, index_by
from app.schemas.leave import (
    FacultyLeaveRequestCreate,
    FacultyLeaveRequestResponse,
    FacultyLeaveRequestReview,
)

router = APIRouter(prefix="/leave-requests", tags=["Faculty Leave Requests"])


def _to_response(
    request: Doc,
    db: DocStore,
    faculties: dict | None = None,
    users: dict | None = None,
) -> FacultyLeaveRequestResponse:
    faculty = faculties.get(request.faculty_id) if faculties is not None else db.get("faculty_profiles", request.faculty_id)
    faculty_user = users.get(faculty.user_id) if users is not None and faculty else (
        db.get("users", faculty.user_id) if faculty else None
    )
    reviewer = users.get(request.reviewed_by_id) if users is not None and request.reviewed_by_id else (
        db.get("users", request.reviewed_by_id) if request.reviewed_by_id else None
    )
    return FacultyLeaveRequestResponse(
        id=request.id,
        faculty_id=request.faculty_id,
        faculty_name=faculty_user.full_name if faculty_user else "",
        employee_id=faculty.employee_id if faculty else "",
        start_date=request.start_date,
        end_date=request.end_date,
        reason=request.reason,
        status=request.status,
        reviewed_by_name=reviewer.full_name if reviewer else None,
        review_comments=request.review_comments,
        created_at=request.created_at.isoformat(),
    )


@router.get("", response_model=List[FacultyLeaveRequestResponse])
def list_leave_requests(
    current_user=Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """Faculty see their own requests; office staff see requests for their institution."""
    query = {}
    if current_user.institution_id:
        query["institution_id"] = current_user.institution_id
    if current_user.faculty_profile:
        query["faculty_id"] = current_user.faculty_profile.id
    else:
        allowed_roles = {"OFFICE_STAFF", "SUPER_ADMIN"}
        if not allowed_roles.intersection(current_user.role_names):
            raise HTTPException(status_code=403, detail="Only faculty or office staff can access leave requests")

    requests = db.find("faculty_leave_requests", query, sort=[("created_at", -1)])
    faculties = index_by(db.get_many("faculty_profiles", ids(requests, "faculty_id")).values())
    users = index_by(
        db.get_many(
            "users",
            ids(faculties.values(), "user_id") + ids(requests, "reviewed_by_id"),
        ).values()
    )
    return [_to_response(request, db, faculties, users) for request in requests]


@router.post("", response_model=FacultyLeaveRequestResponse, status_code=status.HTTP_201_CREATED)
def create_leave_request(
    request: FacultyLeaveRequestCreate,
    current_user=Depends(require_roles("FACULTY")),
    db: DocStore = Depends(get_db),
):
    """Submit a leave request for office-staff review."""
    if not current_user.faculty_profile:
        raise HTTPException(status_code=403, detail="Only faculty members can submit leave requests")

    faculty_id = current_user.faculty_profile.id
    overlapping = db.find_one(
        "faculty_leave_requests",
        {
            "faculty_id": faculty_id,
            "status": in_(["PENDING", "APPROVED"]),
            "start_date": {"$lte": request.end_date},
            "end_date": {"$gte": request.start_date},
        },
    )
    if overlapping:
        raise HTTPException(
            status_code=400,
            detail="This leave period overlaps an existing pending or approved request",
        )

    leave_request = db.insert(
        "faculty_leave_requests",
        {
            "institution_id": current_user.institution_id,
            "faculty_id": faculty_id,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "reason": request.reason,
        },
    )
    return _to_response(leave_request, db)


@router.put("/{request_id}/review", response_model=FacultyLeaveRequestResponse)
def review_leave_request(
    request_id: str,
    review: FacultyLeaveRequestReview,
    current_user=Depends(require_roles("OFFICE_STAFF", "SUPER_ADMIN")),
    db: DocStore = Depends(get_db),
):
    """Approve or reject a pending faculty leave request."""
    query = {"id": request_id}
    if current_user.institution_id:
        query["institution_id"] = current_user.institution_id
    leave_request = db.find_one("faculty_leave_requests", query)
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if leave_request.status != "PENDING":
        raise HTTPException(status_code=400, detail="Only pending leave requests can be reviewed")

    leave_request = db.update(
        leave_request,
        {
            "status": review.status,
            "reviewed_by_id": current_user.id,
            "review_comments": review.review_comments,
        },
    )
    return _to_response(leave_request, db)
