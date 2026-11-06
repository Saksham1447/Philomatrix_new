import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Student } from '../types';
import { AlertCircle, Calendar, CheckCircle2, Download, Eye, GraduationCap, Mail, Phone, Search, Trash2, UserPlus, Users, X } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';

export const StudentsPage: React.FC = () => {
  const { activeRole } = useAuth();
  const [searchParams] = useSearchParams();
  const classFilter = searchParams.get('class_id');
  const [students, setStudents] = useState<Student[]>([]);
  const [search, setSearch] = useState('');
  const [selectedClassId, setSelectedClassId] = useState(classFilter || '');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'INACTIVE'>('ALL');
  const [showModal, setShowModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [attendanceError, setAttendanceError] = useState<string | null>(null);
  const [feeError, setFeeError] = useState<string | null>(null);
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [attendanceSummary, setAttendanceSummary] = useState<any | null>(null);
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    first_name: '',
    middle_name: '',
    last_name: '',
    phone_number: '',
    admission_number: '',
    date_of_birth: '2009-01-01',
    gender: '',
    admission_date: new Date().toISOString().split('T')[0],
    class_id: classFilter || '',
    division_id: '',
    academic_year_id: '',
    roll_number: '',
  });

  const [classes, setClasses] = useState<any[]>([]);
  const [years, setYears] = useState<any[]>([]);

  const loadStudents = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (selectedClassId) params.set('class_id', selectedClassId);
      const data = await api.get<Student[]>(`/students${params.toString() ? `?${params.toString()}` : ''}`);
      setStudents(data);
    } catch (err) {
      console.error('Failed to load students', err);
      setErrorMsg('Could not load the student registry. Please try again.');
    }
  };

  useEffect(() => {
    loadStudents();
  }, [search, selectedClassId]);

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const cls = await api.get<any[]>('/academics/classes');
        setClasses(cls);
        const yrs = await api.get<any[]>('/academics/years');
        setYears(yrs);

        const selectedClass = cls.find((item) => item.id === classFilter) || cls[0];
        if (selectedClass && selectedClass.divisions.length > 0) {
          setFormData(prev => ({
            ...prev,
            class_id: selectedClass.id,
            division_id: selectedClass.divisions[0].id,
            academic_year_id: yrs[0]?.id || '',
          }));
        }
      } catch (err) {
        console.error('Failed to load classes or years', err);
      }
    };
    fetchMetadata();
  }, []);

  const handleCreateStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSuccessMsg(null);
    try {
      await api.post('/students', formData);
      setSuccessMsg('Student admitted and enrolled successfully!');
      setShowModal(false);
      loadStudents();
    } catch (err: any) {
      alert(err.message || 'Admission failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteStudent = async (studentId: string) => {
    if (!window.confirm('Remove this student and their institute login?')) return;
    try {
      await api.delete(`/students/${studentId}`);
      setSuccessMsg('Student removed successfully.');
      if (selectedStudent?.id === studentId) setSelectedStudent(null);
      loadStudents();
    } catch (err: any) {
      alert(err.message || 'Could not remove student');
    }
  };

  const handleFeeStatusChange = async (student: Student, fee_status: Student['fee_status']) => {
    try {
      const updated = await api.put<Student>(`/students/${student.id}/fee-status`, { fee_status });
      const merged = { ...student, ...updated, guardians: student.guardians };
      setStudents(current => current.map(item => item.id === student.id ? merged : item));
      setSelectedStudent(current => current?.id === student.id ? merged : current);
      setFeeError(null);
      setSuccessMsg(`Fee status updated for ${student.full_name}.`);
    } catch (err: any) {
      setFeeError(err.message || 'Could not update fee status.');
    }
  };

  const visibleStudents = useMemo(
    () => students.filter(student => statusFilter === 'ALL' || student.status?.toUpperCase() === statusFilter),
    [students, statusFilter]
  );
  const activeCount = students.filter(student => student.status?.toUpperCase() === 'ACTIVE').length;
  const inactiveCount = students.length - activeCount;

  const openDossier = async (student: Student) => {
    setSelectedStudent(student);
    setAttendanceSummary(null);
    setAttendanceError(null);
    setFeeError(null);
    setIsLoadingSummary(true);
    try {
      const summary = await api.get<any>(`/attendance/summary/student/${student.id}`);
      setAttendanceSummary(summary);
    } catch (err: any) {
      setAttendanceError(err.message || 'Could not load attendance details for this student.');
    } finally {
      setIsLoadingSummary(false);
    }
  };

  const exportCsv = () => {
    const columns = ['Student Name', 'Admission Number', 'Roll Number', 'Class', 'Division', 'Academic Year', 'Status', 'Fee Status', 'Email', 'Phone'];
    const escapeCsv = (value: string | undefined) => `"${(value || '').replace(/"/g, '""')}"`;
    const rows = visibleStudents.map(student => [
      student.full_name,
      student.admission_number,
      student.roll_number,
      student.class_name,
      student.division_name,
      student.academic_year_name,
      student.status,
      student.fee_status || 'PENDING',
      student.email,
      student.phone_number,
    ].map(escapeCsv).join(','));
    const file = new Blob([[columns.join(','), ...rows].join('\r\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(file);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'student-registry.csv';
    link.click();
    URL.revokeObjectURL(url);
  };
  const studentGuardians = selectedStudent?.guardians || [];

  return (
    <div className="mx-auto max-w-[1600px] space-y-6">
      <div className="mb-1 flex items-center gap-2 text-xs font-medium text-slate-400">
        <span>Executive Portal</span><span>›</span><span className="text-slate-600">Student Registry &amp; Academic Dossier</span>
      </div>
      <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex items-center gap-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-3.5 text-slate-700 shadow-sm"><GraduationCap className="h-7 w-7" /></div>
          <div>
            <h1 className="font-display text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">Student Registry &amp; Academic Dossier</h1>
            <p className="mt-1 text-sm text-slate-500">Comprehensive centralized student records, attendance tracking, and academic standings</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={exportCsv} disabled={visibleStudents.length === 0} className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50">
            <Download className="h-4 w-4" /> Export CSV
          </button>
          {(activeRole === 'PRINCIPAL' || activeRole === 'OFFICE_STAFF') && (
            <button type="button" onClick={() => setShowModal(true)} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-bold text-white shadow-md shadow-indigo-500/20 transition hover:bg-indigo-700">
              <UserPlus className="h-4 w-4" /> Enroll New Student
            </button>
          )}
        </div>
      </div>

      {successMsg && (
        <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800">
          <CheckCircle2 className="h-5 w-5 text-emerald-600" /> {successMsg}
        </div>
      )}
      {errorMsg && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-800">
          <AlertCircle className="h-5 w-5 shrink-0 text-rose-600" /> {errorMsg}
          <button type="button" onClick={() => setErrorMsg(null)} className="ml-auto text-xs font-bold hover:underline">Dismiss</button>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <span className="mr-1 text-xs font-bold uppercase tracking-wider text-slate-400">Perspective:</span>
        <button type="button" onClick={() => setStatusFilter('ALL')} aria-pressed={statusFilter === 'ALL'}
          className={`rounded-lg border px-3.5 py-2 text-xs font-bold transition ${statusFilter === 'ALL' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'}`}>
          All Scholars ({students.length})
        </button>
        <button type="button" disabled title="Fee tracking is not available in this system" className="cursor-not-allowed rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-rose-700 opacity-70">
          Fee Overdue
        </button>
        <button type="button" disabled title="Fee tracking is not available in this system" className="cursor-not-allowed rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-amber-700 opacity-70">
          Fee Clearance Pending
        </button>
      </div>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between gap-3 bg-[#151b2d] px-5 py-3.5 text-white">
          <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide"><Search className="h-4 w-4 text-indigo-300" /> Student Search &amp; Cohort Filters</h2>
          <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-[10px] font-bold text-cyan-200">Active Query Engine</span>
        </div>
        <div className="grid gap-3 p-4 md:grid-cols-[minmax(240px,1fr)_220px_190px]">
          <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3.5">
            <Search className="h-4 w-4 shrink-0 text-slate-400" />
            <input type="search" value={search} onChange={event => setSearch(event.target.value)} aria-label="Search students"
              placeholder="Search by student name, roll number, admission ID, or email..."
              className="w-full bg-transparent py-3 text-sm text-slate-800 outline-none placeholder:text-slate-400" />
          </label>
          <select aria-label="Filter by class" value={selectedClassId} onChange={event => setSelectedClassId(event.target.value)} className="rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-slate-700 outline-none focus:border-indigo-400">
            <option value="">All Classes</option>
            {classes.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <select aria-label="Filter by status" value={statusFilter} onChange={event => setStatusFilter(event.target.value as typeof statusFilter)} className="rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-slate-700 outline-none focus:border-indigo-400">
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
          </select>
        </div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 bg-[#151b2d] px-5 py-4 text-white">
          <div>
            <h2 className="text-base font-bold">Student Academic Registry{selectedClassId ? ` (${visibleStudents.length} Scholars Enrolled in ${classes.find((item: any) => item.id === selectedClassId)?.name || 'Class'})` : ` (${visibleStudents.length} Scholars)`}</h2>
            <p className="mt-1 text-xs text-slate-400">Student enrollment, academic cohort, contact details, and attendance dossier</p>
          </div>
          {selectedClassId && <span className="rounded-full border border-violet-400/20 bg-violet-400/10 px-3 py-1.5 text-xs font-bold text-violet-200">Active Class: {classes.find((item: any) => item.id === selectedClassId)?.name}</span>}
          {!selectedClassId && <span className="rounded-full border border-violet-400/20 bg-violet-400/10 px-3 py-1.5 text-xs font-bold text-violet-200">{activeCount} Active · {inactiveCount} Inactive</span>}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1050px] border-collapse text-left text-xs">
            <thead className="bg-[#1b2235] text-slate-300">
              <tr className="text-[10px] font-bold uppercase tracking-wide">
                <th className="px-4 py-3.5">Student Name &amp; ID</th>
                <th className="px-4 py-3.5">Department &amp; Program</th>
                <th className="px-4 py-3.5 text-center">Class</th>
                <th className="px-4 py-3.5 text-center">Total Percentage</th>
                <th className="px-4 py-3.5 text-center">Attendance</th>
                <th className="px-4 py-3.5 text-center">Fee Status</th>
                <th className="px-4 py-3.5 text-center">Status</th>
                <th className="px-4 py-3.5 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {visibleStudents.map(student => (
                <tr key={student.id} className="transition hover:bg-slate-50/80">
                  <td className="px-4 py-3.5">
                    <div className="flex min-w-[190px] items-center gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-sm font-bold text-indigo-700">{student.first_name?.[0] || '?'}</div>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-bold text-slate-900">{student.full_name}</p>
                        <p className="mt-0.5 text-[10px] text-slate-400">{student.admission_number}{student.roll_number ? ` · Roll ${student.roll_number}` : ''}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    <p className="font-semibold text-slate-700">{student.class_name || '—'}</p>
                    <p className="mt-0.5 text-[10px] text-slate-400">{student.academic_year_name || 'Academic year not set'}</p>
                  </td>
                  <td className="px-4 py-3.5 text-center"><span className="inline-flex rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 font-semibold text-slate-600">{student.class_name || '—'}{student.division_name ? ` - ${student.division_name}` : ''}</span></td>
                  <td className="px-4 py-3.5 text-center text-slate-400" title="Marks percentage is not available in the student registry data">—</td>
                  <td className="px-4 py-3.5 text-center text-slate-400" title="Open the dossier to load verified attendance">View dossier</td>
                  <td className="px-4 py-3.5 text-center">
                    {(activeRole === 'PRINCIPAL' || activeRole === 'OFFICE_STAFF') ? (
                      <select
                        aria-label={`Fee status for ${student.full_name}`}
                        value={student.fee_status || 'PENDING'}
                        onChange={event => handleFeeStatusChange(student, event.target.value as Student['fee_status'])}
                        className={`rounded-lg border px-2.5 py-1.5 text-xs font-bold ${student.fee_status === 'PAID' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : student.fee_status === 'OVERDUE' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-amber-200 bg-amber-50 text-amber-700'}`}
                      >
                        <option value="PAID">Paid</option>
                        <option value="PENDING">Pending</option>
                        <option value="OVERDUE">Overdue</option>
                      </select>
                    ) : (
                      <span className={`rounded-lg px-2.5 py-1.5 text-xs font-bold ${student.fee_status === 'PAID' ? 'bg-emerald-50 text-emerald-700' : student.fee_status === 'OVERDUE' ? 'bg-rose-50 text-rose-700' : 'bg-amber-50 text-amber-700'}`}>{student.fee_status || 'PENDING'}</span>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-center">
                    <span className={`rounded-lg px-2.5 py-1.5 font-bold ${student.status?.toUpperCase() === 'ACTIVE' ? 'bg-slate-100 text-slate-600' : 'bg-rose-50 text-rose-700'}`}>{student.status || 'Unknown'}</span>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex justify-center gap-1">
                      <button type="button" onClick={() => openDossier(student)} aria-label={`View ${student.full_name} dossier`} className="rounded-lg p-2 text-slate-400 transition hover:bg-indigo-50 hover:text-indigo-600"><Eye className="h-4 w-4" /></button>
                      {(activeRole === 'PRINCIPAL' || activeRole === 'SUPER_ADMIN') && <button type="button" onClick={() => handleDeleteStudent(student.id)} aria-label={`Remove ${student.full_name}`} className="rounded-lg p-2 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"><Trash2 className="h-4 w-4" /></button>}
                    </div>
                  </td>
                </tr>
              ))}
              {visibleStudents.length === 0 && (
                <tr><td colSpan={8} className="px-6 py-16 text-center">
                  <Users className="mx-auto mb-3 h-10 w-10 text-slate-300" />
                  <p className="font-semibold text-slate-700">No students found</p>
                  <p className="mt-1 text-xs text-slate-400">Try a different search or cohort filter.</p>
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {selectedStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm" onClick={() => setSelectedStudent(null)}>
          <section role="dialog" aria-modal="true" aria-labelledby="student-dossier-title" onClick={event => event.stopPropagation()} className="flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl">
            <header className="flex items-start justify-between gap-4 bg-[#151b2d] px-6 py-5 text-white">
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-indigo-300/30 bg-indigo-400/15 text-xl font-bold text-indigo-100">{selectedStudent.first_name?.[0] || '?'}</div>
                <div>
                  <div className="flex flex-wrap items-center gap-2"><h2 id="student-dossier-title" className="text-xl font-bold">{selectedStudent.full_name}</h2><span className="rounded-full bg-indigo-400/20 px-2.5 py-1 text-[10px] font-bold uppercase text-indigo-200">{selectedStudent.status}</span></div>
                  <p className="mt-1 text-xs text-slate-300">Admission ID: {selectedStudent.admission_number} {selectedStudent.roll_number ? ` · Roll No: ${selectedStudent.roll_number}` : ''}</p>
                  <p className="mt-1 text-xs text-slate-300">Class: <span className="font-semibold text-white">{selectedStudent.class_name || '—'}{selectedStudent.division_name ? ` - Div ${selectedStudent.division_name}` : ''}</span></p>
                </div>
              </div>
              <button type="button" onClick={() => setSelectedStudent(null)} aria-label="Close dossier" className="rounded-lg p-2 text-slate-300 transition hover:bg-white/10 hover:text-white"><X className="h-5 w-5" /></button>
            </header>
            <div className="space-y-5 overflow-y-auto p-5 sm:p-7">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5"><p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Lecture Attendance</p><p className="mt-2 text-3xl font-bold text-slate-900">{isLoadingSummary ? '…' : attendanceSummary ? `${attendanceSummary.overall_percentage}%` : '—'}</p><p className="mt-1 text-xs text-slate-500">{attendanceSummary ? `${attendanceSummary.total_attended} of ${attendanceSummary.total_conducted} sessions attended` : 'Verified attendance summary'}</p></div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5"><p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Marks Total Percentage</p><p className="mt-2 text-3xl font-bold text-slate-900">—</p><p className="mt-1 text-xs text-slate-500">No marks summary available</p></div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Fee Status</p>
                  {(activeRole === 'PRINCIPAL' || activeRole === 'OFFICE_STAFF') ? (
                    <select aria-label={`Dossier fee status for ${selectedStudent.full_name}`} value={selectedStudent.fee_status || 'PENDING'} onChange={event => handleFeeStatusChange(selectedStudent, event.target.value as Student['fee_status'])} className="mt-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-bold text-slate-700">
                      <option value="PAID">Paid</option><option value="PENDING">Pending</option><option value="OVERDUE">Overdue</option>
                    </select>
                  ) : <p className="mt-2 text-2xl font-bold text-slate-700">{selectedStudent.fee_status || 'PENDING'}</p>}
                  <p className="mt-1 text-xs text-slate-500">Status only; fee amounts and transactions are not tracked.</p>
                </div>
              </div>
              {attendanceError && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">Attendance details: {attendanceError}</p>}
              {feeError && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">Fee status update: {feeError}</p>}
              <div className="rounded-2xl border border-indigo-100 bg-indigo-50/40 p-5">
                <h3 className="mb-4 text-sm font-bold uppercase tracking-wide text-indigo-950">Student Academic &amp; Contact Details</h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  <p className="flex items-center gap-2 text-sm text-slate-700"><Mail className="h-4 w-4 text-slate-400" />{selectedStudent.email}</p>
                  <p className="flex items-center gap-2 text-sm text-slate-700"><Phone className="h-4 w-4 text-slate-400" />{selectedStudent.phone_number || 'Phone not provided'}</p>
                  <p className="flex items-center gap-2 text-sm text-slate-700"><Calendar className="h-4 w-4 text-slate-400" />Date of birth: {selectedStudent.date_of_birth}</p>
                  <p className="flex items-center gap-2 text-sm text-slate-700"><GraduationCap className="h-4 w-4 text-slate-400" />Academic year: {selectedStudent.academic_year_name || 'Not set'}</p>
                </div>
                {attendanceSummary?.subject_breakdown?.length > 0 && (
                  <div className="mt-5 border-t border-indigo-100 pt-4">
                    <h4 className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-500">Attendance by Subject</h4>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {attendanceSummary.subject_breakdown.map((subject: any) => <div key={subject.subject_id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2.5"><span className="text-sm font-semibold text-slate-700">{subject.subject_name}</span><span className="text-sm font-bold text-indigo-700">{subject.percentage}%</span></div>)}
                    </div>
                  </div>
                )}
              </div>
              {studentGuardians.length > 0 && <div className="rounded-2xl border border-slate-200 p-5"><h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-700">Guardian Contacts</h3><div className="grid gap-3 sm:grid-cols-2">{studentGuardians.map(guardian => <div key={guardian.id} className="rounded-xl bg-slate-50 p-3"><p className="font-semibold text-slate-800">{guardian.full_name} · {guardian.relationship_type}</p><p className="mt-1 text-xs text-slate-500">{guardian.email} · {guardian.phone_number || 'Phone not provided'}</p></div>)}</div></div>}
            </div>
            <footer className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-6 py-4">
              <span className="text-xs text-slate-400">Philomatrix Academic ERP · Dossier Verification</span>
              <button type="button" onClick={() => setSelectedStudent(null)} className="rounded-xl bg-[#151b2d] px-5 py-2.5 text-sm font-bold text-white hover:bg-slate-800">Close Dossier</button>
            </footer>
          </section>
        </div>
      )}

      {/* Admission Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
          <div className="max-h-[90vh] w-full max-w-xl space-y-4 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl">
            <div className="-mx-6 -mt-6 mb-5 rounded-t-2xl bg-[#151b2d] px-6 py-4 text-white">
              <h2 className="text-lg font-bold font-display">Enroll New Student</h2>
              <p className="mt-1 text-xs text-slate-300">Admit a student and create their academic enrollment and login</p>
            </div>
            <form onSubmit={handleCreateStudent} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">First Name</label>
                  <input
                    type="text"
                    required
                    value={formData.first_name}
                    onChange={e => setFormData({ ...formData, first_name: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Middle Name</label>
                  <input
                    type="text"
                    required
                    value={formData.middle_name}
                    onChange={e => setFormData({ ...formData, middle_name: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Academic unit</label>
                    <select
                      required
                      value={formData.class_id}
                      onChange={e => {
                        const selected = classes.find((item) => item.id === e.target.value);
                        setFormData({ ...formData, class_id: e.target.value, division_id: selected?.divisions?.[0]?.id || '' });
                      }}
                      className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                    >
                      <option value="">Select academic unit</option>
                      {classes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Division</label>
                    <select
                      required
                      value={formData.division_id}
                      onChange={e => setFormData({ ...formData, division_id: e.target.value })}
                      className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                    >
                      <option value="">Select division</option>
                      {(classes.find((item) => item.id === formData.class_id)?.divisions || []).map((division: { id: string; name: string }) => <option key={division.id} value={division.id}>{division.name}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Last Name</label>
                  <input
                    type="text"
                    required
                    value={formData.last_name}
                    onChange={e => setFormData({ ...formData, last_name: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="block font-semibold text-slate-700 mb-1">Official Email</label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={e => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Password</label>
                  <input
                    type="password"
                    required
                    value={formData.password}
                    onChange={e => setFormData({ ...formData, password: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Student ID (Admission Number)</label>
                  <input
                    type="text"
                    required
                    placeholder="ADM-2026-XXX"
                    value={formData.admission_number}
                    onChange={e => setFormData({ ...formData, admission_number: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Gender</label>
                  <select
                    required
                    value={formData.gender}
                    onChange={e => setFormData({ ...formData, gender: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  >
                    <option value="">Select gender</option>
                    <option value="MALE">Male</option>
                    <option value="FEMALE">Female</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border rounded-lg font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 bg-brand-600 text-white rounded-lg font-bold hover:bg-brand-700"
                >
                  {isSubmitting ? 'Enrolling...' : 'Confirm Admission'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
