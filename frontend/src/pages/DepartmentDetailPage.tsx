import React, { useEffect, useState } from 'react';
import { ArrowLeft, GraduationCap, UserRound } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useIsEngineeringCollege } from '../hooks/useIsEngineeringCollege';

interface AcademicClass { id: string; name: string; stream: string; divisions: { id: string; name: string }[]; }

export const DepartmentDetailPage: React.FC = () => {
  const { id } = useParams();
  const [department, setDepartment] = useState<AcademicClass | null>(null);
  const isEngineering = useIsEngineeringCollege();
  useEffect(() => { api.get<AcademicClass[]>('/academics/classes').then((items) => setDepartment(items.find((item) => item.id === id) || null)); }, [id]);
  if (!department || isEngineering === null) return <div className="premium-card p-6 text-sm text-slate-500">Loading department...</div>;
  return <div className="mx-auto max-w-5xl space-y-7">
    <Link to="/departments" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-indigo-600"><ArrowLeft className="h-4 w-4" /> Back to departments</Link>
    <div><p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">{department.stream || 'Custom category'}</p><h1 className="font-display text-3xl font-semibold tracking-tight text-slate-950">{department.name}</h1><p className="mt-2 text-sm text-slate-500">{isEngineering ? 'Manage only the faculty and students assigned to this department.' : 'Admit students into this department or class.'}</p></div>
    <div className="grid gap-5 sm:grid-cols-2">
      {isEngineering && <Link to={`/faculty?department=${encodeURIComponent(department.name)}`} className="premium-card group p-6"><GraduationCap className="mb-8 h-8 w-8 text-indigo-600" /><h2 className="font-display text-xl font-semibold">Department faculty</h2><p className="mt-2 text-sm text-slate-500">Add faculty accounts with email login credentials and manage this department’s lecturers.</p><span className="mt-5 inline-block text-sm font-bold text-indigo-600 group-hover:underline">Open faculty management →</span></Link>}
      <Link to={`/students?class_id=${department.id}`} className="premium-card group p-6"><UserRound className="mb-8 h-8 w-8 text-indigo-600" /><h2 className="font-display text-xl font-semibold">{isEngineering ? 'Department students' : 'Class students'}</h2><p className="mt-2 text-sm text-slate-500">Admit students and create their email login credentials.</p><span className="mt-5 inline-block text-sm font-bold text-indigo-600 group-hover:underline">Open student management →</span></Link>
    </div>
    <div className="premium-card p-5"><h2 className="font-semibold text-slate-900">Divisions</h2><div className="mt-3 flex flex-wrap gap-2">{department.divisions.length ? department.divisions.map((division) => <span key={division.id} className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs text-slate-600">Division {division.name}</span>) : <span className="text-sm text-slate-400">No divisions configured.</span>}</div></div>
  </div>;
};
