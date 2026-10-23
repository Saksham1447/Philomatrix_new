import React from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Navbar } from '../components/common/Navbar';
import { Sidebar } from '../components/common/Sidebar';
import { AnimatedLogo } from '../components/common/AnimatedLogo';

export const AppLayout: React.FC = () => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <AnimatedLogo size="lg" variant="spin" />
          <p className="text-xs font-semibold text-slate-400 animate-pulse">
            Initializing PHILOMATRIX ERP...
          </p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-transparent relative">
      <div className="fixed inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-indigo-200/20 blur-3xl" />
        <div className="absolute top-1/3 -right-48 w-[30rem] h-[30rem] rounded-full bg-sky-200/15 blur-3xl" />
      </div>
      <Navbar />
      <div className="flex-1 flex flex-col sm:flex-row relative z-10">
        <Sidebar />
        <main className="min-w-0 flex-1 overflow-x-hidden px-3 py-5 sm:px-6 sm:py-8 lg:px-10">
          <div className="max-w-[1480px] mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
