// Example: Using Animated Logo Components in PHILOMATRIX

// ============================================
// 1. LOGIN SPLASH (After successful login)
// ============================================
// File: src/pages/LoginPage.tsx (already implemented)

import { LoginSplash } from '../components/common/LoginSplash';

const [showSplash, setShowSplash] = useState(false);
const [splashData, setSplashData] = useState(null);

const handleLogin = async () => {
  // ... authentication logic ...
  setSplashData({
    fullName: profile.full_name,
    role: profile.roles[0],
    institution: profile.institution_name,
  });
  setShowSplash(true);
};

return (
  <>
    {showSplash && splashData && (
      <LoginSplash 
        userFullName={splashData.fullName}
        userRole={splashData.role}
        institutionName={splashData.institution}
        onComplete={() => setShowSplash(false)}
        duration={3000}
      />
    )}
    {/* Login form ... */}
  </>
);

// ============================================
// 2. PAGE LOADING (App initialization)
// ============================================
// File: src/layouts/AppLayout.tsx (already implemented)

import { AnimatedLogo } from '../components/common/AnimatedLogo';

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

// ============================================
// 3. LOADING OVERLAY (For API calls)
// ============================================
// Example in a page component

import { useState } from 'react';
import { LoadingOverlay, AnimatedLogo } from '../components/common';
import { useApiLoading } from '../hooks/useApiLoading';
import { api } from '../services/api';

function DashboardPage() {
  const { isLoading, withLoading } = useApiLoading();
  const [data, setData] = useState(null);

  const handleFetchData = async () => {
    const result = await withLoading(async () => {
      return await api.get('/api/v1/dashboard/data');
    });
    if (result) {
      setData(result);
    }
  };

  return (
    <div className="relative">
      <LoadingOverlay 
        isVisible={isLoading}
        message="Loading your dashboard..."
        variant="spin"
        fullScreen={true}
      />
      
      <button onClick={handleFetchData}>
        Fetch Data
      </button>

      {data && (
        <div className="mt-8">
          {/* Display data ... */}
        </div>
      )}
    </div>
  );
}

// ============================================
// 4. CUSTOM ANIMATED LOGO USAGE
// ============================================
// Use in any component that needs loading state

import { AnimatedLogo } from '../components/common';

function StudentsPage() {
  return (
    <div className="space-y-6">
      <h1>Students Directory</h1>

      <div className="space-y-4">
        {/* With text below */}
        <AnimatedLogo 
          size="md" 
          variant="spin" 
          showText={true}
        />

        {/* Just the logo */}
        <AnimatedLogo 
          size="sm" 
          variant="pulse"
        />

        {/* Big bounce animation */}
        <AnimatedLogo 
          size="xl" 
          variant="bounce"
        />
      </div>
    </div>
  );
}

// ============================================
// 5. ASYNC DATA WITH LOADING STATE
// ============================================
// Real-world example pattern

import { useEffect, useState } from 'react';
import { LoadingOverlay } from '../components/common';
import { api } from '../services/api';

function AttendancePage() {
  const [attendance, setAttendance] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAttendance = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.get('/api/v1/attendance/records');
        setAttendance(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAttendance();
  }, []);

  if (isLoading) {
    return (
      <LoadingOverlay 
        isVisible={true}
        message="Loading attendance records..."
        variant="spin"
      />
    );
  }

  if (error) {
    return <div className="text-red-600">Error: {error}</div>;
  }

  return (
    <div>
      {/* Attendance content */}
    </div>
  );
}

// ============================================
// 6. FORM SUBMISSION WITH LOADING
// ============================================
// Example: Marks entry submission

import { FormEvent, useState } from 'react';
import { LoadingOverlay } from '../components/common';
import { api } from '../services/api';

function MarkEntryForm() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({ marks: '', notes: '' });

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      await api.post('/api/v1/examinations/marks', formData);
      alert('Marks submitted successfully!');
      setFormData({ marks: '', notes: '' });
    } catch (error) {
      alert('Failed to submit marks: ' + error.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative">
      <LoadingOverlay 
        isVisible={isSubmitting}
        message="Submitting marks..."
        variant="pulse"
        fullScreen={false}
      />

      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="number"
          placeholder="Marks out of 100"
          value={formData.marks}
          onChange={(e) => setFormData({ ...formData, marks: e.target.value })}
          disabled={isSubmitting}
        />
        <textarea
          placeholder="Additional notes"
          value={formData.notes}
          onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
          disabled={isSubmitting}
        />
        <button 
          type="submit" 
          disabled={isSubmitting}
          className="opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? 'Submitting...' : 'Submit Marks'}
        </button>
      </form>
    </div>
  );
}

// ============================================
// 7. ANIMATED LOADING IN TABLE/LIST
// ============================================
// Example: Faculty list with loading state

import { useState, useEffect } from 'react';
import { AnimatedLogo } from '../components/common';

function FacultyDirectory() {
  const [faculty, setFaculty] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate loading
    setTimeout(() => {
      setFaculty([
        { id: 1, name: 'Prof. John Doe', subject: 'Physics' },
        { id: 2, name: 'Prof. Jane Smith', subject: 'Chemistry' },
      ]);
      setIsLoading(false);
    }, 2000);
  }, []);

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <AnimatedLogo size="md" variant="spin" showText={true} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {faculty.map(person => (
        <div key={person.id} className="p-4 border rounded">
          <h3>{person.name}</h3>
          <p>{person.subject}</p>
        </div>
      ))}
    </div>
  );
}

// ============================================
// 8. MULTI-STEP PROCESS WITH ANIMATIONS
// ============================================
// Example: Multi-step report card generation

import { useState } from 'react';
import { LoadingOverlay } from '../components/common';

function ReportCardGenerator() {
  const [step, setStep] = useState('select'); // select -> generating -> complete
  const [isLoading, setIsLoading] = useState(false);

  const handleGenerate = async () => {
    setIsLoading(true);
    setStep('generating');

    try {
      // Step 1: Prepare data
      await new Promise(r => setTimeout(r, 1000));
      
      // Step 2: Generate PDF
      await new Promise(r => setTimeout(r, 2000));
      
      setStep('complete');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {step === 'select' && (
        <>
          <h2>Generate Report Cards</h2>
          <button onClick={handleGenerate}>
            Generate PDFs
          </button>
        </>
      )}

      {step === 'generating' && (
        <LoadingOverlay 
          isVisible={isLoading}
          message="Generating report cards... This may take a minute"
          variant="pulse"
          fullScreen={true}
        />
      )}

      {step === 'complete' && (
        <div className="p-6 bg-green-50 rounded border border-green-200">
          <p className="text-green-800">✓ Report cards generated successfully!</p>
        </div>
      )}
    </div>
  );
}

export {
  DashboardPage,
  AttendancePage,
  MarkEntryForm,
  FacultyDirectory,
  ReportCardGenerator,
};
