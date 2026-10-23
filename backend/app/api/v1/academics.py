from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User
from app.models.academic import AcademicYear, ClassModel, Division, Subject
from app.schemas.academic import (
    AcademicYearCreate,
    AcademicYearResponse,
    ClassCreate,
    ClassResponse,
    DivisionCreate,
    DivisionResponse,
    SubjectCreate,
    SubjectResponse,
)

router = APIRouter(prefix="/academics", tags=["Academic Structure"])


# Academic Years
@router.get("/years", response_model=List[AcademicYearResponse])
def list_academic_years(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List academic years for the caller's institution."""
    return (
        db.query(AcademicYear)
        .filter(AcademicYear.institution_id == current_user.institution_id)
        .order_by(AcademicYear.start_date.desc())
        .all()
    )


@router.post("/years", response_model=AcademicYearResponse, status_code=status.HTTP_201_CREATED)
def create_academic_year(
    request: AcademicYearCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: Session = Depends(get_db)
):
    """Add an academic year for the institution."""
    existing = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.institution_id == current_user.institution_id,
            AcademicYear.name == request.name
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Academic year with this name already exists")

    if request.is_current:
        # unset other current years
        db.query(AcademicYear).filter(
            AcademicYear.institution_id == current_user.institution_id
        ).update({"is_current": False})

    year = AcademicYear(
        institution_id=current_user.institution_id,
        name=request.name,
        start_date=request.start_date,
        end_date=request.end_date,
        is_current=request.is_current,
        is_archived=False
    )
    db.add(year)
    db.commit()
    db.refresh(year)
    return year


@router.put("/years/{id}/set-current")
def set_current_year(
    id: str,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: Session = Depends(get_db)
):
    """Set an academic year as active/current."""
    year = (
        db.query(AcademicYear)
        .filter(AcademicYear.id == id, AcademicYear.institution_id == current_user.institution_id)
        .first()
    )
    if not year:
        raise HTTPException(status_code=404, detail="Academic year not found")

    db.query(AcademicYear).filter(
        AcademicYear.institution_id == current_user.institution_id
    ).update({"is_current": False})

    year.is_current = True
    db.commit()
    return {"message": f"Academic year {year.name} set as current"}


# Classes & Divisions
@router.get("/classes", response_model=List[ClassResponse])
def list_classes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List classes and divisions for the caller's institution."""
    return (
        db.query(ClassModel)
        .options(selectinload(ClassModel.divisions))
        .filter(ClassModel.institution_id == current_user.institution_id)
        .order_by(ClassModel.display_order.asc())
        .all()
    )


@router.post("/classes", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(
    request: ClassCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: Session = Depends(get_db)
):
    """Create a new class (e.g., Class 11, Class 12)."""
    existing = (
        db.query(ClassModel)
        .filter(
            ClassModel.institution_id == current_user.institution_id,
            ClassModel.name == request.name,
            ClassModel.stream == request.stream
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Class already exists")

    new_class = ClassModel(
        institution_id=current_user.institution_id,
        name=request.name,
        stream=request.stream,
        display_order=request.display_order
    )
    db.add(new_class)
    db.flush()
    division_names = list(dict.fromkeys(name.strip() for name in request.divisions if name.strip()))
    for division_name in division_names:
        db.add(Division(
            institution_id=current_user.institution_id,
            class_id=new_class.id,
            name=division_name,
        ))
    db.commit()
    db.refresh(new_class)
    db.refresh(new_class, attribute_names=["divisions"])
    return new_class


@router.put("/classes/{id}", response_model=ClassResponse)
def update_class(
    id: str,
    request: ClassCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: Session = Depends(get_db),
):
    cls = db.query(ClassModel).filter(ClassModel.id == id, ClassModel.institution_id == current_user.institution_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    cls.name = request.name
    cls.stream = request.stream
    cls.display_order = request.display_order
    existing_divisions = {division.name for division in cls.divisions}
    for division_name in dict.fromkeys(name.strip() for name in request.divisions if name.strip()):
        if division_name not in existing_divisions:
            db.add(Division(
                institution_id=current_user.institution_id,
                class_id=cls.id,
                name=division_name,
            ))
    db.commit()
    db.refresh(cls)
    db.refresh(cls, attribute_names=["divisions"])
    return cls


@router.delete("/classes/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(
    id: str,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: Session = Depends(get_db),
):
    cls = db.query(ClassModel).filter(ClassModel.id == id, ClassModel.institution_id == current_user.institution_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    if any(division.enrollments for division in cls.divisions):
        raise HTTPException(status_code=409, detail="Cannot delete a class with enrolled students")
    db.delete(cls)
    db.commit()
    return None


@router.post("/divisions", response_model=DivisionResponse, status_code=status.HTTP_201_CREATED)
def create_division(
    request: DivisionCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "OFFICE_STAFF")),
    db: Session = Depends(get_db)
):
    """Add a division to an existing class."""
    cls = (
        db.query(ClassModel)
        .filter(ClassModel.id == request.class_id, ClassModel.institution_id == current_user.institution_id)
        .first()
    )
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    existing = (
        db.query(Division)
        .filter(Division.class_id == request.class_id, Division.name == request.name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Division already exists in this class")

    div = Division(
        institution_id=current_user.institution_id,
        class_id=request.class_id,
        name=request.name,
        room_number=request.room_number,
        capacity=request.capacity
    )
    db.add(div)
    db.commit()
    db.refresh(div)
    return div


# Subjects
@router.get("/subjects", response_model=List[SubjectResponse])
def list_subjects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all subjects offered in the institution."""
    return (
        db.query(Subject)
        .filter(Subject.institution_id == current_user.institution_id)
        .order_by(Subject.name.asc())
        .all()
    )


@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(
    request: SubjectCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: Session = Depends(get_db)
):
    """Create a new subject with theory & practical mark limits."""
    existing = (
        db.query(Subject)
        .filter(
            Subject.institution_id == current_user.institution_id,
            Subject.code == request.code
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Subject with this code already exists")

    subject = Subject(
        institution_id=current_user.institution_id,
        code=request.code,
        name=request.name,
        stream=request.stream,
        has_practical=request.has_practical,
        max_theory_marks=request.max_theory_marks,
        max_practical_marks=request.max_practical_marks,
        min_pass_percentage=request.min_pass_percentage
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject
