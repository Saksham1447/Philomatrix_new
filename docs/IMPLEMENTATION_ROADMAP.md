# PHILOMATRIX SOFTWARE — MASTER IMPLEMENTATION ROADMAP
**Document Version:** 1.0.0  

---

## ROADMAP PHASES & MILESTONES

```
[Phase 0] Architecture & Specs (DONE)
   │
   ▼
[Phase 1] Foundation: Backend (FastAPI, SQLAlchemy 2.0, Alembic) & Frontend (React 19, Vite, Tailwind CSS)
   │
   ▼
[Phase 2] Authentication, RBAC & Multi-Tenancy Engine
   │
   ▼
[Phase 3] Academic Structure, Faculty Allocation & Student/Guardian Lifecycles
   │
   ▼
[Phase 4] Timetable Engine, Lecture-Wise Attendance & Approval Governance
   │
   ▼
[Phase 5] Examination Engine, Marks Moderation, Result Publication & Report Cards
   │
   ▼
[Phase 6] Assignments, Notices, Academic Feedback & In-App Notifications
   │
   ▼
[Phase 7] Full Role-Based Portals (Super Admin, Principal, Faculty, Student, Parent, Staff)
   │
   ▼
[Phase 8] Test Verification (18 Scenarios), Security Hardening, Audit Verification & Pilot Launch Package
```

### Phase Details & Execution Order

- **PHASE 0: Requirements, Architecture & Data Modeling (Completed)**
  - System architecture defined in `docs/ARCHITECTURE.md`.
  - Roles & Permissions codified in `docs/ROLE_PERMISSION_MATRIX.md`.
  - Operational workflows diagrammed in `docs/WORKFLOWS.md`.
  - Entity-relationship & schema models defined in `docs/DATABASE_DESIGN.md`.
  - RESTful API contracts established in `docs/API_CONTRACTS.md`.
  - Testing & Acceptance matrix drafted in `docs/TESTING_AND_ACCEPTANCE_PLAN.md`.

- **PHASE 1: Project Foundation & Environment Setup**
  - Project directory layout: `backend/`, `frontend/`, `docker/`, `docs/`.
  - Backend setup: FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, Pytest configuration.
  - Frontend setup: React 19 + TypeScript (strict mode), Vite, Tailwind CSS, Lucide icons, React Router, TanStack Query, Vitest configuration.
  - Docker Compose configuration for PostgreSQL and local services.
  - Environment configuration (`.env.example`).

- **PHASE 2: Authentication, Multi-Tenancy & User Management**
  - Tenant isolation middleware and database scoping.
  - Password hashing (Argon2id / bcrypt), short-lived JWT access tokens and secure refresh token handling.
  - Role-based authorization dependencies (`require_role`, `require_permission`).
  - Core tables: `institutions`, `institution_settings`, `users`, `roles`, `user_role_assignments`, `refresh_token_records`.
  - Automated Seed Script: Realistic demo institution ("Royal Junior College of Science"), Super Admin, Principal, Faculty, Student, Parent, and Staff test accounts.
  - Test suite for Auth & Multi-Tenant security.

- **PHASE 3: Academic Structure & Student Lifecycle**
  - Academic Years, Classes (11 & 12 Science), Divisions (A, B, C), Subjects (Physics, Chem, Math, Bio, CS, English).
  - Faculty profiles and subject-division-lecture teaching assignments.
  - Student admission, profile attributes, class-division enrollments, unique admission numbers.
  - Guardian profiles and verified student-guardian relationships.
  - Search, filtering, and enrollment management APIs and UI screens.

- **PHASE 4: Timetable Engine & Lecture-Wise Attendance**
  - Timetable versioning, day-period schedule matrix, and conflict detection (teacher, division, room).
  - Lecture attendance marking API and interactive matrix UI.
  - Real-time attendance computation: $(\text{Attended} / \text{Conducted}) \times 100$.
  - Attendance correction requests and Principal review/approval workflow with audit trail.
  - Daily, class-wise, subject-wise, and at-risk (< 75%) attendance analytics dashboards.

- **PHASE 5: Examination Engine, Marks Moderation & Report Cards**
  - Exam scheduling (Unit Tests, Terminals, Practicals, Prelims) with theory and practical limits.
  - Marks entry screen for assigned faculty with DRAFT save and SUBMIT validations.
  - Principal review, approval, and rejection workflow.
  - Immutable result publication lock.
  - Official Report Card generator (subject-wise breakdown, totals, percentages, grades, attendance summary, remarks, and PDF print layout).

- **PHASE 6: Assignments, Communication & Feedback**
  - Homework & assignment creation, due date alerts, student submission status.
  - Scoped Notice Board (Institution, Class, Division, Role-targeted) with priority badges.
  - Academic Feedback module with rating scales, anonymous submission support, and aggregated sentiment reports.
  - In-app notification center.

- **PHASE 7: Comprehensive Role-Based Portals**
  - Super Admin Dashboard: Tenant metrics, institution provisioning, system health.
  - Principal Dashboard: Full institution KPIs, pending approvals, attendance alerts, exam publishing.
  - Faculty Dashboard: Today's lectures, pending attendance, marks entry, student roster.
  - Student Dashboard: Personal timetable, attendance percentage, published marks, assignments.
  - Parent Dashboard: Multi-child switcher, real-time absence tracking, report cards, notices.
  - Office Staff Portal: Admissions processing, student records, document verification.

- **PHASE 8: Hardening, Automated E2E Verification & Pilot Readiness**
  - Execute test suite validating all 18 mandatory acceptance scenarios.
  - Verify tenant isolation (cross-tenant leakage tests).
  - Run security and boundary checks.
  - Generate pilot launch runbook and seed data verification report.
