import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CheckCircle2, GraduationCap, Trash2, UserPlus } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useIsEngineeringCollege } from '../hooks/useIsEngineeringCollege';

interface FacultyMember { id: string; full_name: string; employee_id: string; gender?: string | null; email: string; designation: string; department: string; }

export const FacultyPage: React.FC = () => {
  const { activeRole } = useAuth();
  const isEngineering = useIsEngineeringCollege();
  const [departments, setDepartments] = useState<string[]>([]);
  const [faculty, setFaculty] = useState<FacultyMember[]>([]);
  const [searchParams] = useSearchParams();
  const departmentFilter = isEngineering ? searchParams.get('department') : null;
  const [showForm, setShowForm] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ email: '', password: '', first_name: '', middle_name: '', last_name: '', phone_number: '', employee_id: '', gender: '', designation: 'Lecturer', department: searchParams.get('department') || '', qualification: '' });

  const load = async () => {
    try { setFaculty(await api.get<FacultyMember[]>(`/faculty${departmentFilter ? `?department=${encodeURIComponent(departmentFilter)}` : ''}`)); } catch (err: any) { setError(err.message || 'Could not load faculty'); }
  };
  useEffect(() => { if (isEngineering !== null) load(); }, [departmentFilter, isEngineering]);
  useEffect(() => {
    if (isEngineering) api.get<{ name: string }[]>('/academics/classes').then((items) => setDepartments(items.map((item) => item.name))).catch(() => setDepartments([]));
  }, [isEngineering]);
  const update = (field: keyof typeof form, value: string) => setForm((current) => ({ ...current, [field]: value }));
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError(null); setMessage(null);
    try {
      const { department, ...rest } = form;
      await api.post('/faculty', isEngineering ? form : rest);
      setMessage('Faculty account created in this institute database.'); setShowForm(false);
      setForm({ email: '', password: '', first_name: '', middle_name: '', last_name: '', phone_number: '', employee_id: '', gender: '', designation: 'Lecturer', department: departmentFilter || '', qualification: '' });
      await load();
    }
    catch (err: any) { setError(err.message || 'Could not create faculty account'); }
  };
  const remove = async (id: string) => {
    if (!window.confirm('Remove this faculty account from the institute?')) return;
    try { await api.delete(`/faculty/${id}`); setMessage('Faculty account removed.'); await load(); } catch (err: any) { setError(err.message || 'Could not remove faculty'); }
  };
  const fields = [['first_name','First name','text'],['middle_name','Middle name','text'],['last_name','Last name','text'],['email','Email (username)','email'],['password','Temporary password','password'],['employee_id','Faculty ID (Employee ID)','text'],['gender','Gender','gender'],['designation','Designation','text'],...(isEngineering ? [['department','Department','select']] : []),['qualification','Qualification','text'],['phone_number','Phone number','text']] as [keyof typeof form,string,string][];
  return <div className="mx-auto max-w-6xl space-y-7">
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">Academic administration</p><h1 className="font-display text-3xl font-semibold tracking-tight text-slate-950">Faculty directory{departmentFilter ? ` · ${departmentFilter}` : ''}</h1><p className="mt-2 text-sm text-slate-500">{isEngineering ? 'Faculty belong to a department. Office staff can add lecturers to a department and create their institute login accounts.' : 'Faculty are not tied to a department: any lecturer can teach different subjects in different classes once the principal assigns them. Office staff can add lecturers and create their institute login accounts.'}</p></div><button type="button" onClick={() => setShowForm(true)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white"><UserPlus className="h-4 w-4" /> Add faculty</button></div>
    {message && <div className="flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"><CheckCircle2 className="h-4 w-4" />{message}</div>}
    {error && <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
    {showForm && <form onSubmit={submit} className="premium-card grid gap-4 p-5 sm:grid-cols-2 sm:p-7">{fields.map(([field,label,type]) => <label key={field}><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{type === 'gender' ? <select required value={form[field]} onChange={(event) => update(field, event.target.value)} className="premium-input w-full"><option value="">Select gender</option><option value="MALE">Male</option><option value="FEMALE">Female</option><option value="OTHER">Other</option></select> : type === 'select' ? <select required value={form[field]} onChange={(event) => update(field, event.target.value)} className="premium-input w-full"><option value="">Select department</option>{departments.map((name) => <option key={name} value={name}>{name}</option>)}</select> : <input required={!['phone_number','qualification'].includes(field)} type={type} value={form[field]} onChange={(event) => update(field, event.target.value)} className="premium-input w-full" />}</label>)}<div className="flex justify-end gap-3 sm:col-span-2"><button type="button" onClick={() => setShowForm(false)} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-500">Cancel</button><button className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white">Create faculty account</button></div></form>}
    <div className="grid gap-4 md:grid-cols-2">{faculty.map((member) => <div key={member.id} className="premium-card flex items-center gap-4 p-5"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600"><GraduationCap className="h-5 w-5" /></span><div className="min-w-0 flex-1"><h2 className="font-semibold text-slate-900">{member.full_name}</h2><p className="text-xs text-slate-500">{member.employee_id} · {member.gender ? member.gender.charAt(0) + member.gender.slice(1).toLowerCase() + ' · ' : ''}{member.designation}{isEngineering ? ` · ${member.department}` : ''}</p><p className="truncate text-xs text-slate-500">{member.email}</p></div>{activeRole !== 'OFFICE_STAFF' && <button type="button" onClick={() => remove(member.id)} className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600" aria-label={`Remove ${member.full_name}`}><Trash2 className="h-4 w-4" /></button>}</div>)}</div>
  </div>;
};
