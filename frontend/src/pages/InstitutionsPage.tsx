import React, { useEffect, useState } from 'react';
import { Building2, CheckCircle2, Database, ImagePlus, Pencil, Plus, ShieldCheck, X } from 'lucide-react';
import { api } from '../services/api';
import { Institution } from '../types';

type InstituteForm = {
  name: string; code: string; slug: string; city: string; state: string; address: string;
  phone: string; email: string; logo_url: string; institution_type: string; principal_email: string;
  principal_password: string; principal_first_name: string; principal_middle_name: string; principal_last_name: string;
};

const emptyForm: InstituteForm = {
  name: '', code: '', slug: '', city: '', state: 'Maharashtra', address: '', phone: '', email: '',
  logo_url: '', principal_email: '', principal_password: '', principal_first_name: '', principal_middle_name: '', principal_last_name: '',
  institution_type: 'OTHER',
};

const formatInstitutionName = (name: string) => {
  if (!name || name !== name.toUpperCase()) return name;
  return name.toLowerCase()
    .replace(/\bjr\.?\s*college\b/g, 'Junior College')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
};

export const InstitutionsPage: React.FC = () => {
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [form, setForm] = useState<InstituteForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadInstitutions = async () => {
    try {
      setInstitutions(await api.get<Institution[]>('/institutions'));
    } catch (err: any) {
      setError(err.message || 'Could not load institutes');
    }
  };

  useEffect(() => { loadInstitutions(); }, []);

  const update = (field: keyof InstituteForm, value: string) => setForm((current) => ({ ...current, [field]: value }));

  const handleImage = (file?: File) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Please select a valid image file.');
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setError('Institute images must be 2 MB or smaller.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => update('logo_url', String(reader.result));
    reader.onerror = () => setError('The institute image could not be read.');
    reader.readAsDataURL(file);
  };

  const startCreate = () => {
    setForm(emptyForm);
    setEditingId(null);
    setShowForm(true);
    setMessage(null);
    setError(null);
  };

  const startEdit = (institution: Institution) => {
    setForm({
      ...emptyForm,
      name: formatInstitutionName(institution.name),
      code: institution.code,
      slug: institution.slug,
      city: institution.city || '',
      state: institution.state || '',
      address: institution.address || '',
      phone: institution.phone || '',
      email: institution.email || '',
      logo_url: institution.logo_url || '',
      institution_type: institution.institution_type || 'OTHER',
    });
    setEditingId(institution.id);
    setShowForm(true);
    setMessage(null);
    setError(null);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsSaving(true);
    try {
      if (editingId) {
        await api.put(`/institutions/${editingId}`, {
          name: form.name,
          address: form.address,
          city: form.city,
          state: form.state,
          phone: form.phone,
          email: form.email || undefined,
          logo_url: form.logo_url || undefined,
          institution_type: form.institution_type,
        });
        setMessage('Institute details and branding updated successfully.');
      } else {
        await api.post('/institutions', {
          ...form,
          slug: form.slug || form.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''),
          email: form.email || undefined,
        });
        setMessage('Institute created and its isolated database was provisioned successfully.');
      }
      setShowForm(false);
      setForm(emptyForm);
      setEditingId(null);
      await loadInstitutions();
    } catch (err: any) {
      setError(err.message || 'Institute operation failed');
    } finally {
      setIsSaving(false);
    }
  };

  const fields: [keyof InstituteForm, string, boolean][] = [
    ['name', 'Institute name', true], ['code', 'Institute code', true], ['slug', 'Institute short ID / slug (optional)', false],
    ['city', 'City', false], ['state', 'State', false], ['phone', 'Phone', false], ['email', 'Official email', false],
    ['address', 'Address', false],
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-7">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">Platform control plane</p><h1 className="font-display text-3xl font-semibold tracking-tight text-slate-950">Institute workspaces</h1><p className="mt-2 max-w-2xl text-sm text-slate-500">Create, brand, and edit isolated academic environments from one secure console.</p></div>
        <button type="button" onClick={startCreate} className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-600/20 hover:bg-indigo-500"><Plus className="h-4 w-4" /> Add institute</button>
      </div>
      {message && <div className="flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"><CheckCircle2 className="h-4 w-4" />{message}</div>}
      {error && <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

      {showForm && (
        <form onSubmit={submit} className="premium-card grid gap-5 p-5 sm:grid-cols-2 sm:p-7">
          <div className="sm:col-span-2 flex items-center justify-between border-b border-slate-100 pb-4"><div className="flex items-center gap-3"><Building2 className="h-5 w-5 text-indigo-600" /><div><h2 className="font-display text-xl font-semibold">{editingId ? 'Edit institute details' : 'Provision new institute'}</h2><p className="text-xs text-slate-500">{editingId ? 'Changes apply to the institute card and login branding.' : 'The database is created automatically after submission.'}</p></div></div><button type="button" onClick={() => setShowForm(false)} aria-label="Close form"><X className="h-5 w-5 text-slate-400" /></button></div>
          {fields.map(([field, label, required]) => <label key={field} className={field === 'address' ? 'sm:col-span-2' : ''}><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span><input required={required} disabled={editingId !== null && (field === 'code' || field === 'slug')} type={field === 'email' ? 'email' : 'text'} value={form[field]} onChange={(event) => update(field, event.target.value)} className="premium-input w-full disabled:cursor-not-allowed disabled:bg-slate-100" /></label>)}
          <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Institution type</span><select value={form.institution_type} onChange={(event) => update('institution_type', event.target.value)} className="premium-input w-full"><option value="SCHOOL">School</option><option value="JUNIOR_COLLEGE">Junior College</option><option value="DEGREE_COLLEGE">Degree College</option><option value="ENGINEERING_COLLEGE">Engineering College</option><option value="OTHER">Other / Multi-purpose</option></select></label>
          <label className="sm:col-span-2"><span className="mb-1.5 block text-xs font-semibold text-slate-600">Institute image</span><div className="flex flex-wrap items-center gap-4"><label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-indigo-300 bg-indigo-50 px-4 py-3 text-sm font-semibold text-indigo-700"><ImagePlus className="h-4 w-4" /> Upload image<input type="file" accept="image/*" className="hidden" onChange={(event) => handleImage(event.target.files?.[0])} /></label>{form.logo_url && <img src={form.logo_url} alt="Institute preview" className="h-16 w-28 rounded-xl object-cover ring-1 ring-slate-200" />}<span className="text-xs text-slate-400">PNG/JPG, maximum 2 MB</span></div></label>
          {!editingId && <><label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Principal first name</span><input required value={form.principal_first_name} onChange={(event) => update('principal_first_name', event.target.value)} className="premium-input w-full" /></label><label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Principal middle name</span><input required value={form.principal_middle_name} onChange={(event) => update('principal_middle_name', event.target.value)} className="premium-input w-full" /></label><label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Principal last name</span><input required value={form.principal_last_name} onChange={(event) => update('principal_last_name', event.target.value)} className="premium-input w-full" /></label><label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Principal email</span><input required type="email" value={form.principal_email} onChange={(event) => update('principal_email', event.target.value)} className="premium-input w-full" /></label><label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Principal temporary password</span><input required type="password" value={form.principal_password} onChange={(event) => update('principal_password', event.target.value)} className="premium-input w-full" /></label></>}
          <div className="flex justify-end gap-3 sm:col-span-2"><button type="button" onClick={() => setShowForm(false)} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-500 hover:bg-slate-100">Cancel</button><button disabled={isSaving} className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{isSaving ? 'Saving...' : editingId ? 'Save institute details' : 'Create isolated workspace'}</button></div>
        </form>
      )}

      <div className="grid gap-5 md:grid-cols-2">
        {institutions.map((institution) => <div key={institution.id} className="premium-card overflow-hidden"><div className="relative h-36 bg-slate-900">{institution.logo_url ? <img src={institution.logo_url} alt="" className="h-full w-full object-cover opacity-80" /> : <div className="flex h-full items-center justify-center"><Building2 className="h-10 w-10 text-white/30" /></div>}<button type="button" onClick={() => startEdit(institution)} className="absolute right-4 top-4 inline-flex items-center gap-1.5 rounded-lg bg-white/90 px-3 py-2 text-xs font-bold text-slate-700 shadow hover:bg-white"><Pencil className="h-3.5 w-3.5" /> Edit</button></div><div className="p-5 sm:p-6"><div className="flex items-start justify-between gap-4"><div><h2 className="font-display text-lg font-semibold">{formatInstitutionName(institution.name)}</h2><p className="text-xs text-slate-500">{institution.code} · {institution.city || 'Location not set'}</p></div><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-700">{institution.status}</span></div><div className="mt-5 flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2.5 text-xs text-slate-600"><Database className="h-4 w-4 text-indigo-500" />{institution.database_url ? 'Dedicated database provisioned' : 'Shared legacy database'}</div></div></div>)}
      </div>
      <div className="flex items-center gap-2 text-xs text-slate-400"><ShieldCheck className="h-4 w-4 text-emerald-500" /> Tenant isolation is enforced by the selected institute session.</div>
    </div>
  );
};
