import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import {
  MessageSquare,
  Star,
  Send,
  CheckCircle2,
  BarChart3,
  Plus,
  ShieldCheck,
  AlertCircle,
  Users
} from 'lucide-react';

export const FeedbackPage: React.FC = () => {
  const { activeRole } = useAuth();
  const isPrincipal = activeRole === 'PRINCIPAL' || activeRole === 'SUPER_ADMIN';

  const [activeTab, setActiveTab] = useState<'RESPOND' | 'ANALYTICS' | 'CREATE'>(
    isPrincipal ? 'ANALYTICS' : 'RESPOND'
  );

  const [forms, setForms] = useState<any[]>([]);
  const [selectedForm, setSelectedForm] = useState<any | null>(null);
  const [analytics, setAnalytics] = useState<any | null>(null);
  const [answers, setAnswers] = useState<Record<string, { rating?: number; text?: string }>>({});
  const [submitted, setSubmitted] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Create Form State
  const [newTitle, setNewTitle] = useState('');
  const [newTargetRole, setNewTargetRole] = useState('STUDENT');
  const [newIsAnonymous, setNewIsAnonymous] = useState(true);
  const [newEndDate, setNewEndDate] = useState('');
  const [newQ1, setNewQ1] = useState('');
  const [newQ2, setNewQ2] = useState('');

  const loadForms = async () => {
    try {
      const data = await api.get<any[]>('/feedback/forms');
      setForms(data);
      if (data.length > 0 && !selectedForm) {
        selectForm(data[0]);
      }
    } catch (err) {
      console.error('Failed to load feedback forms', err);
    }
  };

  useEffect(() => {
    loadForms();
  }, [activeRole]);

  const selectForm = async (form: any) => {
    setSelectedForm(form);
    setAnswers({});
    setSubmitted(false);
    setErrorMsg(null);
    setSuccessMsg(null);

    if (isPrincipal) {
      try {
        const aData = await api.get<any>(`/feedback/forms/${form.id}/analytics`);
        setAnalytics(aData);
      } catch (err) {
        console.error('Failed to fetch analytics', err);
      }
    }
  };

  const handleRating = (qId: string, val: number) => {
    setAnswers(prev => ({
      ...prev,
      [qId]: { ...prev[qId], rating: val },
    }));
  };

  const handleText = (qId: string, text: string) => {
    setAnswers(prev => ({
      ...prev,
      [qId]: { ...prev[qId], text },
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedForm) return;
    setErrorMsg(null);

    const formattedAnswers = Object.entries(answers).map(([qId, val]) => ({
      question_id: qId,
      rating_value: val.rating,
      text_response: val.text,
    }));

    try {
      await api.post(`/feedback/forms/${selectedForm.id}/respond`, {
        answers: formattedAnswers,
      });
      setSubmitted(true);
      setSuccessMsg('Academic feedback submitted successfully!');
    } catch (err: any) {
      setErrorMsg(err.message || 'Submission failed');
    }
  };

  const handleCreateForm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle || !newQ1) return;
    setErrorMsg(null);
    setSuccessMsg(null);

    const questions: any[] = [
      { question_text: newQ1, question_type: 'RATING_1_5', display_order: 1 },
    ];
    if (newQ2) {
      questions.push({ question_text: newQ2, question_type: 'TEXT', display_order: 2 });
    }

    try {
      await api.post('/feedback/forms', {
        title: newTitle,
        target_role: newTargetRole,
        is_anonymous: newIsAnonymous,
        end_date: newEndDate || null,
        questions,
      });
      setSuccessMsg(`Feedback form '${newTitle}' published successfully!`);
      setNewTitle('');
      setNewQ1('');
      setNewQ2('');
      setNewEndDate('');
      loadForms();
      setActiveTab('ANALYTICS');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create feedback form');
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight font-display flex items-center gap-2">
            <MessageSquare className="w-7 h-7 text-brand-600" />
            Academic Feedback & Continuous Improvement
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Standard-driven stakeholder surveys with mathematical aggregation and anonymous confidentiality
          </p>
        </div>

        {isPrincipal && (
          <div className="flex items-center space-x-2">
            <button
              onClick={() => { setActiveTab('ANALYTICS'); setErrorMsg(null); setSuccessMsg(null); }}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition-all cursor-pointer flex items-center gap-1.5 ${
                activeTab === 'ANALYTICS'
                  ? 'bg-brand-600 text-white border-brand-600 shadow-sm'
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Survey Analytics</span>
            </button>
            <button
              onClick={() => { setActiveTab('CREATE'); setErrorMsg(null); setSuccessMsg(null); }}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition-all cursor-pointer flex items-center gap-1.5 ${
                activeTab === 'CREATE'
                  ? 'bg-brand-600 text-white border-brand-600 shadow-sm'
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
              }`}
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Survey</span>
            </button>
          </div>
        )}
      </div>

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm font-semibold flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* VIEW 1: PRINCIPAL SURVEY ANALYTICS */}
      {isPrincipal && activeTab === 'ANALYTICS' && (
        <div className="space-y-6">
          {/* Form Picker */}
          <div className="flex flex-wrap gap-2">
            {forms.map(f => (
              <button
                key={f.id}
                onClick={() => selectForm(f)}
                className={`px-4 py-2 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
                  selectedForm?.id === f.id
                    ? 'border-brand-600 bg-brand-50 text-brand-700'
                    : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                }`}
              >
                {f.title} ({f.target_role})
              </button>
            ))}
          </div>

          {analytics ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-100">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-brand-700 bg-brand-50 px-2.5 py-0.5 rounded">
                    {analytics.is_anonymous ? '100% Anonymized Responses' : 'Identified Feedback'}
                  </span>
                  <h2 className="text-xl font-bold text-slate-900 mt-2 font-display">
                    {analytics.title}
                  </h2>
                  <p className="text-xs text-slate-500">
                    Target Audience: {analytics.target_role} • Total Verified Submissions: {analytics.total_submissions}
                  </p>
                </div>
                <div className="bg-brand-50 text-brand-800 px-4 py-2 rounded-xl border border-brand-100 text-center">
                  <span className="text-[10px] font-bold uppercase text-brand-600">Respondent Count</span>
                  <h4 className="text-xl font-extrabold">{analytics.total_submissions}</h4>
                </div>
              </div>

              {/* Questions Analytics List */}
              <div className="space-y-6">
                {analytics.questions?.map((q: any) => (
                  <div key={q.question_id} className="p-5 rounded-xl border border-slate-100 bg-slate-50/50 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-bold text-slate-900">{q.question_text}</h4>
                      {q.average_rating !== null && (
                        <div className="flex items-center space-x-1.5 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-lg">
                          <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                          <span className="text-xs font-bold text-amber-900">{q.average_rating} / 5.0</span>
                        </div>
                      )}
                    </div>

                    {/* Rating Breakdown Bar */}
                    {q.question_type === 'RATING_1_5' && q.rating_distribution && (
                      <div className="space-y-1.5 pt-2">
                        {[5, 4, 3, 2, 1].map(star => {
                          const count = q.rating_distribution[String(star)] || 0;
                          const total = q.total_responses || 1;
                          const pct = Math.round((count / total) * 100);
                          return (
                            <div key={star} className="flex items-center text-xs space-x-2">
                              <span className="w-8 font-semibold text-slate-600">{star} ★</span>
                              <div className="flex-1 bg-slate-200 h-2 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-amber-400 rounded-full"
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                              <span className="w-12 text-right text-slate-500 font-semibold">{count} ({pct}%)</span>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Text Comments */}
                    {q.comments && q.comments.length > 0 && (
                      <div className="space-y-2 pt-2 border-t border-slate-200">
                        <span className="text-[11px] font-bold uppercase text-slate-500">
                          Confidential Feedback Submissions ({q.comments.length}):
                        </span>
                        <div className="space-y-1.5 max-h-48 overflow-y-auto">
                          {q.comments.map((c: string, idx: number) => (
                            <div key={idx} className="p-3 bg-white rounded-lg border border-slate-200 text-xs text-slate-700 italic">
                              "{c}"
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-400">
              Select a feedback form to inspect aggregate responses and ratings.
            </div>
          )}
        </div>
      )}

      {/* VIEW 2: PRINCIPAL CREATE SURVEY */}
      {isPrincipal && activeTab === 'CREATE' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs">
          <h3 className="text-lg font-bold text-slate-900 font-display mb-4">
            Create New Academic Feedback Form
          </h3>

          <form onSubmit={handleCreateForm} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Survey Title
              </label>
              <input
                type="text"
                placeholder="e.g. Physics & Chemistry Laboratory Evaluation"
                value={newTitle}
                onChange={e => setNewTitle(e.target.value)}
                required
                className="w-full text-xs p-3 border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Target Audience
                </label>
                <select
                  value={newTargetRole}
                  onChange={e => setNewTargetRole(e.target.value)}
                  className="w-full text-xs p-2.5 border rounded-xl bg-white"
                >
                  <option value="STUDENT">Enrolled Students</option>
                  <option value="FACULTY">Faculty Members</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Privacy Guarantee
                </label>
                <select
                  value={newIsAnonymous ? 'YES' : 'NO'}
                  onChange={e => setNewIsAnonymous(e.target.value === 'YES')}
                  className="w-full text-xs p-2.5 border rounded-xl bg-white"
                >
                  <option value="YES">100% Anonymous</option>
                  <option value="NO">Identified (Display Name)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Submission Deadline
                </label>
                <input
                  type="date"
                  value={newEndDate}
                  onChange={e => setNewEndDate(e.target.value)}
                  className="w-full text-xs p-2.5 border rounded-xl bg-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Question 1: Rating (1 to 5 Stars)
              </label>
              <input
                type="text"
                placeholder="e.g. How clear and engaging were the physics practical lectures?"
                value={newQ1}
                onChange={e => setNewQ1(e.target.value)}
                required
                className="w-full text-xs p-3 border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Question 2: Open-ended Qualitative Suggestions (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. Suggestions for laboratory equipment improvements or subject doubt solving:"
                value={newQ2}
                onChange={e => setNewQ2(e.target.value)}
                className="w-full text-xs p-3 border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-100">
              <button
                type="submit"
                className="px-6 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-md shadow-brand-500/20 transition-all flex items-center gap-2 cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Publish Feedback Form</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* VIEW 3: STUDENT & FACULTY QUESTIONNAIRE */}
      {(!isPrincipal || activeTab === 'RESPOND') && (
        <div>
          {submitted ? (
            <div className="bg-white rounded-2xl border border-emerald-200 p-8 text-center space-y-3">
              <CheckCircle2 className="w-12 h-12 text-emerald-600 mx-auto" />
              <h2 className="text-xl font-bold text-slate-900 font-display">
                Feedback Submitted Successfully
              </h2>
              <p className="text-xs text-slate-600 max-w-md mx-auto">
                Your responses have been recorded confidentially. Thank you for helping elevate teaching and laboratory standards.
              </p>
            </div>
          ) : selectedForm ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs space-y-6">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-brand-700 bg-brand-50 px-2 py-0.5 rounded">
                  {selectedForm.is_anonymous ? '100% Anonymous Feedback' : 'Identified Academic Survey'}
                </span>
                <h2 className="text-xl font-bold text-slate-900 mt-2 font-display">
                  {selectedForm.title}
                </h2>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                {selectedForm.questions.map((q: any) => (
                  <div key={q.id} className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 space-y-3">
                    <p className="text-sm font-semibold text-slate-900">{q.question_text}</p>
                    {q.question_type === 'RATING_1_5' ? (
                      <div className="flex items-center space-x-2">
                        {[1, 2, 3, 4, 5].map(star => {
                          const active = (answers[q.id]?.rating || 0) >= star;
                          return (
                            <button
                              key={star}
                              type="button"
                              onClick={() => handleRating(q.id, star)}
                              className="p-1 hover:scale-110 transition-transform cursor-pointer"
                            >
                              <Star
                                className={`w-6 h-6 ${
                                  active
                                    ? 'fill-amber-400 text-amber-400'
                                    : 'text-slate-300 hover:text-slate-400'
                                }`}
                              />
                            </button>
                          );
                        })}
                        <span className="text-xs text-slate-500 ml-2 font-semibold">
                          {answers[q.id]?.rating ? `${answers[q.id]?.rating} / 5` : 'Rate'}
                        </span>
                      </div>
                    ) : (
                      <textarea
                        rows={3}
                        value={answers[q.id]?.text || ''}
                        onChange={e => handleText(q.id, e.target.value)}
                        placeholder="Enter suggestions or comments..."
                        className="w-full text-xs p-3 border rounded-xl bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                      />
                    )}
                  </div>
                ))}

                <button
                  type="submit"
                  className="w-full py-3 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-md shadow-brand-500/20 transition-all flex items-center justify-center space-x-2 cursor-pointer"
                >
                  <Send className="w-4 h-4" />
                  <span>Submit Academic Feedback</span>
                </button>
              </form>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-400">
              No feedback forms currently open for response.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
