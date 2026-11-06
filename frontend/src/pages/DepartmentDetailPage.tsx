import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, BookOpen, GraduationCap, Save, UserRound } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useIsEngineeringCollege } from '../hooks/useIsEngineeringCollege';

interface Division { id: string; name: string; }
interface AcademicClass { id: string; name: string; stream: string; divisions: Division[]; }
interface AcademicYear { id: string; name: string; is_current: boolean; }
interface Subject { id: string; name: string; code: string; }
interface Faculty { id: string; full_name: string; }
interface Assignment {
  id: string;
  academic_year_id: string;
  class_id: string;
  division_id: string;
  subject_id: string;
  faculty_id: string;
}

export const DepartmentDetailPage: React.FC = () => {
  const { id } = useParams();
  const { activeRole } = useAuth();
  const [department, setDepartment] = useState<AcademicClass | null>(null);
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [faculty, setFaculty] = useState<Faculty[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [selectedYearId, setSelectedYearId] = useState('');
  const [selectedSubjectIds, setSelectedSubjectIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingCurriculum, setSavingCurriculum] = useState(false);
  const [savingCell, setSavingCell] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const isEngineering = useIsEngineeringCollege();
  const canManage = ['SUPER_ADMIN', 'PRINCIPAL', 'OFFICE_STAFF'].includes(activeRole || '');

  const loadAssignments = async () => {
    const allAssignments = await api.get<Assignment[]>('/faculty/assignments');
    setAssignments(allAssignments);
  };

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        setLoading(true);
        const [classes, academicYears, allSubjects, teachers, allAssignments] = await Promise.all([
          api.get<AcademicClass[]>('/academics/classes'),
          api.get<AcademicYear[]>('/academics/years'),
          api.get<Subject[]>('/academics/subjects'),
          api.get<Faculty[]>('/faculty'),
          api.get<Assignment[]>('/faculty/assignments'),
        ]);
        if (!active) return;
        const selectedClass = classes.find((item) => item.id === id) || null;
        const currentYear = academicYears.find((year) => year.is_current) || academicYears[0];
        setDepartment(selectedClass);
        setYears(academicYears);
        setSubjects(allSubjects);
        setFaculty(teachers);
        setAssignments(allAssignments);
        if (currentYear) setSelectedYearId(currentYear.id);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Could not load department details');
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, [id]);

  useEffect(() => {
    if (!id || !selectedYearId) return;
    let active = true;
    api.get<Subject[]>(`/academics/classes/${id}/subjects?academic_year_id=${encodeURIComponent(selectedYearId)}`)
      .then((items) => { if (active) setSelectedSubjectIds(items.map((subject) => subject.id)); })
      .catch((err) => { if (active) setError(err instanceof Error ? err.message : 'Could not load class subjects'); });
    return () => { active = false; };
  }, [id, selectedYearId]);

  const selectedSubjects = useMemo(
    () => subjects.filter((subject) => selectedSubjectIds.includes(subject.id)),
    [subjects, selectedSubjectIds],
  );
  const assignmentFor = (divisionId: string, subjectId: string) => assignments.find((assignment) =>
    assignment.academic_year_id === selectedYearId &&
    assignment.division_id === divisionId &&
    assignment.subject_id === subjectId
  );

  const saveCurriculum = async () => {
    if (!id || !selectedYearId) return;
    setSavingCurriculum(true);
    setError('');
    setMessage('');
    try {
      const saved = await api.put<Subject[]>(`/academics/classes/${id}/subjects`, {
        academic_year_id: selectedYearId,
        subject_ids: selectedSubjectIds,
      });
      setSelectedSubjectIds(saved.map((subject) => subject.id));
      setMessage('Class subjects saved. They apply to every division in this class.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save class subjects');
    } finally {
      setSavingCurriculum(false);
    }
  };

  const changeTeacher = async (divisionId: string, subjectId: string, facultyId: string) => {
    if (!id || !selectedYearId) return;
    const key = `${divisionId}:${subjectId}`;
    setSavingCell(key);
    setError('');
    setMessage('');
    try {
      const existing = assignmentFor(divisionId, subjectId);
      if (!facultyId) {
        if (existing) await api.delete(`/faculty/assignments/${existing.id}`);
      } else {
        const payload = {
          academic_year_id: selectedYearId,
          faculty_id: facultyId,
          subject_id: subjectId,
          division_id: divisionId,
          is_class_teacher: false,
        };
        if (existing) await api.put(`/faculty/assignments/${existing.id}`, payload);
        else await api.post('/faculty/assignments', payload);
      }
      await loadAssignments();
      setMessage('Teacher assignment saved.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save teacher assignment');
    } finally {
      setSavingCell('');
    }
  };

  if (loading || !department || isEngineering === null) {
    return <div className="premium-card p-6 text-sm text-slate-500">{error || 'Loading department...'}</div>;
  }

  return <div className="mx-auto max-w-5xl space-y-7">
    <Link to="/departments" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-indigo-600"><ArrowLeft className="h-4 w-4" /> Back to departments</Link>
    <div><p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">{department.stream || 'Custom category'}</p><h1 className="font-display text-3xl font-semibold tracking-tight text-slate-950">{department.name}</h1><p className="mt-2 text-sm text-slate-500">{isEngineering ? 'Manage only the faculty and students assigned to this department.' : 'Admit students into this department or class.'}</p></div>
    <div className="grid gap-5 sm:grid-cols-2">
      {isEngineering && <Link to={`/faculty?department=${encodeURIComponent(department.name)}`} className="premium-card group p-6"><GraduationCap className="mb-8 h-8 w-8 text-indigo-600" /><h2 className="font-display text-xl font-semibold">Department faculty</h2><p className="mt-2 text-sm text-slate-500">Add faculty accounts with email login credentials and manage this department’s lecturers.</p><span className="mt-5 inline-block text-sm font-bold text-indigo-600 group-hover:underline">Open faculty management →</span></Link>}
      <Link to={`/students?class_id=${department.id}`} className="premium-card group p-6"><UserRound className="mb-8 h-8 w-8 text-indigo-600" /><h2 className="font-display text-xl font-semibold">{isEngineering ? 'Department students' : 'Class students'}</h2><p className="mt-2 text-sm text-slate-500">Admit students and create their email login credentials.</p><span className="mt-5 inline-block text-sm font-bold text-indigo-600 group-hover:underline">Open student management →</span></Link>
    </div>
    <div className="premium-card p-5"><h2 className="font-semibold text-slate-900">Divisions</h2><div className="mt-3 flex flex-wrap gap-2">{department.divisions.length ? department.divisions.map((division) => <span key={division.id} className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs text-slate-600">Division {division.name}</span>) : <span className="text-sm text-slate-400">No divisions configured.</span>}</div></div>

    <section className="premium-card space-y-5 p-5">
      <div className="flex items-start gap-3"><BookOpen className="mt-1 h-5 w-5 text-indigo-600" /><div><h2 className="font-semibold text-slate-900">Class subjects and teachers</h2><p className="mt-1 text-sm text-slate-500">Choose the subjects shared by every division, then assign a teacher separately for each division.</p></div></div>
      {error && <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      {message && <div role="status" className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</div>}
      <label className="block max-w-sm text-sm font-medium text-slate-700">Academic year
        <select className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2" value={selectedYearId} onChange={(event) => { setSelectedYearId(event.target.value); setError(''); setMessage(''); }}>
          {years.map((year) => <option key={year.id} value={year.id}>{year.name}{year.is_current ? ' (Current)' : ''}</option>)}
        </select>
      </label>
      {canManage && <>
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Subjects for all divisions</h3>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {subjects.map((subject) => <label key={subject.id} className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm">
              <input type="checkbox" checked={selectedSubjectIds.includes(subject.id)} onChange={(event) => setSelectedSubjectIds((current) => event.target.checked ? [...current, subject.id] : current.filter((value) => value !== subject.id))} />
              <span>{subject.name} <span className="text-slate-400">({subject.code})</span></span>
            </label>)}
          </div>
          <button type="button" onClick={saveCurriculum} disabled={savingCurriculum || !selectedYearId} className="mt-3 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"><Save className="h-4 w-4" />{savingCurriculum ? 'Saving...' : 'Save class subjects'}</button>
        </div>
        {selectedSubjects.length > 0 && <div className="overflow-x-auto">
          <h3 className="mb-3 text-sm font-semibold text-slate-800">Teacher assignments by division</h3>
          <table className="w-full min-w-[560px] border-collapse text-left text-sm">
            <thead><tr className="border-b border-slate-200 text-xs uppercase text-slate-500"><th className="px-3 py-2">Division</th>{selectedSubjects.map((subject) => <th key={subject.id} className="px-3 py-2">{subject.name}</th>)}</tr></thead>
            <tbody>{department.divisions.map((division) => <tr key={division.id} className="border-b border-slate-100">
              <th className="px-3 py-3 font-medium text-slate-800">{division.name}</th>
              {selectedSubjects.map((subject) => {
                const assignment = assignmentFor(division.id, subject.id);
                const key = `${division.id}:${subject.id}`;
                return <td key={subject.id} className="px-3 py-2">
                  <select aria-label={`${subject.name} teacher for division ${division.name}`} className="w-full rounded-lg border border-slate-200 bg-white px-2 py-2" value={assignment?.faculty_id || ''} disabled={savingCell === key} onChange={(event) => void changeTeacher(division.id, subject.id, event.target.value)}>
                    <option value="">Unassigned</option>
                    {faculty.map((teacher) => <option key={teacher.id} value={teacher.id}>{teacher.full_name}</option>)}
                  </select>
                </td>;
              })}
            </tr>)}</tbody>
          </table>
        </div>}
      </>}
    </section>
  </div>;
};
