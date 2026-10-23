import React from 'react';
import { AnimatedLogo } from './AnimatedLogo';

interface LoadingOverlayProps {
  isVisible: boolean;
  message?: string;
  variant?: 'spin' | 'pulse' | 'bounce';
  fullScreen?: boolean;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({ 
  isVisible,
  message = 'Loading...',
  variant = 'spin',
  fullScreen = false
}) => {
  if (!isVisible) return null;

  const containerClasses = fullScreen 
    ? 'fixed inset-0 z-40' 
    : 'absolute inset-0 z-40';

  return (
    <div className={`${containerClasses} bg-white/80 backdrop-blur-sm flex items-center justify-center`}>
      <div className="flex flex-col items-center gap-4">
        <AnimatedLogo size="lg" variant={variant} />
        {message && (
          <div className="text-center">
            <p className="text-sm font-semibold text-slate-700">
              {message}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Please wait...
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
