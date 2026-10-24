"""Standard subject list every institute starts with."""
from app.core.docstore import DocStore

# (code, name, has practical component)
DEFAULT_SUBJECTS = (
    ("PHY", "Physics", True),
    ("CHE", "Chemistry", True),
    ("MATH", "Mathematics", False),
    ("BIO", "Biology", True),
    ("ENG", "English", False),
    ("IT", "Information Technology", True),
    ("CS", "Computer Science", True),
    ("MAR", "Marathi", False),
    ("HIN", "Hindi", False),
    ("EVS", "Environmental Education", False),
)


def ensure_default_subjects(store: DocStore, institution_id: str | None) -> int:
    """Add the standard subjects the institute does not already have; returns how many were added.

    A subject counts as present when its code matches or an existing name equals or starts with
    the standard name (e.g. "Mathematics & Statistics" covers "Mathematics").
    """
    if not institution_id:
        return 0
    existing = store.find("subjects", {"institution_id": institution_id})
    codes = {subject.code.lower() for subject in existing}
    names = [subject.name.strip().lower() for subject in existing]
    added = 0
    for code, name, has_practical in DEFAULT_SUBJECTS:
        lowered = name.lower()
        if code.lower() in codes or any(item == lowered or item.startswith(lowered) for item in names):
            continue
        store.insert("subjects", {
            "institution_id": institution_id,
            "code": code,
            "name": name,
            "has_practical": has_practical,
            "max_theory_marks": 70 if has_practical else 100,
            "max_practical_marks": 30 if has_practical else 0,
        })
        added += 1
    return added
