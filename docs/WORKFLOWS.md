# PHILOMATRIX SOFTWARE — MASTER OPERATIONAL WORKFLOWS
**Document Version:** 1.0.0  

---

## 1. LECTURE-WISE ATTENDANCE WORKFLOW

```mermaid
sequenceDiagram
    autonumber
    actor F as Faculty Member
    participant S as PHILOMATRIX System
    participant DB as Database
    actor P as Principal
    actor ST as Student / Parent

    F->>S: Log in & Open Attendance Dashboard
    S->>DB: Fetch today's assigned timetable slots for Faculty
    DB-->>S: Return slots (e.g., 09:00 AM, Class 11-A, Physics Theory)
    F->>S: Select active slot & load student roster
    S->>DB: Query enrolled students for Class 11-A
    DB-->>S: Return student roster
    F->>S: Mark status (Present, Absent, Late, Excused)
    F->>S: Review & Submit Attendance Session
    S->>S: Validate authorization (Faculty matches timetable assignment)
    S->>DB: Insert `attendance_session` (status: COMPLETED) & `attendance_records` in a single transaction
    S->>DB: Recalculate student overall & subject attendance percentages
    S-->>ST: Immediate visibility in Student/Parent portal
    
    opt Correction Workflow
        F->>S: Request Correction (e.g. Student marked Absent was Excused)
        F->>S: Provide mandatory explanation & desired correction
        S->>DB: Create `attendance_correction_requests` (status: PENDING)
        S->>P: Notify Principal of pending correction
        P->>S: Review correction request & reason
        alt Principal Approves
            P->>S: Approve correction
            S->>DB: Update `attendance_records`
            S->>DB: Update request status to APPROVED
            S->>DB: Record action in `audit_logs`
            S-->>ST: Updated attendance reflects in portal
        else Principal Rejects
            P->>S: Reject correction with explanation
            S->>DB: Update request status to REJECTED
            S->>DB: Record action in `audit_logs`
        end
    end
```

### Attendance Formula & Computation Standard
$$\text{Attendance Percentage} = \left(\frac{\text{Attended Eligible Lectures}}{\text{Total Conducted Eligible Lectures}}\right) \times 100$$
- **Present:** Counts as 1 conducted, 1 attended.
- **Late:** Configurable per institution (default: counts as Present with late flag).
- **Excused (Authorized Medical/Sports Leave):** Deducted from total conducted denominator or counted as attended per institution policy (default: neutral/deducted from required pool so student percentage is not penalized).
- **Absent:** Counts as 1 conducted, 0 attended.
- **Unconducted / Pending Sessions:** NEVER counted as absence.

---

## 2. EXAMINATION, MARKS ENTRY & MODERATION WORKFLOW

```mermaid
sequenceDiagram
    autonumber
    actor P as Principal / Exam Admin
    actor F as Faculty Member
    participant S as PHILOMATRIX System
    participant DB as Database
    actor ST as Student / Parent

    P->>S: Create Exam Schedule (e.g., "Term 1 Examination 2026-27")
    P->>S: Define Exam Subjects, Max Theory/Practical Marks, Min Passing Marks
    S->>DB: Save `examinations` & `exam_subjects`
    
    F->>S: Navigate to Marks Entry
    S->>DB: Verify Faculty assignment for subject & division
    F->>S: Input student marks (Theory & Practical) or flag Absent/Exempt
    F->>S: Save as DRAFT (allows iterative saves during grading)
    S->>DB: Save `marks_entries` (is_draft = true)
    
    F->>S: Finalize & Submit for Review
    S->>S: Validate bounds (0 <= marks <= max_marks)
    S->>DB: Update `marks_entries` (status = SUBMITTED)
    S->>DB: Create `marks_approvals` record (status = PENDING)
    
    P->>S: Review Submitted Marks Dashboard
    alt Approve Marks
        P->>S: Approve Marks Batch
        S->>DB: Update `marks_approvals` (status = APPROVED)
        P->>S: Click "PUBLISH RESULTS" for the Examination
        S->>DB: Create `result_publications` entry with timestamp & author
        S->>DB: Write to `audit_logs`
        S-->>ST: Results unlocked in Student & Parent Portals
    else Reject / Return for Correction
        P->>S: Reject Marks Batch with specific review remarks
        S->>DB: Update `marks_approvals` (status = REJECTED)
        S->>F: Notify Faculty to revise marks
    end
```

---

## 3. REPORT CARD GENERATION & PUBLICATION

1. **Prerequisite Check:** Verification that all exam subjects for the selected class/division have `result_publications` in `PUBLISHED` status.
2. **Data Aggregation:**
   - Student demographic details (Admission No, Name, Roll No, Class, Division).
   - Subject-wise scores: Theory Marks Obtained / Max, Practical Marks Obtained / Max, Subject Total, Grade.
   - Aggregate Score: Grand Total, Maximum Possible, Overall Percentage, Overall Class Rank (optional), Final Result (Distinction, First Class, Pass, Needs Support).
   - Term Attendance Summary: Total Conducted vs. Attended, Attendance %.
   - Class Teacher & Principal Remarks.
3. **Template & PDF Render:** Render clean, printable layout with official Junior College header, watermark, signature blocks, and QR verification hash.
4. **Distribution:** Accessible directly inside Student & Parent Portals, with one-click print or PDF download.

---

## 4. ACADEMIC YEAR ROLLOVER & STUDENT PROMOTION

1. **Archival:** The previous academic year (e.g., 2025-2026) is marked as `ARCHIVED`. All historical timetable, attendance, marks, and report card records remain permanently immutable.
2. **Promotion Execution:**
   - Eligible Class 11 Science students are promoted to Class 12 Science in the new Academic Year (e.g., 2026-2027).
   - Students repeating a class are re-enrolled into Class 11.
   - Class 12 graduating students are transitioned to `GRADUATED` status.
3. **New Timetable & Allocation:** Subject assignments and timetables are initialized for the new active academic year without affecting historical records.
