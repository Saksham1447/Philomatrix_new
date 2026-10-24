"""Static Mongo collection schema, codecs, indexes, and FK metadata.

All collection and field names mirror the former SQL tables. References are
metadata only: MongoDB does not enforce foreign keys.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IndexSpec:
    fields: tuple[str, ...]
    unique: bool = False
    name: str = ""
    partial_filter: dict[str, Any] | None = None


@dataclass(frozen=True)
class ForeignKeySpec:
    field: str
    collection: str
    on_delete: str = "CASCADE"


@dataclass(frozen=True)
class CollectionSpec:
    name: str
    fields: dict[str, str] = field(default_factory=dict)
    nullable: frozenset[str] = frozenset()
    defaults: dict[str, Any] = field(default_factory=dict)
    indexes: tuple[IndexSpec, ...] = ()
    fks: tuple[ForeignKeySpec, ...] = ()


def _i(
    fields: str | tuple[str, ...],
    *,
    unique: bool = False,
    name: str = "",
    partial_filter: dict[str, Any] | None = None,
) -> IndexSpec:
    normalized = (fields,) if isinstance(fields, str) else fields
    if not name:
        name = "_".join(normalized) + ("_uniq" if unique else "_idx")
    return IndexSpec(normalized, unique, name, partial_filter)


def _fk(field: str, collection: str, on_delete: str = "CASCADE") -> ForeignKeySpec:
    return ForeignKeySpec(field, collection, on_delete)


def _spec(name: str, fields: dict[str, str] | None = None, *, nullable=(), defaults=None,
          indexes=(), fks=()) -> CollectionSpec:
    types = {"created_at": "dt", "updated_at": "dt"}
    if fields:
        types.update(fields)
    return CollectionSpec(name, types, frozenset(nullable), defaults or {}, tuple(indexes), tuple(fks))


# Registry is the sole source for persisted type conversion, defaults, indexes, and cascades.
COLLECTIONS: dict[str, CollectionSpec] = {
    "institutions": _spec("institutions", nullable=("address", "city", "state", "pincode", "phone", "email", "logo_url", "database_url"), defaults={"status": "ACTIVE", "institution_type": "OTHER"}, indexes=(_i("slug", unique=True), _i("code", unique=True))),
    "institution_settings": _spec("institution_settings", {"min_attendance_threshold": "dec", "allow_late_as_present": "bool", "enable_parent_sms_alerts": "bool"}, defaults={"min_attendance_threshold": 75.00, "allow_late_as_present": True, "enable_parent_sms_alerts": False, "report_card_template_id": "STANDARD_V1", "institution_type": "OTHER", "academic_unit_label": "Department / Class", "educator_label": "Faculty / Teacher", "learner_label": "Student", "head_role_label": "Head / Principal"}, indexes=(_i("institution_id", unique=True),), fks=(_fk("institution_id", "institutions"),)),
    "roles": _spec("roles", nullable=("description",), indexes=(_i("name", unique=True),)),
    "users": _spec("users", {"is_active": "bool", "is_verified": "bool", "last_login_at": "dt"}, nullable=("institution_id", "middle_name", "phone_number", "profile_photo_url", "last_login_at"), defaults={"is_active": True, "is_verified": True}, indexes=(_i("institution_id"), _i("username", unique=True), _i("email", unique=True)), fks=(_fk("institution_id", "institutions"),)),
    "user_role_assignments": _spec("user_role_assignments", indexes=(_i(("user_id", "role_id", "institution_id"), unique=True, name="uq_user_role_institution", partial_filter={"institution_id": {"$type": "string"}}),), fks=(_fk("user_id", "users"), _fk("role_id", "roles"), _fk("institution_id", "institutions"))),
    "refresh_token_records": _spec("refresh_token_records", {"expires_at": "dt", "is_revoked": "bool"}, defaults={"is_revoked": False}, indexes=(_i("token_hash", unique=True),), fks=(_fk("user_id", "users"),)),
    "user_preferences": _spec("user_preferences", {"notify_email": "bool", "notify_in_app": "bool"}, nullable=("default_division_id", "default_subject_id"), defaults={"dashboard_layout": "STANDARD", "attendance_table_density": "COMFORTABLE", "notify_email": True, "notify_in_app": True, "theme_mode": "LIGHT"}, indexes=(_i("user_id", unique=True),), fks=(_fk("user_id", "users"),)),
    "academic_years": _spec("academic_years", {"start_date": "date", "end_date": "date", "is_current": "bool", "is_archived": "bool"}, defaults={"is_current": False, "is_archived": False}, indexes=(_i("institution_id"), _i(("institution_id", "name"), unique=True, name="uq_academic_year_institution_name")), fks=(_fk("institution_id", "institutions"),)),
    "classes": _spec("classes", {"display_order": "int"}, defaults={"stream": "GENERAL", "display_order": 1}, indexes=(_i("institution_id"), _i(("institution_id", "name", "stream"), unique=True, name="uq_class_name_stream")), fks=(_fk("institution_id", "institutions"),)),
    "divisions": _spec("divisions", {"capacity": "int"}, nullable=("room_number",), defaults={"capacity": 60}, indexes=(_i("institution_id"), _i("class_id"), _i(("class_id", "name"), unique=True, name="uq_division_class_name")), fks=(_fk("institution_id", "institutions"), _fk("class_id", "classes"))),
    "subjects": _spec("subjects", {"has_practical": "bool", "max_theory_marks": "dec", "max_practical_marks": "dec", "min_pass_percentage": "dec"}, defaults={"stream": "GENERAL", "has_practical": True, "max_theory_marks": 70.00, "max_practical_marks": 30.00, "min_pass_percentage": 35.00}, indexes=(_i("institution_id"), _i(("institution_id", "code"), unique=True, name="uq_subject_code_institution")), fks=(_fk("institution_id", "institutions"),)),
    "faculty_profiles": _spec("faculty_profiles", {"joining_date": "date"}, nullable=("qualification", "joining_date", "gender"), defaults={"designation": "Lecturer", "department": "General"}, indexes=(_i("user_id", unique=True), _i("institution_id"), _i(("institution_id", "employee_id"), unique=True, name="uq_faculty_emp_id_institution")), fks=(_fk("user_id", "users"), _fk("institution_id", "institutions"))),
    "faculty_subject_assignments": _spec("faculty_subject_assignments", {"is_class_teacher": "bool"}, defaults={"is_class_teacher": False}, indexes=(_i("institution_id"), _i(("academic_year_id", "faculty_id", "subject_id", "division_id"), unique=True, name="uq_fac_sub_div_year")), fks=(_fk("institution_id", "institutions"), _fk("academic_year_id", "academic_years"), _fk("faculty_id", "faculty_profiles"), _fk("subject_id", "subjects"), _fk("division_id", "divisions"))),
    "students": _spec("students", {"date_of_birth": "date", "admission_date": "date"}, nullable=("roll_number", "blood_group", "address", "emergency_contact_name", "emergency_contact_phone"), defaults={"status": "ACTIVE"}, indexes=(_i("user_id", unique=True), _i("institution_id"), _i("admission_number"), _i(("institution_id", "admission_number"), unique=True, name="uq_student_adm_no_institution")), fks=(_fk("user_id", "users"), _fk("institution_id", "institutions"))),
    "guardians": _spec("guardians", nullable=("occupation", "alternative_phone"), indexes=(_i("user_id", unique=True), _i("institution_id")), fks=(_fk("user_id", "users"), _fk("institution_id", "institutions"))),
    "student_guardian_links": _spec("student_guardian_links", {"is_primary": "bool", "is_verified": "bool"}, defaults={"is_primary": True, "is_verified": True}, indexes=(_i("student_id"), _i("guardian_id"), _i(("student_id", "guardian_id"), unique=True, name="uq_student_guardian")), fks=(_fk("student_id", "students"), _fk("guardian_id", "guardians"))),
    "enrollments": _spec("enrollments", nullable=("roll_number",), defaults={"status": "ENROLLED"}, indexes=(_i("institution_id"), _i("student_id"), _i(("academic_year_id", "student_id"), unique=True, name="uq_enrollment_year_student")), fks=(_fk("institution_id", "institutions"), _fk("student_id", "students"), _fk("academic_year_id", "academic_years"), _fk("class_id", "classes"), _fk("division_id", "divisions"))),
    "timetable_versions": _spec("timetable_versions", {"version_number": "int", "is_active": "bool"}, defaults={"version_number": 1, "is_active": True}, indexes=(_i("institution_id"),), fks=(_fk("institution_id", "institutions"), _fk("academic_year_id", "academic_years"))),
    "timetable_entries": _spec("timetable_entries", {"day_of_week": "int", "period_number": "int", "start_time": "time", "end_time": "time", "is_practical_batch": "bool"}, nullable=("room_number", "batch_name"), defaults={"is_practical_batch": False}, indexes=(_i("institution_id"), _i(("timetable_version_id", "faculty_id", "day_of_week", "period_number"), unique=True, name="uq_tt_faculty_day_period"), _i(("timetable_version_id", "division_id", "day_of_week", "period_number"), unique=True, name="uq_tt_division_day_period")), fks=(_fk("timetable_version_id", "timetable_versions"), _fk("institution_id", "institutions"), _fk("division_id", "divisions"), _fk("subject_id", "subjects"), _fk("faculty_id", "faculty_profiles"))),
    "timetable_slots": _spec("timetable_slots", {"day_of_week": "int", "period_number": "int", "start_time": "time", "end_time": "time"}, nullable=("subject_id",), indexes=(_i("institution_id"), _i(("division_id", "day_of_week", "period_number"), unique=True, name="uq_slot_division_day_period", partial_filter={"division_id": {"$type": "string"}})), fks=(_fk("institution_id", "institutions"), _fk("division_id", "divisions"), _fk("subject_id", "subjects", "SET_NULL"))),
    "attendance_sessions": _spec("attendance_sessions", {"session_date": "date", "period_number": "int"}, nullable=("timetable_entry_id",), defaults={"submission_status": "SUBMITTED"}, indexes=(_i("institution_id"), _i("session_date"), _i(("division_id", "subject_id", "session_date", "period_number"), unique=True, name="uq_att_session_slot")), fks=(_fk("institution_id", "institutions"), _fk("academic_year_id", "academic_years"), _fk("timetable_entry_id", "timetable_entries", "SET_NULL"), _fk("division_id", "divisions"), _fk("subject_id", "subjects"), _fk("faculty_id", "faculty_profiles"))),
    "attendance_records": _spec("attendance_records", nullable=("remarks",), indexes=(_i("attendance_session_id"), _i("student_id"), _i(("attendance_session_id", "student_id"), unique=True, name="uq_att_session_student")), fks=(_fk("attendance_session_id", "attendance_sessions"), _fk("student_id", "students"))),
    "attendance_correction_requests": _spec("attendance_correction_requests", {"reviewed_at": "dt"}, nullable=("reviewed_by", "reviewed_at", "review_notes"), defaults={"status": "PENDING"}, indexes=(_i("institution_id"),), fks=(_fk("institution_id", "institutions"), _fk("attendance_record_id", "attendance_records"), _fk("requested_by", "users"), _fk("reviewed_by", "users", "SET_NULL"))),
    "examinations": _spec("examinations", {"start_date": "date", "end_date": "date"}, defaults={"status": "SCHEDULED"}, indexes=(_i("institution_id"),), fks=(_fk("institution_id", "institutions"), _fk("academic_year_id", "academic_years"))),
    "exam_subjects": _spec("exam_subjects", {"max_theory_marks": "dec", "max_practical_marks": "dec", "min_passing_marks": "dec", "exam_date": "date"}, nullable=("exam_date",), defaults={"max_theory_marks": 70.00, "max_practical_marks": 30.00, "min_passing_marks": 35.00}, indexes=(_i("examination_id"), _i(("examination_id", "subject_id", "class_id"), unique=True, name="uq_exam_subject_class")), fks=(_fk("examination_id", "examinations"), _fk("subject_id", "subjects"), _fk("class_id", "classes"))),
    "marks_entries": _spec("marks_entries", {"theory_marks_obtained": "dec", "practical_marks_obtained": "dec", "total_obtained": "dec", "is_absent": "bool", "is_exempt": "bool"}, nullable=("theory_marks_obtained", "practical_marks_obtained", "total_obtained", "entered_by", "teacher_remarks"), defaults={"is_absent": False, "is_exempt": False, "status": "DRAFT"}, indexes=(_i("exam_subject_id"), _i("student_id"), _i(("exam_subject_id", "student_id"), unique=True, name="uq_marks_exam_subject_student")), fks=(_fk("exam_subject_id", "exam_subjects"), _fk("student_id", "students"), _fk("division_id", "divisions"), _fk("entered_by", "users", "SET_NULL"))),
    "marks_approvals": _spec("marks_approvals", {"submitted_at": "dt", "reviewed_at": "dt"}, nullable=("reviewed_by", "reviewed_at", "review_comments"), defaults={"status": "PENDING"}, indexes=(_i("exam_subject_id"), _i("division_id"), _i(("exam_subject_id", "division_id"), unique=True, name="uq_marks_approval_subject_div")), fks=(_fk("exam_subject_id", "exam_subjects"), _fk("division_id", "divisions"), _fk("submitted_by", "users"), _fk("reviewed_by", "users", "SET_NULL"))),
    "result_publications": _spec("result_publications", {"published_at": "dt", "is_active": "bool"}, nullable=("published_by",), defaults={"is_active": True}, indexes=(_i("examination_id"), _i(("examination_id", "class_id"), unique=True, name="uq_result_publication_exam_class")), fks=(_fk("examination_id", "examinations"), _fk("class_id", "classes"), _fk("published_by", "users", "SET_NULL"))),
    "report_card_versions": _spec("report_card_versions", {"version": "int", "summary_data": "json"}, nullable=("generated_by",), defaults={"version": 1}, indexes=(_i("institution_id"), _i("student_id"), _i(("examination_id", "student_id", "version"), unique=True, name="uq_report_card_exam_student_ver")), fks=(_fk("institution_id", "institutions"), _fk("examination_id", "examinations"), _fk("student_id", "students"), _fk("generated_by", "users", "SET_NULL"))),
    "assignments": _spec("assignments", {"due_date": "dt"}, nullable=("description", "attachment_url"), indexes=(_i("institution_id"),), fks=(_fk("institution_id", "institutions"), _fk("division_id", "divisions"), _fk("subject_id", "subjects"), _fk("faculty_id", "faculty_profiles"))),
    "assignment_submissions": _spec("assignment_submissions", {"submitted_at": "dt", "is_late": "bool"}, nullable=("submission_text", "attachment_url", "grade_or_score", "feedback_remarks"), defaults={"is_late": False, "status": "SUBMITTED"}, indexes=(_i("assignment_id"), _i("student_id")), fks=(_fk("assignment_id", "assignments"), _fk("student_id", "students"))),
    "notices": _spec("notices", {"is_published": "bool", "expires_at": "date"}, nullable=("target_class_id", "target_division_id", "published_by", "expires_at"), defaults={"audience_role": "ALL", "priority": "NORMAL", "is_published": True}, indexes=(_i("institution_id"),), fks=(_fk("institution_id", "institutions"), _fk("target_class_id", "classes", "SET_NULL"), _fk("target_division_id", "divisions", "SET_NULL"), _fk("published_by", "users", "SET_NULL"))),
    "feedback_forms": _spec("feedback_forms", {"is_anonymous": "bool", "is_open": "bool", "start_date": "date", "end_date": "date"}, nullable=("start_date", "end_date"), defaults={"target_role": "STUDENT", "is_anonymous": True, "is_open": True}, indexes=(_i("institution_id"),), fks=(_fk("institution_id", "institutions"),)),
    "feedback_questions": _spec("feedback_questions", {"display_order": "int"}, defaults={"question_type": "RATING_1_5", "display_order": 1}, indexes=(_i("feedback_form_id"),), fks=(_fk("feedback_form_id", "feedback_forms"),)),
    "feedback_responses": _spec("feedback_responses", {"rating_value": "int"}, nullable=("respondent_user_id", "rating_value", "text_response"), indexes=(_i("feedback_form_id"),), fks=(_fk("feedback_form_id", "feedback_forms"), _fk("question_id", "feedback_questions"), _fk("respondent_user_id", "users", "SET_NULL"))),
    "notifications": _spec("notifications", {"is_read": "bool"}, nullable=("link_url",), defaults={"notification_type": "GENERAL", "is_read": False}, indexes=(_i("user_id"),), fks=(_fk("user_id", "users"),)),
    "audit_logs": _spec("audit_logs", {"previous_state": "json", "new_state": "json"}, nullable=("institution_id", "user_id", "previous_state", "new_state", "reason", "ip_address"), indexes=(_i("institution_id"), _i("user_id")), fks=(_fk("institution_id", "institutions"), _fk("user_id", "users", "SET_NULL"))),
    "study_materials": _spec("study_materials", {"file_size": "int", "is_published": "bool", "download_count": "int"}, nullable=("description", "topic", "division_id"), defaults={"is_published": True, "download_count": 0}, indexes=(_i("institution_id"), _i("faculty_id"), _i("class_id"), _i("division_id"), _i("subject_id")), fks=(_fk("institution_id", "institutions"), _fk("academic_year_id", "academic_years"), _fk("faculty_id", "faculty_profiles"), _fk("class_id", "classes"), _fk("division_id", "divisions"), _fk("subject_id", "subjects"))),
    "faculty_leave_requests": _spec("faculty_leave_requests", {"start_date": "date", "end_date": "date"}, nullable=("reviewed_by_id", "review_comments"), defaults={"status": "PENDING"}, indexes=(_i("institution_id"), _i("faculty_id"), _i("status")), fks=(_fk("institution_id", "institutions"), _fk("faculty_id", "faculty_profiles"), _fk("reviewed_by_id", "users", "SET_NULL"))),
    "faculty_registration_requests": _spec("faculty_registration_requests", nullable=("middle_name", "phone_number", "qualification", "reviewed_by_id", "review_comments"), defaults={"designation": "Lecturer", "department": "Science", "status": "PENDING"}, indexes=(_i("institution_id"), _i("status")), fks=(_fk("institution_id", "institutions"), _fk("reviewed_by_id", "users", "SET_NULL"))),
}


CASCADE_EDGES: tuple[tuple[str, str, str, str], ...] = tuple(
    (spec.name, foreign_key.field, foreign_key.collection, foreign_key.on_delete)
    for spec in COLLECTIONS.values()
    for foreign_key in spec.fks
)
