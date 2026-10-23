# PHILOMATRIX SOFTWARE
## Master Junior College ERP Platform — Version 1.0 (Class 11 & 12 Science)

**PHILOMATRIX SOFTWARE** is a multi-tenant, enterprise-grade Educational Resource Planning (ERP) SaaS platform for schools, junior colleges, degree colleges, engineering colleges, and other education providers. Academic units, categories, and terminology are configurable per institution instead of being restricted to a particular education type.

---

## 1. KEY SYSTEM CAPABILITIES

- **Multi-Tenant SaaS Architecture:** Logical row-level tenant isolation by `institution_id` on all models and queries.
- **6 Role-Based Portals:**
  1. **SaaS Super Administrator:** Platform tenant provisioning, lifecycle control, and system health.
  2. **Institution Admin / Principal:** Full operational oversight, approvals, timetable configuration, marks moderation, and report card publishing.
  3. **Faculty / Lecturer:** Period-wise lecture attendance, marks entry (Draft & Submit), and homework assignments.
  4. **Student:** Personal timetable, lecture attendance percentage, published examination marks, and official report cards.
  5. **Parent / Guardian:** Multi-child switcher, real-time attendance alerts (< 75% threshold), and certified report cards.
  6. **Office / Admissions Staff:** Admissions, student directory, and guardian relationship verification.
- **Conflict-Aware Timetable Engine:** Real-time overlap prevention for faculty, student divisions, and physical lecture halls.
- **Lecture-Wise Attendance System:** Instant calculation of $\frac{\text{Attended Eligible Lectures}}{\text{Total Conducted Lectures}} \times 100$ with late and excused leave policies.
- **Marks Moderation & Result Publication:** Faculty draft/submit workflows, Principal review/approval/rejection, and immutable publication locks.
- **Printable Official Report Cards:** Dynamic ReportLab PDF streaming with institution branding, theory + practical breakdown, attendance rollups, and signature blocks.
- **Security & Audit Governance:** Non-destructive audit trail recording all sensitive modifications with actor, timestamp, IP, and state diffs.

---

## 2. TECHNOLOGY STACK

- **Frontend:** React 18, TypeScript (Strict Mode), Vite, Tailwind CSS, TanStack Query, React Router, Lucide Icons, Vitest.
- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 ORM, Alembic Migrations, ReportLab (PDF), Pytest.
- **Database:** PostgreSQL (with SQLite compatibility for zero-setup local dev/test execution).
- **Security:** Argon2id / bcrypt password hashing, Short-lived JWT Access Tokens, HTTP-only Refresh Tokens, Server-Side RBAC.

---

## 3. LOCAL DEVELOPMENT QUICKSTART

### Tenant database model

The control database stores platform records and the institute directory. When a Super Admin provisions a new institute from **Institute Workspaces**, PHILOMATRIX creates an isolated SQLite database under `backend/tenant_data/` and bootstraps that institute's principal account and roles there. Login requires selecting an active institute first; all subsequent API requests carry the selected institute context and are routed to that tenant database. Existing legacy institutes continue to use the control database until their data is explicitly migrated.

Each institute can select its type (School, Junior College, Degree College, Engineering College, or Other) and configure neutral labels such as **Academic unit**, **Educator**, **Learner**, and **Head role** from Settings. Academic units accept any name or category, including `Class 5`, `Class 11 Science`, `Computer Engineering`, `B.Sc. Physics`, or a custom course structure.

### Prerequisites
- Python 3.12+
- Node.js v18+ & npm

### Backend Setup
```bash
# 1. Navigate to backend
cd backend

# 2. Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 3. Apply database migrations
alembic upgrade head

# 4. Seed development data (test accounts, sample timetable, attendance & exams)
python -m app.seeds.seed_demo

# 5. Start backend API server (runs on http://localhost:8000)
uvicorn app.main:app --reload --port 8000
```
API Documentation is available at: `http://localhost:8000/docs`

### Frontend Setup
```bash
# 1. Navigate to frontend
cd frontend

# 2. Start Vite development server (runs on http://localhost:3000)
npm run dev
```
Open `http://localhost:3000` in your web browser.

---

## 4. LOCAL DEVELOPMENT TEST ACCOUNTS

The seed script creates realistic demo accounts for instant 1-click evaluation:

| Role | Username / Email | Password | Primary Capabilities Tested |
| :--- | :--- | :--- | :--- |
| **Principal** | `principal@royalscience.edu` | `Royal@Principal2026` | Institution KPIs, Marks Approvals, Timetable & Publications |
| **Faculty (Physics)** | `physics.prof@royalscience.edu` | `Faculty@Pass2026` | Period Attendance Entry, UT-1 Marks Entry Draft/Submit |
| **Student (Arjun)** | `arjun.sharma@royalscience.edu` | `Student@Pass2026` | Class 11 Science Timetable, Attendance % & Report Card |
| **Parent (Mr. Sharma)** | `parent.sharma@gmail.com` | `Parent@Pass2026` | Linked Child Switcher, Real-time Attendance & Marks |
| **Office Staff** | `admissions@royalscience.edu` | `Staff@Pass2026` | Student Admissions, Guardian Linking & Documents |
| **SaaS Super Admin** | `superadmin@philomatrix.local` | `Philomatrix@2026` | Multi-Tenant Management & Platform Health |
| **SaaS Super Admin (named login)** | `SuperAdmin` | `SuperAdmin@123` | Multi-Tenant Management & Platform Health |
| **Tenant B Principal** | `principal@apexcollege.edu` | `Apex@Principal2026` | Multi-Tenant Isolation Testing (Tenant B) |

---

## 5. AUTOMATED TESTING VERIFICATION

### Run Backend Unit & Integration Tests (11 Test Suites)
```bash
cd backend
.\.venv\Scripts\pytest.exe -v app/tests/
```
Output:
```
app/tests/test_e2e_scenarios.py::test_full_18_step_acceptance_workflow PASSED [  9%]
app/tests/test_erp_suite.py::test_health_check PASSED                    [ 18%]
app/tests/test_erp_suite.py::test_authentication_success_and_failure PASSED [ 27%]
app/tests/test_erp_suite.py::test_user_profile_me PASSED                 [ 36%]
app/tests/test_erp_suite.py::test_tenant_isolation_boundary PASSED       [ 45%]
app/tests/test_erp_suite.py::test_timetable_conflict_engine PASSED       [ 54%]
app/tests/test_erp_suite.py::test_attendance_marking_and_calculation PASSED [ 63%]
app/tests/test_erp_suite.py::test_unauthorized_attendance_prevention PASSED [ 72%]
app/tests/test_erp_suite.py::test_student_privacy_isolation PASSED       [ 81%]
app/tests/test_erp_suite.py::test_parent_child_switcher_and_isolation PASSED [ 90%]
app/tests/test_erp_suite.py::test_report_card_generation_and_pdf_stream PASSED [100%]
============================= 11 passed in 10.42s =============================
```

### Run Frontend Component Tests
```bash
cd frontend
npm test
```
Output:
```
✓ src/tests/App.test.tsx (2 tests)
Test Files  1 passed (1)
Tests  2 passed (2)
```

### Build Production Bundle
```bash
cd frontend
npm run build
```
Output:
```
✓ built in 3.43s
```

---

## 6. DOCKER & CONTAINERIZED DEPLOYMENT

```bash
cd docker
docker-compose up --build -d
```
Services deployed:
- `db`: PostgreSQL 15 on port 5432
- `backend`: FastAPI API on port 8000
- `frontend`: Nginx serving production React SPA on port 3000
