import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import { TimetablePage } from '../pages/TimetablePage';

const mockAuth = vi.hoisted(() => ({
  user: null as { faculty_id?: string } | null,
  activeRole: 'PRINCIPAL' as string,
  activeChild: null,
}));

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockAuth,
}));

describe('TimetablePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.user = null;
    mockAuth.activeRole = 'PRINCIPAL';
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

  it('lets faculty take an assigned open slot and refreshes their timetable', async () => {
    mockAuth.user = { faculty_id: 'faculty-1' };
    mockAuth.activeRole = 'FACULTY';
    vi.mocked(api.get).mockImplementation(async (endpoint: string) => {
      if (endpoint === '/timetable?faculty_id=faculty-1') {
        return [{
          id: 'faculty-entry-1',
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
          room_number: null,
          is_practical_batch: false,
        }] as never;
      }
      if (endpoint === '/faculty/assignments') {
        return [{
          subject_id: 'physics',
          subject_name: 'Physics',
          subject_code: 'PHY101',
          division_id: 'division-a',
          division_name: 'A',
          class_name: 'Class 11',
        }] as never;
      }
      if (endpoint === '/timetable/available-slots?division_id=division-a') {
        return [{
          slot_id: 'slot-1',
          day_of_week: 2,
          period_number: 2,
          start_time: '10:00',
          end_time: '11:00',
          status: 'OPEN',
          allowed_subjects: [{ subject_id: 'physics', subject_name: 'Physics', subject_code: 'PHY101' }],
        }] as never;
      }
      return [] as never;
    });
    vi.mocked(api.post).mockResolvedValue({} as never);

    render(<TimetablePage />);

    expect(await screen.findByText('Tuesday · Period 2')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Take' }));

    expect(api.post).toHaveBeenCalledWith('/timetable/entries', {
      division_id: 'division-a',
      subject_id: 'physics',
      faculty_id: 'faculty-1',
      day_of_week: 2,
      period_number: 2,
      start_time: '10:00',
      end_time: '11:00',
    });
    expect(await screen.findByText('Tuesday period 2 added to your timetable.')).toBeInTheDocument();
  });
});
