# PHILOMATRIX SOFTWARE — RESTful API CONTRACT SPECIFICATION
**Version:** 1.0.0  
**Base URL:** `/api/v1`  
**Data Format:** JSON (`application/json`)  
**Security:** Bearer JWT Access Token (`Authorization: Bearer <token>`) + HTTP-Only Refresh Cookie  

---

## 1. STANDARD RESPONSE & ERROR ENVELOPE

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Paginated Response
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 142,
    "total_pages": 8
  }
}
```

### Standard Error Response
```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "You are not authorized to mark attendance for this lecture slot",
    "details": []
  }
}
```

---

## 2. API ENDPOINTS BY DOMAIN

### 2.1 Authentication & Profile (`/api/v1/auth`)
- `POST /api/v1/auth/login` — Authenticate user with username/email & password. Returns JWT access token, user profile, roles, and sets secure refresh token.
- `POST /api/v1/auth/refresh` — Issue new short-lived access token using active refresh token.
- `POST /api/v1/auth/logout` — Revoke active refresh token and invalidate session.
- `GET /api/v1/auth/me` — Return current authenticated user profile, permissions, institution context, and assigned student/guardian links.
- `PUT /api/v1/auth/password` — Change password requiring current password verification.

### 2.2 Institutions & Platform (`/api/v1/institutions`)
- `GET /api/v1/institutions` — [SUPER_ADMIN] List all institutions with status, student/faculty counts, and operational health.
- `POST /api/v1/institutions` — [SUPER_ADMIN] Provision a new institution tenant with default settings.
- `GET /api/v1/institutions/{id}` — [SUPER_ADMIN | PRINCIPAL (own)] Get institution profile and branding details.
- `PUT /api/v1/institutions/{id}` — [SUPER_ADMIN | PRINCIPAL (own)] Update institution branding, contact details, and settings.
- `PUT /api/v1/institutions/{id}/status` — [SUPER_ADMIN] Activate, suspend, or deactivate an institution.

### 2.3 Academic Structure (`/api/v1/academics`)
- `GET /api/v1/academics/years` — List academic years for the current institution.
- `POST /api/v1/academics/years` — [PRINCIPAL] Create academic year (e.g., "2026-2027").
- `PUT /api/v1/academics/years/{id}/set-current` — [PRINCIPAL] Set active academic year.
- `GET /api/v1/academics/classes` — List classes (Class 11, Class 12) with divisions.
- `POST /api/v1/academics/classes` — [PRINCIPAL] Create class.
- `POST /api/v1/academics/divisions` — [PRINCIPAL] Add division to a class (e.g., "11-A").
- `GET /api/v1/academics/subjects` — List subjects offered (Physics, Chemistry, Maths, Bio, English, CS).
- `POST /api/v1/academics/subjects` — [PRINCIPAL] Add or update subject with theory/practical max marks and code.

### 2.4 Faculty & Teaching Assignments (`/api/v1/faculty`)
- `GET /api/v1/faculty` — [PRINCIPAL | STAFF] List faculty members with departments and workloads.
- `POST /api/v1/faculty` — [PRINCIPAL] Create faculty profile and login credentials.
- `GET /api/v1/faculty/assignments` — List subject-division assignments.
- `POST /api/v1/faculty/assignments` — [PRINCIPAL] Assign faculty to subject & division (and optional class teacher tag).
- `GET /api/v1/faculty/my-workload` — [FACULTY] Fetch logged-in teacher's classes, divisions, subjects, and timetable slots.

### 2.5 Students, Guardians & Enrollments (`/api/v1/students`)
- `GET /api/v1/students` — [PRINCIPAL | STAFF | FACULTY] Search, filter, and paginate enrolled students.
- `POST /api/v1/students` — [PRINCIPAL | STAFF] Admit new student with personal, academic, and guardian records.
- `GET /api/v1/students/{id}` — Get student detailed profile (scoped: Principal, Staff, Assigned Faculty, Student own, Parent linked).
- `PUT /api/v1/students/{id}` — [PRINCIPAL | STAFF] Update student demographics and enrollment.
- `POST /api/v1/students/{id}/guardians` — [PRINCIPAL | STAFF] Link verified guardian to student.
- `GET /api/v1/students/my-profile` — [STUDENT] Fetch self profile.
- `GET /api/v1/guardians/my-children` — [PARENT] Fetch list of linked children with enrollment status for quick switcher.

### 2.6 Timetable (`/api/v1/timetable`)
- `GET /api/v1/timetable` — Query timetable by division, faculty, or student ID.
- `POST /api/v1/timetable/entries` — [PRINCIPAL] Create timetable entry with automatic conflict validation.
- `PUT /api/v1/timetable/entries/{id}` — [PRINCIPAL] Update period slot.
- `DELETE /api/v1/timetable/entries/{id}` — [PRINCIPAL] Remove period slot.
- `GET /api/v1/timetable/conflicts/check` — Verify whether a proposed slot clashes with faculty, room, or division.

### 2.7 Lecture Attendance & Corrections (`/api/v1/attendance`)
- `GET /api/v1/attendance/today-slots` — [FACULTY] Get today's timetable periods assigned to faculty with completion status.
- `GET /api/v1/attendance/roster` — Fetch student roster for a specific division and date.
- `POST /api/v1/attendance/submit` — [FACULTY] Submit attendance session and records in an atomic transaction.
- `GET /api/v1/attendance/summary/student/{student_id}` — Get subject-wise and overall lecture attendance metrics for a student.
- `GET /api/v1/attendance/summary/institution` — [PRINCIPAL] Institution-wide daily attendance completion and at-risk students (< 75%).
- `POST /api/v1/attendance/corrections` — [FACULTY] Submit attendance correction request with mandatory reason.
- `GET /api/v1/attendance/corrections` — [PRINCIPAL] List pending attendance correction requests.
- `PUT /api/v1/attendance/corrections/{id}/review` — [PRINCIPAL] Approve or reject correction request with audit log.

### 2.8 Examinations, Marks & Moderation (`/api/v1/examinations`, `/api/v1/marks`)
- `GET /api/v1/examinations` — List examinations for active academic year.
- `POST /api/v1/examinations` — [PRINCIPAL] Create new exam (Unit Test 1, Term 1, Prelim) with dates and subjects.
- `GET /api/v1/examinations/{id}/subjects` — List subjects, max theory/practical marks, and exam dates.
- `GET /api/v1/marks/roster` — [FACULTY] Get student roster with existing marks entries for assigned exam subject & division.
- `POST /api/v1/marks/save-draft` — [FACULTY] Save marks entries in DRAFT mode.
- `POST /api/v1/marks/submit` — [FACULTY] Submit finalized marks batch for Principal approval.
- `GET /api/v1/marks/approvals/pending` — [PRINCIPAL] List marks submissions pending review.
- `PUT /api/v1/marks/approvals/{id}/review` — [PRINCIPAL] Approve or reject marks batch with review feedback.
- `POST /api/v1/examinations/{id}/publish` — [PRINCIPAL] Formally publish exam results to students and parents.
- `GET /api/v1/marks/student/{student_id}` — View approved and published marks for a student.

### 2.9 Report Cards & Analytics (`/api/v1/reports`)
- `GET /api/v1/reports/report-card/{examination_id}/student/{student_id}` — Generate dynamic report card data payload.
- `GET /api/v1/reports/report-card/{examination_id}/student/{student_id}/pdf` — Stream rendered official PDF report card.
- `GET /api/v1/reports/analytics/class-performance` — [PRINCIPAL] Subject-wise averages, pass percentages, toppers, and at-risk students.

### 2.10 Assignments & Homework (`/api/v1/assignments`)
- `GET /api/v1/assignments` — List assignments (filtered by division, subject, or student).
- `POST /api/v1/assignments` — [FACULTY] Create assignment with instructions, due date, and attachments.
- `POST /api/v1/assignments/{id}/submit` — [STUDENT] Submit assignment solution/text/attachment.
- `GET /api/v1/assignments/{id}/submissions` — [FACULTY] View student submissions and enter feedback/grades.

### 2.11 Notices & Bulletins (`/api/v1/notices`)
- `GET /api/v1/notices` — Fetch notices scoped to current user role and enrolled division.
- `POST /api/v1/notices` — [PRINCIPAL | FACULTY] Post notice with priority, audience filter, and attachments.

### 2.12 Feedback (`/api/v1/feedback`)
- `GET /api/v1/feedback/forms` — List active feedback forms available to current role.
- `POST /api/v1/feedback/forms` — [PRINCIPAL] Create feedback form with questions (Likert scale / text).
- `POST /api/v1/feedback/forms/{id}/respond` — [STUDENT | PARENT] Submit feedback response (anonymized where configured).
- `GET /api/v1/feedback/forms/{id}/analytics` — [PRINCIPAL] Aggregated rating distributions and sentiment summaries.

### 2.13 Notifications & Audit Logs (`/api/v1/notifications`, `/api/v1/audit`)
- `GET /api/v1/notifications` — Fetch user's in-app notifications with read/unread status.
- `PUT /api/v1/notifications/{id}/read` — Mark notification as read.
- `GET /api/v1/audit/logs` — [SUPER_ADMIN | PRINCIPAL] Query filterable audit log of all system changes.
