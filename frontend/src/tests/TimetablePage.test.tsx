import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import { TimetablePage } from '../pages/TimetablePage';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    activeRole: 'PRINCIPAL',
    activeChild: null,
  }),
}));

describe('TimetablePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockImplementation(async (endpoint: string) => {
      if (endpoint === '/academics/classes') {
        return [{
          id: 'class-11',
          name: 'Class 11',
          stream: 'Science',
          display_order: 1,
          divisions: [{ id: 'division-a', name: 'A' }],
        }] as never;
      }
      if (endpoint === '/academics/subjects') {
        return [{
          id: 'physics',
          code: 'PHY101',
          name: 'Physics',
          stream: 'Science',
          has_practical: true,
          max_theory_marks: 100,
          max_practical_marks: 0,
          min_pass_percentage: 35,
        }] as never;
      }
      if (endpoint === '/faculty') return [] as never;
      if (endpoint === '/timetable/slots?division_id=division-a') {
        return [{
          day_of_week: 1,
          period_number: 1,
          start_time: '09:00',
          end_time: '10:00',
          subject_id: 'physics',
        }] as never;
      }
      if (endpoint === '/timetable?division_id=division-a') {
        return [{
          id: 'monday-period-1',
          division_id: 'division-a',
          division_name: 'A',
          class_name: 'Class 11',
          subject_id: 'physics',
          subject_name: 'Physics',
          subject_code: 'PHY101',
          faculty_id: 'faculty-1',
          faculty_name: 'Soham More',
          day_of_week: 1,
          period_number: 1,
          start_time: '09:00',
          end_time: '10:00',
          room_number: 'Lab 1',
          is_practical_batch: false,
        }] as never;
      }
      return [] as never;
    });
  });

  it('shows the cohort timetable and opens scheduling from the first free period', async () => {
    render(<TimetablePage />);

    expect(await screen.findByText('Soham More')).toBeInTheDocument();
    expect(screen.getByText('Weekly Lecture Schedule Matrix (Class 11 · Division A)')).toBeInTheDocument();
    expect(screen.getByText('PHY101')).toBeInTheDocument();
    expect(screen.getByText('Physics')).toBeInTheDocument();
    expect(screen.getByText('Lab 1')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Schedule Class Slot' }));

    expect(await screen.findByRole('heading', { name: 'Monday · Period 2' })).toBeInTheDocument();
  });
});
