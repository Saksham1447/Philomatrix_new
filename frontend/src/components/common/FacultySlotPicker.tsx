import React, { useEffect, useMemo, useState } from 'react';
import { CalendarCheck } from 'lucide-react';
import { api } from '../../services/api';
import { formatIndianTime } from '../../utils/time';

interface Assignment { subject_id: string; subject_name: string; subject_code: string; division_id: string; division_name: string; class_name: string; }
interface AvailableSlot {
  slot_id: string; day_of_week: number; period_number: number; start_time: string; end_time: string;
  status: 'OPEN' | 'TAKEN' | 'FACULTY_BUSY'; taken_by?: string | null; taken_subject?: string | null;
  allowed_subjects: { subject_id: string; subject_name: string; subject_code: string }[];
}

const DAY_NAMES = ['', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

interface Props {
  facultyId: string;
  assignments: Assignment[];
  onScheduled: () => void;
}

/** Lets a teacher pick open slots, set by the office/principal for a class, for the subjects assigned to them. */
export const FacultySlotPicker: React.FC<Props> = ({ facultyId, assignments, onScheduled }) => {
  const divisions = useMemo(() => {
    const seen = new Map<string, string>();
    assignments.forEach((item) => seen.set(item.division_id, `${item.class_name} · Division ${item.division_name}`));
    return [...seen.entries()];
  }, [assignments]);
  const [divisionId, setDivisionId] = useState('');
  const [slots, setSlots] = useState<AvailableSlot[]>([]);
  const [chosenSubject, setChosenSubject] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => { if (!divisionId && divisions.length) setDivisionId(divisions[0][0]); }, [divisions, divisionId]);

  const load = async (id: string) => {
    try { setSlots(await api.get<AvailableSlot[]>(`/timetable/available-slots?division_id=${id}`)); }
    catch (err: any) { setError(err.message || 'Could not load the available slots'); }
  };
  useEffect(() => { if (divisionId) load(divisionId); }, [divisionId]);

  const take = async (slot: AvailableSlot) => {
    const subjectId = chosenSubject[slot.slot_id] || slot.allowed_subjects[0]?.subject_id;
    if (!subjectId) return;
    setError(null); setMessage(null);
    try {
      await api.post('/timetable/entries', {
        division_id: divisionId,
        subject_id: subjectId,
        faculty_id: facultyId,
        day_of_week: slot.day_of_week,
        period_number: slot.period_number,
        start_time: slot.start_time,
        end_time: slot.end_time,
      });
      setMessage(`${DAY_NAMES[slot.day_of_week]} period ${slot.period_number} added to your timetable.`);
      await load(divisionId);
      onScheduled();
    } catch (err: any) { setError(err.message || 'Unable to take this slot'); }
  };

  if (divisions.length === 0 || (slots.length === 0 && !error)) return null;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900"><CalendarCheck className="w-4 h-4 text-brand-600" /> Set your timetable from the class time slots</h2>
          <p className="text-xs text-slate-500 mt-1">Open slots are shown for the subjects assigned to you. Slots you or another teacher already hold are locked.</p>
        </div>
        <select value={divisionId} onChange={(event) => setDivisionId(event.target.value)} className="px-3 py-2 border rounded-lg bg-slate-50 text-xs">
          {divisions.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select>
      </div>
      {message && <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs">{message}</div>}
      {error && <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs">{error}</div>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {slots.map((slot) => {
          const canTake = slot.status === 'OPEN' && slot.allowed_subjects.length > 0;
          return (
            <div key={slot.slot_id} className={`rounded-xl border p-3 text-xs space-y-2 ${slot.status === 'OPEN' ? 'border-slate-200' : 'border-slate-100 bg-slate-50 text-slate-400'}`}>
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800">{DAY_NAMES[slot.day_of_week]} · Period {slot.period_number}</span>
                <span>{formatIndianTime(slot.start_time)} – {formatIndianTime(slot.end_time)}</span>
              </div>
              {slot.status === 'TAKEN' && <p>Taken: {slot.taken_subject} ({slot.taken_by})</p>}
              {slot.status === 'FACULTY_BUSY' && <p>You teach another class in this period.</p>}
              {slot.status === 'OPEN' && slot.allowed_subjects.length === 0 && <p>None of your assigned subjects fits this slot.</p>}
              {canTake && (
                <div className="flex gap-2">
                  <select value={chosenSubject[slot.slot_id] || slot.allowed_subjects[0].subject_id} onChange={(event) => setChosenSubject({ ...chosenSubject, [slot.slot_id]: event.target.value })} className="min-w-0 flex-1 px-2 py-1.5 border rounded-lg bg-slate-50">
                    {slot.allowed_subjects.map((subject) => <option key={subject.subject_id} value={subject.subject_id}>{subject.subject_code} {subject.subject_name}</option>)}
                  </select>
                  <button type="button" onClick={() => take(slot)} className="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-bold">Take</button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
