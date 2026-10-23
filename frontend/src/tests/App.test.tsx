import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { LoginPage } from '../pages/LoginPage';

describe('LoginPage Component', () => {
  it('renders PHILOMATRIX branding and Junior College subtitle', () => {
    render(
      <AuthProvider>
        <BrowserRouter>
          <LoginPage />
        </BrowserRouter>
      </AuthProvider>
    );

    expect(screen.getByText(/PHILOMATRIX SOFTWARE/i)).toBeInTheDocument();
    expect(screen.getByText(/Integrated Junior College ERP Platform/i)).toBeInTheDocument();
  });

  it('renders all 6 role quick-fill demo buttons', () => {
    render(
      <AuthProvider>
        <BrowserRouter>
          <LoginPage />
        </BrowserRouter>
      </AuthProvider>
    );

    expect(screen.getByText('Principal')).toBeInTheDocument();
    expect(screen.getByText('Physics Lecturer')).toBeInTheDocument();
    expect(screen.getByText('Student (Arjun)')).toBeInTheDocument();
    expect(screen.getByText('Parent (Mr. Sharma)')).toBeInTheDocument();
    expect(screen.getByText('Office Staff')).toBeInTheDocument();
    expect(screen.getByText('SaaS Super Admin')).toBeInTheDocument();
  });
});
