export type UserRole = 'SUPER_ADMIN' | 'PRINCIPAL' | 'FACULTY' | 'STUDENT' | 'PARENT' | 'OFFICE_STAFF';

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone_number?: string;
  institution_id?: string;
  institution_name?: string;
  roles: UserRole[];
  is_active: boolean;
  student_id?: string;
  faculty_id?: string;
  guardian_id?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface FacultyLeaveRequest {
  id: string;
  faculty_id: string;
  faculty_name: string;
  employee_id: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  reviewed_by_name?: string;
  review_comments?: string;
  created_at: string;
}

export interface Institution {
  id: string;
  name: string;
  code: string;
  slug: string;
  status: 'ACTIVE' | 'SUSPENDED' | 'DEACTIVATED';
  address?: string;
  city?: string;
  state?: string;
  pincode?: string;
  phone?: string;
  email?: string;
  logo_url?: string;
  database_url?: string;
  institution_type?: string;
}

export interface AcademicYear {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  is_archived: boolean;
}

export interface Division {
  id: string;
  class_id: string;
  name: string;
  room_number?: string;
  capacity: number;
}

export interface ClassModel {
  id: string;
  name: string;
  stream: string;
  display_order: number;
  divisions: Division[];
}

export interface Subject {
  id: string;
  code: string;
  name: string;
  stream: string;
  has_practical: boolean;
  max_theory_marks: number;
  max_practical_marks: number;
  min_pass_percentage: number;
}

export interface Student {
  id: string;
  user_id: string;
  admission_number: string;
  roll_number?: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  phone_number?: string;
  date_of_birth: string;
  gender: string;
  blood_group?: string;
  admission_date: string;
  address?: string;
  status: string;
  class_name?: string;
  division_name?: string;
  division_id?: string;
  academic_year_name?: string;
}

export interface TimetableEntry {
  id: string;
  division_id: string;
  division_name: string;
  class_name: string;
  subject_id: string;
  subject_name: string;
  subject_code: string;
  faculty_id: string;
  faculty_name: string;
  day_of_week: number;
  period_number: number;
  start_time: string;
  end_time: string;
  room_number?: string;
  is_practical_batch: boolean;
  batch_name?: string;
}

export interface AttendanceRecordItem {
  id?: string;
  sr_no?: number;
  student_id: string;
  student_name: string;
  admission_number: string;
  roll_number?: string;
  class_name?: string;
  division_name?: string;
  status: 'PRESENT' | 'ABSENT' | 'LATE' | 'EXCUSED' | 'UNMARKED';
  cumulative_attendance?: number;
  statutory_status?: 'ELIGIBLE' | 'SHORTAGE';
  remarks?: string;
}


export interface SubjectAttendanceStat {
  subject_id: string;
  subject_code: string;
  subject_name: string;
  total_conducted: number;
  total_attended: number;
  percentage: number;
}

export interface StudentAttendanceSummary {
  student_id: string;
  student_name: string;
  admission_number: string;
  class_name: string;
  division_name: string;
  total_conducted: number;
  total_attended: number;
  overall_percentage: number;
  is_below_threshold: boolean;
  subject_breakdown: SubjectAttendanceStat[];
}

export interface ExamSubject {
  id: string;
  subject_id: string;
  subject_name: string;
  subject_code: string;
  class_id: string;
  class_name: string;
  max_theory_marks: number;
  max_practical_marks: number;
  min_passing_marks: number;
  exam_date?: string;
}

export interface Examination {
  id: string;
  academic_year_id: string;
  name: string;
  exam_type: string;
  start_date: string;
  end_date: string;
  status: string;
  is_published: boolean;
  subjects: ExamSubject[];
}

export interface MarksEntry {
  id: string;
  student_id: string;
  student_name: string;
  admission_number: string;
  roll_number?: string;
  theory_marks_obtained?: number;
  practical_marks_obtained?: number;
  total_obtained?: number;
  is_absent: boolean;
  is_exempt: boolean;
  status: string;
  teacher_remarks?: string;
}

export interface MarksApprovalItem {
  id: string;
  exam_subject_id: string;
  examination_name: string;
  subject_name: string;
  subject_code: string;
  division_id: string;
  division_name: string;
  class_name: string;
  submitted_by_name: string;
  submitted_at: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  reviewed_by_name?: string;
  reviewed_at?: string;
  review_comments?: string;
}

export interface ReportCardSubjectScore {
  subject_code: string;
  subject_name: string;
  theory_max: number;
  theory_obtained?: number;
  practical_max: number;
  practical_obtained?: number;
  total_max: number;
  total_obtained?: number;
  percentage: number;
  grade: string;
  status: string;
}

export interface ReportCardData {
  institution_name: string;
  institution_address?: string;
  institution_code: string;
  institution_logo_url?: string;
  academic_year: string;
  examination_name: string;
  examination_type: string;
  student_name: string;
  admission_number: string;
  roll_number?: string;
  class_name: string;
  division_name: string;
  stream: string;
  attendance_percentage: number;
  total_conducted_lectures: number;
  total_attended_lectures: number;
  subjects: ReportCardSubjectScore[];
  grand_total_max: number;
  grand_total_obtained: number;
  overall_percentage: number;
  overall_grade: string;
  final_result: string;
  teacher_remarks?: string;
  principal_remarks?: string;
  published_date?: string;
}

export interface Assignment {
  id: string;
  division_id: string;
  division_name: string;
  class_name: string;
  subject_id: string;
  subject_name: string;
  faculty_name: string;
  title: string;
  description?: string;
  due_date: string;
  attachment_url?: string;
  created_at: string;
  is_submitted_by_student: boolean;
  submission_status?: string;
}

export interface Notice {
  id: string;
  title: string;
  content: string;
  audience_role: string;
  target_class_id?: string;
  target_division_id?: string;
  priority: 'LOW' | 'NORMAL' | 'URGENT';
  published_by_name?: string;
  created_at: string;
  expires_at?: string;
}

export interface AuditLog {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  user_name?: string;
  previous_state?: Record<string, any>;
  new_state?: Record<string, any>;
  reason?: string;
  ip_address?: string;
  created_at: string;
}
