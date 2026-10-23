from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine, ensure_control_schema
import app.models  # ensure all models are registered
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

# Initialize database tables
Base.metadata.create_all(bind=engine)
ensure_control_schema()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-Institution Junior College ERP SaaS Platform — Version 1.0 (Indian Junior Colleges: Class 11 & 12 Science)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Domain Routers under /api/v1
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
    """System health and operational status check."""
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "target": "Junior College Science ERP (Class 11 & 12)"
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API v1.0",
        "documentation": "/docs"
    }
