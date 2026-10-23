import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Building2, CheckCircle2, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { AuthTokens, Institution, UserProfile } from '../types';
import { LoginSplash } from '../components/common/LoginSplash';

const campusImages = [
  'https://images.unsplash.com/photo-1562774053-701939374585?auto=format&fit=crop&w=1000&q=85',
  'https://images.unsplash.com/photo-1541339907198-e08756dedf3f?auto=format&fit=crop&w=1000&q=85',
  'https://images.unsplash.com/photo-1498243691581-b145c3f54a5a?auto=format&fit=crop&w=1000&q=85',
];

const formatInstitutionName = (name: string) => {
  if (!name || name !== name.toUpperCase()) return name;
  return name
    .toLowerCase()
    .replace(/\bjr\.?\s*college\b/g, 'Junior College')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
};

export const LoginPage: React.FC = () => {
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [selectedInstitution, setSelectedInstitution] = useState<Institution | null>(null);
  const [isPlatformAdmin, setIsPlatformAdmin] = useState(false);
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingInstitutions, setIsLoadingInstitutions] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSplash, setShowSplash] = useState(false);
  const [splashData, setSplashData] = useState<{ fullName: string; role: string; institution?: string } | null>(null);
  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    api.get<Institution[]>('/institutions/public')
      .then(setInstitutions)
      .catch(() => setError('Institutes could not be loaded. Please try again.'))
      .finally(() => setIsLoadingInstitutions(false));
  }, []);

  const selectedIndex = useMemo(
    () => Math.max(0, institutions.findIndex((institution) => institution.id === selectedInstitution?.id)),
    [institutions, selectedInstitution],
  );

  const chooseInstitution = (institution: Institution | null) => {
    setSelectedInstitution(institution);
    setIsPlatformAdmin(false);
    setError(null);
    if (institution) {
      localStorage.setItem('philomatrix_institution_id', institution.id);
    } else {
      localStorage.removeItem('philomatrix_institution_id');
    }
  };

  const choosePlatformAdmin = () => {
    setSelectedInstitution(null);
    setIsPlatformAdmin(true);
    setError(null);
    localStorage.removeItem('philomatrix_institution_id');
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const tokenRes = await api.post<AuthTokens>('/auth/login', {
        username_or_email: usernameOrEmail,
        password,
        ...(selectedInstitution
          ? { institution_id: selectedInstitution.id }
          : { institution_id: undefined }),
      });
      localStorage.setItem('philomatrix_access_token', tokenRes.access_token);
      const profile = await api.get<UserProfile>('/auth/me');
      setSplashData({
        fullName: profile.full_name,
        role: profile.roles?.[0] || 'USER',
        institution: profile.institution_name || selectedInstitution?.name,
      });
      setShowSplash(true);
      if (rememberMe) {
        localStorage.setItem('philomatrix_remember_login', 'true');
      }
      window.setTimeout(() => {
        login(tokenRes.access_token, profile);
        navigate('/dashboard');
      }, 1800);
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!selectedInstitution && !isPlatformAdmin) {
    return (
      <div className="min-h-screen bg-[#f4f0e6] text-slate-900">
        <div className="flex min-h-screen flex-col">
          <header className="sticky top-0 z-20 flex items-center justify-between border-b border-slate-900/10 bg-[#f8f5ed]/90 px-5 py-4 shadow-[0_12px_30px_-24px_rgba(15,23,42,.55)] backdrop-blur-xl sm:px-10 lg:px-[8vw]">
            <div className="flex items-center gap-3">
              <img src="/assets/logos/philomatrix-logo.png" alt="PHILOMATRIX" className="h-11 w-11 object-contain" />
              <div>
                <p className="font-display text-lg font-bold tracking-tight">PHILOMATRIX</p>
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Education workspace</p>
              </div>
            </div>
            <div className="hidden items-center gap-2 text-xs font-semibold text-slate-500 sm:flex">
              <ShieldCheck className="h-4 w-4 text-emerald-600" /> Secure institutional access
            </div>
          </header>

          <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col justify-center px-5 py-12 sm:px-10 lg:px-16">
            <div className="mb-10 max-w-3xl">
              <p className="mb-3 text-xs font-bold uppercase tracking-[0.24em] text-indigo-600">Welcome to your campus</p>
              <h1 className="font-display text-4xl font-semibold tracking-[-0.045em] text-slate-950 sm:text-6xl">
                Choose your institute
              </h1>
              <p className="mt-4 max-w-xl text-sm leading-6 text-slate-600 sm:text-base">
                Select the institute workspace you belong to. Your academic data and login remain completely isolated within that institute.
              </p>
            </div>

            {error && <div className="mb-6 max-w-2xl rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
            {isLoadingInstitutions ? (
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {[1, 2, 3].map((item) => <div key={item} className="h-64 animate-pulse rounded-3xl bg-white/70" />)}
              </div>
            ) : (
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {institutions.map((institution, index) => (
                  <button
                    key={institution.id}
                    type="button"
                    onClick={() => chooseInstitution(institution)}
                    className="group relative min-h-64 overflow-hidden rounded-[1.5rem] bg-slate-900 text-left shadow-[0_25px_70px_-34px_rgba(15,23,42,.75)] ring-1 ring-white/30 transition duration-300 hover:-translate-y-1.5 hover:shadow-[0_35px_80px_-32px_rgba(15,23,42,.7)]"
                  >
                    <img src={institution.logo_url || campusImages[index % campusImages.length]} alt="" className="absolute inset-0 h-full w-full object-cover opacity-75 transition duration-500 group-hover:scale-105 group-hover:opacity-90" />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent" />
                    <div className="relative flex h-full min-h-64 flex-col justify-between p-5 text-white">
                      <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/25 bg-white/15 backdrop-blur"><Building2 className="h-5 w-5" /></span>
                      <span>
                        <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.2em] text-white/65">{institution.code}</span>
                        <span className="block font-display text-xl font-semibold leading-tight">{formatInstitutionName(institution.name)}</span>
                        <span className="mt-2 block text-xs text-white/70">{[institution.city, institution.state].filter(Boolean).join(', ') || 'Institution workspace'}</span>
                      </span>
                    </div>
                  </button>
                ))}
                <button
                  type="button"
                  onClick={choosePlatformAdmin}
                  className="group min-h-64 rounded-[1.5rem] border border-slate-300/80 bg-white/35 p-6 text-left shadow-[0_18px_45px_-38px_rgba(15,23,42,.65)] backdrop-blur-sm transition hover:-translate-y-1 hover:border-indigo-400 hover:bg-white/80 hover:shadow-[0_25px_55px_-34px_rgba(79,70,229,.35)]"
                >
                  <ShieldCheck className="mb-10 h-8 w-8 text-indigo-600" />
                  <p className="font-display text-xl font-semibold">Platform administration</p>
                  <p className="mt-2 text-sm text-slate-500">For the PHILOMATRIX super administrator.</p>
                </button>
              </div>
            )}
          </main>
          <footer className="flex w-full flex-col gap-2 border-t border-slate-900/10 bg-[#f8f5ed]/75 px-5 py-4 text-xs text-slate-500 backdrop-blur-xl sm:flex-row sm:items-center sm:justify-between sm:px-10 lg:px-[8vw]">
            <span>© 2026 PHILOMATRIX SOFTWARE</span><span>Private · Secure · Connected</span>
          </footer>
        </div>
      </div>
    );
  }

  return (
    <>
      {showSplash && splashData && <LoginSplash userFullName={splashData.fullName} userRole={splashData.role} institutionName={splashData.institution} onComplete={() => setShowSplash(false)} duration={1800} />}
      <div className="min-h-screen bg-[#f4f0e6] p-3 text-slate-900 sm:p-6 lg:p-10">
        <div className="relative mx-auto flex min-h-[calc(100vh-1.5rem)] max-w-[1500px] overflow-hidden rounded-[2rem] bg-slate-950 shadow-[0_30px_100px_-40px_rgba(15,23,42,.75)] sm:min-h-[calc(100vh-3rem)]">
          <div className="absolute inset-0 hidden bg-cover bg-center lg:block" style={{ backgroundImage: `url(${campusImages[selectedIndex % campusImages.length]})` }} />
          <div className="absolute inset-0 hidden bg-gradient-to-r from-slate-950/80 via-slate-950/35 to-slate-950/70 lg:block" />
          <div className="relative hidden w-1/2 flex-col justify-between p-10 text-white lg:flex xl:p-16">
            <div className="flex items-center gap-3">
              <img src="/assets/logos/philomatrix-logo.png" alt="" className="h-12 w-12 object-contain brightness-0 invert" />
              <div><p className="font-display text-lg font-bold">PHILOMATRIX</p><p className="text-[10px] uppercase tracking-[0.2em] text-white/60">Institutional ERP</p></div>
            </div>
            <div className="max-w-md">
              <p className="mb-4 text-xs font-bold uppercase tracking-[0.22em] text-white/65">
                {isPlatformAdmin ? 'Platform workspace' : 'Selected workspace'}
              </p>
              <h1 className="font-display text-5xl font-semibold leading-tight">
                {isPlatformAdmin ? 'PHILOMATRIX Administration' : selectedInstitution?.name}
              </h1>
              <p className="mt-5 text-sm leading-6 text-white/75">One secure space for academic operations, faculty collaboration, student success, and parent engagement.</p>
            </div>
            <p className="text-xs text-white/55">
              {isPlatformAdmin ? 'Platform control plane' : `${selectedInstitution?.city || 'India'} · Protected institutional access`}
            </p>
          </div>

          <div className="relative flex w-full items-center justify-center bg-white/95 px-5 py-10 sm:px-10 lg:w-1/2 lg:bg-slate-950/85 lg:px-16 lg:backdrop-blur-xl xl:px-24">
            <div className="w-full max-w-md">
              <button type="button" onClick={() => chooseInstitution(null)} className="mb-10 inline-flex items-center gap-2 text-xs font-semibold text-slate-500 transition hover:text-indigo-600 lg:text-white/65 lg:hover:text-white">
                <ArrowLeft className="h-4 w-4" /> Change institute
              </button>
              <div className="mb-9">
                <div className="mb-5 flex items-center gap-3 lg:hidden"><img src="/assets/logos/philomatrix-logo.png" alt="" className="h-10 w-10 object-contain" /><span className="font-display text-lg font-bold">PHILOMATRIX</span></div>
                <p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-indigo-600 lg:text-indigo-300">Secure sign in</p>
                <h2 className="font-display text-4xl font-semibold tracking-tight lg:text-white">Welcome back.</h2>
                <p className="mt-3 text-sm text-slate-500 lg:text-white/60">
                  Sign in to <span className="font-semibold text-slate-700 lg:text-white">
                    {isPlatformAdmin ? 'the PHILOMATRIX platform administration console' : formatInstitutionName(selectedInstitution?.name || '')}
                  </span>.
                </p>
              </div>
              {error && <div className="mb-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
              <form onSubmit={handleSubmit} className="space-y-5">
                <label className="block"><span className="mb-2 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500 lg:text-white/70">Username or official email</span><span className="relative block"><Mail className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><input required value={usernameOrEmail} onChange={(event) => setUsernameOrEmail(event.target.value)} placeholder="Enter your username or email" className="w-full rounded-xl border border-slate-200 bg-white px-11 py-3.5 text-sm outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/15 lg:border-white/15 lg:bg-white/10 lg:text-white lg:placeholder:text-white/35" /></span></label>
                <label className="block"><span className="mb-2 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500 lg:text-white/70">Password</span><span className="relative block"><LockKeyhole className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><input required type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter your password" className="w-full rounded-xl border border-slate-200 bg-white px-11 py-3.5 pr-12 text-sm outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/15 lg:border-white/15 lg:bg-white/10 lg:text-white lg:placeholder:text-white/35" /><button type="button" onClick={() => setShowPassword((value) => !value)} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-indigo-500" aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></span></label>
                <div className="flex items-center justify-between text-xs"><label className="flex items-center gap-2 text-slate-500 lg:text-white/60"><input type="checkbox" checked={rememberMe} onChange={(event) => setRememberMe(event.target.checked)} className="h-4 w-4 rounded border-slate-300 text-indigo-600" /> Remember me</label><button type="button" className="font-semibold text-indigo-600 lg:text-indigo-300">Forgot password?</button></div>
                <button disabled={isSubmitting} className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 py-3.5 text-sm font-bold text-white shadow-lg shadow-indigo-600/25 transition hover:bg-indigo-500 disabled:opacity-60">{isSubmitting ? 'Signing in securely...' : 'Sign in securely'} <ArrowRight className="h-4 w-4" /></button>
              </form>
              <div className="mt-8 flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400 lg:text-white/35"><span className="h-px flex-1 bg-slate-200 lg:bg-white/15" /> Protected workspace <span className="h-px flex-1 bg-slate-200 lg:bg-white/15" /></div>
              <div className="mt-5 flex items-center justify-center gap-2 text-xs text-slate-400 lg:text-white/45"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> Your institute data stays private and isolated</div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
