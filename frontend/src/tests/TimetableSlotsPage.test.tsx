import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import { TimetableSlotsPage } from '../pages/TimetableSlotsPage';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('TimetableSlotsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockImplementation(async (endpoint: string) => {
      if (endpoint === '/academics/classes') {
        return [{
          id: 'class-11',
          name: 'Class 11',
          divisions: [{ id: 'division-a', name: 'A' }],
        }] as never;
      }
      if (endpoint === '/academics/subjects') return [] as never;
      if (endpoint.startsWith('/timetable/slots?')) {
        return [{
          id: 'monday-period-2',
          class_id: 'class-11',
          day_of_week: 1,
          period_number: 2,
          start_time: '10:00:00',
          end_time: '23:00:00',
        }] as never;
      }
      return [] as never;
    });
    vi.mocked(api.put).mockResolvedValue({
      id: 'monday-period-2',
      end_time: '11:00:00',
    } as never);
  });

  it('lets an administrator correct a slot end time without changing the period or day', async () => {
    render(<TimetableSlotsPage />);

    fireEvent.click(await screen.findByRole('button', { name: 'Edit period 2 on Mon' }));
    fireEvent.change(screen.getByLabelText('Ends'), { target: { value: '11:00' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save period' }));

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith('/timetable/slots/monday-period-2', {
        start_time: '10:00',
        end_time: '11:00',
      });
    });
    expect(await screen.findByText('Period 2 updated.')).toBeInTheDocument();
  });

  it('offers to edit the overlapping period directly from the slot creation error', async () => {
    vi.mocked(api.post).mockRejectedValue(new Error(
      'Time overlaps period 2 (10:00 AM–11:00 PM) on Monday. Adjust that period or choose a non-overlapping time.',
    ));
    render(<TimetableSlotsPage />);

    await screen.findByRole('button', { name: 'Edit period 2 on Mon' });
    fireEvent.change(screen.getByLabelText('Period'), { target: { value: '3' } });
    fireEvent.change(screen.getByLabelText('Starts'), { target: { value: '11:10' } });
    fireEvent.change(screen.getByLabelText('Ends'), { target: { value: '12:10' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add period' }));

    fireEvent.click(await screen.findByRole('button', { name: 'Edit Period 2 on Mon' }));

    expect(screen.getByLabelText('Period')).toHaveValue(2);
    expect(screen.getByLabelText('Starts')).toHaveValue('10:00');
    expect(screen.getByLabelText('Ends')).toHaveValue('23:00');
    expect(screen.getByRole('button', { name: 'Save period' })).toBeInTheDocument();
  });
});
