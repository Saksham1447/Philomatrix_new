import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import {
  Building2,
  Sliders,
  Calendar,
  Layers,
  Save,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Percent,
  BellRing,
  FileCheck,
  Plus,
  Camera
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { user, activeRole } = useAuth();
  const isPrincipalOrAdmin = activeRole === 'PRINCIPAL' || activeRole === 'SUPER_ADMIN';
  const [activeTab, setActiveTab] = useState<'PERSONAL' | 'PROFILE' | 'POLICIES' | 'ACADEMICS'>(
    isPrincipalOrAdmin ? 'PROFILE' : 'PERSONAL'
  );

  // Personal Workspace Preferences State
  const [dashboardLayout, setDashboardLayout] = useState<'STANDARD' | 'ANALYTICS' | 'COMPACT'>('STANDARD');
  const [attendanceDensity, setAttendanceDensity] = useState<'COMFORTABLE' | 'COMPACT'>('COMFORTABLE');
  const [notifyEmail, setNotifyEmail] = useState(true);
  const [notifyInApp, setNotifyInApp] = useState(true);
  const [themeMode, setThemeMode] = useState<'LIGHT' | 'DARK'>('LIGHT');
  const [profileFirstName, setProfileFirstName] = useState('');
  const [profileMiddleName, setProfileMiddleName] = useState('');
  const [profileLastName, setProfileLastName] = useState('');
  const [profileEmail, setProfileEmail] = useState('');
  const [profilePhone, setProfilePhone] = useState('');
  const [profilePhoto, setProfilePhoto] = useState('');

  // Institution Profile State
  const [instName, setInstName] = useState('');
  const [instCode, setInstCode] = useState('');
  const [instAddress, setInstAddress] = useState('');
  const [instCity, setInstCity] = useState('');
  const [instState, setInstState] = useState('');
  const [instPhone, setInstPhone] = useState('');
  const [instEmail, setInstEmail] = useState('');
  const [instLogo, setInstLogo] = useState('');
  const [institutionType, setInstitutionType] = useState('OTHER');

  // Operational Policy State
  const [minThreshold, setMinThreshold] = useState<number>(75);
  const [allowLate, setAllowLate] = useState(true);
  const [enableSms, setEnableSms] = useState(false);
  const [templateId, setTemplateId] = useState('STANDARD_V1');
  const [academicUnitLabel, setAcademicUnitLabel] = useState('Department / Class');
  const [educatorLabel, setEducatorLabel] = useState('Faculty / Teacher');
  const [learnerLabel, setLearnerLabel] = useState('Student');
  const [headRoleLabel, setHeadRoleLabel] = useState('Head / Principal');

  // Academic Structure State
  const [academicYears, setAcademicYears] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [newYearName, setNewYearName] = useState('');
  const [newYearStart, setNewYearStart] = useState('');
  const [newYearEnd, setNewYearEnd] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const institutionId = user?.institution_id || 'inst-001';

  // Load all settings
  const loadSettings = async () => {
    setIsLoading(true);
    try {
      setProfileFirstName(user?.first_name || '');
      setProfileMiddleName(user?.middle_name || '');
      setProfileLastName(user?.last_name || '');
      setProfileEmail(user?.email || '');
      setProfilePhone(user?.phone_number || '');
      setProfilePhoto(user?.profile_photo_url || '');
      // 0. Personal Preferences
      try {
        const prefData = await api.get<any>('/auth/preferences');
        if (prefData) {
          setDashboardLayout(prefData.dashboard_layout || 'STANDARD');
          setAttendanceDensity(prefData.attendance_table_density || 'COMFORTABLE');
          setNotifyEmail(prefData.notify_email ?? true);
          setNotifyInApp(prefData.notify_in_app ?? true);
          setThemeMode(prefData.theme_mode || 'LIGHT');
        }
      } catch (err) {
        console.warn('Could not load user preferences', err);
      }

      // If user is principal or admin, load institution data
      if (isPrincipalOrAdmin) {
        // 1. Institution details
        const instData = await api.get<any>(`/institutions/${institutionId}`);
        setInstName(instData.name || '');
        setInstCode(instData.code || '');
        setInstAddress(instData.address || '');
        setInstCity(instData.city || '');
        setInstState(instData.state || '');
        setInstPhone(instData.phone || '');
        setInstEmail(instData.email || '');
        setInstLogo(instData.logo_url || '');
        setInstitutionType(instData.institution_type || 'OTHER');

        // 2. Institution operational settings
        const settingsData = await api.get<any>(`/institutions/${institutionId}/settings`);
        setMinThreshold(Number(settingsData.min_attendance_threshold) || 75);
        setAllowLate(Boolean(settingsData.allow_late_as_present));
        setEnableSms(Boolean(settingsData.enable_parent_sms_alerts));
        setTemplateId(settingsData.report_card_template_id || 'STANDARD_V1');
        setAcademicUnitLabel(settingsData.academic_unit_label || 'Department / Class');
        setEducatorLabel(settingsData.educator_label || 'Faculty / Teacher');
        setLearnerLabel(settingsData.learner_label || 'Student');
        setHeadRoleLabel(settingsData.head_role_label || 'Head / Principal');

        // 3. Academic Years & Classes
        const yearsData = await api.get<any[]>('/academics/years');
        setAcademicYears(yearsData);
        const classesData = await api.get<any[]>('/academics/classes');
        setClasses(classesData);
      }
    } catch (err: any) {
      console.error('Failed to load institution settings', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, [institutionId]);

  // Handle Personal Preferences Save
  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMsg(null);
    setErrorMsg(null);
    try {
      await api.put('/auth/preferences', {
        dashboard_layout: dashboardLayout,
        attendance_table_density: attendanceDensity,
        notify_email: notifyEmail,
        notify_in_app: notifyInApp,
        theme_mode: themeMode
      });
      setSuccessMsg('Personal workspace preferences saved and persisted successfully!');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save preferences');
    }
  };

  const handleProfilePhoto = (file?: File) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setErrorMsg('Please select an image file.');
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setErrorMsg('Profile photos must be 2 MB or smaller.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setProfilePhoto(String(reader.result));
    reader.onerror = () => setErrorMsg('The profile photo could not be read.');
    reader.readAsDataURL(file);
  };

  const handleSaveUserProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMsg(null);
    setErrorMsg(null);
    try {
      await api.put('/auth/profile', {
        first_name: profileFirstName,
        middle_name: profileMiddleName || null,
        last_name: profileLastName,
        email: profileEmail,
        phone_number: profilePhone || null,
        profile_photo_url: profilePhoto || null,
      });
      setSuccessMsg('Your profile details and photo were saved successfully.');
      window.dispatchEvent(new Event('profile:updated'));
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update your profile');
    }
  };


  // Handle Profile Save
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMsg(null);
    setErrorMsg(null);
    try {
      await api.put(`/institutions/${institutionId}`, {
        name: instName,
        address: instAddress,
        city: instCity,
        state: instState,
        phone: instPhone,
        email: instEmail,
        logo_url: instLogo,
        institution_type: institutionType,
      });
      setSuccessMsg('Institution identity and contact branding updated successfully!');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update institution profile');
    }
  };

  // Handle Policy Save
  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMsg(null);
    setErrorMsg(null);
    try {
      await api.put(`/institutions/${institutionId}/settings`, {
        min_attendance_threshold: minThreshold,
        allow_late_as_present: allowLate,
        enable_parent_sms_alerts: enableSms,
        report_card_template_id: templateId,
        institution_type: institutionType,
        academic_unit_label: academicUnitLabel,
        educator_label: educatorLabel,
        learner_label: learnerLabel,
        head_role_label: headRoleLabel,
      });
      setSuccessMsg('Academic compliance thresholds and reporting policies saved!');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update operational settings');
    }
  };

  // Handle Add Academic Year
  const handleAddYear = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newYearName || !newYearStart || !newYearEnd) return;
    setSuccessMsg(null);
    setErrorMsg(null);
    try {
      await api.post('/academics/years', {
        name: newYearName,
        start_date: newYearStart,
        end_date: newYearEnd,
        is_current: false,
      });
      setNewYearName('');
      setNewYearStart('');
      setNewYearEnd('');
      setSuccessMsg('New academic session created successfully!');
      loadSettings();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create academic year');
    }
  };

  // Handle Set Current Year
  const handleSetCurrentYear = async (yearId: string) => {
    try {
      await api.put(`/academics/years/${yearId}/set-current`, {});
      setSuccessMsg('Active academic year updated across ERP!');
      loadSettings();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to set active year');
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight font-display flex items-center gap-2">
            <Sliders className="w-7 h-7 text-brand-600" />
            Institution Configuration & Governance
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Enterprise multi-tenant customization: Branding, compliance rules, and academic structures
          </p>
        </div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-semibold border border-emerald-200">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Role Authorized: {activeRole}</span>
        </div>
      </div>

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm font-semibold flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-200 overflow-x-auto">
        <button
          onClick={() => { setActiveTab('PERSONAL'); setSuccessMsg(null); setErrorMsg(null); }}
          className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 cursor-pointer flex items-center gap-2 shrink-0 ${
            activeTab === 'PERSONAL'
              ? 'border-brand-600 text-brand-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <Sliders className="w-4 h-4" />
          Personal Workspace & Preferences
        </button>

        {isPrincipalOrAdmin && (
          <>
            <button
              onClick={() => { setActiveTab('PROFILE'); setSuccessMsg(null); setErrorMsg(null); }}
              className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 cursor-pointer flex items-center gap-2 shrink-0 ${
                activeTab === 'PROFILE'
                  ? 'border-brand-600 text-brand-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Building2 className="w-4 h-4" />
              Institution Branding
            </button>

            <button
              onClick={() => { setActiveTab('POLICIES'); setSuccessMsg(null); setErrorMsg(null); }}
              className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 cursor-pointer flex items-center gap-2 shrink-0 ${
                activeTab === 'POLICIES'
                  ? 'border-brand-600 text-brand-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Percent className="w-4 h-4" />
              Attendance & Report Rules
            </button>

            <button
              onClick={() => { setActiveTab('ACADEMICS'); setSuccessMsg(null); setErrorMsg(null); }}
              className={`pb-3 px-4 text-xs font-bold transition-all border-b-2 cursor-pointer flex items-center gap-2 shrink-0 ${
                activeTab === 'ACADEMICS'
                  ? 'border-brand-600 text-brand-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Calendar className="w-4 h-4" />
              Academic Years & Classes
            </button>
          </>
        )}
      </div>

      {/* TAB 0: PERSONAL WORKSPACE & PREFERENCES */}
      {activeTab === 'PERSONAL' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs space-y-6">
          {/* User Dossier Summary */}
          <div className="p-5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="relative w-14 h-14 rounded-xl bg-indigo-600 text-white font-bold text-xl flex items-center justify-center shrink-0 overflow-hidden">
                {profilePhoto ? <img src={profilePhoto} alt="Profile" className="h-full w-full object-cover" /> : <>{user?.first_name?.[0] || 'U'}{user?.last_name?.[0] || 'P'}</>}
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-base">{user?.full_name}</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Email: {user?.email} • Role: <span className="font-semibold text-indigo-600">{activeRole}</span>
                </p>
                <p className="text-xs text-slate-400 mt-0.5">
                  Institution: {user?.institution_name || 'PHILOMATRIX Junior College'}
                </p>
              </div>
            </div>
            <div className="text-xs text-slate-500 bg-white px-3 py-2 rounded-lg border border-slate-200">
              <span className="font-bold text-slate-800">Workspace Authority:</span> Personal settings are isolated and do not alter global institution policies.
            </div>
          </div>

          <form onSubmit={handleSaveUserProfile} className="space-y-4 rounded-xl border border-slate-200 p-5">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Edit profile</h3>
              <p className="mt-1 text-xs text-slate-500">Update the details shown to other users in your institution.</p>
            </div>
            <div className="flex flex-wrap items-center gap-4">
              <div className="h-16 w-16 overflow-hidden rounded-2xl bg-indigo-600 text-xl font-bold text-white flex items-center justify-center">
                {profilePhoto ? <img src={profilePhoto} alt="Profile preview" className="h-full w-full object-cover" /> : `${profileFirstName[0] || 'U'}${profileLastName[0] || 'P'}`}
              </div>
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-indigo-300 bg-indigo-50 px-4 py-3 text-xs font-bold text-indigo-700">
                <Camera className="h-4 w-4" /> Upload profile photo
                <input type="file" accept="image/*" className="hidden" onChange={(event) => handleProfilePhoto(event.target.files?.[0])} />
              </label>
              {profilePhoto && <button type="button" onClick={() => setProfilePhoto('')} className="text-xs font-semibold text-rose-600">Remove photo</button>}
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {([
                ['First name', profileFirstName, setProfileFirstName],
                ['Middle name', profileMiddleName, setProfileMiddleName],
                ['Last name', profileLastName, setProfileLastName],
                ['Email', profileEmail, setProfileEmail],
                ['Phone number', profilePhone, setProfilePhone],
              ] as [string, string, React.Dispatch<React.SetStateAction<string>>][]).map(([label, value, setter]) => (
                <label key={label} className={label === 'Phone number' ? 'sm:col-span-2' : ''}>
                  <span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>
                  <input required={label !== 'Middle name' && label !== 'Phone number'} type={label === 'Email' ? 'email' : 'text'} value={value} onChange={(event) => setter(event.target.value)} className="premium-input w-full" />
                </label>
              ))}
            </div>
            <div className="flex justify-end">
              <button type="submit" className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-bold text-white"><Save className="h-4 w-4" /> Save profile</button>
            </div>
          </form>

          <form onSubmit={handleSavePreferences} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Dashboard Layout Preference */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Personal Dashboard Layout
                </label>
                <div className="space-y-2">
                  {[
                    { id: 'STANDARD', title: 'Standard Operational', desc: 'Balanced card overview with quick actions & schedule' },
                    { id: 'ANALYTICS', title: 'Performance Analytics', desc: 'Emphasizes attendance trends & evaluation queues' },
                    { id: 'COMPACT', title: 'Compact Minimalist', desc: 'High-density tabular list for fast monitoring' }
                  ].map(opt => (
                    <label
                      key={opt.id}
                      className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                        dashboardLayout === opt.id
                          ? 'border-indigo-600 bg-indigo-50/50 ring-1 ring-indigo-500'
                          : 'border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <input
                        type="radio"
                        name="dash_layout"
                        value={opt.id}
                        checked={dashboardLayout === opt.id}
                        onChange={() => setDashboardLayout(opt.id as any)}
                        className="mt-0.5 text-indigo-600 focus:ring-indigo-500"
                      />
                      <div>
                        <div className="text-xs font-bold text-slate-800">{opt.title}</div>
                        <div className="text-[11px] text-slate-500">{opt.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Attendance Register Density */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Attendance Register Density
                </label>
                <div className="space-y-2">
                  {[
                    { id: 'COMFORTABLE', title: 'Comfortable View', desc: 'Standard row height with generous padding (Reference UI)' },
                    { id: 'COMPACT', title: 'Compact High-Density', desc: 'Reduced row heights for rapidly viewing large rosters' }
                  ].map(opt => (
                    <label
                      key={opt.id}
                      className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                        attendanceDensity === opt.id
                          ? 'border-indigo-600 bg-indigo-50/50 ring-1 ring-indigo-500'
                          : 'border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <input
                        type="radio"
                        name="att_density"
                        value={opt.id}
                        checked={attendanceDensity === opt.id}
                        onChange={() => setAttendanceDensity(opt.id as any)}
                        className="mt-0.5 text-indigo-600 focus:ring-indigo-500"
                      />
                      <div>
                        <div className="text-xs font-bold text-slate-800">{opt.title}</div>
                        <div className="text-[11px] text-slate-500">{opt.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            {/* Notification & Communication Toggles */}
            <div className="pt-4 border-t border-slate-200">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
                Notification Preferences
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <label className="flex items-center gap-3 p-3 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifyInApp}
                    onChange={e => setNotifyInApp(e.target.checked)}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-slate-300 rounded"
                  />
                  <div>
                    <div className="text-xs font-bold text-slate-800">In-App Alerts</div>
                    <div className="text-[11px] text-slate-500">Receive real-time alerts for roster changes and timetable updates</div>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifyEmail}
                    onChange={e => setNotifyEmail(e.target.checked)}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-slate-300 rounded"
                  />
                  <div>
                    <div className="text-xs font-bold text-slate-800">Email Digest Notifications</div>
                    <div className="text-[11px] text-slate-500">Receive daily summary digests and administrative announcements</div>
                  </div>
                </label>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-200 flex justify-end">
              <button
                type="submit"
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-sm transition-all"
              >
                <Save className="w-4 h-4" />
                Save Personal Preferences
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 1: INSTITUTION PROFILE */}
      {activeTab === 'PROFILE' && isPrincipalOrAdmin && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs">
          <form onSubmit={handleSaveProfile} className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Institution Name
                </label>
                <input
                  type="text"
                  value={instName}
                  onChange={e => setInstName(e.target.value)}
                  required
                  className="w-full text-xs p-3 border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Affiliation Code
                </label>
                <input
                  type="text"
                  value={instCode}
                  disabled
                  className="w-full text-xs p-3 border border-slate-200 rounded-xl bg-slate-50 text-slate-500 cursor-not-allowed"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Institution Type
                </label>
                <select value={institutionType} onChange={e => setInstitutionType(e.target.value)} className="w-full text-xs p-3 border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-1 focus:ring-brand-500">
                  <option value="SCHOOL">School</option>
                  <option value="JUNIOR_COLLEGE">Junior College</option>
                  <option value="DEGREE_COLLEGE">Degree College</option>
                  <option value="ENGINEERING_COLLEGE">Engineering College</option>
                  <option value="OTHER">Other / Multi-purpose</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-700">Flexible terminology</h3>
                  <p className="mt-1 text-[11px] text-slate-500">Use labels that fit your institution without changing the underlying system.</p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <label className="text-xs font-semibold text-slate-600">Academic unit label<input value={academicUnitLabel} onChange={e => setAcademicUnitLabel(e.target.value)} placeholder="Department / Class" className="mt-1 w-full text-xs p-3 border border-slate-200 rounded-xl bg-white" /></label>
                    <label className="text-xs font-semibold text-slate-600">Educator label<input value={educatorLabel} onChange={e => setEducatorLabel(e.target.value)} placeholder="Faculty / Teacher" className="mt-1 w-full text-xs p-3 border border-slate-200 rounded-xl bg-white" /></label>
                    <label className="text-xs font-semibold text-slate-600">Learner label<input value={learnerLabel} onChange={e => setLearnerLabel(e.target.value)} placeholder="Student / Pupil" className="mt-1 w-full text-xs p-3 border border-slate-200 rounded-xl bg-white" /></label>
                    <label className="text-xs font-semibold text-slate-600">Head role label<input value={headRoleLabel} onChange={e => setHeadRoleLabel(e.target.value)} placeholder="Head / Principal" className="mt-1 w-full text-xs p-3 border border-slate-200 rounded-xl bg-white" /></label>
                  </div>
                </div>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Campus Address
                </label>
                <textarea
                  rows={2}
                  value={instAddress}
                  onChange={e => setInstAddress(e.target.value)}
                  className="w-full text-xs p-3 border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  City
                </label>
                <input
                  type="text"
                  value={instCity}
                  onChange={e => setInstCity(e.target.value)}
                  className="w-full text-xs p-3 border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  State
                </label>
                <input
                  type="text"
                  value={instState}
                  onChange={e => setInstState(e.target.value)}
                  className="w-full text-xs p-3 border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Official Contact Phone
                </label>
                <input
                  type="text"
                  value={instPhone}
                  onChange={e => setInstPhone(e.target.value)}
                  className="w-full text-xs p-3 border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Official Email
                </label>
                <input
                  type="email"
                  value={instEmail}
                  onChange={e => setInstEmail(e.target.value)}
                  className="w-full text-xs p-3 border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Header Logo URL (Appears on Official PDFs)
                </label>
                <input
                  type="text"
                  value={instLogo}
                  onChange={e => setInstLogo(e.target.value)}
                  placeholder="https://example.com/logo.png"
                  className="w-full text-xs p-3 border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-100">
              <button
                type="submit"
                className="px-6 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-md shadow-brand-500/20 transition-all flex items-center gap-2 cursor-pointer"
              >
                <Save className="w-4 h-4" />
                <span>Save Institution Branding</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 2: OPERATIONAL POLICIES */}
      {activeTab === 'POLICIES' && isPrincipalOrAdmin && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs">
          <form onSubmit={handleSavePolicy} className="space-y-6">
            <div className="space-y-6">
              {/* Attendance Threshold */}
              <div className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h4 className="text-sm font-bold text-slate-900">
                    Statutory Attendance Threshold (%)
                  </h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Students below this percentage trigger executive at-risk warnings on Principal dashboards
                  </p>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    min="50"
                    max="100"
                    value={minThreshold}
                    onChange={e => setMinThreshold(Number(e.target.value))}
                    className="w-20 text-xs p-2 text-center border font-bold rounded-lg bg-white"
                  />
                  <span className="text-xs font-bold text-slate-600">%</span>
                </div>
              </div>

              {/* Late Attendance Policy */}
              <div className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-slate-900">
                    Treat "LATE" as Present in Attendance Calculations
                  </h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    When enabled, students marked LATE are credited as attended in the denominator
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={allowLate}
                    onChange={e => setAllowLate(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-600" />
                </label>
              </div>

              {/* Parent Alerts */}
              <div className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-slate-900">
                    Parent Automated Absence Notifications
                  </h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Dispatch notifications immediately when a student is recorded absent in any lecture
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={enableSms}
                    onChange={e => setEnableSms(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-600" />
                </label>
              </div>

              {/* Report Card Template */}
              <div className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 space-y-2">
                <h4 className="text-sm font-bold text-slate-900">
                  Official Report Card Layout Template
                </h4>
                <select
                  value={templateId}
                  onChange={e => setTemplateId(e.target.value)}
                  className="w-full text-xs p-2.5 border rounded-lg bg-white"
                >
                  <option value="STANDARD_V1">Standard Indian Junior College (Theory + Practical + Attendance Rollup)</option>
                  <option value="PREMIER_JC_V2">Premier Science JC Executive (With Class Rank & Distinction Badges)</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-100">
              <button
                type="submit"
                className="px-6 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-md shadow-brand-500/20 transition-all flex items-center gap-2 cursor-pointer"
              >
                <Save className="w-4 h-4" />
                <span>Save Operational Rules</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 3: ACADEMIC YEARS & CLASSES */}
      {activeTab === 'ACADEMICS' && isPrincipalOrAdmin && (
        <div className="space-y-6">
          {/* Academic Years List */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
            <h3 className="text-base font-bold text-slate-900 font-display flex items-center gap-2">
              <Calendar className="w-5 h-5 text-brand-600" />
              Configured Academic Sessions
            </h3>

            <div className="divide-y divide-slate-100">
              {academicYears.map(y => (
                <div key={y.id} className="py-3 flex items-center justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-bold text-slate-900">{y.name}</span>
                      {y.is_current ? (
                        <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                          Active Current Session
                        </span>
                      ) : (
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                          Archived
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Session duration: {y.start_date} to {y.end_date}
                    </p>
                  </div>

                  {!y.is_current && (
                    <button
                      type="button"
                      onClick={() => handleSetCurrentYear(y.id)}
                      className="px-3 py-1.5 text-xs font-bold text-brand-600 hover:bg-brand-50 rounded-lg border border-brand-200 transition-colors cursor-pointer"
                    >
                      Set as Active
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Form to add academic session */}
            <form onSubmit={handleAddYear} className="pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-4 gap-3">
              <div>
                <input
                  type="text"
                  placeholder="e.g. 2027-2028"
                  value={newYearName}
                  onChange={e => setNewYearName(e.target.value)}
                  required
                  className="w-full text-xs p-2.5 border rounded-lg bg-white"
                />
              </div>
              <div>
                <input
                  type="date"
                  value={newYearStart}
                  onChange={e => setNewYearStart(e.target.value)}
                  required
                  className="w-full text-xs p-2.5 border rounded-lg bg-white"
                />
              </div>
              <div>
                <input
                  type="date"
                  value={newYearEnd}
                  onChange={e => setNewYearEnd(e.target.value)}
                  required
                  className="w-full text-xs p-2.5 border rounded-lg bg-white"
                />
              </div>
              <div>
                <button
                  type="submit"
                  className="w-full py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-lg transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Session</span>
                </button>
              </div>
            </form>
          </div>

          {/* Configured Classes & Divisions */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
            <h3 className="text-base font-bold text-slate-900 font-display flex items-center gap-2">
              <Layers className="w-5 h-5 text-brand-600" />
              Classes & Active Divisions
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {classes.map(c => (
                <div key={c.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/40 space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-bold text-slate-900">{c.name}</h4>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-brand-50 text-brand-700">
                      {c.stream}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {c.divisions?.map((d: any) => (
                      <span key={d.id} className="text-xs px-2.5 py-1 rounded-md bg-white border border-slate-200 text-slate-700 font-semibold">
                        Division {d.name} {d.room_number ? `(${d.room_number})` : ''}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
