import mimetypes
import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.core.deps import get_db
from app.core.deps import get_current_user, require_roles, verify_student_access
from app.core.docstore import Doc, DocStore
from app.core.q import ids, in_, index_by
from app.schemas.study_material import StudyMaterialResponse, StudyMaterialUpdate

router = APIRouter(prefix="/study-materials", tags=["Study Materials & Class Notes"])

# Local secure storage directory
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "storage", "study_materials")
os.makedirs(STORAGE_DIR, exist_ok=True)

# Permitted file extensions and MIME types
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".txt"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


def _to_response(material: Doc, db: DocStore, relations: dict | None = None) -> StudyMaterialResponse:
    relations = relations or {}
    cls = relations["classes"].get(material.class_id) if "classes" in relations else db.get("classes", material.class_id)
    division = (
        relations["divisions"].get(material.division_id)
        if "divisions" in relations and material.division_id
        else db.get("divisions", material.division_id) if material.division_id else None
    )
    subject = relations["subjects"].get(material.subject_id) if "subjects" in relations else db.get("subjects", material.subject_id)
    faculty = relations["faculties"].get(material.faculty_id) if "faculties" in relations else db.get("faculty_profiles", material.faculty_id)
    faculty_user = (
        relations["users"].get(faculty.user_id)
        if "users" in relations and faculty
        else db.get("users", faculty.user_id) if faculty else None
    )
    return StudyMaterialResponse(
        id=material.id,
        title=material.title,
        description=material.description,
        topic=material.topic,
        file_name=material.file_name,
        file_size=material.file_size,
        file_type=material.file_type,
        is_published=material.is_published,
        download_count=material.download_count,
        created_at=material.created_at,
        class_id=material.class_id,
        class_name=cls.name if cls else "Class",
        division_id=material.division_id,
        division_name=division.name if division else "All Divisions",
        subject_id=material.subject_id,
        subject_name=subject.name if subject else "Subject",
        subject_code=subject.code if subject else "",
        faculty_id=material.faculty_id,
        faculty_name=faculty_user.full_name if faculty_user else "Faculty",
    )


@router.post("", response_model=StudyMaterialResponse, status_code=status.HTTP_201_CREATED)
@router.post("/upload", response_model=StudyMaterialResponse, status_code=status.HTTP_201_CREATED)
async def upload_study_material(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    topic: Optional[str] = Form(None),
    class_id: str = Form(...),
    division_id: Optional[str] = Form(None),
    subject_id: str = Form(...),
    is_published: bool = Form(True),
    current_user=Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY")),
    db: DocStore = Depends(get_db),
):
    """[FACULTY | PRINCIPAL] Upload lecture notes, reference PDFs, slides, or diagrams."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Permitted educational formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of 25MB (Received {round(file_size / (1024*1024), 2)}MB)",
        )
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Cannot upload an empty file")

    faculty = current_user.faculty_profile
    if not faculty:
        faculty = db.find_one("faculty_profiles", {"institution_id": current_user.institution_id})
        if not faculty:
            raise HTTPException(status_code=400, detail="No faculty profile available in institution")

    active_year = db.find_one(
        "academic_years",
        {"institution_id": current_user.institution_id, "is_current": True},
    )
    if not active_year:
        active_year = db.find_one("academic_years", {"institution_id": current_user.institution_id})
    if not active_year:
        raise HTTPException(status_code=400, detail="No academic year found for institution")

    unique_filename = f"{uuid.uuid4().hex}_{os.path.basename(file.filename)}"
    dest_path = os.path.join(STORAGE_DIR, unique_filename)
    with open(dest_path, "wb") as out_f:
        out_f.write(content)

    mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
    actual_class_id = class_id
    if (not actual_class_id or actual_class_id == "none") and division_id:
        division = db.get("divisions", division_id)
        if division:
            actual_class_id = division.class_id
    if not actual_class_id or actual_class_id == "none":
        first_class = db.find_one("classes", {"institution_id": current_user.institution_id})
        actual_class_id = first_class.id if first_class else "none"

    material = db.insert(
        "study_materials",
        {
            "institution_id": current_user.institution_id,
            "academic_year_id": active_year.id,
            "faculty_id": faculty.id,
            "class_id": actual_class_id,
            "division_id": division_id or None,
            "subject_id": subject_id,
            "title": title,
            "description": description,
            "topic": topic,
            "file_name": file.filename,
            "file_path": dest_path,
            "file_size": file_size,
            "file_type": mime_type,
            "is_published": is_published,
            "download_count": 0,
        },
    )
    db.insert(
        "audit_logs",
        {
            "institution_id": current_user.institution_id,
            "user_id": current_user.id,
            "action": "STUDY_MATERIAL_UPLOADED",
            "entity_type": "study_materials",
            "entity_id": material.id,
            "new_state": {
                "title": title,
                "file_name": file.filename,
                "file_size": file_size,
                "is_published": is_published,
            },
            "reason": "Faculty uploaded educational resource",
        },
    )
    return _to_response(material, db)


@router.get("", response_model=List[StudyMaterialResponse])
def list_study_materials(
    class_id: Optional[str] = None,
    division_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    student_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """List study materials filtered and scoped to caller's role and enrollment."""
    query = {"institution_id": current_user.institution_id}
    and_filters = []

    if current_user.student_profile:
        enrollment = db.find_one("enrollments", {"student_id": current_user.student_profile.id})
        if not enrollment:
            return []
        query.update(
            {
                "is_published": True,
                "class_id": enrollment.class_id,
                "division_id": in_([enrollment.division_id, None]),
            }
        )
    elif current_user.guardian_profile:
        if student_id:
            student = verify_student_access(student_id, current_user, db)
            enrollment = db.find_one("enrollments", {"student_id": student.id})
        else:
            link = db.find_one(
                "student_guardian_links",
                {"guardian_id": current_user.guardian_profile.id, "is_verified": True},
            )
            enrollment = db.find_one("enrollments", {"student_id": link.student_id}) if link else None
        if not enrollment:
            return []
        query.update(
            {
                "is_published": True,
                "class_id": enrollment.class_id,
                "division_id": in_([enrollment.division_id, None]),
            }
        )
    elif current_user.faculty_profile:
        if not class_id and not subject_id:
            query["faculty_id"] = current_user.faculty_profile.id

    if class_id:
        if "class_id" in query and query["class_id"] != class_id:
            and_filters.append({"class_id": class_id})
        else:
            query["class_id"] = class_id
    if division_id:
        and_filters.append({"division_id": in_([division_id, None])})
    if subject_id:
        query["subject_id"] = subject_id
    if and_filters:
        query["$and"] = and_filters

    materials = db.find("study_materials", query, sort=[("created_at", -1)])
    relations = {
        "classes": index_by(db.get_many("classes", ids(materials, "class_id")).values()),
        "divisions": index_by(db.get_many("divisions", ids(materials, "division_id")).values()),
        "subjects": index_by(db.get_many("subjects", ids(materials, "subject_id")).values()),
        "faculties": index_by(db.get_many("faculty_profiles", ids(materials, "faculty_id")).values()),
    }
    relations["users"] = index_by(
        db.get_many("users", ids(relations["faculties"].values(), "user_id")).values()
    )
    return [_to_response(material, db, relations) for material in materials]


@router.get("/{id}/download")
def download_study_material(
    id: str,
    student_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: DocStore = Depends(get_db),
):
    """Secure streaming download of educational document with authorization check."""
    material = db.get("study_materials", id)
    if not material:
        raise HTTPException(status_code=404, detail="Study material not found")
    if material.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Cross-institution document access forbidden")

    if current_user.student_profile:
        if not material.is_published:
            raise HTTPException(status_code=403, detail="Document is in draft mode and not published")
        enrollment = db.find_one("enrollments", {"student_id": current_user.student_profile.id})
        if not enrollment or enrollment.class_id != material.class_id:
            raise HTTPException(status_code=403, detail="You are not enrolled in the class for this document")
    elif current_user.guardian_profile:
        if not material.is_published:
            raise HTTPException(status_code=403, detail="Document is in draft mode and not published")
        links = db.find(
            "student_guardian_links",
            {"guardian_id": current_user.guardian_profile.id, "is_verified": True},
        )
        child_ids = [link.student_id for link in links]
        authorized = db.find_one(
            "enrollments",
            {"student_id": in_(child_ids), "class_id": material.class_id},
        )
        if not authorized:
            raise HTTPException(status_code=403, detail="Your linked children are not enrolled in the class for this document")

    if not os.path.exists(material.file_path):
        raise HTTPException(status_code=404, detail="Physical file resource not found on server")
    db.increment("study_materials", material.id, "download_count")
    return FileResponse(
        path=material.file_path,
        filename=material.file_name,
        media_type=material.file_type or "application/octet-stream",
    )


@router.put("/{id}", response_model=StudyMaterialResponse)
def update_study_material(
    id: str,
    update: StudyMaterialUpdate,
    current_user=Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY")),
    db: DocStore = Depends(get_db),
):
    """[FACULTY | PRINCIPAL] Edit metadata or publication status of study material."""
    material = db.find_one(
        "study_materials",
        {"id": id, "institution_id": current_user.institution_id},
    )
    if not material:
        raise HTTPException(status_code=404, detail="Study material not found")
    if current_user.faculty_profile and material.faculty_id != current_user.faculty_profile.id:
        raise HTTPException(status_code=403, detail="You can only modify materials you uploaded")

    material = db.update(material, update.model_dump(exclude_unset=True))
    return _to_response(material, db)


@router.delete("/{id}")
def delete_study_material(
    id: str,
    current_user=Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY")),
    db: DocStore = Depends(get_db),
):
    """[FACULTY | PRINCIPAL] Delete study material record and file."""
    material = db.find_one(
        "study_materials",
        {"id": id, "institution_id": current_user.institution_id},
    )
    if not material:
        raise HTTPException(status_code=404, detail="Study material not found")
    if current_user.faculty_profile and material.faculty_id != current_user.faculty_profile.id:
        raise HTTPException(status_code=403, detail="You can only delete materials you uploaded")

    if os.path.exists(material.file_path):
        try:
            os.remove(material.file_path)
        except OSError:
            pass

    db.delete("study_materials", material)
    return {"message": "Study material deleted successfully"}
