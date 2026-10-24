import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard,
  CalendarCheck,
  Calendar,
  CalendarClock,
  Award,
  FileText,
  Users,
  BookOpen,
  Bell,
  MessageSquare,
  ShieldCheck,
  Building2,
  Sliders,
  FolderOpen,
  ClipboardCheck
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { activeRole } = useAuth();

  const navItems = [
    {
      label: 'Dashboard',
      path: '/dashboard',
      icon: LayoutDashboard,
      roles: ['SUPER_ADMIN', 'PRINCIPAL', 'FACULTY', 'STUDENT', 'PARENT', 'OFFICE_STAFF']
    },
    {
      label: 'Lecture Attendance',
      path: '/attendance',
      icon: CalendarCheck,
      roles: ['PRINCIPAL', 'FACULTY', 'STUDENT', 'PARENT', 'OFFICE_STAFF']
    },
    {
      label: 'Academic Timetable',
      path: '/timetable',
      icon: Calendar,
      roles: ['PRINCIPAL', 'FACULTY', 'STUDENT', 'PARENT', 'OFFICE_STAFF']
    },
    {
      label: 'Time Slots',
      path: '/timetable-slots',
      icon: CalendarClock,
      roles: ['PRINCIPAL', 'OFFICE_STAFF']
    },
    {
      label: 'Examinations & Marks',
      path: '/examinations',
      icon: Award,
      roles: ['PRINCIPAL', 'FACULTY', 'STUDENT', 'PARENT']
    },
    {
      label: 'Official Report Cards',
      path: '/report-cards',
      icon: FileText,
      roles: ['PRINCIPAL', 'FACULTY', 'STUDENT', 'PARENT']
    },
    {
      label: 'Student Directory',
      path: '/students',
      icon: Users,
      roles: ['PRINCIPAL', 'OFFICE_STAFF', 'FACULTY']
    },
    {
      label: 'Study Materials & Notes',
      path: '/study-materials',
      icon: FolderOpen,
      roles: ['SUPER_ADMIN', 'PRINCIPAL', 'FACULTY', 'STUDENT', 'PARENT']
    },
    {
      label: 'Faculty Leave Requests',
      path: '/leave-requests',
      icon: ClipboardCheck,
      roles: ['FACULTY', 'OFFICE_STAFF']
    },
    {
      label: 'Homework & Assignments',
      path: '/assignments',
      icon: BookOpen,
      roles: ['FACULTY', 'STUDENT', 'PARENT']
    },
    {
      label: 'Notices & Bulletins',
      path: '/notices',
      icon: Bell,
      roles: ['SUPER_ADMIN', 'PRINCIPAL', 'FACULTY', 'STUDENT', 'PARENT', 'OFFICE_STAFF']
    },
    {
      label: 'Academic Feedback',
      path: '/feedback',
      icon: MessageSquare,
      roles: ['PRINCIPAL', 'FACULTY', 'STUDENT']
    },
    {
      label: 'Settings & Preferences',
      path: '/settings',
      icon: Sliders,
      roles: ['SUPER_ADMIN', 'PRINCIPAL', 'FACULTY', 'OFFICE_STAFF']
    },
    {
      label: 'Institute Workspaces',
      path: '/institutions',
      icon: Building2,
      roles: ['SUPER_ADMIN']
    },
    {
      label: 'Office Staff',
      path: '/office-staff',
      icon: Users,
      roles: ['PRINCIPAL', 'SUPER_ADMIN']
    },
    {
      label: 'Faculty Directory',
      path: '/faculty',
      icon: Users,
      roles: ['PRINCIPAL', 'OFFICE_STAFF', 'SUPER_ADMIN']
    },
    {
      label: 'Departments & Classes',
      path: '/departments',
      icon: BookOpen,
      roles: ['OFFICE_STAFF', 'PRINCIPAL', 'SUPER_ADMIN']
    },
    {
      label: 'Security & Audit Logs',
      path: '/audit-logs',
      icon: ShieldCheck,
      roles: ['SUPER_ADMIN', 'PRINCIPAL']
    },
  ];

  const visibleItems = navItems.filter(item =>
    activeRole ? item.roles.includes(activeRole) : false
  );

  return (
    <aside className="w-full sm:w-64 bg-[#10172a] text-slate-300 flex flex-col shrink-0 border-b sm:border-b-0 sm:border-r border-slate-800/80 shadow-[10px_0_40px_-32px_rgba(15,23,42,0.9)] sm:sticky sm:top-[4.5rem] sm:h-[calc(100vh-4.5rem)]">
      <div className="p-5 border-b border-white/10 bg-gradient-to-br from-indigo-950 via-[#10172a] to-slate-950">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
          Academic Navigation
        </p>
      </div>

      <nav className="flex flex-1 sm:block px-3 py-3 sm:py-4 space-x-1 sm:space-x-0 sm:space-y-1 overflow-x-auto sm:overflow-y-auto scrollbar-hidden">
        {visibleItems.map(item => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex shrink-0 items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-gradient-to-r from-brand-600 via-indigo-600 to-sky-600 text-white shadow-lg shadow-indigo-950/40 ring-1 ring-white/10'
                    : 'text-slate-400 hover:text-white hover:bg-white/[0.07]'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="whitespace-nowrap">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer System Status */}
      <div className="hidden sm:block p-4 border-t border-slate-800/80 bg-slate-950/40">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_10px_rgba(52,211,153,0.8)]" />
          <p className="text-xs font-medium text-slate-400">
            System Online & Connected
          </p>
        </div>
      </div>
    </aside>
  );
};
