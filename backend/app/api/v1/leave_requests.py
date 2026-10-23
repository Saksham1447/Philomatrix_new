from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.academic import FacultyProfile
from app.models.leave import FacultyLeaveRequest
from app.models.user import User
from app.schemas.leave import (
    FacultyLeaveRequestCreate,
    FacultyLeaveRequestResponse,
    FacultyLeaveRequestReview,
)

router = APIRouter(prefix="/leave-requests", tags=["Faculty Leave Requests"])


def _to_response(request: FacultyLeaveRequest) -> FacultyLeaveRequestResponse:
    return FacultyLeaveRequestResponse(
        id=request.id,
        faculty_id=request.faculty_id,
        faculty_name=request.faculty.user.full_name,
        employee_id=request.faculty.employee_id,
        start_date=request.start_date,
        end_date=request.end_date,
        reason=request.reason,
        status=request.status,
        reviewed_by_name=request.reviewed_by.full_name if request.reviewed_by else None,
        review_comments=request.review_comments,
        created_at=request.created_at.isoformat(),
    )


@router.get("", response_model=List[FacultyLeaveRequestResponse])
def list_leave_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Faculty see their own requests; office staff see requests for their institution."""
    query = db.query(FacultyLeaveRequest)
    if current_user.institution_id:
        query = query.filter(FacultyLeaveRequest.institution_id == current_user.institution_id)
    if current_user.faculty_profile:
        query = query.filter(FacultyLeaveRequest.faculty_id == current_user.faculty_profile.id)
    else:
        allowed_roles = {"OFFICE_STAFF", "SUPER_ADMIN"}
        role_names = {assignment.role.name for assignment in current_user.role_assignments}
        if not role_names.intersection(allowed_roles):
            raise HTTPException(status_code=403, detail="Only faculty or office staff can access leave requests")

    requests = query.order_by(FacultyLeaveRequest.created_at.desc()).all()
    return [_to_response(request) for request in requests]


@router.post("", response_model=FacultyLeaveRequestResponse, status_code=status.HTTP_201_CREATED)
def create_leave_request(
    request: FacultyLeaveRequestCreate,
    current_user: User = Depends(require_roles("FACULTY")),
    db: Session = Depends(get_db),
):
    """Submit a leave request for office-staff review."""
    if not current_user.faculty_profile:
        raise HTTPException(status_code=403, detail="Only faculty members can submit leave requests")

    overlapping = (
        db.query(FacultyLeaveRequest)
        .filter(
            FacultyLeaveRequest.faculty_id == current_user.faculty_profile.id,
            FacultyLeaveRequest.status.in_(["PENDING", "APPROVED"]),
            FacultyLeaveRequest.start_date <= request.end_date,
            FacultyLeaveRequest.end_date >= request.start_date,
        )
        .first()
    )
    if overlapping:
        raise HTTPException(
            status_code=400,
            detail="This leave period overlaps an existing pending or approved request",
        )

    leave_request = FacultyLeaveRequest(
        institution_id=current_user.institution_id,
        faculty_id=current_user.faculty_profile.id,
        start_date=request.start_date,
        end_date=request.end_date,
        reason=request.reason,
    )
    db.add(leave_request)
    db.commit()
    db.refresh(leave_request)
    return _to_response(leave_request)


@router.put("/{request_id}/review", response_model=FacultyLeaveRequestResponse)
def review_leave_request(
    request_id: str,
    review: FacultyLeaveRequestReview,
    current_user: User = Depends(require_roles("OFFICE_STAFF", "SUPER_ADMIN")),
    db: Session = Depends(get_db),
):
    """Approve or reject a pending faculty leave request."""
    request_query = db.query(FacultyLeaveRequest).filter(FacultyLeaveRequest.id == request_id)
    if current_user.institution_id:
        request_query = request_query.filter(
            FacultyLeaveRequest.institution_id == current_user.institution_id
        )
    leave_request = request_query.first()
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if leave_request.status != "PENDING":
        raise HTTPException(status_code=400, detail="Only pending leave requests can be reviewed")

    leave_request.status = review.status
    leave_request.reviewed_by_id = current_user.id
    leave_request.review_comments = review.review_comments
    db.commit()
    db.refresh(leave_request)
    return _to_response(leave_request)
