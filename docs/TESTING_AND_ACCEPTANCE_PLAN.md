# PHILOMATRIX SOFTWARE — TESTING & ACCEPTANCE PLAN
**Document Version:** 1.0.0  

---

## 1. TESTING STRATEGY OVERVIEW

Quality and reliability in educational records software require strict multi-tiered testing:
1. **Backend Unit & Integration Tests (Pytest + FastAPI TestClient + SQLite/PostgreSQL in-memory):**
   - Authentication, Password Hashing, Refresh Token Rotation.
   - Strict Tenant Isolation: Assert queries cannot access other institution data.
   - Role & Resource Authorization: Verify 403 Forbidden on unassigned faculty attendance or marks entry.
   - Attendance Calculation Engine: Verify formula: $\frac{\text{Attended}}{\text{Conducted}} \times 100$, late policy, excused policy.
   - Timetable Conflict Detection: Verify prevention of overlapping teacher, room, and division periods.
   - Marks Moderation & Publication: Assert draft saves, submission lock, approval requirement before publication.
   - Report Card Generation: Verify math calculations, grades, attendance rollup, and PDF structure.
2. **Frontend Component & Hook Tests (Vitest + React Testing Library):**
   - Form validation schemas (Zod).
   - Role-based routing and navigation rendering.
   - Attendance matrix component (batch toggle, status indicators).
   - Marks entry grid (min/max bound enforcement, draft saving feedback).
   - Child switcher for parents.
3. **End-to-End Scenario Verification (Automated Workflow Suite):**
   - Executes the 18 critical scenarios outlined in Section 23 of the Master Specification.

---

## 2. THE 18 MANDATORY ACCEPTANCE SCENARIOS

| # | Acceptance Scenario | Expected Result |
| :--- | :--- | :--- |
| **1** | Admin creates Institution and Academic Year | Institution is provisioned; Academic Year 2026-2027 marked active. |
| **2** | Admin creates Class 11 and Class 12 | Classes saved with display order and stream = Science. |
| **3** | Admin adds Divisions (A, B) and Subjects (Physics, Chemistry, Maths, Bio, English) | Hierarchy linked; subject max marks configured. |
| **4** | Admin creates Faculty accounts and assigns subjects to divisions | Faculty profiles generated with credentials; assignments stored. |
| **5** | Admin admits students and links verified guardians | Unique admission numbers generated; Parent-student links active. |
| **6** | Admin creates Timetable entries | Period slots created; conflict engine prevents overlaps. |
| **7** | Faculty marks attendance for assigned lecture | Session saved with status SUBMITTED; records created. |
| **8** | System calculates student attendance correctly | Student attendance percentage updates in real-time. |
| **9** | Unauthorized faculty cannot edit another faculty's attendance | System returns 403 Forbidden with security audit log. |
| **10** | Faculty enters and submits examination marks | Marks verified within bounds; approval status set to PENDING. |
| **11** | Principal reviews and approves marks batch | Marks approval status set to APPROVED; logged in audit. |
| **12** | Principal publishes examination results | Result publication record created; results unlocked for students/parents. |
| **13** | Student sees ONLY their own published results | Other student marks are inaccessible; unapproved exams hidden. |
| **14** | Parent sees only results for linked children | Child switcher toggles verified children; non-linked records blocked. |
| **15** | System generates correct Report Card (PDF & Data) | Subject marks, attendance %, grades, and remarks match source data. |
| **16** | Faculty requests attendance correction; Principal reviews | Request created with reason; Principal approval updates record and audit trail. |
| **17** | Audit logs record sensitive actions | Marks approval, attendance correction, and role grants recorded with actor, IP, timestamp. |
| **18** | Multi-institution data isolation is absolute | User from Institution A querying Institution B receives 403/404; no data leak. |

---

## 3. DEVELOPMENT TEST ACCOUNTS MATRIX

All development accounts are provisioned via our automated seed script (`backend/app/seeds/seed_demo.py`).

| Role | Username | Default Password | Institution Context | Primary Verification Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **SUPER_ADMIN** | `superadmin@philomatrix.local` | `Philomatrix@2026` | Platform / Global | Tenant provisioning, global audit, institution health |
| **PRINCIPAL** | `principal@royalscience.edu` | `Royal@Principal2026` | Royal JC of Science | Academic setup, approvals, timetable, result publishing |
| **FACULTY (Physics)** | `physics.prof@royalscience.edu`| `Faculty@Pass2026` | Royal JC of Science | Class 11-A Physics attendance, UT-1 marks entry |
| **FACULTY (Chemistry)**| `chem.prof@royalscience.edu` | `Faculty@Pass2026` | Royal JC of Science | Class 11-A Chemistry attendance, assignments |
| **OFFICE_STAFF** | `admissions@royalscience.edu` | `Staff@Pass2026` | Royal JC of Science | Student admission, guardian linking, document verification |
| **STUDENT (Arjun)** | `arjun.sharma@royalscience.edu`| `Student@Pass2026`| Royal JC of Science | Enrolled in Class 11-A; views attendance, marks, report card |
| **STUDENT (Priya)** | `priya.patel@royalscience.edu` | `Student@Pass2026`| Royal JC of Science | Enrolled in Class 11-A; views own records |
| **PARENT (Mr. Sharma)**| `parent.sharma@gmail.com` | `Parent@Pass2026` | Royal JC of Science | Linked to Arjun Sharma; verifies child switcher & alerts |
| **TENANT B PRINCIPAL** | `principal@apexcollege.edu` | `Apex@Principal2026`| Apex Science College | Multi-tenant isolation testing (Tenant B) |
