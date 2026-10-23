import os
import uuid
import mimetypes
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles, verify_student_access
from app.models.user import User, Role, UserRoleAssignment
from app.models.academic import FacultyProfile, ClassModel, Division, Subject, AcademicYear
from app.models.student import Student, Enrollment, StudentGuardianLink
from app.models.study_material import StudyMaterial
from app.models.communication import AuditLog
from app.schemas.study_material import StudyMaterialResponse, StudyMaterialUpdate

router = APIRouter(prefix="/study-materials", tags=["Study Materials & Class Notes"])

# Local secure storage directory
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "storage", "study_materials")
os.makedirs(STORAGE_DIR, exist_ok=True)

# Permitted file extensions and MIME types
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".txt"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


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
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY")),
    db: Session = Depends(get_db)
):
    """[FACULTY | PRINCIPAL] Upload lecture notes, reference PDFs, slides, or diagrams."""
    # 1. Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Permitted educational formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # 2. Read content and enforce size boundary
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of 25MB (Received {round(file_size / (1024*1024), 2)}MB)"
        )
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Cannot upload an empty file")

    # 3. Determine faculty profile
    f_profile = current_user.faculty_profile
    if not f_profile:
        # Principal uploading on behalf of institution: find first faculty profile in institution or fallback
        f_profile = db.query(FacultyProfile).filter(FacultyProfile.institution_id == current_user.institution_id).first()
        if not f_profile:
            raise HTTPException(status_code=400, detail="No faculty profile available in institution")

    # 4. Fetch active academic year
    active_year = (
        db.query(AcademicYear)
        .filter(AcademicYear.institution_id == current_user.institution_id, AcademicYear.is_current == True)
        .first()
    )
    if not active_year:
        active_year = db.query(AcademicYear).filter(AcademicYear.institution_id == current_user.institution_id).first()
    if not active_year:
        raise HTTPException(status_code=400, detail="No academic year found for institution")

    # 5. Save physical file to private disk
    unique_filename = f"{uuid.uuid4().hex}_{os.path.basename(file.filename)}"
    dest_path = os.path.join(STORAGE_DIR, unique_filename)
    with open(dest_path, "wb") as out_f:
        out_f.write(content)

    mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    # Resolve class_id if missing or 'none'
    actual_class_id = class_id
    if (not actual_class_id or actual_class_id == "none") and division_id:
        div_obj = db.query(Division).filter(Division.id == division_id).first()
        if div_obj:
            actual_class_id = div_obj.class_id
    if not actual_class_id or actual_class_id == "none":
        first_cls = db.query(ClassModel).filter(ClassModel.institution_id == current_user.institution_id).first()
        actual_class_id = first_cls.id if first_cls else "none"

    # 6. Create database record
    material = StudyMaterial(
        institution_id=current_user.institution_id,
        academic_year_id=active_year.id,
        faculty_id=f_profile.id,
        class_id=actual_class_id,
        division_id=division_id if division_id else None,
        subject_id=subject_id,
        title=title,
        description=description,
        topic=topic,
        file_name=file.filename,
        file_path=dest_path,
        file_size=file_size,
        file_type=mime_type,
        is_published=is_published,
        download_count=0
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    # 7. Audit Log
    audit = AuditLog(
        institution_id=current_user.institution_id,
        user_id=current_user.id,
        action="STUDY_MATERIAL_UPLOADED",
        entity_type="study_materials",
        entity_id=material.id,
        new_state={"title": title, "file_name": file.filename, "file_size": file_size, "is_published": is_published},
        reason="Faculty uploaded educational resource"
    )
    db.add(audit)
    db.commit()

    cls = material.class_model
    div = material.division
    subj = material.subject

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
        division_name=div.name if div else "All Divisions",
        subject_id=material.subject_id,
        subject_name=subj.name if subj else "Subject",
        subject_code=subj.code if subj else "",
        faculty_id=material.faculty_id,
        faculty_name=material.faculty.user.full_name
    )


@router.get("", response_model=List[StudyMaterialResponse])
def list_study_materials(
    class_id: Optional[str] = None,
    division_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    student_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List study materials filtered and scoped to caller's role and enrollment."""
    query = (
        db.query(StudyMaterial)
        .filter(StudyMaterial.institution_id == current_user.institution_id)
    )

    # Scoping by role:
    if current_user.student_profile:
        # Enrolled student: only materials published for their class/division
        enr = db.query(Enrollment).filter(Enrollment.student_id == current_user.student_profile.id).first()
        if not enr:
            return []
        query = query.filter(
            StudyMaterial.is_published == True,
            StudyMaterial.class_id == enr.class_id,
            (StudyMaterial.division_id == enr.division_id) | (StudyMaterial.division_id == None)
        )
    elif current_user.guardian_profile:
        # Parent: verify linked child
        if student_id:
            student = verify_student_access(student_id, current_user, db)
            enr = db.query(Enrollment).filter(Enrollment.student_id == student.id).first()
        else:
            link = (
                db.query(StudentGuardianLink)
                .filter(StudentGuardianLink.guardian_id == current_user.guardian_profile.id, StudentGuardianLink.is_verified == True)
                .first()
            )
            enr = db.query(Enrollment).filter(Enrollment.student_id == link.student_id).first() if link else None

        if not enr:
            return []
        query = query.filter(
            StudyMaterial.is_published == True,
            StudyMaterial.class_id == enr.class_id,
            (StudyMaterial.division_id == enr.division_id) | (StudyMaterial.division_id == None)
        )
    elif current_user.faculty_profile:
        # Faculty: show their own uploads (published and drafts), or filter by class/division
        if not class_id and not subject_id:
            query = query.filter(StudyMaterial.faculty_id == current_user.faculty_profile.id)

    # Optional filters
    if class_id:
        query = query.filter(StudyMaterial.class_id == class_id)
    if division_id:
        query = query.filter((StudyMaterial.division_id == division_id) | (StudyMaterial.division_id == None))
    if subject_id:
        query = query.filter(StudyMaterial.subject_id == subject_id)

    materials = query.order_by(StudyMaterial.created_at.desc()).all()
    results = []
    for m in materials:
        results.append(
            StudyMaterialResponse(
                id=m.id,
                title=m.title,
                description=m.description,
                topic=m.topic,
                file_name=m.file_name,
                file_size=m.file_size,
                file_type=m.file_type,
                is_published=m.is_published,
                download_count=m.download_count,
                created_at=m.created_at,
                class_id=m.class_id,
                class_name=m.class_model.name if m.class_model else "Class",
                division_id=m.division_id,
                division_name=m.division.name if m.division else "All Divisions",
                subject_id=m.subject_id,
                subject_name=m.subject.name if m.subject else "Subject",
                subject_code=m.subject.code if m.subject else "",
                faculty_id=m.faculty_id,
                faculty_name=m.faculty.user.full_name if m.faculty else "Faculty"
            )
        )
    return results


@router.get("/{id}/download")
def download_study_material(
    id: str,
    student_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Secure streaming download of educational document with authorization check."""
    material = db.query(StudyMaterial).filter(StudyMaterial.id == id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Study material not found")

    # Cross-tenant check
    if material.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Cross-institution document access forbidden")

    # Authorization verification:
    if current_user.student_profile:
        if not material.is_published:
            raise HTTPException(status_code=403, detail="Document is in draft mode and not published")
        enr = db.query(Enrollment).filter(Enrollment.student_id == current_user.student_profile.id).first()
        if not enr or enr.class_id != material.class_id:
            raise HTTPException(status_code=403, detail="You are not enrolled in the class for this document")
    elif current_user.guardian_profile:
        if not material.is_published:
            raise HTTPException(status_code=403, detail="Document is in draft mode and not published")
        # Validate parent access to at least one child in the enrolled class
        links = (
            db.query(StudentGuardianLink)
            .filter(StudentGuardianLink.guardian_id == current_user.guardian_profile.id, StudentGuardianLink.is_verified == True)
            .all()
        )
        child_ids = [l.student_id for l in links]
        authorized = (
            db.query(Enrollment)
            .filter(Enrollment.student_id.in_(child_ids), Enrollment.class_id == material.class_id)
            .first()
        )
        if not authorized:
            raise HTTPException(status_code=403, detail="Your linked children are not enrolled in the class for this document")

    if not os.path.exists(material.file_path):
        raise HTTPException(status_code=404, detail="Physical file resource not found on server")

    # Increment download counter atomically
    material.download_count += 1
    db.commit()

    return FileResponse(
        path=material.file_path,
        filename=material.file_name,
        media_type=material.file_type or "application/octet-stream"
    )


@router.put("/{id}", response_model=StudyMaterialResponse)
def update_study_material(
    id: str,
    update: StudyMaterialUpdate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY")),
    db: Session = Depends(get_db)
):
    """[FACULTY | PRINCIPAL] Edit metadata or publication status of study material."""
    material = db.query(StudyMaterial).filter(StudyMaterial.id == id, StudyMaterial.institution_id == current_user.institution_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Study material not found")

    # Faculty can only edit materials they uploaded
    if current_user.faculty_profile and material.faculty_id != current_user.faculty_profile.id:
        raise HTTPException(status_code=403, detail="You can only modify materials you uploaded")

    for field, val in update.model_dump(exclude_unset=True).items():
        setattr(material, field, val)

    db.commit()
    db.refresh(material)

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
        class_name=material.class_model.name if material.class_model else "Class",
        division_id=material.division_id,
        division_name=material.division.name if material.division else "All Divisions",
        subject_id=material.subject_id,
        subject_name=material.subject.name if material.subject else "Subject",
        subject_code=material.subject.code if material.subject else "",
        faculty_id=material.faculty_id,
        faculty_name=material.faculty.user.full_name
    )


@router.delete("/{id}")
def delete_study_material(
    id: str,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "PRINCIPAL", "FACULTY")),
    db: Session = Depends(get_db)
):
    """[FACULTY | PRINCIPAL] Delete study material record and file."""
    material = db.query(StudyMaterial).filter(StudyMaterial.id == id, StudyMaterial.institution_id == current_user.institution_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Study material not found")

    if current_user.faculty_profile and material.faculty_id != current_user.faculty_profile.id:
        raise HTTPException(status_code=403, detail="You can only delete materials you uploaded")

    # Remove physical file if exists
    if os.path.exists(material.file_path):
        try:
            os.remove(material.file_path)
        except OSError:
            pass

    db.delete(material)
    db.commit()
    return {"message": "Study material deleted successfully"}
