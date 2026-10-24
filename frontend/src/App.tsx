import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { AppLayout } from './layouts/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { AttendancePage } from './pages/AttendancePage';
import { ExaminationsPage } from './pages/ExaminationsPage';
import { ReportCardPage } from './pages/ReportCardPage';
import { TimetablePage } from './pages/TimetablePage';
import { TimetableSlotsPage } from './pages/TimetableSlotsPage';
import { StudentsPage } from './pages/StudentsPage';
import { AssignmentsPage } from './pages/AssignmentsPage';
import { NoticesPage } from './pages/NoticesPage';
import { FeedbackPage } from './pages/FeedbackPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { SettingsPage } from './pages/SettingsPage';
import { StudyMaterialsPage } from './pages/StudyMaterialsPage';
import { LeaveRequestsPage } from './pages/LeaveRequestsPage';
import { InstitutionsPage } from './pages/InstitutionsPage';
import { StaffPage } from './pages/StaffPage';
import { FacultyPage } from './pages/FacultyPage';
import { DepartmentsPage } from './pages/DepartmentsPage';
import { DepartmentDetailPage } from './pages/DepartmentDetailPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route path="/" element={<AppLayout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="attendance" element={<AttendancePage />} />
              <Route path="timetable" element={<TimetablePage />} />
              <Route path="timetable-slots" element={<TimetableSlotsPage />} />
              <Route path="examinations" element={<ExaminationsPage />} />
              <Route path="report-cards" element={<ReportCardPage />} />
              <Route path="students" element={<StudentsPage />} />
              <Route path="study-materials" element={<StudyMaterialsPage />} />
              <Route path="leave-requests" element={<LeaveRequestsPage />} />
              <Route path="assignments" element={<AssignmentsPage />} />
              <Route path="notices" element={<NoticesPage />} />
              <Route path="feedback" element={<FeedbackPage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="institutions" element={<InstitutionsPage />} />
              <Route path="office-staff" element={<StaffPage />} />
              <Route path="faculty" element={<FacultyPage />} />
              <Route path="departments" element={<DepartmentsPage />} />
              <Route path="departments/:id" element={<DepartmentDetailPage />} />
              <Route path="audit-logs" element={<AuditLogsPage />} />
            </Route>


            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;
