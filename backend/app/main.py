from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import ensure_indexes, get_control_store
from app.api.v1 import (
    auth,
    institutions,
    academics,
    faculty,
    students,
    timetable,
    attendance,
    examinations,
    reports,
    communication,
    study_materials,
    leave_requests,
    faculty_registrations,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-Institution Junior College ERP SaaS Platform ? Version 1.0 (Indian Junior Colleges: Class 11 & 12 Science)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def bootstrap_mongodb() -> None:
    """Prepare all control collections/indexes; actual Atlas connection is lazy until here."""
    ensure_indexes(get_control_store())


app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(institutions.router, prefix=settings.API_V1_STR)
app.include_router(academics.router, prefix=settings.API_V1_STR)
app.include_router(faculty.router, prefix=settings.API_V1_STR)
app.include_router(students.router, prefix=settings.API_V1_STR)
app.include_router(timetable.router, prefix=settings.API_V1_STR)
app.include_router(attendance.router, prefix=settings.API_V1_STR)
app.include_router(examinations.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(communication.router, prefix=settings.API_V1_STR)
app.include_router(study_materials.router, prefix=settings.API_V1_STR)
app.include_router(leave_requests.router, prefix=settings.API_V1_STR)
app.include_router(faculty_registrations.router, prefix=settings.API_V1_STR)


@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "target": "Junior College Science ERP (Class 11 & 12)",
    }


@app.get("/", tags=["Root"])
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API v1.0", "documentation": "/docs"}
