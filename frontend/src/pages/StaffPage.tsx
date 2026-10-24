import React, { useEffect, useState } from 'react';
import { CheckCircle2, ShieldCheck, UserPlus, Users } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

interface StaffMember {
  id: string;
  username: string;
  email: string;
  full_name: string;
  phone_number?: string;
  is_active: boolean;
}

export const StaffPage: React.FC = () => {
  const { user, activeRole } = useAuth();
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ email: '', password: '', first_name: '', middle_name: '', last_name: '', phone_number: '' });

  const loadStaff = async () => {
    if (!user?.institution_id) return;
    try {
      setStaff(await api.get<StaffMember[]>(`/institutions/${user.institution_id}/staff`));
    } catch (err: any) {
      setError(err.message || 'Could not load office staff');
    }
  };

  useEffect(() => { loadStaff(); }, [user?.institution_id]);

  const update = (field: keyof typeof form, value: string) => setForm((current) => ({ ...current, [field]: value }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!user?.institution_id) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await api.post(`/institutions/${user.institution_id}/staff`, form);
      setMessage('Office staff account created inside this institute database.');
      setForm({ email: '', password: '', first_name: '', middle_name: '', last_name: '', phone_number: '' });
      setShowForm(false);
      await loadStaff();
    } catch (err: any) {
      setError(err.message || 'Could not create office staff account');
    } finally {
      setSaving(false);
    }
  };

  if (activeRole !== 'PRINCIPAL' && activeRole !== 'SUPER_ADMIN') {
    return <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-800">Only a Principal or Super Admin can create office staff accounts.</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-7">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">Institute administration</p><h1 className="font-display text-3xl font-semibold tracking-tight text-slate-950">Office staff</h1><p className="mt-2 text-sm text-slate-500">Create office accounts that can manage admissions, students, and faculty for this institute.</p></div>
        <button type="button" onClick={() => setShowForm(true)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-600/20 hover:bg-indigo-500"><UserPlus className="h-4 w-4" /> Add office staff</button>
      </div>
      {message && <div className="flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"><CheckCircle2 className="h-4 w-4" />{message}</div>}
      {error && <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
      {showForm && <form onSubmit={submit} className="premium-card grid gap-4 p-5 sm:grid-cols-2 sm:p-7">
        {([
          ['first_name', 'First name', 'text'], ['middle_name', 'Middle name', 'text'], ['last_name', 'Last name', 'text'],
          ['email', 'Email', 'email'], ['password', 'Temporary password', 'password'], ['phone_number', 'Phone number', 'text'],
        ] as [keyof typeof form, string, string][]).map(([field, label, type]) => <label key={field}><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span><input required={field !== 'phone_number'} type={type} value={form[field]} onChange={(event) => update(field, event.target.value)} className="premium-input w-full" /></label>)}
        <div className="flex justify-end gap-3 sm:col-span-2"><button type="button" onClick={() => setShowForm(false)} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-500">Cancel</button><button disabled={saving} className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{saving ? 'Creating...' : 'Create account'}</button></div>
      </form>}
      <div className="grid gap-4 md:grid-cols-2">
        {staff.map((member) => <div key={member.id} className="premium-card flex items-center gap-4 p-5"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600"><Users className="h-5 w-5" /></span><div className="min-w-0"><h2 className="font-semibold text-slate-900">{member.full_name}</h2><p className="truncate text-xs text-slate-500">{member.email}</p><p className="mt-1 text-[11px] font-semibold uppercase tracking-wider text-emerald-600">{member.is_active ? 'Active office staff' : 'Inactive'}</p></div></div>)}
      </div>
      <div className="flex items-center gap-2 text-xs text-slate-400"><ShieldCheck className="h-4 w-4 text-emerald-500" /> Office staff accounts are stored in the selected institute database.</div>
    </div>
  );
};
