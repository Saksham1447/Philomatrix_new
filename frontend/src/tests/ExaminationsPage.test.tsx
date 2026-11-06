import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import { ExaminationsPage } from '../pages/ExaminationsPage';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ activeRole: 'OFFICE_STAFF', user: null, activeChild: null }),
}));

const classes = [{
  id: 'class-11',
  name: 'Class 11',
  divisions: [{ id: 'division-a', class_id: 'class-11', name: 'A' }],
}];
const assignments = [{
  id: 'assignment-physics-a',
  academic_year_id: 'year-1',
  class_id: 'class-11',
  faculty_id: 'teacher-physics',
  faculty_name: 'Physics Teacher',
  subject_id: 'physics',
  subject_name: 'Physics',
  subject_code: 'PHY-101',
  division_id: 'division-a',
}];

describe('ExaminationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockImplementation(async (endpoint: string) => {
      if (endpoint === '/academics/classes') return classes as never;
      if (endpoint === '/academics/years') return [{ id: 'year-1', name: '2025-2026', is_current: true }] as never;
      if (endpoint === '/faculty/assignments') return assignments as never;
      if (endpoint.startsWith('/academics/classes/class-11/subjects')) return [{ id: 'physics' }] as never;
      return [] as never;
    });
  });

  it('creates a division-specific exam with the teacher assigned to each selected subject', async () => {
    render(<MemoryRouter><ExaminationsPage /></MemoryRouter>);

    fireEvent.click(await screen.findByRole('button', { name: 'Schedule examination' }));
    fireEvent.change(screen.getByLabelText('Examination name'), { target: { value: 'Unit Test 2' } });
    fireEvent.click(screen.getByRole('checkbox', { name: /Physics \(PHY-101\)/ }));
    fireEvent.change(screen.getByLabelText('Physics exam date'), { target: { value: '2026-10-11' } });
    fireEvent.change(screen.getByLabelText('Physics start time'), { target: { value: '10:15' } });
    fireEvent.change(screen.getByLabelText('Physics end time'), { target: { value: '11:45' } });
    fireEvent.change(screen.getByLabelText('Physics theory maximum marks'), { target: { value: '30' } });
    fireEvent.change(screen.getByLabelText('Physics practical maximum marks'), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create examination schedule' }));

    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/examinations', expect.objectContaining({
      academic_year_id: 'year-1',
      name: 'Unit Test 2',
      subjects: [expect.objectContaining({
        subject_id: 'physics',
        class_id: 'class-11',
        division_id: 'division-a',
        faculty_id: 'teacher-physics',
        exam_date: '2026-10-11',
        start_time: '10:15',
        end_time: '11:45',
        max_theory_marks: 30,
        max_practical_marks: 0,
      })],
    })));
  });

  it('edits an existing subject date and time', async () => {
    const exam = {
      id: 'exam-1',
      academic_year_id: 'year-1',
      name: 'Unit Test 1',
      exam_type: 'UNIT_TEST',
      start_date: '2026-10-10',
      end_date: '2026-10-12',
      status: 'SCHEDULED',
      is_published: false,
      subjects: [{
        id: 'exam-subject-1',
        subject_id: 'physics',
        subject_name: 'Physics',
        subject_code: 'PHY-101',
        class_id: 'class-11',
        class_name: 'Class 11',
        division_id: 'division-a',
        division_name: 'A',
        faculty_id: 'teacher-physics',
        faculty_name: 'Physics Teacher',
        marks_status: 'NOT_STARTED',
        max_theory_marks: 70,
        max_practical_marks: 30,
        min_passing_marks: 35,
        exam_date: '2026-10-10',
        start_time: '09:00:00',
        end_time: '10:00:00',
      }],
    };
    vi.mocked(api.get).mockImplementation(async (endpoint: string) => {
      if (endpoint === '/examinations') return [exam] as never;
      if (endpoint === '/academics/classes') return classes as never;
      if (endpoint === '/academics/years') return [{ id: 'year-1', name: '2025-2026', is_current: true }] as never;
      if (endpoint === '/faculty/assignments') return assignments as never;
      return [] as never;
    });

    render(<MemoryRouter><ExaminationsPage /></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button', { name: 'Edit' }));
    fireEvent.change(screen.getByLabelText('Physics exam date'), { target: { value: '2026-10-11' } });
    fireEvent.change(screen.getByLabelText('Physics start time'), { target: { value: '13:00' } });
    fireEvent.change(screen.getByLabelText('Physics end time'), { target: { value: '14:30' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save examination changes' }));

    await waitFor(() => expect(api.put).toHaveBeenCalledWith('/examinations/exam-1', expect.objectContaining({
      subjects: [expect.objectContaining({
        subject_id: 'physics',
        exam_date: '2026-10-11',
        start_time: '13:00',
        end_time: '14:30',
      })],
    })));
  });
});
