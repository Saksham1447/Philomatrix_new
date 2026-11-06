import React, { useEffect, useMemo, useState } from 'react';
import { CalendarClock, CheckCircle2, Pencil, Plus, Trash2 } from 'lucide-react';
import { api } from '../services/api';
import { formatIndianTime } from '../utils/time';

interface AcademicClass { id: string; name: string; divisions: Array<{ id: string; name: string }>; }
interface Subject { id: string; name: string; code: string; }
interface Slot {
  id: string; class_id: string; day_of_week: number; period_number: number;
  start_time: string; end_time: string; subject_id?: string | null; subject_name?: string | null; subject_code?: string | null;
}

const DAYS = [
  { num: 1, name: 'Mon' }, { num: 2, name: 'Tue' }, { num: 3, name: 'Wed' },
  { num: 4, name: 'Thu' }, { num: 5, name: 'Fri' }, { num: 6, name: 'Sat' },
];

const emptyForm = { period_number: 1, start_time: '09:00', end_time: '10:00', subject_id: '', days: [1, 2, 3, 4, 5, 6] as number[] };

export const TimetableSlotsPage: React.FC = () => {
  const [classes, setClasses] = useState<AcademicClass[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [classId, setClassId] = useState('');
  const [divisionId, setDivisionId] = useState('');
  const [slots, setSlots] = useState<Slot[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editingSlotId, setEditingSlotId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [conflictingSlot, setConflictingSlot] = useState<Slot | null>(null);

  useEffect(() => {
    Promise.all([api.get<AcademicClass[]>('/academics/classes'), api.get<Subject[]>('/academics/subjects')])
      .then(([classList, subjectList]) => {
        setClasses(classList);
        setSubjects(subjectList);
        if (classList.length) {
          setClassId(classList[0].id);
          setDivisionId(classList[0].divisions[0]?.id || '');
        }
      })
      .catch((err: any) => setError(err.message || 'Could not load departments and subjects'));
  }, []);

  const loadSlots = async (id: string) => {
    try { setSlots(await api.get<Slot[]>(`/timetable/slots?division_id=${id}`)); } catch (err: any) { setError(err.message || 'Could not load slots'); }
  };
  useEffect(() => { if (divisionId) loadSlots(divisionId); else setSlots([]); }, [divisionId]);

  const periods = useMemo(() => {
    const byPeriod = new Map<number, Slot[]>();
    slots.forEach((slot) => byPeriod.set(slot.period_number, [...(byPeriod.get(slot.period_number) || []), slot]));
    return [...byPeriod.entries()].sort((a, b) => a[0] - b[0]);
  }, [slots]);

  const toggleDay = (day: number) => setForm((current) => ({
    ...current,
    days: current.days.includes(day) ? current.days.filter((item) => item !== day) : [...current.days, day].sort(),
  }));

  const showError = (err: any, fallback: string) => {
    const message = err.message || fallback;
    const conflict = message.match(/Time overlaps period (\d+).* on (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)/i);
    const dayNumber = conflict ? DAYS.find(day => day.name.toLowerCase() === conflict[2].slice(0, 3).toLowerCase())?.num : undefined;
    setConflictingSlot(conflict && dayNumber
      ? slots.find(slot => slot.period_number === Number(conflict[1]) && slot.day_of_week === dayNumber) || null
      : null);
    setError(message);
  };

  const addPeriod = async (event: React.FormEvent) => {
    event.preventDefault(); setError(null); setConflictingSlot(null); setMessage(null);
    try {
      if (editingSlotId) {
        await api.put(`/timetable/slots/${editingSlotId}`, {
          start_time: form.start_time,
          end_time: form.end_time,
        });
        setMessage(`Period ${form.period_number} updated.`);
        setEditingSlotId(null);
        setForm(emptyForm);
        await loadSlots(divisionId);
        return;
      }

      await api.post('/timetable/slots', {
        division_id: divisionId,
        days_of_week: form.days,
        period_number: form.period_number,
        start_time: form.start_time,
        end_time: form.end_time,
        subject_id: form.subject_id || null,
      });
      setMessage(`Period ${form.period_number} added.`);
      setForm({ ...emptyForm, period_number: Math.min(form.period_number + 1, 8) });
      await loadSlots(divisionId);
    } catch (err: any) { showError(err, 'Could not add the period'); }
  };

  const editSlot = (slot: Slot) => {
    setEditingSlotId(slot.id);
    setForm({
      ...emptyForm,
      period_number: slot.period_number,
      start_time: slot.start_time.slice(0, 5),
      end_time: slot.end_time.slice(0, 5),
      subject_id: slot.subject_id || '',
      days: [slot.day_of_week],
    });
    setError(null);
    setConflictingSlot(null);
    setMessage(null);
  };

  const cancelEdit = () => {
    setEditingSlotId(null);
    setForm(emptyForm);
    setError(null);
    setConflictingSlot(null);
  };

  const removeSlot = async (slot: Slot) => {
    setError(null); setMessage(null);
    try { await api.delete(`/timetable/slots/${slot.id}`); setMessage('Slot removed.'); await loadSlots(divisionId); }
    catch (err: any) { showError(err, 'Could not remove the slot'); }
  };

  return <div className="mx-auto max-w-6xl space-y-7">
    <div>
      <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">Timetable setup</p>
      <h1 className="flex items-center gap-2 font-display text-3xl font-semibold tracking-tight text-slate-950"><CalendarClock className="h-7 w-7 text-indigo-600" /> Time slots</h1>
      <p className="mt-2 text-sm text-slate-500">Define periods for each division, optionally reserving a subject for a slot. Teachers choose from that division's open slots for the subjects assigned to them. Divisions without configured slots keep a free-form timetable.</p>
    </div>
    {message && <div className="flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"><CheckCircle2 className="h-4 w-4" />{message}</div>}
    {error && <div role="alert" className="flex flex-col gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 sm:flex-row sm:items-center sm:justify-between">
      <span>{error}</span>
      {conflictingSlot && !editingSlotId && <button
        type="button"
        onClick={() => editSlot(conflictingSlot)}
        className="shrink-0 self-start rounded-lg border border-rose-300 bg-white px-3 py-2 text-xs font-bold text-rose-700 transition hover:bg-rose-100 sm:self-auto"
      >
        Edit Period {conflictingSlot.period_number} on {DAYS.find(day => day.num === conflictingSlot.day_of_week)?.name}
      </button>}
    </div>}

    <label className="block max-w-sm"><span className="mb-1.5 block text-xs font-semibold text-slate-600">Department / class</span>
      <select value={classId} disabled={Boolean(editingSlotId)} onChange={(event) => {
        const nextClass = classes.find((item) => item.id === event.target.value);
        setClassId(event.target.value);
        setDivisionId(nextClass?.divisions[0]?.id || '');
      }} className="premium-input w-full">{classes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
    </label>

    <label className="block max-w-sm"><span className="mb-1.5 block text-xs font-semibold text-slate-600">Division</span>
      <select value={divisionId} onChange={(event) => setDivisionId(event.target.value)} className="premium-input w-full" disabled={Boolean(editingSlotId) || !classes.find((item) => item.id === classId)?.divisions.length}>
        {(classes.find((item) => item.id === classId)?.divisions || []).map((item) => <option key={item.id} value={item.id}>Division {item.name}</option>)}
      </select>
    </label>

    <form onSubmit={addPeriod} className="premium-card grid gap-4 p-5 sm:grid-cols-4">
      <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Period</span><input type="number" min={1} max={8} required value={form.period_number} onChange={(event) => setForm({ ...form, period_number: Number(event.target.value) })} className="premium-input w-full" disabled={Boolean(editingSlotId)} /></label>
      <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Starts</span><input type="time" required value={form.start_time} onChange={(event) => setForm({ ...form, start_time: event.target.value })} className="premium-input w-full" /></label>
      <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Ends</span><input type="time" required value={form.end_time} onChange={(event) => setForm({ ...form, end_time: event.target.value })} className="premium-input w-full" /></label>
      <label><span className="mb-1.5 block text-xs font-semibold text-slate-600">Subject (optional)</span>
        <select value={form.subject_id} onChange={(event) => setForm({ ...form, subject_id: event.target.value })} className="premium-input w-full" disabled={Boolean(editingSlotId)}><option value="">Any subject</option>{subjects.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select>
      </label>
      <div className="sm:col-span-4"><span className="mb-1.5 block text-xs font-semibold text-slate-600">Days</span>
        <div className="flex flex-wrap gap-2">{DAYS.map((day) => <button key={day.num} type="button" onClick={() => toggleDay(day.num)} disabled={Boolean(editingSlotId)} className={`rounded-lg border px-3 py-1.5 text-xs font-semibold ${form.days.includes(day.num) ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-slate-200 text-slate-500'}`}>{day.name}</button>)}</div>
      </div>
      <div className="flex gap-2 sm:col-span-4">
        <button disabled={!divisionId || form.days.length === 0} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{editingSlotId ? <CheckCircle2 className="h-4 w-4" /> : <Plus className="h-4 w-4" />}{editingSlotId ? 'Save period' : 'Add period'}</button>
        {editingSlotId && <button type="button" onClick={cancelEdit} className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-600">Cancel</button>}
      </div>
    </form>

    <div className="premium-card overflow-x-auto">
      <table className="w-full border-collapse text-left text-xs">
        <thead><tr className="bg-slate-900 font-bold uppercase tracking-wider text-white"><th className="px-4 py-3">Period</th>{DAYS.map((day) => <th key={day.num} className="px-3 py-3 text-center">{day.name}</th>)}</tr></thead>
        <tbody className="divide-y divide-slate-200">
          {periods.length === 0 && <tr><td colSpan={7} className="px-4 py-6 text-center text-slate-400">No slots yet for this department/class.</td></tr>}
          {periods.map(([period, periodSlots]) => <tr key={period}>
            <td className="bg-slate-50 px-4 py-3 font-bold text-slate-900">Period {period}</td>
            {DAYS.map((day) => {
              const slot = periodSlots.find((item) => item.day_of_week === day.num);
              return <td key={day.num} className="px-2 py-2 align-top">{slot ? <div className="flex items-start justify-between gap-1 rounded-lg border border-indigo-100 bg-indigo-50/60 p-2"><div><p className="font-semibold text-slate-800">{formatIndianTime(slot.start_time)} – {formatIndianTime(slot.end_time)}</p><p className="text-[10px] text-slate-500">{slot.subject_code ? `${slot.subject_code} only` : 'Any subject'}</p></div><div className="flex gap-1"><button type="button" onClick={() => editSlot(slot)} disabled={Boolean(editingSlotId)} aria-label={`Edit period ${period} on ${day.name}`} className="text-slate-400 hover:text-indigo-600 disabled:opacity-50"><Pencil className="h-3.5 w-3.5" /></button><button type="button" onClick={() => removeSlot(slot)} disabled={Boolean(editingSlotId)} aria-label={`Remove period ${period} on ${day.name}`} className="text-slate-400 hover:text-rose-600 disabled:opacity-50"><Trash2 className="h-3.5 w-3.5" /></button></div></div> : <span className="block text-center text-slate-300">—</span>}</td>;
            })}
          </tr>)}
        </tbody>
      </table>
    </div>
  </div>;
};
