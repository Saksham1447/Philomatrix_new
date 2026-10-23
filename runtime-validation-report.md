# Runtime Validation Report

**Generated**: 2026-10-22T22:24:00+05:30
**Target**: `D:\RP\Projects\PHILOMATRIX\PHILOMATRIX`

## Summary

| Step | Status | Exit Code | Details |
|------|--------|-----------|---------|
| Database migration | PASS | 0 | `python -m alembic upgrade head` completed against SQLite |
| Backend tests | PASS | 0 | 23 tests passed in 42.34s |
| Frontend tests | PASS | 0 | 2 tests passed |
| Frontend build | PASS | 0 | TypeScript check and Vite production build completed |
| Backend startup | PASS | 0 | Uvicorn listening on `http://127.0.0.1:8000` |
| Frontend startup | PASS | 0 | Vite listening on `http://127.0.0.1:3000` |
| Runtime smoke checks | PASS | 0 | Health, OpenAPI, SPA root, and principal login verified |

**Overall**: PASS with environment notes below.

## Environment

- Docker: unavailable because the Docker daemon was not responding.
- Node.js: available (`v22.20.0`).
- Python: available (`3.13.5`).
- Database tier: SQLite fallback, as configured by `backend/.env`.
- Browser tier: not exercised with Playwright; the Vite SPA entry point was verified over HTTP.

## Issues and Constraints

1. `backend/.venv` is not portable: `pyvenv.cfg` references a Python installation under another user's profile (`C:\Users\saksh\...`) that does not exist in this environment. Validation used the available system Python after confirming the declared dependencies were installed.
2. Docker-backed PostgreSQL validation was not possible because the Docker daemon was unavailable. SQLite migrations and the full backend suite passed.
3. The backend emits one existing `PendingDeprecationWarning` from Starlette's multipart import; it does not affect the test result.

## Super-Admin Login Fix

The platform admin login was failing after authentication during `/api/v1/auth/me`.
The account uses the intentional local-only address `superadmin@philomatrix.local`,
which Pydantic's `EmailStr` rejects as a reserved domain. The profile response now
preserves the database string value, while login and all existing role checks remain
unchanged.

- Login: HTTP 200
- Profile: HTTP 200
- Role: `SUPER_ADMIN`

## Faculty Leave Requests

- Faculty can submit a request with a start date, end date, and reason.
- Faculty can view their own request history and statuses.
- Office staff can view institution-scoped requests and approve or reject pending requests with an optional comment.
- Overlapping pending or approved leave periods are rejected.
- API workflow tests cover submission, office review, persistence, and non-faculty authorization.

## Faculty Timetable Scheduling

- Faculty timetable cells now show `Free` when no lecture is assigned.
- Faculty can click a free cell, select one of their assigned class/subject combinations, optionally enter a room, and schedule the slot.
- Existing timetable entries remain read-only in the faculty view.
- Server-side faculty, division, subject, assignment, and conflict checks remain enforced.
- Frontend tests: 2 passed; production build passed.
- Full backend regression: 23 passed.

## Indian Time Format

- Added a shared `en-IN` time formatter with 12-hour output and AM/PM.
- Timetable headers, timetable cards, attendance slots, dashboard teaching cards, and audit timestamps now display Indian 12-hour time.
- Backend storage and request payloads remain unchanged in machine-friendly format.
- Frontend tests: 2 passed; production build passed.

## Timetable Period Slots

The faculty timetable now uses seven periods:

1. 9:00 AM - 10:00 AM
2. 10:00 AM - 11:00 AM
3. 11:10 AM - 12:10 PM
4. 12:10 PM - 1:10 PM
5. 1:50 PM - 2:50 PM
6. 2:50 PM - 3:50 PM
7. 4:00 PM - 5:00 PM

## Premium Responsive UI

- Refined the shared application shell with premium surfaces, gradients, shadows, focus states, typography, and spacing.
- Added responsive navigation: the sidebar becomes a horizontally scrollable navigation strip on small screens.
- Improved header behavior and mobile spacing.
- Updated the login experience with a glassmorphism surface and responsive controls.
- Mobile viewport smoke check: 390px wide with no horizontal overflow.
- Desktop viewport smoke check: 1440px wide with no horizontal overflow.
- Frontend tests: 2 passed; production build passed.

## Live-Time Faculty Attendance

- Faculty attendance roster access and submission are now enforced server-side against
  the assigned timetable entry.
- Attendance is available only when the requested date is the current date in
  `Asia/Kolkata` and the current wall-clock time is within the half-open scheduled
  interval `[start_time, end_time)`.
- Before and after the interval, the frontend displays the slot as outside live time
  and locks roster editing and save actions.
- Submitted sessions remain permanently locked; correction requests remain the
  supported post-submission workflow.
- Backend regression suite: 23 passed, including the live-window workflow with a
  controlled clock.
- Frontend tests: 2 passed; production build passed.
- Runtime smoke checks: backend `/api/health` HTTP 200 and frontend root HTTP 200.

## Faculty Registration and Office Approval

- Login now loads approved faculty members into a faculty shortcut dropdown.
- Public faculty registration collects institution, identity, employee, and
  qualification details without exposing passwords.
- New requests remain `PENDING` and cannot log in until office staff approves them.
- Office staff can approve or reject requests directly from the office dashboard.
- Approval creates the active user, `FACULTY` role assignment, and faculty profile.
- Verified end-to-end flow: registration `PENDING` -> office `APPROVED` ->
  new faculty login token issued successfully.
- Temporary verification accounts were removed after testing.
- Backend regression suite: 23 passed.
- Frontend tests: 2 passed; production build passed.

## Direct Office Faculty Creation

- Office staff now have a dedicated Faculty Management action on the dashboard.
- The action creates an active faculty user, `FACULTY` role assignment, and faculty
  profile using the existing validated faculty endpoint.
- Existing duplicate username, email, and employee-ID checks remain enforced.
- Verified end-to-end: office staff created a faculty account and the new faculty
  credentials successfully authenticated.
- Temporary verification account was removed after testing.
- Backend regression suite: 23 passed; frontend production build passed.

## Premium UI Refresh

- Reworked the shared visual foundation with a layered premium canvas, refined
  typography, glass surfaces, softer borders, elevated card shadows, responsive
  spacing, and consistent focus/hover motion.
- Updated the authenticated application shell, navbar, sidebar, dashboard
  surfaces, login experience, modal surfaces, and form controls without changing
  routes, API calls, permissions, or user workflows.
- Added responsive decorative backgrounds and improved mobile-safe navigation
  treatment.
- Frontend production build: passed.
- Frontend tests: 2 passed.
- Login page smoke check: HTTP 200.

## Login Surface Adjustment

- Removed the standalone Faculty Login Shortcut from the top of the login form.
- Removed the visible Register as New Faculty button and registration modal entry
  from the login surface.
- Added a compact chevron control to the Office Staff quick-login card; expanding
  it reveals approved faculty members and fills the selected faculty email into
  the normal login field.
- Authentication APIs and the office-side faculty registration workflows remain
  unchanged.
- Frontend build: passed; frontend tests: 2 passed.
