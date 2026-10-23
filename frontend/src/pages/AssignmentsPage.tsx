import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Assignment } from '../types';
import { BookOpen, Plus, Calendar, Clock, CheckCircle2, Send, FileCheck } from 'lucide-react';

export const AssignmentsPage: React.FC = () => {
  const { user, activeRole } = useAuth();
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [selectedAssignment, setSelectedAssignment] = useState<Assignment | null>(null);
  const [submissionText, setSubmissionText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // New assignment form
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newDueDate, setNewDueDate] = useState('');
  const [divisions, setDivisions] = useState<any[]>([]);
  const [subjects, setSubjects] = useState<any[]>([]);
  const [selectedDiv, setSelectedDiv] = useState('');
  const [selectedSub, setSelectedSub] = useState('');

  const loadAssignments = async () => {
    try {
      const data = await api.get<Assignment[]>('/assignments');
      setAssignments(data);
    } catch (err) {
      console.error('Failed to load assignments', err);
    }
  };

  useEffect(() => {
    loadAssignments();
    const loadMeta = async () => {
      try {
        const cls = await api.get<any[]>('/academics/classes');
        if (cls.length > 0 && cls[0].divisions.length > 0) {
          setDivisions(cls[0].divisions);
          setSelectedDiv(cls[0].divisions[0].id);
        }
        const subs = await api.get<any[]>('/academics/subjects');
        setSubjects(subs);
        if (subs.length > 0) {
          setSelectedSub(subs[0].id);
        }
      } catch (err) {
        console.error('Failed to load assignment metadata', err);
      }
    };
    loadMeta();
  }, [activeRole]);

  const handleCreateAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await api.post('/assignments', {
        division_id: selectedDiv,
        subject_id: selectedSub,
        title: newTitle,
        description: newDesc,
        due_date: new Date(newDueDate).toISOString(),
      });
      setShowCreateModal(false);
      setNewTitle('');
      setNewDesc('');
      loadAssignments();
    } catch (err: any) {
      alert(err.message || 'Failed to create assignment');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitSolution = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAssignment) return;
    setIsSubmitting(true);
    try {
      await api.post(`/assignments/${selectedAssignment.id}/submit`, {
        submission_text: submissionText,
      });
      alert('Homework submitted successfully!');
      setShowSubmitModal(false);
      setSubmissionText('');
      loadAssignments();
    } catch (err: any) {
      alert(err.message || 'Submission failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight font-display flex items-center gap-2">
            <BookOpen className="w-7 h-7 text-brand-600" />
            Homework & Academic Assignments
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Subject-wise assignments, practical exercises, and solution submission tracking
          </p>
        </div>

        {activeRole === 'FACULTY' && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-md shadow-brand-500/20 transition-all flex items-center space-x-1.5 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Create Assignment</span>
          </button>
        )}
      </div>

      {/* Assignment Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {assignments.map(a => (
          <div
            key={a.id}
            className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs flex flex-col justify-between space-y-4 hover:border-brand-300 transition-all"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold text-brand-700 bg-brand-50 px-2 py-0.5 rounded">
                  {a.subject_name}
                </span>
                <span className="text-xs text-slate-400">
                  {a.class_name} • Div {a.division_name}
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900">{a.title}</h3>
              <p className="text-xs text-slate-600 mt-1 line-clamp-3">{a.description}</p>
            </div>

            <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-500 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-amber-500" />
                Due: {new Date(a.due_date).toLocaleDateString()}
              </span>

              {activeRole === 'STUDENT' && (
                <button
                  onClick={() => {
                    setSelectedAssignment(a);
                    setShowSubmitModal(true);
                  }}
                  className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-colors ${
                    a.is_submitted_by_student
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-brand-600 text-white hover:bg-brand-700'
                  }`}
                >
                  {a.is_submitted_by_student ? 'Submitted' : 'Submit Solution'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900 font-display">Create Assignment</h2>
            <form onSubmit={handleCreateAssignment} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Subject</label>
                  <select
                    value={selectedSub}
                    onChange={e => setSelectedSub(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  >
                    {subjects.map(s => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Division</label>
                  <select
                    value={selectedDiv}
                    onChange={e => setSelectedDiv(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  >
                    {divisions.map(d => (
                      <option key={d.id} value={d.id}>
                        Division {d.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Assignment Title</label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  placeholder="e.g. Physics Numerical Problems: Chapter 4"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Instructions</label>
                <textarea
                  rows={3}
                  required
                  value={newDesc}
                  onChange={e => setNewDesc(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  placeholder="Provide detailed instructions or textbook questions..."
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Due Date</label>
                <input
                  type="datetime-local"
                  required
                  value={newDueDate}
                  onChange={e => setNewDueDate(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border rounded-lg font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 bg-brand-600 text-white rounded-lg font-bold hover:bg-brand-700"
                >
                  {isSubmitting ? 'Publishing...' : 'Publish Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Submit Modal */}
      {showSubmitModal && selectedAssignment && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900 font-display">
              Submit Solution: {selectedAssignment.title}
            </h2>
            <form onSubmit={handleSubmitSolution} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Solution Text / Notes / Online Link
                </label>
                <textarea
                  rows={5}
                  required
                  value={submissionText}
                  onChange={e => setSubmissionText(e.target.value)}
                  placeholder="Enter your completed numerical derivation or notes here..."
                  className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setShowSubmitModal(false)}
                  className="px-4 py-2 border rounded-lg font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 bg-emerald-600 text-white rounded-lg font-bold hover:bg-emerald-700"
                >
                  {isSubmitting ? 'Submitting...' : 'Confirm Submission'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
