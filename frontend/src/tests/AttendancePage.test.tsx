import React from 'react';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import { AttendancePage } from '../pages/AttendancePage';
import { formatLocalDate, toIndiaDateInputValue } from '../utils/time';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: {
      first_name: 'Test',
      last_name: 'Teacher',
      full_name: 'Test Teacher',
      username: 'teacher',
      institution_name: 'Test College',
    },
    activeRole: 'FACULTY',
    activeChild: null,
  }),
}));

describe('AttendancePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const today = toIndiaDateInputValue();
    const weekday = new Date(`${today}T00:00:00`).getDay() || 7;
    const otherWeekday = weekday === 1 ? 2 : 1;
    vi.mocked(api.get).mockImplementation(async (endpoint: string) => {
      if (endpoint.startsWith('/attendance/today-slots?')) {
        return [
          {
            timetable_entry_id: 'today-slot',
            day_of_week: weekday,
            day_name: formatLocalDate(today).split(',')[0],
            period_number: 1,
            start_time: '09:00',
            end_time: '10:00',
            class_name: 'Class 11',
            division_name: 'A',
            subject_id: 'physics',
            subject_name: 'Current-day class',
            subject_code: 'TODAY',
          },
          {
            timetable_entry_id: 'other-day-slot',
            day_of_week: otherWeekday,
            day_name: 'Other day',
            period_number: 2,
            start_time: '10:00',
            end_time: '11:00',
            class_name: 'Class 11',
            division_name: 'A',
            subject_id: 'chemistry',
            subject_name: 'Other-day class',
            subject_code: 'OTHER',
          },
        ] as never;
      }
      return [] as never;
    });
  });

  it('calculates today in India time instead of UTC', () => {
    expect(toIndiaDateInputValue(new Date('2026-11-05T19:00:00Z'))).toBe('2026-11-06');
  });

  it('defaults to the current India date and offers only slots for that weekday', async () => {
    render(<AttendancePage />);

    const today = toIndiaDateInputValue();
    expect(await screen.findByDisplayValue(today)).toBeInTheDocument();
    expect(screen.getByText(formatLocalDate(today))).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Current-day class/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Other-day class/ })).not.toBeInTheDocument();
  });
});
