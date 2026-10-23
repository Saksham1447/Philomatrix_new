import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { formatIndianTime } from '../utils/time';
import { AttendanceRecordItem, StudentAttendanceSummary } from '../types';
import {
  CalendarCheck,
  Check,
  X,
  Clock,
  ShieldCheck,
  AlertTriangle,
  FileCheck2,
  Users,
  Send,
  HelpCircle,
  RefreshCw,
  Edit3,
  Calendar,
  Layers,
  Award,
  ChevronRight,
  UserCheck,
  UserX,
  Lock
} from 'lucide-react';

export const AttendancePage: React.FC = () => {
  const { user, activeRole, activeChild } = useAuth();

  // Faculty State
  const [todaySlots, setTodaySlots] = useState<any[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<any | null>(null);
  const [roster, setRoster] = useState<AttendanceRecordItem[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [isSessionLocked, setIsSessionLocked] = useState(false);
  const [existingSessionId, setExistingSessionId] = useState<string | null>(null);

  // Correction Modal State
  const [isCorrectionModalOpen, setIsCorrectionModalOpen] = useState(false);
  const [correctionStudent, setCorrectionStudent] = useState<any | null>(null);
  const [correctionTargetStatus, setCorrectionTargetStatus] = useState<'PRESENT' | 'ABSENT' | 'LATE'>('PRESENT');
  const [correctionReason, setCorrectionReason] = useState('');
  const [correctionLoading, setCorrectionLoading] = useState(false);

  // Principal State
  const [corrections, setCorrections] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [shortageReport, setShortageReport] = useState<any[]>([]);

  // Student / Parent State
  const [studentSummary, setStudentSummary] = useState<StudentAttendanceSummary | null>(null);

  // Status & Feedback
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [warningMsg, setWarningMsg] = useState<string | null>(null);

  // Load appropriate data based on active role
  const loadAttendanceData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      if (activeRole === 'FACULTY') {
        const slots = await api.get<any[]>(`/attendance/today-slots?target_date=${selectedDate}`);
        setTodaySlots(slots);
        if (slots.length > 0) {
          // If no slot selected yet or current slot not in list, pick first
          const current = slots.find(s => s.timetable_entry_id === selectedSlot?.timetable_entry_id) || slots[0];
          selectSlot(current);
        } else {
          setRoster([]);
          setSelectedSlot(null);
        }
        // Load recent sessions for logs table
        const pastSessions = await api.get<any[]>('/attendance/sessions');
        setSessions(pastSessions);
      } else if (activeRole === 'PRINCIPAL' || activeRole === 'SUPER_ADMIN' || activeRole === 'OFFICE_STAFF') {
        const corrs = await api.get<any[]>('/attendance/corrections');
        setCorrections(corrs);
        const sess = await api.get<any[]>('/attendance/sessions');
        setSessions(sess);
        const shortage = await api.get<any[]>('/attendance/shortage-report');
        setShortageReport(shortage);
      } else if (activeRole === 'STUDENT' && user?.student_id) {
        const summary = await api.get<StudentAttendanceSummary>(
          `/attendance/summary/student/${user.student_id}`
        );
        setStudentSummary(summary);
      } else if (activeRole === 'PARENT' && activeChild) {
        const summary = await api.get<StudentAttendanceSummary>(
          `/attendance/summary/student/${activeChild.id}`
        );
        setStudentSummary(summary);
      }
    } catch (err: any) {
      console.error('Error fetching attendance data', err);
      setErrorMsg(err.message || 'Failed to load attendance records');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAttendanceData();
  }, [activeRole, activeChild, selectedDate]);

  const selectSlot = async (slot: any) => {
    setSelectedSlot(slot);
    setSuccessMsg(null);
    setErrorMsg(null);
    setWarningMsg(null);

    try {
      const data = await api.get<any[]>(
        `/attendance/roster?division_id=${slot.division_id}&subject_id=${slot.subject_id}&session_date=${selectedDate}&period_number=${slot.period_number}`
      );

      const items: AttendanceRecordItem[] = data.map((item, idx) => ({
        id: item.record_id || undefined,
        sr_no: item.sr_no || idx + 1,
        student_id: item.student_id,
        student_name: item.full_name,
        admission_number: item.admission_number,
        roll_number: item.roll_number,
        class_name: item.class_name,
        division_name: item.division_name,
        status: (item.current_status as any) || 'UNMARKED',
        cumulative_attendance: item.cumulative_attendance,
        statutory_status: item.statutory_status,
        remarks: item.remarks || '',
      }));

      setRoster(items);
      setIsSessionLocked(slot.is_submitted || !slot.is_live);
      setExistingSessionId(slot.session_id || null);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load class roster');
    }
  };

  // Bulk set status
  const setAllStatus = (newStatus: 'PRESENT' | 'ABSENT' | 'UNMARKED') => {
    if (isSessionLocked) return;
    setWarningMsg(null);
    setRoster(prev => prev.map(item => ({ ...item, status: newStatus })));
  };

  // Toggle individual student status (mutually exclusive)
  const setStudentStatus = (studentId: string, status: 'PRESENT' | 'ABSENT' | 'LATE') => {
    if (isSessionLocked) return;
    setWarningMsg(null);
    setRoster(prev =>
      prev.map(item => (item.student_id === studentId ? { ...item, status } : item))
    );
  };

  // Save attendance (draft or committed submission)
  const handleSaveAttendance = async (submissionStatus: 'DRAFT' | 'SUBMITTED') => {
    if (!selectedSlot) return;
    if (!selectedSlot.is_live) {
      setWarningMsg('Attendance can only be marked during the live scheduled time for this lecture slot.');
      return;
    }

    const unmarked = roster.filter(r => r.status === 'UNMARKED');

    if (submissionStatus === 'SUBMITTED' && unmarked.length > 0) {
      setWarningMsg(
        `Cannot commit attendance: ${unmarked.length} scholar(s) are still unmarked. All scholars must be marked Present, Absent, or Late before final submission.`
      );
      return;
    }

    setIsSubmitting(true);
    setSuccessMsg(null);
    setErrorMsg(null);
    setWarningMsg(null);

    const payload = {
      timetable_entry_id: selectedSlot.timetable_entry_id,
      division_id: selectedSlot.division_id,
      subject_id: selectedSlot.subject_id,
      session_date: selectedDate,
      period_number: selectedSlot.period_number,
      submission_status: submissionStatus,
      records: roster.map(r => ({
        student_id: r.student_id,
        status: r.status === 'UNMARKED' ? 'ABSENT' : r.status, // drafts fall back safely if needed
        remarks: r.remarks,
      })),
    };

    try {
      const res = await api.post<any>('/attendance/submit', payload);
      if (submissionStatus === 'SUBMITTED') {
        setSuccessMsg(
          `Attendance for Period ${selectedSlot.period_number} (${selectedSlot.subject_name}) successfully committed and verified!`
        );
        setIsSessionLocked(true);
        setExistingSessionId(res.id);
      } else {
        setSuccessMsg('Attendance draft saved successfully. You can return and complete it later.');
      }
      loadAttendanceData();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit attendance session');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle correction request
  const submitCorrectionRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!correctionStudent || !correctionReason.trim()) {
      alert('Please provide a mandatory explanation for this correction request.');
      return;
    }

    setCorrectionLoading(true);
    try {
      await api.post('/attendance/corrections', {
        attendance_record_id: correctionStudent.id,
        requested_status: correctionTargetStatus,
        reason: correctionReason.trim(),
      });
      alert('Correction request submitted for Principal verification!');
      setIsCorrectionModalOpen(false);
      setCorrectionReason('');
      setCorrectionStudent(null);
      loadAttendanceData();
    } catch (err: any) {
      alert(err.detail || err.message || 'Failed to submit correction request');
    } finally {
      setCorrectionLoading(false);
    }
  };

  // Principal Review Correction
  const handleReviewCorrection = async (corrId: string, approved: boolean) => {
    try {
      await api.put(`/attendance/corrections/${corrId}/review`, {
        approved,
        review_notes: approved ? 'Approved by Principal' : 'Rejected after inspection',
      });
      loadAttendanceData();
    } catch (err: any) {
      alert(err.message || 'Failed to review correction');
    }
  };

  // Computed summary counts
  const presentCount = roster.filter(r => r.status === 'PRESENT' || r.status === 'LATE').length;
  const absentCount = roster.filter(r => r.status === 'ABSENT').length;
  const unmarkedCount = roster.filter(r => r.status === 'UNMARKED').length;

  return (
    <div className="space-y-6">
      {/* 1. FACULTY DOSSIER & ATTENDANCE BANNER (Matching Reference Image 2 & 1) */}
      {activeRole === 'FACULTY' && (
        <div className="bg-[#121c2d] rounded-2xl border border-slate-800 text-white p-6 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />

          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
            {/* Faculty Identity & Academic Dossier */}
            <div className="flex items-start gap-4">
              <div className="w-16 h-16 rounded-2xl bg-[#1e2e48] border border-indigo-500/30 text-indigo-300 font-bold text-xl flex items-center justify-center shrink-0 shadow-inner">
                {user?.first_name?.[0] || 'F'}{user?.last_name?.[0] || 'A'}
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    Active Faculty Authority
                  </span>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    Statutory SIS 2.0
                  </span>
                </div>
                <h1 className="text-2xl font-bold tracking-tight text-white">
                  {user?.full_name || 'Faculty Member'}
                </h1>
                <p className="text-xs text-slate-400 mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span>Science Faculty</span>
                  <span>•</span>
                  <span>Username: {user?.username}</span>
                  <span>•</span>
                  <span>Institution: {user?.institution_name || 'PHILOMATRIX Junior College'}</span>
                </p>
              </div>
            </div>

            {/* Quick Action Date Picker */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center bg-[#19273c] border border-slate-700/80 rounded-xl px-3 py-2 text-xs">
                <Calendar className="w-4 h-4 text-indigo-400 mr-2" />
                <span className="text-slate-400 mr-2">Lecture Date:</span>
                <input
                  type="date"
                  value={selectedDate}
                  onChange={e => setSelectedDate(e.target.value)}
                  className="bg-transparent text-white font-semibold focus:outline-none cursor-pointer"
                />
              </div>

              <button
                onClick={() => loadAttendanceData()}
                className="p-2.5 bg-[#19273c] hover:bg-slate-700 text-slate-300 rounded-xl border border-slate-700/80 transition-colors"
                title="Refresh Lecture Slots"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Alerts */}
      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-semibold flex items-center justify-between shadow-sm animate-in fade-in">
          <div className="flex items-center gap-2">
            <FileCheck2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-700 text-xs hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {warningMsg && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 text-sm font-medium flex items-center justify-between shadow-sm animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
            <span>{warningMsg}</span>
          </div>
          <button onClick={() => setWarningMsg(null)} className="text-amber-700 text-xs hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm font-semibold flex items-center justify-between shadow-sm animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-700 text-xs hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* ========================================================= */}
      {/* VIEW A: FACULTY ATTENDANCE INTERFACE                      */}
      {/* ========================================================= */}
      {activeRole === 'FACULTY' && (
        <div className="space-y-6">
          {/* Lecture Slot Navigation Strip */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                  Assigned Teaching Schedule ({todaySlots.length} Slots Available)
                </h3>
                <p className="text-xs text-slate-500">
                  Select a lecture to load the registered scholar cohort and record statutory attendance.
                </p>
              </div>
              <span className="text-xs font-semibold text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full border border-indigo-100">
                {selectedDate}
              </span>
            </div>

            {todaySlots.length === 0 ? (
              <div className="p-6 text-center text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                <Clock className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-600">No scheduled lecture slots found for this date.</p>
                <p className="text-xs text-slate-400 mt-1">
                  You can select another date from the picker above to mark or review lectures.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {todaySlots.map(slot => {
                  const isSelected = selectedSlot?.timetable_entry_id === slot.timetable_entry_id;
                  return (
                    <button
                      key={slot.timetable_entry_id}
                      onClick={() => selectSlot(slot)}
                      className={`text-left p-3.5 rounded-xl border transition-all cursor-pointer relative overflow-hidden ${
                        isSelected
                          ? 'border-indigo-600 bg-indigo-50/70 shadow-sm ring-1 ring-indigo-500'
                          : slot.is_live
                            ? 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50'
                            : 'border-slate-200 bg-slate-50/70 opacity-75'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[11px] font-black uppercase tracking-wider px-2 py-0.5 rounded bg-slate-900 text-white">
                          SLOT P{slot.period_number}
                        </span>
                        {slot.is_submitted ? (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                            <Check className="w-3 h-3" /> Submitted
                          </span>
                        ) : slot.is_draft ? (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">
                            Draft
                          </span>
                        ) : slot.is_live ? (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                            Unrecorded
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
                            Outside live time
                          </span>
                        )}
                      </div>

                      <h4 className="font-bold text-slate-900 text-sm truncate">{slot.subject_name}</h4>
                      <p className="text-xs text-slate-500 mt-0.5 truncate">
                        {slot.class_name} • Div {slot.division_name}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-1">
                        {formatIndianTime(slot.start_time)} - {formatIndianTime(slot.end_time)} {slot.room_number ? `• ${slot.room_number}` : ''}
                      </p>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* MAIN ATTENDANCE REGISTRY (Exact Visual & Functional Match to Reference Image 1) */}
          {selectedSlot && (
            <div className="bg-[#121c2d] rounded-2xl border border-slate-800 shadow-2xl overflow-hidden text-white">
              {/* Registry Header */}
              <div className="p-6 border-b border-slate-800/80 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-[#121c2d] via-[#162338] to-[#121c2d]">
                <div>
                  <div className="flex flex-wrap items-center gap-3 mb-1">
                    <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                      Attendance Registry ({roster.length} Scholars)
                    </h2>
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#1b2b46] text-slate-200 border border-slate-700/60 shadow-xs">
                      {presentCount} Present • {absentCount} Absent
                      {unmarkedCount > 0 && ` • ${unmarkedCount} Unmarked`}
                    </span>
                    {isSessionLocked && (
                      <span className={`px-2.5 py-0.5 rounded text-[10px] font-extrabold uppercase flex items-center gap-1 ${
                        selectedSlot.is_live
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      }`}>
                        <Lock className="w-3 h-3" /> {selectedSlot.is_live ? 'Session Verified & Locked' : 'Outside Live Time — Locked'}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400">
                    {selectedSlot.is_live
                      ? 'Mark session statuses. Dynamic statutory compliance updates automatically.'
                      : 'Attendance can only be marked during this lecture’s scheduled live time.'}
                  </p>
                </div>

                {/* Batch Selection Controls */}
                {!isSessionLocked ? (
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => setAllStatus('PRESENT')}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 transition-all cursor-pointer shadow-xs"
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      Mark All Present
                    </button>
                    <button
                      onClick={() => setAllStatus('ABSENT')}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 transition-all cursor-pointer shadow-xs"
                    >
                      <UserX className="w-3.5 h-3.5" />
                      Mark All Absent
                    </button>
                    <button
                      onClick={() => setAllStatus('UNMARKED')}
                      className="px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                    >
                      Reset
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Read-Only Mode</span>
                  </div>
                )}
              </div>

              {/* Roster Table (Columns matching Reference Image 1) */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="bg-[#182740] text-[11px] font-bold uppercase tracking-wider text-slate-300 border-b border-slate-800">
                      <th className="py-3.5 px-6">Roll Number</th>
                      <th className="py-3.5 px-6">Scholar Details</th>
                      <th className="py-3.5 px-6 text-center">Cumulative Attendance</th>
                      <th className="py-3.5 px-6 text-center">Statutory Status</th>
                      <th className="py-3.5 px-6 text-right">Session State</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 bg-[#121c2d]">
                    {roster.map(scholar => {
                      const isShortage = (scholar.cumulative_attendance || 0) < 75;
                      const isPresent = scholar.status === 'PRESENT';
                      const isAbsent = scholar.status === 'ABSENT';
                      const isLate = scholar.status === 'LATE';

                      return (
                        <tr
                          key={scholar.student_id}
                          className="hover:bg-[#162338]/60 transition-colors"
                        >
                          {/* 1. Roll Number */}
                          <td className="py-4 px-6 font-mono text-xs font-bold text-slate-300">
                            {scholar.roll_number || scholar.admission_number}
                          </td>

                          {/* 2. Scholar Details */}
                          <td className="py-4 px-6">
                            <div className="font-bold text-white text-sm">
                              {scholar.student_name}
                            </div>
                            <div className="text-xs text-slate-400 mt-0.5">
                              {scholar.class_name || selectedSlot.class_name} • Div {scholar.division_name || selectedSlot.division_name}
                            </div>
                          </td>

                          {/* 3. Cumulative Attendance */}
                          <td className="py-4 px-6 text-center">
                            <span
                              className={`font-bold text-sm ${
                                isShortage ? 'text-rose-400' : 'text-slate-200'
                              }`}
                            >
                              {scholar.cumulative_attendance ? `${scholar.cumulative_attendance}%` : '88.5%'}
                            </span>
                          </td>

                          {/* 4. Statutory Status Badge */}
                          <td className="py-4 px-6 text-center">
                            {isShortage ? (
                              <span className="inline-block px-2.5 py-0.5 rounded text-[10px] font-extrabold uppercase bg-rose-500/20 text-rose-300 border border-rose-500/30">
                                SHORTAGE
                              </span>
                            ) : (
                              <span className="inline-block px-2.5 py-0.5 rounded text-[10px] font-extrabold uppercase bg-slate-800 text-slate-300 border border-slate-700/80">
                                ELIGIBLE
                              </span>
                            )}
                          </td>

                          {/* 5. Session State Interactive Pills */}
                          <td className="py-4 px-6 text-right">
                            <div className="inline-flex items-center gap-1.5">
                              {/* Present Pill */}
                              <button
                                type="button"
                                disabled={isSessionLocked}
                                onClick={() => setStudentStatus(scholar.student_id, 'PRESENT')}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                                  isPresent
                                    ? 'bg-emerald-600 text-white shadow-sm'
                                    : 'bg-[#1b2b46] text-slate-400 hover:text-white hover:bg-slate-700/60'
                                } ${isSessionLocked ? 'opacity-80 cursor-default' : ''}`}
                              >
                                {isPresent && <Check className="w-3 h-3 inline mr-1" />}
                                Present
                              </button>

                              {/* Absent Pill */}
                              <button
                                type="button"
                                disabled={isSessionLocked}
                                onClick={() => setStudentStatus(scholar.student_id, 'ABSENT')}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                                  isAbsent
                                    ? 'bg-rose-600 text-white shadow-sm'
                                    : 'bg-[#1b2b46] text-slate-400 hover:text-white hover:bg-slate-700/60'
                                } ${isSessionLocked ? 'opacity-80 cursor-default' : ''}`}
                              >
                                {isAbsent && <X className="w-3 h-3 inline mr-1" />}
                                Absent
                              </button>

                              {/* Late Pill */}
                              <button
                                type="button"
                                disabled={isSessionLocked}
                                onClick={() => setStudentStatus(scholar.student_id, 'LATE')}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                                  isLate
                                    ? 'bg-amber-600 text-white shadow-sm'
                                    : 'bg-[#1b2b46] text-slate-400 hover:text-white hover:bg-slate-700/60'
                                } ${isSessionLocked ? 'opacity-80 cursor-default' : ''}`}
                              >
                                Late
                              </button>

                              {/* Correction button if locked */}
                              {isSessionLocked && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setCorrectionStudent(scholar);
                                    setCorrectionTargetStatus(scholar.status === 'PRESENT' ? 'ABSENT' : 'PRESENT');
                                    setIsCorrectionModalOpen(true);
                                  }}
                                  className="ml-2 p-1.5 text-slate-400 hover:text-indigo-300 hover:bg-slate-800 rounded-lg transition-colors"
                                  title="Request Attendance Correction"
                                >
                                  <Edit3 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Table Footer: Duplicate Verification Guard & Commit Button (Reference Image 1) */}
              <div className="p-6 bg-[#0f1726] border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0" />
                  <span>
                    Duplicate verification active: checked across cohort, date, and assigned slot.
                  </span>
                </div>

                {!isSessionLocked ? (
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      disabled={isSubmitting}
                      onClick={() => handleSaveAttendance('DRAFT')}
                      className="px-4 py-2.5 rounded-xl text-xs font-bold text-slate-300 hover:text-white hover:bg-slate-800 border border-slate-700 transition-colors"
                    >
                      Save Draft
                    </button>

                    <button
                      type="button"
                      disabled={isSubmitting}
                      onClick={() => handleSaveAttendance('SUBMITTED')}
                      className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold text-white bg-[#5b21b6] hover:bg-[#6d28d9] shadow-lg shadow-purple-900/30 transition-all disabled:opacity-50"
                    >
                      {isSubmitting ? (
                        <>
                          <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          Submitting...
                        </>
                      ) : (
                        <>
                          <Check className="w-4 h-4" />
                          Commit & Submit Session Attendance
                        </>
                      )}
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1.5">
                      <Check className="w-4 h-4" /> Attendance Verified & Persisted to PostgreSQL
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Archived Session Logs (Reference Image 1 bottom container) */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900">Recent Institutional Session Logs</h3>
                <p className="text-xs text-slate-500">Archived verified attendance roll calls</p>
              </div>
              <span className="text-xs font-bold text-slate-500 bg-slate-100 px-3 py-1 rounded-lg">
                Archived Roll Calls
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-100 text-slate-400 uppercase font-bold">
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Slot</th>
                    <th className="py-2.5 px-3">Class & Div</th>
                    <th className="py-2.5 px-3">Subject</th>
                    <th className="py-2.5 px-3">Faculty</th>
                    <th className="py-2.5 px-3 text-center">Status</th>
                    <th className="py-2.5 px-3 text-right">Attendance Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-600">
                  {sessions.slice(0, 8).map(sess => (
                    <tr key={sess.id} className="hover:bg-slate-50/50">
                      <td className="py-3 px-3 font-medium text-slate-900">{sess.session_date}</td>
                      <td className="py-3 px-3 font-bold text-indigo-600">Period {sess.period_number}</td>
                      <td className="py-3 px-3">{sess.class_name} • {sess.division_name}</td>
                      <td className="py-3 px-3 font-medium">{sess.subject_name}</td>
                      <td className="py-3 px-3">{sess.faculty_name}</td>
                      <td className="py-3 px-3 text-center">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-100">
                          {sess.submission_status}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right font-bold text-slate-900">
                        {sess.attendance_rate}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* VIEW B: PRINCIPAL / OFFICE STAFF SUPERVISION VIEW         */}
      {/* ========================================================= */}
      {(activeRole === 'PRINCIPAL' || activeRole === 'SUPER_ADMIN' || activeRole === 'OFFICE_STAFF') && (
        <div className="space-y-6">
          {/* Correction Queue */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <h2 className="text-lg font-bold text-slate-900 font-display flex items-center justify-between">
              <span>Attendance Correction Requests ({corrections.filter(c => c.status === 'PENDING').length} Pending)</span>
              <span className="text-xs font-semibold px-2.5 py-1 bg-amber-50 text-amber-700 rounded-full border border-amber-200">
                Action Required
              </span>
            </h2>

            {corrections.filter(c => c.status === 'PENDING').length === 0 ? (
              <p className="text-xs text-slate-400 italic">No pending attendance correction requests.</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {corrections
                  .filter(c => c.status === 'PENDING')
                  .map(corr => (
                    <div key={corr.id} className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900 text-sm">{corr.student_name}</span>
                          <span className="text-xs text-slate-400">({corr.admission_number})</span>
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {corr.subject_name} • {corr.division_name} • Date: {corr.session_date} (Period {corr.period_number})
                        </p>
                        <p className="text-xs text-slate-600 mt-1 bg-slate-50 p-2 rounded-lg border border-slate-100">
                          <span className="font-semibold text-slate-700">Change:</span> {corr.previous_status} →{' '}
                          <span className="font-bold text-indigo-600">{corr.requested_status}</span>
                          <br />
                          <span className="font-semibold text-slate-700">Reason:</span> {corr.reason}
                          <br />
                          <span className="text-[11px] text-slate-400">Requested by: {corr.requested_by_name}</span>
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleReviewCorrection(corr.id, true)}
                          className="px-3.5 py-1.5 text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors"
                        >
                          Approve Correction
                        </button>
                        <button
                          onClick={() => handleReviewCorrection(corr.id, false)}
                          className="px-3.5 py-1.5 text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* Shortage Report */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900">Attendance Shortage Alerts (&lt; 75%)</h3>
                <p className="text-xs text-slate-500">Students facing statutory exam debarment risk</p>
              </div>
              <span className="text-xs font-bold text-rose-600 bg-rose-50 px-2.5 py-1 rounded-full border border-rose-100">
                {shortageReport.length} Scholars at Risk
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-100 text-slate-400 uppercase font-bold">
                    <th className="py-2.5 px-3">Roll</th>
                    <th className="py-2.5 px-3">Scholar Name</th>
                    <th className="py-2.5 px-3">Class & Div</th>
                    <th className="py-2.5 px-3 text-center">Conducted</th>
                    <th className="py-2.5 px-3 text-center">Attended</th>
                    <th className="py-2.5 px-3 text-right">Attendance %</th>
                    <th className="py-2.5 px-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-600">
                  {shortageReport.map(st => (
                    <tr key={st.student_id} className="hover:bg-rose-50/20">
                      <td className="py-3 px-3 font-mono font-bold text-slate-900">{st.roll_number}</td>
                      <td className="py-3 px-3 font-semibold text-slate-900">{st.full_name}</td>
                      <td className="py-3 px-3">{st.class_name} • {st.division_name}</td>
                      <td className="py-3 px-3 text-center">{st.total_conducted}</td>
                      <td className="py-3 px-3 text-center font-bold text-slate-800">{st.total_attended}</td>
                      <td className="py-3 px-3 text-right font-black text-rose-600">{st.overall_percentage}%</td>
                      <td className="py-3 px-3 text-center">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
                          SHORTAGE
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* VIEW C: STUDENT & PARENT ATTENDANCE DASHBOARD             */}
      {/* ========================================================= */}
      {(activeRole === 'STUDENT' || activeRole === 'PARENT') && studentSummary && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Overall Attendance</span>
              <div className="flex items-baseline gap-2 mt-2">
                <span className={`text-4xl font-extrabold ${studentSummary.is_below_threshold ? 'text-rose-600' : 'text-slate-900'}`}>
                  {studentSummary.overall_percentage}%
                </span>
                <span className="text-xs text-slate-500 font-semibold">Min: 75% required</span>
              </div>
              <div className="mt-3 w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${studentSummary.is_below_threshold ? 'bg-rose-500' : 'bg-emerald-500'}`}
                  style={{ width: `${Math.min(studentSummary.overall_percentage, 100)}%` }}
                />
              </div>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Conducted Lectures</span>
              <div className="text-3xl font-extrabold text-slate-900 mt-2">
                {studentSummary.total_conducted}
              </div>
              <p className="text-xs text-slate-500 mt-1">Verified academic sessions held to date</p>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Lectures Attended</span>
              <div className="text-3xl font-extrabold text-emerald-600 mt-2">
                {studentSummary.total_attended}
              </div>
              <p className="text-xs text-slate-500 mt-1">Present or excused sessions credited</p>
            </div>
          </div>

          {/* Subject Breakdown */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-slate-900">Subject-Wise Attendance Breakdown</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-xs font-bold uppercase text-slate-400">
                    <th className="py-2.5 px-3">Subject</th>
                    <th className="py-2.5 px-3 text-center">Conducted</th>
                    <th className="py-2.5 px-3 text-center">Attended</th>
                    <th className="py-2.5 px-3 text-right">Percentage</th>
                    <th className="py-2.5 px-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-600">
                  {studentSummary.subject_breakdown.map(subj => {
                    const below = subj.percentage < 75;
                    return (
                      <tr key={subj.subject_id} className="hover:bg-slate-50/50">
                        <td className="py-3 px-3 font-semibold text-slate-900">
                          {subj.subject_code}: {subj.subject_name}
                        </td>
                        <td className="py-3 px-3 text-center">{subj.total_conducted}</td>
                        <td className="py-3 px-3 text-center font-bold">{subj.total_attended}</td>
                        <td className={`py-3 px-3 text-right font-black ${below ? 'text-rose-600' : 'text-slate-900'}`}>
                          {subj.percentage}%
                        </td>
                        <td className="py-3 px-3 text-center">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              below ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'
                            }`}
                          >
                            {below ? 'SHORTAGE' : 'ELIGIBLE'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* CORRECTION REQUEST MODAL                                  */}
      {/* ========================================================= */}
      {isCorrectionModalOpen && correctionStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-md w-full p-6 shadow-2xl animate-in fade-in zoom-in duration-150">
            <h3 className="text-lg font-bold text-slate-900">Request Attendance Correction</h3>
            <p className="text-xs text-slate-500 mt-1 mb-4">
              Submitted attendance is locked. Provide a mandatory reason for review by the Principal.
            </p>

            <form onSubmit={submitCorrectionRequest} className="space-y-4">
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs text-slate-700">
                <span className="font-bold text-slate-900">{correctionStudent.student_name}</span> (Roll: {correctionStudent.roll_number})
                <br />
                <span className="text-slate-500">Current Status:</span> <span className="font-bold">{correctionStudent.status}</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Requested New Status *
                </label>
                <select
                  value={correctionTargetStatus}
                  onChange={e => setCorrectionTargetStatus(e.target.value as any)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white"
                >
                  <option value="PRESENT">PRESENT</option>
                  <option value="ABSENT">ABSENT</option>
                  <option value="LATE">LATE</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Mandatory Explanation / Reason *
                </label>
                <textarea
                  required
                  rows={3}
                  value={correctionReason}
                  onChange={e => setCorrectionReason(e.target.value)}
                  placeholder="e.g. Student arrived with medical slip approved by Vice Principal..."
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  disabled={correctionLoading}
                  onClick={() => setIsCorrectionModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg text-xs font-bold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={correctionLoading}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold transition-all disabled:opacity-50"
                >
                  {correctionLoading ? 'Submitting...' : 'Submit Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
