import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import { StudentsPage } from '../pages/StudentsPage';

const mockAuth = vi.hoisted(() => ({ activeRole: 'PRINCIPAL' }));

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockAuth,
}));

const roster = [
  {
    id: 'student-1',
    user_id: 'user-1',
    admission_number: 'ADM-001',
    roll_number: '11',
    first_name: 'Asha',
    last_name: 'Patel',
    full_name: 'Asha Patel',
    email: 'asha@example.edu',
    phone_number: '9876543210',
    date_of_birth: '2009-01-01',
    gender: 'FEMALE',
    admission_date: '2025-06-01',
    status: 'ACTIVE',
    fee_status: 'PENDING',
    class_name: 'Class 11',
    division_name: 'A',
    academic_year_name: '2025-2026',
  },
  {
    id: 'student-2',
    user_id: 'user-2',
    admission_number: 'ADM-002',
    roll_number: '12',
    first_name: 'Ravi',
    last_name: 'Shah',
    full_name: 'Ravi Shah',
    email: 'ravi@example.edu',
    date_of_birth: '2009-02-01',
    gender: 'MALE',
    admission_date: '2025-06-01',
    status: 'INACTIVE',
    fee_status: 'OVERDUE',
    class_name: 'Class 11',
    division_name: 'A',
    academic_year_name: '2025-2026',
  },
];

describe('StudentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.activeRole = 'PRINCIPAL';
    vi.mocked(api.get).mockImplementation(async (endpoint: string) => {
      if (endpoint.startsWith('/students?') || endpoint === '/students') return roster as never;
      if (endpoint === '/academics/classes') {
        return [{ id: 'class-11', name: 'Class 11', divisions: [{ id: 'division-a', name: 'A' }] }] as never;
      }
      if (endpoint === '/academics/years') return [{ id: 'year-1', name: '2025-2026' }] as never;
      if (endpoint === '/attendance/summary/student/student-1') {
        return {
          overall_percentage: 89,
          total_attended: 89,
          total_conducted: 100,
          subject_breakdown: [{ subject_id: 'physics', subject_name: 'Physics', percentage: 90 }],
        } as never;
      }
      return [] as never;
    });
  });

  it('renders the searchable registry, filters by status, and opens an attendance dossier', async () => {
    render(<MemoryRouter><StudentsPage /></MemoryRouter>);

    expect(await screen.findByRole('heading', { name: 'Student Registry & Academic Dossier' })).toBeInTheDocument();
    expect(await screen.findByText('Asha Patel')).toBeInTheDocument();
    expect(screen.getByText('Ravi Shah')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Fee status for Asha Patel' })).toHaveValue('PENDING');
    expect(screen.getByRole('combobox', { name: 'Fee status for Ravi Shah' })).toHaveValue('OVERDUE');

    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by status' }), { target: { value: 'ACTIVE' } });
    expect(screen.queryByText('Ravi Shah')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'View Asha Patel dossier' }));
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(await screen.findByText('89%')).toBeInTheDocument();
    expect(screen.getByText('Physics')).toBeInTheDocument();
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/attendance/summary/student/student-1'));
  });

  it('updates the cohort query when a class filter is selected', async () => {
    render(<MemoryRouter><StudentsPage /></MemoryRouter>);

    await screen.findByText('Asha Patel');
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by class' }), { target: { value: 'class-11' } });

    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/students?class_id=class-11'));
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by division' }), { target: { value: 'division-a' } });
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/students?class_id=class-11&division_id=division-a'));
  });

  it('updates and persists a student fee status', async () => {
    vi.mocked(api.put).mockResolvedValue({ ...roster[0], fee_status: 'PAID' } as never);
    render(<MemoryRouter><StudentsPage /></MemoryRouter>);

    const feeStatus = await screen.findByRole('combobox', { name: 'Fee status for Asha Patel' });
    fireEvent.change(feeStatus, { target: { value: 'PAID' } });

    await waitFor(() => expect(api.put).toHaveBeenCalledWith('/students/student-1/fee-status', { fee_status: 'PAID' }));
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Fee status for Asha Patel' })).toHaveValue('PAID'));
  });

  it('shows fee status as read-only for faculty', async () => {
    mockAuth.activeRole = 'FACULTY';
    render(<MemoryRouter><StudentsPage /></MemoryRouter>);

    await screen.findByText('Asha Patel');
    expect(screen.queryByRole('combobox', { name: 'Fee status for Asha Patel' })).not.toBeInTheDocument();
    expect(screen.getByText('PENDING')).toBeInTheDocument();
  });
});
