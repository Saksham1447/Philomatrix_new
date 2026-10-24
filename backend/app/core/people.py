"""Validation shared by the routes that add faculty and students."""
import re
from typing import Optional

from fastapi import HTTPException

from app.core.docstore import DocStore

GENDERS = ("MALE", "FEMALE", "OTHER")


def normalize_gender(value: Optional[str], *, required: bool = True) -> Optional[str]:
    """Return MALE, FEMALE or OTHER, rejecting anything else."""
    cleaned = (value or "").strip().upper()
    if not cleaned:
        if required:
            raise HTTPException(status_code=400, detail="Gender is required (Male, Female or Other)")
        return None
    if cleaned not in GENDERS:
        raise HTTPException(status_code=400, detail="Gender must be Male, Female or Other")
    return cleaned


def ensure_unique_person_id(
    db: DocStore,
    collection: str,
    field: str,
    value: Optional[str],
    institution_id: Optional[str],
    label: str,
    exclude_id: Optional[str] = None,
) -> str:
    """Trim an ID and reject it when another record in the institution already uses it (ignoring case)."""
    cleaned = (value or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail=f"{label} is required")
    matches = db.find(collection, {
        "institution_id": institution_id,
        field: {"$regex": f"^{re.escape(cleaned)}$", "$options": "i"},
    })
    if any(match.id != exclude_id for match in matches):
        raise HTTPException(status_code=400, detail=f"{label} '{cleaned}' already exists")
    return cleaned
