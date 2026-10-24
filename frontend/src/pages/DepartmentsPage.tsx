import React, { useEffect, useState } from 'react';
import { BookOpen, CheckCircle2, ChevronRight, Pencil, Plus, Trash2, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

interface Division { id: string; name: string; room_number?: string; capacity: number; }
interface ClassModel { id: string; name: string; stream: string; display_order: number; divisions: Division[]; }

export const DepartmentsPage: React.FC = () => {
  const navigate = useNavigate();
  const { activeRole } = useAuth();
  // Office staff only add students/faculty; the principal manages departments, classes and divisions.
  const canManage = activeRole !== 'OFFICE_STAFF';
  const [classes, setClasses] = useState<ClassModel[]>([]);
  const [form, setForm] = useState({ name: '', stream: 'GENERAL', display_order: 1, divisions: '' });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => { try { setClasses(await api.get<ClassModel[]>('/academics/classes')); } catch (err: any) { setError(err.message || 'Could not load classes'); } };
  useEffect(() => { load(); }, []);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError(null); setMessage(null);
    try {
      const payload = { ...form, divisions: form.divisions.split(',').map((name) => name.trim()).filter(Boolean) };
      if (editingId) await api.put(`/academics/classes/${editingId}`, payload);
      else await api.post('/academics/classes', payload);
      setMessage(editingId ? 'Class updated successfully.' : 'Class created successfully.');
      setForm({ name: '', stream: 'GENERAL', display_order: 1, divisions: '' }); setEditingId(null); await load();
    } catch (err: any) { setError(err.message || 'Class operation failed'); }
  };
  const remove = async (id: string) => {
    if (!window.confirm('Delete this class? Classes with enrolled students cannot be deleted.')) return;
    try { await api.delete(`/academics/classes/${id}`); setMessage('Class deleted.'); await load(); } catch (err: any) { setError(err.message || 'Could not delete class'); }
  };
  return <div className="mx-auto max-w-6xl space-y-7">
  <div><p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">Office staff workspace</p><h1 className="font-display text-3xl font-semibold tracking-tight text-slate-950">Departments & classes</h1><p className="mt-2 text-sm text-slate-500">{canManage ? 'Create any department or class name, including Computer Engineering, Mechanical Engineering, Civil Engineering, Class 11 Science, or any custom academic unit.' : 'Choose a department or class to add new students (and faculty where the institute uses departments).'}</p></div>
    {message && <div className="flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"><CheckCircle2 className="h-4 w-4" />{message}</div>}
    {error && <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
    {canManage && <form onSubmit={submit} className="premium-card grid gap-4 p-5 sm:grid-cols-[1fr_220px_220px_120px_auto] sm:items-start"><label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Academic unit name</span><input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Class 5 / Computer Engineering / B.Sc. Physics" className="premium-input w-full" /></label><label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Category or course type</span><input value={form.stream} onChange={(event) => setForm({ ...form, stream: event.target.value })} placeholder="School / Engineering / Science" className="premium-input w-full" /></label><label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Divisions</span><input value={form.divisions} onChange={(event) => setForm({ ...form, divisions: event.target.value })} placeholder="A, B, C" className="premium-input w-full" /><span className="mt-1 block text-[10px] text-slate-400">Separate names with commas</span></label><label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Order</span><input type="number" min="1" value={form.display_order} onChange={(event) => setForm({ ...form, display_order: Number(event.target.value) })} className="premium-input w-full" /></label><div className="flex gap-2 sm:mt-[29px]"><button className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white"><Plus className="h-4 w-4" />{editingId ? 'Save' : 'Create'}</button>{editingId && <button type="button" onClick={() => { setEditingId(null); setForm({ name: '', stream: 'GENERAL', display_order: 1, divisions: '' }); }} className="rounded-xl px-3 py-2 text-sm text-slate-500">Cancel</button>}</div></form>}
    <div className="grid gap-5 md:grid-cols-2">{classes.map((item) => <div key={item.id} className="premium-card cursor-pointer p-5 transition hover:-translate-y-0.5" onClick={() => navigate(`/departments/${item.id}`)}><div className="flex items-start justify-between gap-4"><div className="flex gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600"><BookOpen className="h-5 w-5" /></span><div><h2 className="font-display text-lg font-semibold">{item.name}</h2><p className="text-xs text-slate-500">{item.stream || 'Custom category'} · {item.divisions.length} divisions</p></div></div>{canManage && <div className="flex gap-1" onClick={(event) => event.stopPropagation()}><button type="button" onClick={() => { setEditingId(item.id); setForm({ name: item.name, stream: item.stream, display_order: item.display_order, divisions: item.divisions.map((division) => division.name).join(', ') }); }} className="rounded-lg p-2 text-slate-400 hover:bg-indigo-50 hover:text-indigo-600" aria-label="Edit class"><Pencil className="h-4 w-4" /></button><button type="button" onClick={() => remove(item.id)} className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600" aria-label="Delete class"><Trash2 className="h-4 w-4" /></button></div>}</div><div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-4 text-xs font-semibold text-indigo-600"><span className="inline-flex items-center gap-2"><Users className="h-4 w-4" /> Manage faculty & students</span><ChevronRight className="h-4 w-4" /></div></div>)}</div>
  </div>;
};
