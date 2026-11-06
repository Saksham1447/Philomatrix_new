import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Examination, MarksApprovalItem, MarksEntry } from '../types';
import {
  Award,
  CheckCircle2,
  Clock,
  Send,
  Save,
  Check,
  X,
  ShieldCheck,
  AlertCircle,
  FileText,
  Plus,
  Pencil,
  Trash2
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const ExaminationsPage: React.FC = () => {
  const { user, activeRole, activeChild } = useAuth();
  const [examinations, setExaminations] = useState<Examination[]>([]);
  const [selectedExam, setSelectedExam] = useState<Examination | null>(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
  const [divisions, setDivisions] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [academicYears, setAcademicYears] = useState<any[]>([]);
  const [academicSubjects, setAcademicSubjects] = useState<any[]>([]);
  const [creationClassSubjectIds, setCreationClassSubjectIds] = useState<string[]>([]);
  const [assignments, setAssignments] = useState<any[]>([]);
  const [selectedDivisionId, setSelectedDivisionId] = useState<string>('');
  const [marksRoster, setMarksRoster] = useState<MarksEntry[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<MarksApprovalItem[]>([]);
  const [studentMarks, setStudentMarks] = useState<any[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);
  const [showCreateExam, setShowCreateExam] = useState(false);
  const [editingExam, setEditingExam] = useState<Examination | null>(null);
  const [subjectSchedule, setSubjectSchedule] = useState<Record<string, { exam_date: string; start_time: string; end_time: string }>>({});
  const [examForm, setExamForm] = useState({
    academic_year_id: '',
    name: '',
    exam_type: 'UNIT_TEST',
    start_date: new Date().toISOString().slice(0, 10),
    end_date: new Date().toISOString().slice(0, 10),
  });
  const [creationClassId, setCreationClassId] = useState('');
  const [creationDivisionId, setCreationDivisionId] = useState('');
  const [selectedAssignmentIds, setSelectedAssignmentIds] = useState<string[]>([]);

  const loadExams = async () => {
    try {
      const exams = await api.get<Examination[]>('/examinations');
      setExaminations(exams);
      if (exams.length > 0 && !selectedExam) {
        setSelectedExam(exams[0]);
        if (exams[0].subjects.length > 0) {
          setSelectedSubjectId(exams[0].subjects[0].id);
        }
      }

      if (activeRole === 'PRINCIPAL') {
        const approvals = await api.get<MarksApprovalItem[]>('/examinations/marks/approvals/pending');
        setPendingApprovals(approvals);
      }

      // Load classes/divisions
      const classes = await api.get<any[]>('/academics/classes');
      setClasses(classes);
      setDivisions(classes.flatMap((item: any) => item.divisions || []));
      if (classes.length > 0 && classes[0].divisions?.length > 0) {
        if (!selectedDivisionId) {
          setSelectedDivisionId(classes[0].divisions[0].id);
        }
      }
      if (activeRole === 'PRINCIPAL' || activeRole === 'OFFICE_STAFF') {
        const [years, assignmentList, subjectList] = await Promise.all([
          api.get<any[]>('/academics/years'),
          api.get<any[]>('/faculty/assignments'),
          api.get<any[]>('/academics/subjects'),
        ]);
        setAcademicYears(years);
        setAssignments(assignmentList);
        setAcademicSubjects(subjectList);
        const currentYear = years.find((year: any) => year.is_current) || years[0];
        if (currentYear) setExamForm(form => ({ ...form, academic_year_id: form.academic_year_id || currentYear.id }));
        const firstClass = classes[0];
        if (firstClass) {
          setCreationClassId(firstClass.id);
          setCreationDivisionId(firstClass.divisions?.[0]?.id || '');
        }
      } else if (activeRole === 'FACULTY') {
        setAssignments(await api.get<any[]>('/faculty/assignments'));
      }

      if (activeRole === 'STUDENT' && user?.student_id) {
        const marks = await api.get<any[]>(`/examinations/marks/student/${user.student_id}`);
        setStudentMarks(marks);
      } else if (activeRole === 'PARENT' && activeChild) {
        const marks = await api.get<any[]>(`/examinations/marks/student/${activeChild.id}`);
        setStudentMarks(marks);
      }
    } catch (err) {
      console.error('Failed to load examinations', err);
    }
  };

  useEffect(() => {
    loadExams();
  }, [activeRole, activeChild]);

  const examSubjectsForTeacher = selectedExam?.subjects.filter(subject =>
    activeRole !== 'FACULTY' || assignments.some(assignment =>
      assignment.subject_id === subject.subject_id &&
      (!subject.division_id || assignment.division_id === subject.division_id) &&
      (!selectedExam?.academic_year_id || assignment.academic_year_id === selectedExam.academic_year_id)
    )
  ) || [];

  const selectedExamSubject = selectedExam?.subjects.find(subject => subject.id === selectedSubjectId);
  const eligibleTeacherDivisions = selectedExamSubject
    ? assignments
      .filter(assignment => assignment.subject_id === selectedExamSubject.subject_id &&
        assignment.academic_year_id === selectedExam?.academic_year_id)
      .map(assignment => divisions.find(division => division.id === assignment.division_id))
      .filter((division, index, list) => division && division.class_id === selectedExamSubject.class_id &&
        list.findIndex(item => item?.id === division.id) === index)
    : [];
  const canLoadSelectedRoster = activeRole === 'FACULTY' && Boolean(selectedSubjectId) &&
    eligibleTeacherDivisions.some(division => division.id === selectedDivisionId);
  useEffect(() => {
    if (activeRole === 'FACULTY' && selectedExamSubject && eligibleTeacherDivisions.length > 0) {
      if (!eligibleTeacherDivisions.some(division => division.id === selectedDivisionId)) {
        setSelectedDivisionId(selectedExamSubject.division_id || eligibleTeacherDivisions[0].id);
      }
    }
  }, [activeRole, selectedSubjectId, selectedExam?.id, assignments, selectedDivisionId]);
  useEffect(() => {
    if (activeRole !== 'FACULTY' || !selectedExam) return;
    const assignedSubject = selectedExam.subjects.find(subject => assignments.some(assignment =>
      assignment.subject_id === subject.subject_id &&
      assignment.academic_year_id === selectedExam.academic_year_id &&
      (!subject.division_id || assignment.division_id === subject.division_id)
    ));
    if (assignedSubject && !examSubjectsForTeacher.some(subject => subject.id === selectedSubjectId)) {
      selectTeacherSubject(assignedSubject.id, selectedExam);
    }
  }, [activeRole, selectedExam?.id, assignments, selectedSubjectId]);
  const creationDivisions = classes.find(item => item.id === creationClassId)?.divisions || [];
  useEffect(() => {
    if (!creationClassId || !examForm.academic_year_id) {
      setCreationClassSubjectIds([]);
      return;
    }
    let active = true;
    api.get<any[]>(`/academics/classes/${creationClassId}/subjects?academic_year_id=${encodeURIComponent(examForm.academic_year_id)}`)
      .then(subjects => { if (active) setCreationClassSubjectIds(subjects.map(subject => subject.id)); })
      .catch(err => {
        if (active) {
          setCreationClassSubjectIds([]);
          setFeedbackMsg(`Error: Could not load class subjects: ${err.message}`);
        }
      });
    return () => { active = false; };
  }, [creationClassId, examForm.academic_year_id]);
  const availableSubjectAssignments = assignments.filter(assignment =>
    assignment.academic_year_id === examForm.academic_year_id &&
    assignment.division_id === creationDivisionId &&
    assignment.class_id === creationClassId &&
    creationClassSubjectIds.includes(assignment.subject_id)
  );
  const hasClassCurriculum = creationClassSubjectIds.length > 0;

  const getSubjectSchedule = (key: string, defaultDate = examForm.start_date) =>
    subjectSchedule[key] || { exam_date: defaultDate, start_time: '09:00', end_time: '10:00' };

  const handleCreateExam = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    setFeedbackMsg(null);
    try {
      const selectedItems = editingExam
        ? editingExam.subjects.map(subject => ({
          id: subject.id,
          subject_id: subject.subject_id,
          class_id: subject.class_id,
          division_id: subject.division_id,
          faculty_id: subject.faculty_id,
          max_theory_marks: subject.max_theory_marks,
          max_practical_marks: subject.max_practical_marks,
          min_passing_marks: subject.min_passing_marks,
        }))
        : assignments.filter(assignment => selectedAssignmentIds.includes(assignment.id));
      const missingSchedule = selectedItems.find(item => {
        const schedule = getSubjectSchedule(item.id);
        return !schedule.exam_date || !schedule.start_time || !schedule.end_time || schedule.end_time <= schedule.start_time;
      });
      if (missingSchedule) {
        setFeedbackMsg('Set a valid date, start time, and end time for every subject. End time must be after start time.');
        return;
      }
      const scheduledDates = selectedItems
        .map(item => getSubjectSchedule(item.id).exam_date)
        .sort();
      const payload = {
        ...examForm,
        start_date: scheduledDates[0],
        end_date: scheduledDates[scheduledDates.length - 1],
        subjects: selectedItems.map(item => {
          const assignment = item as any;
          const subject = academicSubjects.find(item => item.id === assignment.subject_id);
          const maxTheory = Number(subject?.max_theory_marks ?? 70);
          const maxPractical = Number(subject?.max_practical_marks ?? 30);
          const schedule = getSubjectSchedule(assignment.id);
          return {
            subject_id: assignment.subject_id,
            class_id: assignment.class_id || creationClassId,
            division_id: assignment.division_id,
            faculty_id: assignment.faculty_id,
            max_theory_marks: Number(assignment.max_theory_marks ?? maxTheory),
            max_practical_marks: Number(assignment.max_practical_marks ?? maxPractical),
            min_passing_marks: Number(assignment.min_passing_marks ?? ((maxTheory + maxPractical) * Number(subject?.min_pass_percentage ?? 35) / 100)),
            exam_date: schedule.exam_date,
            start_time: schedule.start_time,
            end_time: schedule.end_time,
          };
        }),
      };
      if (editingExam) await api.put(`/examinations/${editingExam.id}`, payload);
      else await api.post('/examinations', payload);
      setShowCreateExam(false);
      setEditingExam(null);
      setSelectedAssignmentIds([]);
      setSubjectSchedule({});
      setFeedbackMsg(editingExam ? 'Examination schedule updated.' : 'Examination schedule created.');
      await loadExams();
    } catch (err: any) {
      setFeedbackMsg(`Error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const beginEditExam = (exam: Examination) => {
    setEditingExam(exam);
    setExamForm({
      academic_year_id: exam.academic_year_id,
      name: exam.name,
      exam_type: exam.exam_type,
      start_date: exam.start_date,
      end_date: exam.end_date,
    });
    setSubjectSchedule(Object.fromEntries(exam.subjects.map(subject => [
      subject.id,
      {
        exam_date: subject.exam_date || exam.start_date,
        start_time: subject.start_time?.slice(0, 5) || '09:00',
        end_time: subject.end_time?.slice(0, 5) || '10:00',
      },
    ])));
    setShowCreateExam(true);
    setFeedbackMsg(null);
  };

  const handleDeleteExam = async (exam: Examination) => {
    if (!window.confirm(`Delete "${exam.name}" and its subject schedule? This cannot be undone.`)) return;
    setFeedbackMsg(null);
    try {
      await api.delete(`/examinations/${exam.id}`);
      if (selectedExam?.id === exam.id) {
        setSelectedExam(null);
        setSelectedSubjectId('');
      }
      setFeedbackMsg('Examination schedule deleted.');
      await loadExams();
    } catch (err: any) {
      setFeedbackMsg(`Error: ${err.message}`);
    }
  };

  const scheduleRows = editingExam
    ? editingExam.subjects
    : availableSubjectAssignments.filter(assignment => selectedAssignmentIds.includes(assignment.id));

  // Load marks roster when subject and division are selected
  useEffect(() => {
    if (canLoadSelectedRoster) {
      loadMarksRoster();
    } else if (activeRole === 'FACULTY') {
      setMarksRoster([]);
    }
  }, [selectedSubjectId, selectedDivisionId, activeRole, canLoadSelectedRoster]);

  const loadMarksRoster = async () => {
    try {
      const data = await api.get<MarksEntry[]>(
        `/examinations/marks/roster?exam_subject_id=${selectedSubjectId}&division_id=${selectedDivisionId}`
      );
      setMarksRoster(data);
    } catch (err) {
      console.error('Failed to load marks roster', err);
    }
  };

  const updateStudentMark = (studentId: string, field: 'theory' | 'practical', val: string) => {
    const num = val === '' ? undefined : parseFloat(val);
    setMarksRoster(prev =>
      prev.map(item => {
        if (item.student_id === studentId) {
          const th = field === 'theory' ? num : item.theory_marks_obtained;
          const pr = field === 'practical' ? num : item.practical_marks_obtained;
          const tot = (th ?? 0) + (pr ?? 0);
          return {
            ...item,
            theory_marks_obtained: th,
            practical_marks_obtained: pr,
            total_obtained: tot,
          };
        }
        return item;
      })
    );
  };

  const handleSaveMarks = async (submitForApproval: boolean) => {
    setIsSubmitting(true);
    setFeedbackMsg(null);
    try {
      const payload = {
        exam_subject_id: selectedSubjectId,
        division_id: selectedDivisionId,
        submit_for_approval: submitForApproval,
        entries: marksRoster.map(r => ({
          student_id: r.student_id,
          theory_marks_obtained: r.theory_marks_obtained,
          practical_marks_obtained: r.practical_marks_obtained,
          is_absent: r.is_absent,
          is_exempt: r.is_exempt,
          teacher_remarks: r.teacher_remarks,
        })),
      };

      await api.post('/examinations/marks/save-draft', payload);
      setFeedbackMsg(
        submitForApproval
          ? 'Marks batch successfully submitted for Principal Moderation!'
          : 'Marks drafts saved locally.'
      );
      loadMarksRoster();
    } catch (err: any) {
      setFeedbackMsg(`Error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePrincipalApproval = async (approvalId: string, approved: boolean) => {
    try {
      await api.put(`/examinations/marks/approvals/${approvalId}/review`, {
        approved,
        review_comments: approved ? 'Approved by Principal' : 'Revision required',
      });
      loadExams();
    } catch (err: any) {
      alert(err.message || 'Approval action failed');
    }
  };

  const handlePublishResults = async (examId: string) => {
    try {
      await api.post(`/examinations/${examId}/publish`);
      alert('Examination results formally published to students and parents!');
      loadExams();
    } catch (err: any) {
      alert(err.message || 'Publication failed');
    }
  };

  const selectTeacherSubject = (subjectId: string, exam: Examination | null = selectedExam) => {
    setSelectedSubjectId(subjectId);
    const subject = exam?.subjects.find(item => item.id === subjectId);
    if (!subject) return;
    const matchingAssignment = assignments.find(assignment =>
      assignment.subject_id === subject.subject_id &&
      assignment.academic_year_id === exam?.academic_year_id &&
      (!subject.division_id || assignment.division_id === subject.division_id)
    );
    setSelectedDivisionId(subject.division_id || matchingAssignment?.division_id || '');
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight font-display flex items-center gap-2">
            <Award className="w-7 h-7 text-brand-600" />
            Examinations, Marks & Moderation Engine
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Theory & practical mark entry, Principal review, approval governance, and result publication
          </p>
        </div>

        {activeRole === 'PRINCIPAL' && selectedExam && (
          <button
            onClick={() => handlePublishResults(selectedExam.id)}
            disabled={selectedExam.is_published}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-xs transition-colors flex items-center space-x-1.5 cursor-pointer"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>{selectedExam.is_published ? 'Results Published' : 'Publish Examination Results'}</span>
          </button>
        )}
      </div>

      {feedbackMsg && (
        <div className="p-4 rounded-xl bg-brand-50 border border-brand-200 text-brand-900 text-sm font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-brand-600" /> {feedbackMsg}
        </div>
      )}

      {activeRole === 'FACULTY' && (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
          <h2 className="font-bold text-slate-900">My examination schedule and marks progress</h2>
          <div className="mt-3 divide-y divide-slate-100">
            {examinations.flatMap(exam => exam.subjects.filter(subject =>
              assignments.some(assignment => assignment.subject_id === subject.subject_id &&
                assignment.academic_year_id === exam.academic_year_id &&
                (!subject.division_id || assignment.division_id === subject.division_id))
            ).map(subject => (
              <div key={`${exam.id}-${subject.id}`} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div><p className="text-sm font-bold text-slate-800">{exam.name} · {subject.subject_name}</p><p className="text-xs text-slate-500">{subject.class_name}{subject.division_name ? ` / ${subject.division_name}` : ''} · {subject.exam_date || exam.start_date}{subject.start_time ? ` · ${subject.start_time.slice(0, 5)}–${subject.end_time?.slice(0, 5) || ''}` : ''}</p></div>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-bold text-slate-700">{subject.marks_status || 'NOT_STARTED'}</span>
              </div>
            )))}
            {examinations.every(exam => !exam.subjects.some(subject => assignments.some(assignment => assignment.subject_id === subject.subject_id && assignment.academic_year_id === exam.academic_year_id))) && <p className="py-6 text-center text-sm text-slate-400">No examination schedule is assigned to your subjects.</p>}
          </div>
        </section>
      )}

      {(activeRole === 'PRINCIPAL' || activeRole === 'OFFICE_STAFF') && (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-bold text-slate-900">Exam schedule and marks progress</h2>
              <p className="mt-1 text-xs text-slate-500">Division-specific subjects, assigned teachers, and entry status.</p>
            </div>
            <button type="button" onClick={() => {
              if (showCreateExam) {
                setShowCreateExam(false);
                setEditingExam(null);
                setSubjectSchedule({});
              } else {
                setEditingExam(null);
                setSelectedAssignmentIds([]);
                setSubjectSchedule({});
                setShowCreateExam(true);
              }
            }} className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-xs font-bold text-white hover:bg-brand-700">
              <Plus className="h-4 w-4" /> {showCreateExam ? 'Close form' : 'Schedule examination'}
            </button>
          </div>
          {showCreateExam && (
            <form onSubmit={handleCreateExam} className="mt-5 space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <label className="text-xs font-semibold text-slate-600">Examination name
                  <input required value={examForm.name} onChange={event => setExamForm({ ...examForm, name: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2" placeholder="e.g. Unit Test 1" />
                </label>
                <label className="text-xs font-semibold text-slate-600">Academic year
                  <select required disabled={Boolean(editingExam)} value={examForm.academic_year_id} onChange={event => { setExamForm({ ...examForm, academic_year_id: event.target.value }); setSelectedAssignmentIds([]); }} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 disabled:bg-slate-100">
                    <option value="">Select year</option>{academicYears.map(year => <option key={year.id} value={year.id}>{year.name}</option>)}
                  </select>
                </label>
                <label className="text-xs font-semibold text-slate-600">Examination type
                  <select value={examForm.exam_type} onChange={event => setExamForm({ ...examForm, exam_type: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2">
                    {['UNIT_TEST', 'TERMINAL', 'PRACTICAL', 'PRELIM', 'FINAL'].map(type => <option key={type} value={type}>{type.replace('_', ' ')}</option>)}
                  </select>
                </label>
                {!editingExam && <label className="text-xs font-semibold text-slate-600">Class
                  <select required value={creationClassId} onChange={event => { const nextClass = classes.find(item => item.id === event.target.value); setCreationClassId(event.target.value); setCreationDivisionId(nextClass?.divisions?.[0]?.id || ''); setSelectedAssignmentIds([]); }} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2">
                    <option value="">Select class</option>{classes.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                </label>}
                {!editingExam && <label className="text-xs font-semibold text-slate-600">Division
                  <select required value={creationDivisionId} onChange={event => { setCreationDivisionId(event.target.value); setSelectedAssignmentIds([]); }} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2">
                    <option value="">Select division</option>{creationDivisions.map((division: any) => <option key={division.id} value={division.id}>{division.name}</option>)}
                  </select>
                </label>}
              </div>
              <fieldset>
                <legend className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Subjects and assigned teachers</legend>
                {!editingExam && <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {availableSubjectAssignments.map(assignment => (
                    <label key={assignment.id} className="flex items-start gap-2 rounded-lg border border-slate-200 bg-white p-3 text-xs">
                      <input type="checkbox" checked={selectedAssignmentIds.includes(assignment.id)} onChange={event => {
                        setSelectedAssignmentIds(current => {
                          const withoutSubject = current.filter(itemId => assignments.find(item => item.id === itemId)?.subject_id !== assignment.subject_id);
                          return event.target.checked ? [...withoutSubject, assignment.id] : withoutSubject;
                        });
                        setSubjectSchedule(current => event.target.checked
                          ? { ...current, [assignment.id]: current[assignment.id] || { exam_date: examForm.start_date, start_time: '09:00', end_time: '10:00' } }
                          : Object.fromEntries(Object.entries(current).filter(([key]) => key !== assignment.id)));
                      }} />
                      <span><strong className="block text-slate-800">{assignment.subject_name} ({assignment.subject_code})</strong><span className="text-slate-500">{assignment.faculty_name}</span></span>
                    </label>
                  ))}
                </div>}
                {!editingExam && creationDivisionId && availableSubjectAssignments.length === 0 && <p className="text-xs text-slate-500">
                  {!hasClassCurriculum
                    ? <>No subjects are configured for this class and academic year. <Link className="font-semibold text-brand-600 underline" to={`/departments/${creationClassId}`}>Configure class subjects and division teachers</Link> first.</>
                    : <>The class subjects are configured, but no teachers are assigned to this division for the selected academic year. <Link className="font-semibold text-brand-600 underline" to={`/departments/${creationClassId}`}>Assign subject teachers</Link> first.</>}
                </p>}
                {editingExam && <p className="mb-3 text-xs text-slate-500">Edit each subject's examination date and time below. Subjects and teacher assignments are retained.</p>}
                {scheduleRows.map((item: any) => {
                  const schedule = getSubjectSchedule(item.id);
                  return <div key={item.id} className="mt-3 grid gap-3 rounded-lg border border-slate-200 bg-white p-3 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="self-center text-xs"><strong className="block text-slate-800">{item.subject_name}</strong><span className="text-slate-500">{item.faculty_name || academicSubjects.find(subject => subject.id === item.subject_id)?.name || 'Assigned teacher'}</span></div>
                    <label className="text-xs font-semibold text-slate-600">Exam date
                      <input aria-label={`${item.subject_name} exam date`} type="date" required value={schedule.exam_date} onChange={event => setSubjectSchedule(current => ({ ...current, [item.id]: { ...getSubjectSchedule(item.id), exam_date: event.target.value } }))} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
                    </label>
                    <label className="text-xs font-semibold text-slate-600">Start time
                      <input aria-label={`${item.subject_name} start time`} type="time" required value={schedule.start_time} onChange={event => setSubjectSchedule(current => ({ ...current, [item.id]: { ...getSubjectSchedule(item.id), start_time: event.target.value } }))} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
                    </label>
                    <label className="text-xs font-semibold text-slate-600">End time
                      <input aria-label={`${item.subject_name} end time`} type="time" required min={schedule.start_time} value={schedule.end_time} onChange={event => setSubjectSchedule(current => ({ ...current, [item.id]: { ...getSubjectSchedule(item.id), end_time: event.target.value } }))} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
                    </label>
                  </div>;
                })}
              </fieldset>
              <button type="submit" disabled={isSubmitting || !examForm.name || !examForm.academic_year_id || (editingExam ? editingExam.subjects.length === 0 : selectedAssignmentIds.length === 0)} className="rounded-xl bg-brand-600 px-4 py-2 text-xs font-bold text-white disabled:opacity-50">
                {isSubmitting ? 'Saving…' : editingExam ? 'Save examination changes' : 'Create examination schedule'}
              </button>
            </form>
          )}
          <div className="mt-4 divide-y divide-slate-100">
            {examinations.flatMap(exam => exam.subjects.map(subject => (
              <div key={`${exam.id}-${subject.id}`} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                <div><p className="font-bold text-slate-800">{exam.name} · {subject.subject_name}</p><p className="text-xs text-slate-500">{subject.class_name}{subject.division_name ? ` / ${subject.division_name}` : ''} · {subject.faculty_name || 'Teacher not assigned'} · {subject.exam_date || exam.start_date}{subject.start_time ? ` · ${subject.start_time.slice(0, 5)}–${subject.end_time?.slice(0, 5) || ''}` : ''}</p></div>
                <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${subject.marks_status === 'APPROVED' ? 'bg-emerald-100 text-emerald-800' : subject.marks_status === 'PENDING' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'}`}>{subject.marks_status || 'NOT_STARTED'}</span>
                {exam.subjects[0]?.id === subject.id && <div className="flex gap-2">
                  <button type="button" title="Edit examination" disabled={exam.is_published || exam.subjects.some(item => item.marks_status && item.marks_status !== 'NOT_STARTED')} onClick={() => beginEditExam(exam)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-40"><Pencil className="h-3.5 w-3.5" />Edit</button>
                  <button type="button" title="Delete examination" disabled={exam.is_published || exam.subjects.some(item => item.marks_status && item.marks_status !== 'NOT_STARTED')} onClick={() => void handleDeleteExam(exam)} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-700 disabled:opacity-40"><Trash2 className="h-3.5 w-3.5" />Delete</button>
                </div>}
              </div>
            )))}
            {examinations.every(exam => exam.subjects.length === 0) && <p className="py-6 text-center text-sm text-slate-400">No examination schedules yet.</p>}
          </div>
        </section>
      )}

      {(activeRole === 'STUDENT' || activeRole === 'PARENT') && (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
          <h2 className="font-bold text-slate-900">Examination schedule</h2>
          <div className="mt-3 divide-y divide-slate-100">
            {examinations.flatMap(exam => exam.subjects.map(subject => (
              <div key={`${exam.id}-${subject.id}`} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div><p className="text-sm font-bold text-slate-800">{exam.name} · {subject.subject_name}</p><p className="text-xs text-slate-500">{subject.exam_date || exam.start_date}{subject.start_time ? ` · ${subject.start_time.slice(0, 5)}–${subject.end_time?.slice(0, 5) || ''}` : ''} · {subject.division_name ? `Division ${subject.division_name} · ` : ''}{subject.marks_status || 'NOT_STARTED'}</p></div>
                {exam.is_published && <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-[10px] font-bold text-emerald-800">Results published</span>}
              </div>
            )))}
            {examinations.every(exam => exam.subjects.length === 0) && <p className="py-6 text-center text-sm text-slate-400">No examination schedule is available for this class.</p>}
          </div>
        </section>
      )}

      {/* VIEW 1: PRINCIPAL MODERATION QUEUE */}
      {activeRole === 'PRINCIPAL' && pendingApprovals.length > 0 && (
        <div className="bg-white rounded-2xl border border-amber-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center space-x-2">
            <Clock className="w-5 h-5 text-amber-600" />
            <h3 className="text-base font-bold text-slate-900 font-display">
              Pending Faculty Marks Approval Queue ({pendingApprovals.length})
            </h3>
          </div>
          <div className="divide-y divide-slate-100">
            {pendingApprovals.map(appr => (
              <div key={appr.id} className="py-3 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-slate-900">
                    {appr.examination_name} — {appr.subject_name} ({appr.subject_code})
                  </h4>
                  <p className="text-xs text-slate-500">
                    Division {appr.division_name} • Submitted by {appr.submitted_by_name} on {new Date(appr.submitted_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handlePrincipalApproval(appr.id, true)}
                    className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg transition-colors cursor-pointer"
                  >
                    Approve Batch
                  </button>
                  <button
                    onClick={() => handlePrincipalApproval(appr.id, false)}
                    className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg transition-colors cursor-pointer"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* VIEW 2: FACULTY MARKS ENTRY GRID */}
      {activeRole === 'FACULTY' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
            <div className="flex flex-wrap items-center gap-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase">
                  Examination
                </label>
                <select
                  value={selectedExam?.id || ''}
                  onChange={e => {
                    const ex = examinations.find(x => x.id === e.target.value);
                    if (ex) {
                      setSelectedExam(ex);
                      const subject = ex.subjects.find(item => assignments.some(assignment =>
                        assignment.subject_id === item.subject_id &&
                        assignment.academic_year_id === ex.academic_year_id &&
                        (!item.division_id || assignment.division_id === item.division_id)
                      ));
                      selectTeacherSubject(subject?.id || '', ex);
                    }
                  }}
                  className="mt-1 px-3 py-1.5 text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg"
                >
                  {examinations.map(ex => (
                    <option key={ex.id} value={ex.id}>
                      {ex.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase">
                  Subject
                </label>
                <select
                  value={selectedSubjectId}
                  onChange={e => selectTeacherSubject(e.target.value)}
                  className="mt-1 px-3 py-1.5 text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg"
                >
                  {examSubjectsForTeacher.map(s => (
                    <option key={s.id} value={s.id}>
                      {s.subject_name} ({s.subject_code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase">
                  Division
                </label>
                <select
                  value={selectedDivisionId}
                  onChange={e => setSelectedDivisionId(e.target.value)}
                  className="mt-1 px-3 py-1.5 text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg"
                >
                  {eligibleTeacherDivisions.map((d: any) => (
                    <option key={d.id} value={d.id}>
                      Division {d.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleSaveMarks(false)}
                disabled={isSubmitting || !selectedSubjectId || !selectedDivisionId}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold rounded-xl transition-colors flex items-center space-x-1 cursor-pointer"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save Draft</span>
              </button>
              <button
                onClick={() => handleSaveMarks(true)}
                disabled={isSubmitting || !selectedSubjectId || !selectedDivisionId}
                className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors flex items-center space-x-1 cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Submit for Approval</span>
              </button>
            </div>
          </div>

          {/* Marks Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs font-semibold uppercase text-slate-500">
                  <th className="py-2.5 px-3">Roll</th>
                  <th className="py-2.5 px-3">Student Name</th>
                  <th className="py-2.5 px-3 text-center">Theory (Max {selectedExamSubject?.max_theory_marks ?? 70})</th>
                  <th className="py-2.5 px-3 text-center">Practical (Max {selectedExamSubject?.max_practical_marks ?? 30})</th>
                  <th className="py-2.5 px-3 text-center">Total ({(selectedExamSubject?.max_theory_marks ?? 70) + (selectedExamSubject?.max_practical_marks ?? 30)})</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {marksRoster.map(st => (
                  <tr key={st.student_id} className="hover:bg-slate-50/70">
                    <td className="py-3 px-3 font-semibold text-slate-700">
                      {st.roll_number || '-'}
                    </td>
                    <td className="py-3 px-3 font-semibold text-slate-900">
                      {st.student_name}
                      <span className="block text-xs font-normal text-slate-400">
                        {st.admission_number}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <input
                        type="number"
                        min="0"
                        max={selectedExamSubject?.max_theory_marks ?? 70}
                        step="0.5"
                        value={st.theory_marks_obtained ?? ''}
                        onChange={e => updateStudentMark(st.student_id, 'theory', e.target.value)}
                        className="w-20 px-2 py-1 text-center font-bold text-slate-800 bg-slate-50 border border-slate-200 rounded-lg text-sm"
                        placeholder="0.0"
                      />
                    </td>
                    <td className="py-3 px-3 text-center">
                      <input
                        type="number"
                        min="0"
                        max={selectedExamSubject?.max_practical_marks ?? 30}
                        step="0.5"
                        value={st.practical_marks_obtained ?? ''}
                        onChange={e => updateStudentMark(st.student_id, 'practical', e.target.value)}
                        className="w-20 px-2 py-1 text-center font-bold text-slate-800 bg-slate-50 border border-slate-200 rounded-lg text-sm"
                        placeholder="0.0"
                      />
                    </td>
                    <td className="py-3 px-3 text-center font-bold text-brand-700">
                      {st.total_obtained !== undefined ? st.total_obtained : '-'}
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`text-[11px] font-extrabold px-2 py-0.5 rounded-full ${
                          st.status === 'APPROVED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : st.status === 'SUBMITTED'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {st.status || 'DRAFT'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* VIEW 3: STUDENT & PARENT PUBLISHED SCORES */}
      {(activeRole === 'STUDENT' || activeRole === 'PARENT') && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200">
            <div>
              <h3 className="text-base font-bold text-slate-900 font-display">
                Official Published Examination Marks
              </h3>
              <p className="text-xs text-slate-500">
                Verified results released by Principal
              </p>
            </div>
            <Link
              to="/report-cards"
              className="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5"
            >
              <FileText className="w-3.5 h-3.5" /> Full Report Card
            </Link>
          </div>

          {studentMarks.length === 0 ? (
            <p className="text-sm text-slate-400 py-6 text-center">
              No published examination results available yet.
            </p>
          ) : (
            <div className="divide-y divide-slate-100">
              {studentMarks.map((m, idx) => (
                <div key={idx} className="py-3.5 flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">
                      {m.subject_name} ({m.subject_code})
                    </h4>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Theory: {m.theory_obtained ?? '-'} / {m.max_theory} • Practical: {m.practical_obtained ?? '-'} / {m.max_practical}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-lg font-extrabold text-slate-900">
                      {m.total_obtained ?? '-'} / {m.max_total}
                    </span>
                    <span className="block text-[11px] font-bold text-emerald-600">
                      {m.total_obtained && m.max_total ? `${Math.round((m.total_obtained / m.max_total) * 100)}%` : ''}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
