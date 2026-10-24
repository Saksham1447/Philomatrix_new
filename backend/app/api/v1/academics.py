from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.default_subjects import ensure_default_subjects
from app.core.deps import get_db, get_current_user, require_roles
from app.core.docstore import DocStore, UserDoc
from app.core.q import ids
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


def _class_with_divisions(db: DocStore, cls) -> dict:
    """Return the class document plus its nested divisions (replaces selectinload)."""
    return {**cls, "divisions": db.find("divisions", {"class_id": cls.id})}


# Academic Years
@router.get("/years", response_model=List[AcademicYearResponse])
def list_academic_years(
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """List academic years for the caller's institution."""
    return db.find(
        "academic_years",
        {"institution_id": current_user.institution_id},
        sort=[("start_date", -1)],
    )


@router.post("/years", response_model=AcademicYearResponse, status_code=status.HTTP_201_CREATED)
def create_academic_year(
    request: AcademicYearCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db)
):
    """Add an academic year for the institution."""
    existing = db.find_one(
        "academic_years",
        {"institution_id": current_user.institution_id, "name": request.name},
    )
    if existing:
        raise HTTPException(status_code=400, detail="Academic year with this name already exists")

    if request.is_current:
        # unset other current years
        db.update_many(
            "academic_years",
            {"institution_id": current_user.institution_id},
            {"is_current": False},
        )

    return db.insert("academic_years", {
        "institution_id": current_user.institution_id,
        "name": request.name,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "is_current": request.is_current,
        "is_archived": False,
    })


@router.put("/years/{id}/set-current")
def set_current_year(
    id: str,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db)
):
    """Set an academic year as active/current."""
    year = db.find_one(
        "academic_years",
        {"id": id, "institution_id": current_user.institution_id},
    )
    if not year:
        raise HTTPException(status_code=404, detail="Academic year not found")

    db.update_many(
        "academic_years",
        {"institution_id": current_user.institution_id},
        {"is_current": False},
    )
    db.update(year, {"is_current": True})
    return {"message": f"Academic year {year.name} set as current"}


# Classes & Divisions
@router.get("/classes", response_model=List[ClassResponse])
def list_classes(
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """List classes and divisions for the caller's institution."""
    classes = db.find(
        "classes",
        {"institution_id": current_user.institution_id},
        sort=[("display_order", 1)],
    )
    divisions = db.find("divisions", {"class_id": {"$in": ids(classes)}}) if classes else []
    by_class: dict = {}
    for division in divisions:
        by_class.setdefault(division.class_id, []).append(division)
    return [{**cls, "divisions": by_class.get(cls.id, [])} for cls in classes]


@router.post("/classes", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(
    request: ClassCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db)
):
    """Create a new class (e.g., Class 11, Class 12)."""
    existing = db.find_one(
        "classes",
        {
            "institution_id": current_user.institution_id,
            "name": request.name,
            "stream": request.stream,
        },
    )
    if existing:
        raise HTTPException(status_code=400, detail="Class already exists")

    new_class = db.insert("classes", {
        "institution_id": current_user.institution_id,
        "name": request.name,
        "stream": request.stream,
        "display_order": request.display_order,
    })
    division_names = list(dict.fromkeys(name.strip() for name in request.divisions if name.strip()))
    for division_name in division_names:
        db.insert("divisions", {
            "institution_id": current_user.institution_id,
            "class_id": new_class.id,
            "name": division_name,
        })
    return _class_with_divisions(db, new_class)


@router.put("/classes/{id}", response_model=ClassResponse)
def update_class(
    id: str,
    request: ClassCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db),
):
    cls = db.find_one("classes", {"id": id, "institution_id": current_user.institution_id})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    db.update(cls, {
        "name": request.name,
        "stream": request.stream,
        "display_order": request.display_order,
    })
    existing_divisions = {division.name for division in db.find("divisions", {"class_id": cls.id})}
    for division_name in dict.fromkeys(name.strip() for name in request.divisions if name.strip()):
        if division_name not in existing_divisions:
            db.insert("divisions", {
                "institution_id": current_user.institution_id,
                "class_id": cls.id,
                "name": division_name,
            })
    return _class_with_divisions(db, cls)


@router.delete("/classes/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(
    id: str,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db),
):
    cls = db.find_one("classes", {"id": id, "institution_id": current_user.institution_id})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    division_ids = ids(db.find("divisions", {"class_id": cls.id}))
    if division_ids and db.exists("enrollments", {"division_id": {"$in": division_ids}}):
        raise HTTPException(status_code=409, detail="Cannot delete a class with enrolled students")
    db.delete("classes", cls)
    return None


@router.post("/divisions", response_model=DivisionResponse, status_code=status.HTTP_201_CREATED)
def create_division(
    request: DivisionCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db)
):
    """Add a division to an existing class."""
    cls = db.find_one(
        "classes",
        {"id": request.class_id, "institution_id": current_user.institution_id},
    )
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    existing = db.find_one("divisions", {"class_id": request.class_id, "name": request.name})
    if existing:
        raise HTTPException(status_code=400, detail="Division already exists in this class")

    return db.insert("divisions", {
        "institution_id": current_user.institution_id,
        "class_id": request.class_id,
        "name": request.name,
        "room_number": request.room_number,
        "capacity": request.capacity,
    })


# Subjects
@router.get("/subjects", response_model=List[SubjectResponse])
def list_subjects(
    current_user: UserDoc = Depends(get_current_user),
    db: DocStore = Depends(get_db)
):
    """List all subjects offered in the institution."""
    # Institutes created before the standard subject list existed get it on first use.
    if not db.count("subjects", {"institution_id": current_user.institution_id}):
        ensure_default_subjects(db, current_user.institution_id)
    return db.find(
        "subjects",
        {"institution_id": current_user.institution_id},
        sort=[("name", 1)],
    )


@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(
    request: SubjectCreate,
    current_user: UserDoc = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL")),
    db: DocStore = Depends(get_db)
):
    """Create a new subject with theory & practical mark limits."""
    existing = db.find_one(
        "subjects",
        {"institution_id": current_user.institution_id, "code": request.code},
    )
    if existing:
        raise HTTPException(status_code=400, detail="Subject with this code already exists")

    return db.insert("subjects", {
        "institution_id": current_user.institution_id,
        "code": request.code,
        "name": request.name,
        "stream": request.stream,
        "has_practical": request.has_practical,
        "max_theory_marks": request.max_theory_marks,
        "max_practical_marks": request.max_practical_marks,
        "min_pass_percentage": request.min_pass_percentage,
    })