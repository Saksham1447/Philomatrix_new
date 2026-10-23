import React, { useEffect } from 'react';
import { AnimatedLogo } from './AnimatedLogo';

interface LoginSplashProps {
  userFullName: string;
  userRole: string;
  institutionName?: string;
  onComplete: () => void;
  duration?: number; // milliseconds
}

export const LoginSplash: React.FC<LoginSplashProps> = ({ 
  userFullName, 
  userRole,
  institutionName,
  onComplete,
  duration = 3000
}) => {
  useEffect(() => {
    const timer = setTimeout(onComplete, duration);
    return () => clearTimeout(timer);
  }, [onComplete, duration]);

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex flex-col items-center justify-center z-50 overflow-hidden">
      {/* Animated Background Orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-brand-600/20 rounded-full blur-[120px] pointer-events-none animate-pulse" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-indigo-600/20 rounded-full blur-[120px] pointer-events-none animate-pulse" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center gap-12">
        {/* Animated Logo */}
        <AnimatedLogo size="xl" variant="bounce" />

        {/* Welcome Text - Fade in animation */}
        <div className="text-center space-y-3 animate-in fade-in slide-in-from-bottom-4 duration-1000">
          <h2 className="text-2xl font-bold text-white">
            Welcome back, {userFullName}! 👋
          </h2>
          
          <div className="flex items-center justify-center gap-2 text-slate-300">
            <span className="text-sm uppercase tracking-wider font-semibold">
              {userRole.toLowerCase().replace('_', ' ')}
            </span>
            {institutionName && (
              <>
                <span className="text-slate-500">•</span>
                <span className="text-sm font-medium text-slate-400">
                  {institutionName}
                </span>
              </>
            )}
          </div>

          <p className="text-xs text-slate-500 pt-4">
            Initializing your dashboard...
          </p>
        </div>

        {/* Loading Progress Indicator */}
        <div className="w-64 h-1 bg-slate-800 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-brand-500 to-indigo-500 rounded-full"
            style={{
              animation: 'slideIn 2s ease-in-out forwards',
            }}
          />
          <style>{`
            @keyframes slideIn {
              from { width: 0; }
              to { width: 100%; }
            }
          `}</style>
        </div>
      </div>
    </div>
  );
};
