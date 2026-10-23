# PHILOMATRIX SOFTWARE — ROLE & PERMISSION MATRIX
**Document Version:** 1.0.0  

---

## 1. USER ROLES OVERVIEW

PHILOMATRIX defines 6 distinct roles:
1. **SUPER_ADMIN (Platform SaaS Super Administrator):** Operates at the multi-tenant platform tier.
2. **PRINCIPAL (Institution Admin / Principal):** Complete administrative authority within their single institution.
3. **FACULTY (Lecturer / Subject Teacher / Class Teacher):** Academic delivery, lecture attendance, marks entry, and assignments.
4. **STUDENT (Enrolled Junior College Student):** Personal attendance, timetables, published marks, assignments, and feedback.
5. **PARENT (Verified Parent / Guardian):** Multi-child switching, attendance oversight, report cards, and notices for linked children.
6. **OFFICE_STAFF (Academic & Admissions Clerk):** Student admissions, document verification, enrollment management, and non-grading clerical operations.

---

## 2. GRANULAR ROLE-PERMISSION MATRIX

| Module / Domain | Specific Permission | SUPER_ADMIN | PRINCIPAL | FACULTY | STUDENT | PARENT | OFFICE_STAFF |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tenants** | `institutions:create` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| | `institutions:manage` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| | `institutions:view_status` | ✅ | ✅ (Own) | ❌ | ❌ | ❌ | ❌ |
| **Settings & Branding** | `settings:branding_update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | `academic_year:manage` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Classes & Subjects** | `classes:manage` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | `subjects:manage` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | `faculty:assign_subject` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Faculty Management** | `faculty:crud` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | `faculty:view_profiles` | ❌ | ✅ | ✅ (Peers) | ❌ | ❌ | ✅ |
| **Student Management** | `students:admit_enroll` | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| | `students:edit_profile` | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| | `students:view_all` | ❌ | ✅ | ✅ (Assigned) | ❌ | ❌ | ✅ |
| | `students:view_own` | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| | `students:link_guardian` | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Timetable** | `timetable:create_update` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | `timetable:view_institution` | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| | `timetable:view_assigned` | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| | `timetable:view_enrolled` | ❌ | ❌ | ❌ | ✅ | ✅ (Linked) | ❌ |
| **Lecture Attendance** | `attendance:mark_lecture` | ❌ | ✅ (Override) | ✅ (Assigned) | ❌ | ❌ | ❌ |
| | `attendance:view_summary` | ❌ | ✅ (All) | ✅ (Assigned) | ✅ (Own) | ✅ (Linked) | ✅ |
| | `attendance:request_correction`| ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| | `attendance:approve_correction`| ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Examinations & Marks**| `exam:create_schedule` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | `marks:enter_draft` | ❌ | ❌ | ✅ (Assigned) | ❌ | ❌ | ❌ |
| | `marks:submit_for_review` | ❌ | ❌ | ✅ (Assigned) | ❌ | ❌ | ❌ |
| | `marks:review_approve_reject` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | `marks:publish_results` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | `marks:view_published` | ❌ | ✅ | ✅ | ✅ (Own) | ✅ (Linked) | ❌ |
| **Report Cards** | `report_card:generate_pdf`| ❌ | ✅ | ✅ (View) | ✅ (Own) | ✅ (Linked) | ❌ |
| | `report_card:batch_publish` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Assignments** | `assignment:create_edit` | ❌ | ✅ | ✅ (Assigned) | ❌ | ❌ | ❌ |
| | `assignment:submit` | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| | `assignment:grade_review` | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Notices & Events** | `notices:publish_all` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | `notices:publish_class` | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| | `notices:view_relevant` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Feedback Management** | `feedback:create_form` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | `feedback:submit_response` | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| | `feedback:view_aggregated`| ❌ | ✅ | ✅ (Assigned) | ❌ | ❌ | ❌ |
| **Audit Logs** | `audit:view_system_logs` | ✅ (Platform) | ❌ | ❌ | ❌ | ❌ | ❌ |
| | `audit:view_institution` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## 3. STRICT BOUNDARY RULES
1. **Cross-Tenant Lockdown:** Users belonging to Institution A cannot read, query, or execute mutations on Institution B under any circumstances.
2. **Student Privacy Shield:** Students can NEVER see marks, attendance, or personal contact records of another student.
3. **Parent Verification Barrier:** Parents can only access records for children explicitly linked via verified `student_guardian_links`.
4. **Faculty Authority Limit:** Faculty can only mark attendance and enter marks for subjects and lecture slots assigned to them.
5. **Principal Gatekeeper:** Result publication and attendance retro-corrections are strictly locked behind Principal sign-off with recorded rationale.
