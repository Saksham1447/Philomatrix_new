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

  const navSections = [
    {
      label: 'Overview',
      items: [{
        label: 'Dashboard',
        path: '/dashboard',
        icon: LayoutDashboard,
        roles: ['SUPER_ADMIN', 'PRINCIPAL', 'FACULTY', 'STUDENT', 'PARENT', 'OFFICE_STAFF']
      }]
    },
    {
      label: 'Academic Core',
      items: [
        {
          label: 'Students & Enrollment',
          path: '/students',
          icon: Users,
          roles: ['PRINCIPAL', 'OFFICE_STAFF', 'FACULTY']
        },
        {
          label: 'Faculty & Workload',
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
          label: 'Timetable & Scheduling',
          path: '/timetable',
          icon: Calendar,
          roles: ['PRINCIPAL', 'FACULTY', 'STUDENT', 'PARENT', 'OFFICE_STAFF']
        },
        {
          label: 'Time Slot Setup',
          path: '/timetable-slots',
          icon: CalendarClock,
          roles: ['PRINCIPAL', 'OFFICE_STAFF']
        },
        {
          label: 'Exams & Gradebook',
          path: '/examinations',
          icon: Award,
          roles: ['PRINCIPAL', 'OFFICE_STAFF', 'FACULTY', 'STUDENT', 'PARENT']
        },
        {
          label: 'Report Cards & Results',
          path: '/report-cards',
          icon: FileText,
          roles: ['PRINCIPAL', 'FACULTY', 'STUDENT', 'PARENT']
        },
        {
          label: 'Learning Resources',
          path: '/study-materials',
          icon: FolderOpen,
          roles: ['SUPER_ADMIN', 'PRINCIPAL', 'FACULTY', 'STUDENT', 'PARENT']
        },
        {
          label: 'Homework & Assignments',
          path: '/assignments',
          icon: BookOpen,
          roles: ['FACULTY', 'STUDENT', 'PARENT']
        },
      ]
    },
    {
      label: 'Operations',
      items: [
        {
          label: 'Attendance Manager',
          path: '/attendance',
          icon: CalendarCheck,
          roles: ['PRINCIPAL', 'FACULTY', 'STUDENT', 'PARENT', 'OFFICE_STAFF']
        },
        {
          label: 'Faculty Leave Requests',
          path: '/leave-requests',
          icon: ClipboardCheck,
          roles: ['FACULTY', 'OFFICE_STAFF']
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
      ]
    },
    {
      label: 'Administration',
      items: [
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
          label: 'Settings & Preferences',
          path: '/settings',
          icon: Sliders,
          roles: ['SUPER_ADMIN', 'PRINCIPAL', 'FACULTY', 'OFFICE_STAFF']
        },
        {
          label: 'Security & Audit Logs',
          path: '/audit-logs',
          icon: ShieldCheck,
          roles: ['SUPER_ADMIN', 'PRINCIPAL']
        },
      ]
    },
  ];

  return (
    <aside className="w-full sm:w-64 bg-[#10172a] text-slate-300 flex flex-col shrink-0 border-b sm:border-b-0 sm:border-r border-slate-800/80 shadow-[10px_0_40px_-32px_rgba(15,23,42,0.9)] sm:sticky sm:top-[4.5rem] sm:h-[calc(100vh-4.5rem)]">
      <div className="p-5 border-b border-white/10 bg-gradient-to-br from-indigo-950 via-[#10172a] to-slate-950">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
          Academic Navigation
        </p>
      </div>

      <nav className="flex flex-1 sm:block px-3 py-3 sm:py-4 space-x-1 sm:space-x-0 sm:space-y-1 overflow-x-auto sm:overflow-y-auto scrollbar-hidden">
        {navSections.map(section => {
          const visibleItems = section.items.filter(item =>
            activeRole ? item.roles.includes(activeRole) : false
          );
          if (visibleItems.length === 0) return null;

          return (
            <div key={section.label} className="space-y-1">
              <p className="px-3 pt-3 pb-1 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500 first:pt-0">
                {section.label}
              </p>
              {visibleItems.map(item => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      `group flex shrink-0 items-center space-x-3 rounded-xl border-l-2 px-3 py-2.5 text-sm font-medium transition-all ${
                        isActive
                          ? 'border-brand-400 bg-gradient-to-r from-brand-600 via-indigo-600 to-sky-600 text-white shadow-lg shadow-indigo-950/40 ring-1 ring-white/10'
                          : 'border-transparent text-slate-400 hover:border-slate-600 hover:bg-white/[0.07] hover:text-white'
                      }`
                    }
                  >
                    <Icon className="h-4 w-4 shrink-0 opacity-80 transition-opacity group-hover:opacity-100" />
                    <span className="whitespace-nowrap">{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
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
