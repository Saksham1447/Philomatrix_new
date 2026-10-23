import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Notice } from '../types';
import { Bell, Plus, Calendar, Tag, ShieldCheck, AlertCircle } from 'lucide-react';

export const NoticesPage: React.FC = () => {
  const { activeRole } = useAuth();
  const [notices, setNotices] = useState<Notice[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [audience, setAudience] = useState('ALL');
  const [priority, setPriority] = useState<'NORMAL' | 'URGENT'>('NORMAL');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadNotices = async () => {
    try {
      const data = await api.get<Notice[]>('/notices');
      setNotices(data);
    } catch (err) {
      console.error('Failed to load notices', err);
    }
  };

  useEffect(() => {
    loadNotices();
  }, [activeRole]);

  const handlePostNotice = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await api.post('/notices', {
        title,
        content,
        audience_role: audience,
        priority,
      });
      setShowModal(false);
      setTitle('');
      setContent('');
      loadNotices();
    } catch (err: any) {
      alert(err.message || 'Failed to post notice');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight font-display flex items-center gap-2">
            <Bell className="w-7 h-7 text-brand-600" />
            Notices & Official Bulletins
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Centralized communications board scoped by audience, class, and priority
          </p>
        </div>

        {(activeRole === 'PRINCIPAL' || activeRole === 'FACULTY' || activeRole === 'SUPER_ADMIN') && (
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-md shadow-brand-500/20 transition-all flex items-center space-x-1.5 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Post New Notice</span>
          </button>
        )}
      </div>

      {/* Notices List */}
      <div className="space-y-4">
        {notices.map(n => (
          <div
            key={n.id}
            className={`bg-white rounded-2xl p-6 border shadow-xs transition-all ${
              n.priority === 'URGENT'
                ? 'border-rose-200 bg-rose-50/20'
                : 'border-slate-200'
            }`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <div className="flex items-center space-x-2">
                <span
                  className={`text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                    n.priority === 'URGENT'
                      ? 'bg-rose-100 text-rose-800 border border-rose-300'
                      : 'bg-brand-50 text-brand-700 border border-brand-200'
                  }`}
                >
                  {n.priority}
                </span>
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">
                  Target: {n.audience_role}
                </span>
              </div>
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                {new Date(n.created_at).toLocaleDateString()}
              </span>
            </div>

            <h3 className="text-lg font-bold text-slate-900">{n.title}</h3>
            <p className="text-xs sm:text-sm text-slate-700 mt-2 leading-relaxed whitespace-pre-line">
              {n.content}
            </p>

            <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-400">
              Published by <span className="font-semibold text-slate-600">{n.published_by_name || 'Administration'}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900 font-display">Post Notice</h2>
            <form onSubmit={handlePostNotice} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Notice Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  placeholder="e.g. Schedule for Preliminary Board Practical Examinations"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Target Audience</label>
                  <select
                    value={audience}
                    onChange={e => setAudience(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  >
                    <option value="ALL">All College Community</option>
                    <option value="FACULTY">Faculty Only</option>
                    <option value="STUDENT">Students Only</option>
                    <option value="PARENT">Parents Only</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Priority</label>
                  <select
                    value={priority}
                    onChange={e => setPriority(e.target.value as any)}
                    className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  >
                    <option value="NORMAL">Normal Priority</option>
                    <option value="URGENT">Urgent Alert</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Notice Description</label>
                <textarea
                  rows={4}
                  required
                  value={content}
                  onChange={e => setContent(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg bg-slate-50"
                  placeholder="Write official announcement..."
                />
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
                  {isSubmitting ? 'Posting...' : 'Post Notice'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
