import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { ClassModel, Faculty, Subject, TimetableEntry } from '../types';
import { formatIndianTime } from '../utils/time';
import { FacultySlotPicker } from '../components/common/FacultySlotPicker';
import { Calendar, Clock, MapPin, User, BookOpen, Plus, X, ShieldCheck, ChevronRight } from 'lucide-react';

const SUBJECT_COLORS = [
  { card: 'border-l-indigo-500 bg-indigo-50/70', chip: 'bg-indigo-100 text-indigo-700' },
  { card: 'border-l-violet-500 bg-violet-50/70', chip: 'bg-violet-100 text-violet-700' },
  { card: 'border-l-sky-500 bg-sky-50/70', chip: 'bg-sky-100 text-sky-700' },
  { card: 'border-l-teal-500 bg-teal-50/70', chip: 'bg-teal-100 text-teal-700' },
  { card: 'border-l-amber-500 bg-amber-50/70', chip: 'bg-amber-100 text-amber-700' },
  { card: 'border-l-rose-500 bg-rose-50/70', chip: 'bg-rose-100 text-rose-700' },
];

export const TimetablePage: React.FC = () => {
  const { user, activeRole, activeChild } = useAuth();
  const isAdminView = activeRole === 'PRINCIPAL' || activeRole === 'OFFICE_STAFF' || activeRole === 'SUPER_ADMIN';
  const canCreateSchedule = activeRole === 'PRINCIPAL' || activeRole === 'SUPER_ADMIN' || activeRole === 'OFFICE_STAFF';
  const [entries, setEntries] = useState<TimetableEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [assignments, setAssignments] = useState<Array<{ subject_id: string; subject_name: string; subject_code: string; division_id: string; division_name: string; class_name: string }>>([]);
  const [selectedSlot, setSelectedSlot] = useState<{ day: number; period: number } | null>(null);
  const [selectedAssignment, setSelectedAssignment] = useState('');
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [selectedFacultyId, setSelectedFacultyId] = useState('');
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [faculty, setFaculty] = useState<Faculty[]>([]);
  const [facultyEntries, setFacultyEntries] = useState<TimetableEntry[]>([]);
  const [roomNumber, setRoomNumber] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Every division of a class has its own timetable; administrators pick which one to view.
  const [classes, setClasses] = useState<ClassModel[]>([]);
  const [selectedClassId, setSelectedClassId] = useState('');
  const [selectedDivisionId, setSelectedDivisionId] = useState('');
  const [slotTimes, setSlotTimes] = useState<Record<number, [string, string]>>({});
  const [slotSubjects, setSlotSubjects] = useState<Record<string, string | null>>({});
  const [timetableRefreshKey, setTimetableRefreshKey] = useState(0);

  const days = [
    { num: 1, name: 'Monday' },
    { num: 2, name: 'Tuesday' },
    { num: 3, name: 'Wednesday' },
    { num: 4, name: 'Thursday' },
    { num: 5, name: 'Friday' },
    { num: 6, name: 'Saturday' },
  ];

  const periods = Array.from({ length: Math.max(7, ...Object.keys(slotTimes).map(Number)) }, (_, index) => index + 1);
  const selectedClass = classes.find(item => item.id === selectedClassId);
  const selectedDivision = selectedClass?.divisions.find(item => item.id === selectedDivisionId);
  const legendSubjects = subjects.filter(subject =>
    entries.some(entry => entry.subject_id === subject.id) ||
    Object.values(slotSubjects).includes(subject.id)
  );
  const defaultPeriodTimes: Record<number, [string, string]> = {
    1: ['09:00', '10:00'],
    2: ['10:00', '11:00'],
    3: ['11:10', '12:10'],
    4: ['12:10', '13:10'],
    5: ['13:50', '14:50'],
    6: ['14:50', '15:50'],
    7: ['16:00', '17:00'],
  };
  const periodTimes: Record<number, [string, string]> = { ...defaultPeriodTimes, ...slotTimes };

  useEffect(() => {
    if (!isAdminView) return;
    Promise.all([
      api.get<ClassModel[]>('/academics/classes'),
      api.get<Subject[]>('/academics/subjects'),
      api.get<Faculty[]>('/faculty'),
    ]).then(([items, subjectList, facultyList]) => {
      setClasses(items);
      setSubjects(subjectList);
      setFaculty(facultyList);
      const first = items.find((item) => item.divisions.length) || items[0];
      if (first) {
        setSelectedClassId(first.id);
        setSelectedDivisionId(first.divisions[0]?.id || '');
      }
    }).catch((err) => console.error('Failed to load timetable setup data', err));
  }, [isAdminView]);

  useEffect(() => {
    if (!selectedFacultyId) {
      setFacultyEntries([]);
      return;
    }
    api.get<TimetableEntry[]>(`/timetable?faculty_id=${selectedFacultyId}`)
      .then(setFacultyEntries)
      .catch((err) => setError(err.message || 'Could not check faculty availability'));
  }, [selectedFacultyId]);

  useEffect(() => {
    const fetchTimetable = async () => {
      setIsLoading(true);
      try {
        let url = '/timetable';
        if (activeRole === 'STUDENT' && user?.student_id) {
          url = `/timetable?student_id=${user.student_id}`;
        } else if (activeRole === 'PARENT' && activeChild) {
          url = `/timetable?student_id=${activeChild.id}`;
        } else if (activeRole === 'FACULTY' && user?.faculty_id) {
          url = `/timetable?faculty_id=${user.faculty_id}`;
        } else if (isAdminView) {
          if (!selectedDivisionId) {
            setEntries([]);
            setSlotTimes({});
            setSlotSubjects({});
            setIsLoading(false);
            return;
          }
          url = `/timetable?division_id=${selectedDivisionId}`;
          const slots = await api.get<Array<{ day_of_week: number; period_number: number; start_time: string; end_time: string; subject_id?: string | null }>>(`/timetable/slots?division_id=${selectedDivisionId}`);
          setSlotTimes(Object.fromEntries(slots.map((slot) => [slot.period_number, [slot.start_time, slot.end_time]])));
          setSlotSubjects(Object.fromEntries(slots.map((slot) => [`${slot.day_of_week}-${slot.period_number}`, slot.subject_id || null])));
        }

        const data = await api.get<TimetableEntry[]>(url);
        setEntries(data);
        if (activeRole === 'FACULTY') {
          setAssignments(await api.get<typeof assignments>('/faculty/assignments'));
        }
      } catch (err) {
        console.error('Failed to load timetable', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTimetable();
  }, [activeRole, activeChild, user, isAdminView, selectedDivisionId, timetableRefreshKey]);

  const getSlot = (dayNum: number, periodNum: number) => {
    return entries.find(e => e.day_of_week === dayNum && e.period_number === periodNum);
  };

  const scheduleFirstFreeSlot = () => {
    const firstFree = days.flatMap(day =>
      periods.map(period => ({ day: day.num, period }))
    ).find(slot => !getSlot(slot.day, slot.period));

    if (!firstFree) {
      setError('There are no free periods available in this timetable.');
      return;
    }

    setError(null);
    if (isAdminView) {
      setSelectedSubjectId(slotSubjects[`${firstFree.day}-${firstFree.period}`] || '');
      setSelectedFacultyId('');
      setFacultyEntries([]);
    }
    setSelectedSlot(firstFree);
  };

  const saveSlot = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedSlot) return;
    const adminSchedule = isAdminView;
    const assignment = assignments.find(item => item.subject_id + item.division_id === selectedAssignment);
    if (!canCreateSchedule) {
      setError('Your role can view the timetable but cannot schedule lectures.');
      return;
    }
    if (!adminSchedule && (!user?.faculty_id || !assignment)) {
      setError('Select one of your assigned classes and subjects before scheduling.');
      return;
    }
    if (adminSchedule && (!selectedDivisionId || !selectedSubjectId || !selectedFacultyId)) {
      setError('Select a division, subject, and faculty member before scheduling.');
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await api.post('/timetable/entries', {
        division_id: adminSchedule ? selectedDivisionId : assignment!.division_id,
        subject_id: adminSchedule ? selectedSubjectId : assignment!.subject_id,
        faculty_id: adminSchedule ? selectedFacultyId : user!.faculty_id,
        day_of_week: selectedSlot.day,
        period_number: selectedSlot.period,
        start_time: periodTimes[selectedSlot.period][0],
        end_time: periodTimes[selectedSlot.period][1],
        room_number: roomNumber || undefined,
      });
      setSelectedSlot(null);
      setSelectedAssignment('');
      setRoomNumber('');
      const data = await api.get<TimetableEntry[]>(adminSchedule
        ? `/timetable?division_id=${selectedDivisionId}`
        : `/timetable?faculty_id=${user!.faculty_id}`);
      setEntries(data);
      if (adminSchedule) {
        setFacultyEntries(await api.get<TimetableEntry[]>(`/timetable?faculty_id=${selectedFacultyId}`));
      }
    } catch (err: any) {
      setError(err.message || 'Unable to schedule this slot');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-[1500px] space-y-7">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-3 flex items-center gap-2 text-xs font-medium text-slate-400">
            <span>Academics</span><ChevronRight className="h-3.5 w-3.5" /><span className="text-slate-600">Timetable &amp; Scheduling</span>
          </div>
          <div className="flex items-start gap-4">
            <div className="hidden rounded-2xl border border-slate-200 bg-slate-100 p-3 text-brand-700 sm:block"><Calendar className="h-7 w-7" /></div>
            <div>
              <h1 className="font-display text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
                Timetable &amp; Conflict-Free Scheduling Matrix
              </h1>
              <p className="mt-1 text-sm text-slate-500">Plan weekly classes with faculty allocation, room details, and built-in clash prevention.</p>
            </div>
          </div>
        </div>
        {canCreateSchedule && (
          <button type="button" disabled={isLoading || (isAdminView && !selectedDivisionId)} onClick={scheduleFirstFreeSlot} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-700 to-violet-700 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-950/20 transition hover:from-indigo-800 hover:to-violet-800 disabled:cursor-not-allowed disabled:opacity-50">
            <Plus className="h-4 w-4" /> Schedule Class Slot
          </button>
        )}
      </div>

      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="bg-gradient-to-r from-[#17263e] via-[#223858] to-[#17263e] px-6 py-5 text-white">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold">Academic Timetable Parameters &amp; Course Legend</h2>
              <p className="mt-1 text-xs text-slate-300">Choose a cohort, review course allocations, and schedule without clashes.</p>
            </div>
            <span className="inline-flex items-center gap-2 rounded-lg border border-slate-500/50 bg-slate-800/60 px-3 py-2 text-[11px] font-bold text-slate-200">
              <ShieldCheck className="h-4 w-4 text-emerald-400" /> Clash Detection: <span className="text-emerald-300">Active</span>
            </span>
          </div>
        </div>
        <div className="space-y-4 p-5 sm:px-6">
          {isAdminView && (
            <label className="flex flex-col gap-2 text-sm font-semibold text-slate-700 sm:flex-row sm:items-center">
              <span className="inline-flex items-center gap-2"><BookOpen className="h-4 w-4 text-slate-400" /> Active Academic Cohort</span>
              <select
                aria-label="Active Academic Cohort"
                value={selectedDivisionId}
                onChange={event => {
                  const nextClass = classes.find(item => item.divisions.some(division => division.id === event.target.value));
                  setSelectedClassId(nextClass?.id || '');
                  setSelectedDivisionId(event.target.value);
                }}
                className="w-full max-w-md rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-normal text-slate-800 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
              >
                {classes.flatMap(item => item.divisions.map(division => (
                  <option key={division.id} value={division.id}>{item.name} · Division {division.name}</option>
                )))}
              </select>
            </label>
          )}
          {legendSubjects.length > 0 ? (
            <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
              <span className="mr-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">Subject legend</span>
              {legendSubjects.map(subject => {
                const color = SUBJECT_COLORS[Math.max(0, subjects.findIndex(item => item.id === subject.id)) % SUBJECT_COLORS.length];
                return <span key={subject.id} className={`inline-flex items-center gap-1.5 rounded-full border border-current/10 px-2.5 py-1 text-[10px] font-bold ${color.chip}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{subject.code}: {subject.name}</span>;
              })}
            </div>
          ) : (
            <p className="border-t border-slate-100 pt-4 text-xs text-slate-400">Subjects will appear here as they are scheduled for this cohort.</p>
          )}
        </div>
      </section>

      {activeRole === 'FACULTY' && user?.faculty_id && (
        <FacultySlotPicker
          facultyId={user.faculty_id}
          assignments={assignments}
          onScheduled={() => setTimetableRefreshKey((current) => current + 1)}
        />
      )}

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-700 bg-gradient-to-r from-[#17263e] via-[#223858] to-[#17263e] px-6 py-5 text-white">
          <div>
            <h2 className="text-base font-bold">Weekly Lecture Schedule Matrix{selectedClass && selectedDivision ? ` (${selectedClass.name} · Division ${selectedDivision.name})` : ''}</h2>
            <p className="mt-1 text-xs text-slate-300">Monday through Saturday · {periods.length} periods daily · Conflict-checked allocations</p>
          </div>
          <span className="rounded-lg border border-slate-500/50 bg-slate-800/60 px-3 py-1.5 text-xs font-semibold text-slate-200">Weekly Schedule</span>
        </div>
        {isLoading ? (
          <div className="p-10 text-center text-sm text-slate-400">Loading timetable…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1050px] border-collapse text-left text-xs">
              <thead>
                <tr className="bg-[#1c2d48] text-white">
                  <th className="w-28 border-r border-slate-700 px-4 py-3 text-center text-[10px] font-bold uppercase tracking-wider">Day</th>
                  {periods.map(period => (
                    <th key={period} className="min-w-[155px] border-r border-slate-700 px-3 py-2.5 text-center">
                      <span className="inline-block rounded-md bg-slate-600/70 px-2 py-1 text-xs font-bold">Period {period}</span>
                      <span className="mt-1 block text-[10px] font-normal text-sky-200">{formatIndianTime(periodTimes[period][0])} – {formatIndianTime(periodTimes[period][1])}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {days.map(day => (
                  <tr key={day.num}>
                    <th scope="row" className="border-r border-slate-100 bg-slate-50 px-3 py-3 text-center">
                      <span className="mx-auto mb-1 flex h-7 w-10 items-center justify-center rounded-md bg-slate-200 text-[9px] font-black uppercase text-slate-600">{day.name.slice(0, 3)}</span>
                      <span className="text-xs font-bold text-slate-800">{day.name}</span>
                    </th>
                    {periods.map(period => {
                      const slot = getSlot(day.num, period);
                      const colorIndex = slot ? subjects.findIndex(subject => subject.id === slot.subject_id) : -1;
                      const color = SUBJECT_COLORS[(colorIndex < 0 ? 0 : colorIndex) % SUBJECT_COLORS.length];
                      return (
                        <td key={period} className="border-r border-slate-100 p-1.5 align-top">
                          {slot ? (
                            <div className={`min-h-[82px] rounded-xl border border-slate-200 border-l-4 p-2.5 shadow-sm ${color.card}`}>
                              <div className="mb-1.5 flex items-center justify-between gap-2">
                                <span className={`max-w-[75%] truncate rounded-full px-2 py-0.5 text-[9px] font-extrabold ${color.chip}`}>{slot.subject_code || 'SUBJECT'}</span>
                                <span className="shrink-0 text-[9px] font-semibold text-slate-400">{slot.is_practical_batch ? 'LAB' : 'LEC'}</span>
                              </div>
                              <p className="truncate text-[11px] font-bold text-slate-900" title={slot.subject_name}>{slot.subject_name}</p>
                              {!isAdminView && <p className="mt-1 truncate text-[10px] font-medium text-slate-500">{slot.class_name} · Div {slot.division_name}</p>}
                              <div className="mt-1.5 flex min-w-0 items-center justify-between gap-1 text-[9px] text-slate-500">
                                <span className="flex min-w-0 items-center gap-1 truncate"><User className="h-3 w-3 shrink-0" />{slot.faculty_name}</span>
                                {slot.room_number && <span className="flex shrink-0 items-center gap-1"><MapPin className="h-3 w-3" />{slot.room_number}</span>}
                              </div>
                            </div>
                          ) : (
                            <button
                              type="button"
                              disabled={!canCreateSchedule}
                              onClick={() => {
                                if (!canCreateSchedule) return;
                                setError(null);
                                if (isAdminView) {
                                  setSelectedSubjectId(slotSubjects[`${day.num}-${period}`] || '');
                                  setSelectedFacultyId('');
                                  setFacultyEntries([]);
                                }
                                setSelectedSlot({ day: day.num, period });
                              }}
                              className={`flex min-h-[82px] w-full flex-col items-center justify-center gap-1 rounded-xl border border-dashed transition ${
                                canCreateSchedule
                                  ? 'border-slate-200 text-slate-400 hover:border-indigo-300 hover:bg-indigo-50/60 hover:text-indigo-600'
                                  : 'border-transparent text-slate-300'
                              }`}
                            >
                              {canCreateSchedule ? <><Clock className="h-4 w-4" /><span className="text-[10px] font-medium">Free</span></> : <span aria-label="No scheduled class">—</span>}
                            </button>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {selectedSlot && (
          <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl w-full max-w-lg p-6">
              <div className="flex items-start justify-between gap-4 mb-5">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-brand-600">Schedule Class Slot</p>
                  <h2 className="text-xl font-bold text-slate-900 mt-1">{days.find(day => day.num === selectedSlot.day)?.name} · Period {selectedSlot.period}</h2>
                  <p className="text-xs text-slate-500 mt-1">{formatIndianTime(periodTimes[selectedSlot.period][0])} - {formatIndianTime(periodTimes[selectedSlot.period][1])}</p>
                </div>
                <button type="button" onClick={() => setSelectedSlot(null)} className="p-2 rounded-lg hover:bg-slate-100 text-slate-500"><X className="w-4 h-4" /></button>
              </div>
              {error && <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs font-semibold text-rose-700">{error}</div>}
              <form onSubmit={saveSlot} className="space-y-4">
                {isAdminView ? <>
                  <label className="block text-xs font-semibold text-slate-700">
                    Division
                    <select required value={selectedDivisionId} onChange={event => setSelectedDivisionId(event.target.value)} className="mt-1 w-full px-3 py-2.5 border rounded-lg bg-slate-50">
                      {(classes.find(item => item.id === selectedClassId)?.divisions || []).map(division => <option key={division.id} value={division.id}>Division {division.name}</option>)}
                    </select>
                  </label>
                  <label className="block text-xs font-semibold text-slate-700">
                    Subject
                    <select required value={selectedSubjectId} onChange={event => setSelectedSubjectId(event.target.value)} className="mt-1 w-full px-3 py-2.5 border rounded-lg bg-slate-50">
                      <option value="">Select subject</option>
                      {subjects.filter(subject => {
                        const reservedSubjectId = selectedSlot ? slotSubjects[`${selectedSlot.day}-${selectedSlot.period}`] : null;
                        return !reservedSubjectId || subject.id === reservedSubjectId;
                      }).map(subject => <option key={subject.id} value={subject.id}>{subject.code} · {subject.name}</option>)}
                    </select>
                    {selectedSlot && slotSubjects[`${selectedSlot.day}-${selectedSlot.period}`] && <span className="mt-1 block text-[11px] font-medium text-amber-700">This time slot is reserved for the configured subject.</span>}
                  </label>
                  <label className="block text-xs font-semibold text-slate-700">
                    Faculty
                    <select required value={selectedFacultyId} onChange={event => setSelectedFacultyId(event.target.value)} className="mt-1 w-full px-3 py-2.5 border rounded-lg bg-slate-50">
                      <option value="">Select faculty</option>
                      {faculty.map(member => {
                        const busy = facultyEntries.some(entry => entry.day_of_week === selectedSlot.day && entry.period_number === selectedSlot.period);
                        return <option key={member.id} value={member.id} disabled={busy}>{member.full_name}{busy ? ' · Busy at this time' : ''}</option>;
                      })}
                    </select>
                    {selectedFacultyId && facultyEntries.some(entry => entry.day_of_week === selectedSlot.day && entry.period_number === selectedSlot.period) && <span className="mt-1 block text-[11px] font-medium text-rose-600">This faculty member is already allocated at this day and period.</span>}
                  </label>
                </> : <label className="block text-xs font-semibold text-slate-700">
                  Assigned class and subject
                  <select required value={selectedAssignment} onChange={event => setSelectedAssignment(event.target.value)} className="mt-1 w-full px-3 py-2.5 border rounded-lg bg-slate-50">
                    <option value="">Select a teaching assignment</option>
                    {assignments.map(assignment => (
                      <option key={assignment.subject_id + assignment.division_id} value={assignment.subject_id + assignment.division_id}>
                        {assignment.class_name} · Division {assignment.division_name} · {assignment.subject_code} {assignment.subject_name}
                      </option>
                    ))}
                  </select>
                </label>}
                <label className="block text-xs font-semibold text-slate-700">
                  Room (optional)
                  <input value={roomNumber} onChange={event => setRoomNumber(event.target.value)} className="mt-1 w-full px-3 py-2.5 border rounded-lg bg-slate-50" placeholder="e.g. Lab-Hall 101" />
                </label>
                <div className="flex justify-end gap-2 pt-4 border-t">
                  <button type="button" onClick={() => setSelectedSlot(null)} className="px-4 py-2 rounded-lg border text-xs font-bold text-slate-600">Cancel</button>
                  <button type="submit" disabled={isSaving || (!isAdminView && assignments.length === 0)} className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold">
                    {isSaving ? 'Scheduling...' : 'Schedule Slot'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </section>
    </div>
  );
};
