import React, { useEffect, useState } from 'react';
import { CalendarDays, Check, ClipboardCheck, Clock3, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { FacultyLeaveRequest } from '../types';

const statusStyles: Record<FacultyLeaveRequest['status'], string> = {
  PENDING: 'bg-amber-50 text-amber-700 border-amber-200',
  APPROVED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  REJECTED: 'bg-rose-50 text-rose-700 border-rose-200',
};

const formatDate = (value: string) =>
  new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

export const LeaveRequestsPage: React.FC = () => {
  const { activeRole } = useAuth();
  const isOfficeStaff = activeRole === 'OFFICE_STAFF';
  const [requests, setRequests] = useState<FacultyLeaveRequest[]>([]);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [reason, setReason] = useState('');
  const [reviewComments, setReviewComments] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRequests = async () => {
    try {
      setError(null);
      setRequests(await api.get<FacultyLeaveRequest[]>('/leave-requests'));
    } catch (err: any) {
      setError(err.message || 'Failed to load leave requests');
    }
  };

  useEffect(() => {
    loadRequests();
  }, [activeRole]);

  const submitRequest = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      await api.post('/leave-requests', { start_date: startDate, end_date: endDate, reason });
      setStartDate('');
      setEndDate('');
      setReason('');
      await loadRequests();
    } catch (err: any) {
      setError(err.message || 'Failed to submit leave request');
    } finally {
      setIsSubmitting(false);
    }
  };

  const reviewRequest = async (requestId: string, status: 'APPROVED' | 'REJECTED') => {
    try {
      await api.put(`/leave-requests/${requestId}/review`, {
        status,
        review_comments: reviewComments[requestId] || undefined,
      });
      await loadRequests();
    } catch (err: any) {
      setError(err.message || 'Failed to review leave request');
    }
  };

  return (
    <div className="space-y-6">
      <div className={isOfficeStaff ? 'flex items-start justify-between gap-4' : ''}>
        <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight font-display flex items-center gap-2">
          <ClipboardCheck className="w-7 h-7 text-brand-600" />
          Leave Requests
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          {isOfficeStaff ? 'Review leave applications submitted by faculty.' : 'Submit and track your leave applications.'}
        </p>
        </div>
        {isOfficeStaff && (
          <span className="shrink-0 px-3 py-1.5 rounded-lg bg-amber-50 text-amber-700 border border-amber-100 text-xs font-semibold">
            {requests.filter(request => request.status === 'PENDING').length} Pending
          </span>
        )}
      </div>

      {error && <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm">{error}</div>}

      {!isOfficeStaff && (
        <form onSubmit={submitRequest} className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
          <h2 className="font-bold text-slate-900">Apply for Leave</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="text-xs font-semibold text-slate-700">
              Start date
              <input required type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="mt-1 w-full px-3 py-2 border rounded-lg bg-slate-50" />
            </label>
            <label className="text-xs font-semibold text-slate-700">
              End date
              <input required type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="mt-1 w-full px-3 py-2 border rounded-lg bg-slate-50" />
            </label>
          </div>
          <label className="block text-xs font-semibold text-slate-700">
            Reason
            <textarea required minLength={3} rows={4} value={reason} onChange={e => setReason(e.target.value)} className="mt-1 w-full px-3 py-2 border rounded-lg bg-slate-50" placeholder="Explain the reason for your leave" />
          </label>
          <button disabled={isSubmitting} className="px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold">
            {isSubmitting ? 'Submitting...' : 'Submit Leave Request'}
          </button>
        </form>
      )}

      <div className={isOfficeStaff ? 'rounded-2xl border-t-4 border-orange-400 bg-white p-5 sm:p-6 shadow-sm' : 'space-y-4'}>
        {isOfficeStaff && <h2 className="sr-only">Faculty leave request queue</h2>}
        {requests.length === 0 && <div className="p-8 text-center text-sm text-slate-500">No leave requests found.</div>}
        <div className={isOfficeStaff ? 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4' : 'space-y-4'}>
        {requests.map(request => (
          <div key={request.id} className="rounded-xl border border-slate-200 p-4 sm:p-5 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-bold text-slate-900">{request.faculty_name} <span className="text-xs font-normal text-slate-500">({request.employee_id})</span></p>
                <p className="text-xs text-slate-500 mt-1">{request.reason}</p>
              </div>
              <span className={`px-2.5 py-1 rounded-md border text-[10px] font-semibold ${statusStyles[request.status]}`}>{request.status.charAt(0) + request.status.slice(1).toLowerCase()}</span>
            </div>
            <div className="mt-4 rounded-lg bg-slate-50 px-3 py-3">
              <p className="text-xs font-bold text-slate-700">Duration</p>
              <p className="text-xs text-slate-600 mt-1 flex items-center gap-1.5">
                <CalendarDays className="w-3.5 h-3.5 text-slate-500" />
                {formatDate(request.start_date)} to {formatDate(request.end_date)}
              </p>
            </div>
            {request.review_comments && <p className="mt-3 text-xs text-slate-500 border-t pt-3">Review note: {request.review_comments}</p>}
            {isOfficeStaff && request.status === 'PENDING' && (
              <div className="mt-4 space-y-2">
                <input value={reviewComments[request.id] || ''} onChange={e => setReviewComments({ ...reviewComments, [request.id]: e.target.value })} className="w-full px-3 py-2 border rounded-lg text-xs bg-white" placeholder="Optional review comment" />
                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => reviewRequest(request.id, 'APPROVED')} className="px-3 py-2 rounded-lg bg-sky-500 hover:bg-sky-600 text-white text-xs font-semibold flex items-center justify-center gap-1"><Check className="w-3.5 h-3.5" />Approve</button>
                  <button onClick={() => reviewRequest(request.id, 'REJECTED')} className="px-3 py-2 rounded-lg border border-rose-300 text-rose-600 hover:bg-rose-50 text-xs font-semibold flex items-center justify-center gap-1"><X className="w-3.5 h-3.5" />Reject</button>
                </div>
              </div>
            )}
            {request.status === 'PENDING' && !isOfficeStaff && <p className="mt-4 text-xs text-amber-700 flex items-center gap-1"><Clock3 className="w-3.5 h-3.5" />Awaiting office staff review</p>}
          </div>
        ))}
        </div>
      </div>
    </div>
  );
};
