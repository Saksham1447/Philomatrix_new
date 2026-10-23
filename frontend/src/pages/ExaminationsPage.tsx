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
  FileText
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const ExaminationsPage: React.FC = () => {
  const { user, activeRole, activeChild } = useAuth();
  const [examinations, setExaminations] = useState<Examination[]>([]);
  const [selectedExam, setSelectedExam] = useState<Examination | null>(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
  const [divisions, setDivisions] = useState<any[]>([]);
  const [selectedDivisionId, setSelectedDivisionId] = useState<string>('');
  const [marksRoster, setMarksRoster] = useState<MarksEntry[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<MarksApprovalItem[]>([]);
  const [studentMarks, setStudentMarks] = useState<any[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

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
      if (classes.length > 0 && classes[0].divisions?.length > 0) {
        setDivisions(classes[0].divisions);
        if (!selectedDivisionId) {
          setSelectedDivisionId(classes[0].divisions[0].id);
        }
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

  // Load marks roster when subject and division are selected
  useEffect(() => {
    if (activeRole === 'FACULTY' && selectedSubjectId && selectedDivisionId) {
      loadMarksRoster();
    }
  }, [selectedSubjectId, selectedDivisionId, activeRole]);

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
                      if (ex.subjects.length > 0) setSelectedSubjectId(ex.subjects[0].id);
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
                  onChange={e => setSelectedSubjectId(e.target.value)}
                  className="mt-1 px-3 py-1.5 text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg"
                >
                  {selectedExam?.subjects.map(s => (
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
                  {divisions.map(d => (
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
                disabled={isSubmitting}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold rounded-xl transition-colors flex items-center space-x-1 cursor-pointer"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save Draft</span>
              </button>
              <button
                onClick={() => handleSaveMarks(true)}
                disabled={isSubmitting}
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
                  <th className="py-2.5 px-3 text-center">Theory (Max 70)</th>
                  <th className="py-2.5 px-3 text-center">Practical (Max 30)</th>
                  <th className="py-2.5 px-3 text-center">Total (100)</th>
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
                        max="70"
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
                        max="30"
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
