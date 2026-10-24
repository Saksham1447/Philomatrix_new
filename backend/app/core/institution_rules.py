"""Institution-type rules shared by the faculty, student and timetable routes."""
from fastapi import HTTPException

from app.core.docstore import DocStore

ENGINEERING_TYPE = "ENGINEERING_COLLEGE"


def is_engineering_college(db: DocStore, institution_id: str | None) -> bool:
    """Engineering colleges keep faculty department-wise; every other type does not."""
    if not institution_id:
        return False
    institution = db.get("institutions", institution_id)
    settings_doc = db.find_one("institution_settings", {"institution_id": institution_id})
    return ENGINEERING_TYPE in (
        getattr(institution, "institution_type", None),
        getattr(settings_doc, "institution_type", None),
    )


def resolve_faculty_department(db: DocStore, institution_id: str | None, requested: str | None, current: str = "General") -> str:
    """Return the department to store for a faculty profile.

    Engineering colleges require one of the institution's departments (classes); all
    other institution types ignore it because staff teach any class or subject.
    """
    if not is_engineering_college(db, institution_id):
        return current
    name = (requested or "").strip()
    if not name or name.lower() == "general":
        raise HTTPException(status_code=400, detail="Select the department this faculty member belongs to")
    for academic_unit in db.find("classes", {"institution_id": institution_id}):
        if academic_unit.name.strip().lower() == name.lower():
            return academic_unit.name
    raise HTTPException(status_code=400, detail=f"Department '{name}' does not exist in this institution")
