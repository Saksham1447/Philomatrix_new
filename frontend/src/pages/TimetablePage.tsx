import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { ClassModel, Faculty, Subject, TimetableEntry } from '../types';
import { formatIndianTime } from '../utils/time';
import { FacultySlotPicker } from '../components/common/FacultySlotPicker';
import { Calendar, Clock, MapPin, User, BookOpen, Plus, X, Filter } from 'lucide-react';

export const TimetablePage: React.FC = () => {
  const { user, activeRole, activeChild } = useAuth();
  const isAdminView = activeRole === 'PRINCIPAL' || activeRole === 'OFFICE_STAFF' || activeRole === 'SUPER_ADMIN';
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

  const days = [
    { num: 1, name: 'Monday' },
    { num: 2, name: 'Tuesday' },
    { num: 3, name: 'Wednesday' },
    { num: 4, name: 'Thursday' },
    { num: 5, name: 'Friday' },
    { num: 6, name: 'Saturday' },
  ];

  const periods = Array.from({ length: Math.max(7, ...Object.keys(slotTimes).map(Number)) }, (_, index) => index + 1);
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
            return;
          }
          url = `/timetable?division_id=${selectedDivisionId}`;
          const slots = await api.get<Array<{ period_number: number; start_time: string; end_time: string }>>(`/timetable/slots?division_id=${selectedDivisionId}`);
          setSlotTimes(Object.fromEntries(slots.map((slot) => [slot.period_number, [slot.start_time, slot.end_time]])));
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
  }, [activeRole, activeChild, user, isAdminView, selectedDivisionId]);

  const getSlot = (dayNum: number, periodNum: number) => {
    return entries.find(e => e.day_of_week === dayNum && e.period_number === periodNum);
  };

  const saveSlot = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedSlot) return;
    const adminSchedule = isAdminView;
    const assignment = assignments.find(item => item.subject_id + item.division_id === selectedAssignment);
    if (!adminSchedule && (!user?.faculty_id || !assignment)) return;
    if (adminSchedule && (!selectedDivisionId || !selectedSubjectId || !selectedFacultyId)) return;
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
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight font-display flex items-center gap-2">
            <Calendar className="w-7 h-7 text-brand-600" />
            Academic Timetable
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Weekly period schedule with conflict validation and room allocation
          </p>
        </div>

        {error && <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm">{error}</div>}

        {activeRole === 'FACULTY' && (
          <div className="bg-white rounded-2xl border border-slate-200 p-4 flex items-center gap-3 text-xs text-slate-600">
            <Filter className="w-4 h-4 text-brand-600" />
            <span>Click any <strong className="text-slate-900">Free</strong> cell to schedule one of your assigned classes. Existing allocations remain protected by conflict detection.</span>
          </div>
        )}
      </div>

      {activeRole === 'FACULTY' && user?.faculty_id && (
        <FacultySlotPicker
          facultyId={user.faculty_id}
          assignments={assignments}
          onScheduled={async () => setEntries(await api.get<TimetableEntry[]>(`/timetable?faculty_id=${user.faculty_id}`))}
        />
      )}

      {isAdminView && (
        <div className="bg-white rounded-2xl border border-slate-200 p-4 flex flex-col sm:flex-row sm:items-end gap-3">
          <label className="text-xs font-semibold text-slate-600">
            Department / class
            <select
              value={selectedClassId}
              onChange={event => {
                const next = classes.find(item => item.id === event.target.value);
                setSelectedClassId(event.target.value);
                setSelectedDivisionId(next?.divisions[0]?.id || '');
              }}
              className="mt-1 block px-3 py-2 border rounded-lg bg-slate-50 text-sm font-normal"
            >
              {classes.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Division
            <select value={selectedDivisionId} onChange={event => setSelectedDivisionId(event.target.value)} className="mt-1 block px-3 py-2 border rounded-lg bg-slate-50 text-sm font-normal">
              {(classes.find(item => item.id === selectedClassId)?.divisions || []).map(division => <option key={division.id} value={division.id}>Division {division.name}</option>)}
            </select>
          </label>
          <p className="text-xs text-slate-500 sm:ml-auto">Each division has its own timetable. Teachers fill it from their own login.</p>
        </div>
      )}

      {/* Timetable Grid */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="bg-slate-900 text-white font-bold uppercase tracking-wider">
                <th className="py-3 px-4 border-r border-slate-800 w-28">Day / Period</th>
                {periods.map(p => (
                  <th key={p} className="py-3 px-3 border-r border-slate-800 text-center min-w-[130px]">
                    <span className="block">Period {p}</span>
                    <span className="text-[10px] font-normal text-slate-300">{formatIndianTime(periodTimes[p][0])} - {formatIndianTime(periodTimes[p][1])}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {days.map(d => (
                <tr key={d.num} className="hover:bg-slate-50/50">
                  <td className="py-4 px-4 font-bold text-slate-900 bg-slate-50 border-r border-slate-200">
                    {d.name}
                  </td>
                  {periods.map(p => {
                    const slot = getSlot(d.num, p);
                    return (
                      <td key={p} className="p-2 border-r border-slate-200 align-top">
                        {slot ? (
                          <div className="p-2.5 rounded-xl bg-brand-50/80 border border-brand-200 text-brand-950 space-y-1 shadow-2xs">
                            <div className="flex items-center justify-between">
                              <span className="font-extrabold text-xs text-brand-700">
                                {slot.subject_code}
                              </span>
                              <span className="text-[10px] text-slate-500">
                                {formatIndianTime(slot.start_time)}
                              </span>
                            </div>
                            <p className="font-bold text-xs truncate" title={slot.subject_name}>
                              {slot.subject_name}
                            </p>
                            {!isAdminView && (
                              <p className="text-[10px] font-semibold text-brand-700 truncate">{slot.class_name} · Div {slot.division_name}</p>
                            )}
                            <p className="text-[11px] text-slate-600 truncate flex items-center gap-1">
                              <User className="w-3 h-3 text-slate-400 shrink-0" />
                              {slot.faculty_name}
                            </p>
                            {slot.room_number && (
                              <p className="text-[10px] text-slate-500 flex items-center gap-1">
                                <MapPin className="w-3 h-3 text-slate-400 shrink-0" />
                                {slot.room_number}
                              </p>
                            )}
                          </div>
                        ) : (
                          <button
                            type="button"
                            disabled={activeRole !== 'FACULTY' && !isAdminView}
                            onClick={() => {
                              if (activeRole === 'FACULTY' || isAdminView) {
                                setError(null);
                                setSelectedSlot({ day: d.num, period: p });
                              }
                            }}
                            className={`h-20 w-full rounded-xl border border-dashed flex flex-col items-center justify-center gap-1 text-[11px] font-medium transition-colors ${
                              activeRole === 'FACULTY' || isAdminView
                                ? 'border-slate-300 text-slate-400 hover:border-brand-400 hover:bg-brand-50 hover:text-brand-700 cursor-pointer'
                                : 'border-transparent text-slate-300'
                            }`}
                          >
                            {(activeRole === 'FACULTY' || isAdminView) && <Plus className="w-4 h-4" />}
                            <span>{activeRole === 'FACULTY' || isAdminView ? 'Add lecture' : '—'}</span>
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
                      {subjects.map(subject => <option key={subject.id} value={subject.id}>{subject.code} · {subject.name}</option>)}
                    </select>
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
                  <button type="submit" disabled={isSaving || assignments.length === 0} className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold">
                    {isSaving ? 'Scheduling...' : 'Schedule Slot'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
