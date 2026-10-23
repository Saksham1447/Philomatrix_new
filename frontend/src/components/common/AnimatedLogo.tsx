import React from 'react';

interface AnimatedLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'spin' | 'pulse' | 'bounce';
  showText?: boolean;
}

const sizeClasses = {
  sm: 'w-12 h-12',
  md: 'w-16 h-16',
  lg: 'w-24 h-24',
  xl: 'w-32 h-32',
};

export const AnimatedLogo: React.FC<AnimatedLogoProps> = ({ 
  size = 'md', 
  variant = 'spin',
  showText = false 
}) => {
  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <style>{`
        @keyframes spin-smooth {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        @keyframes pulse-glow {
          0% { 
            opacity: 1;
            filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.8));
          }
          50% { 
            opacity: 0.7;
            filter: drop-shadow(0 0 16px rgba(59, 130, 246, 0.4));
          }
          100% { 
            opacity: 1;
            filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.8));
          }
        }
        
        @keyframes bounce-gentle {
          0%, 100% { 
            transform: translateY(0);
            opacity: 1;
          }
          50% { 
            transform: translateY(-12px);
            opacity: 0.8;
          }
        }
        
        .logo-spin {
          animation: spin-smooth 2s linear infinite;
        }
        
        .logo-pulse {
          animation: pulse-glow 2s ease-in-out infinite;
        }
        
        .logo-bounce {
          animation: bounce-gentle 1.5s ease-in-out infinite;
        }
      `}</style>

      <div className={`${sizeClasses[size]} ${
        variant === 'spin' ? 'logo-spin' :
        variant === 'pulse' ? 'logo-pulse' :
        'logo-bounce'
      }`}>
        <img 
          src="/assets/logos/philomatrix-logo.png" 
          alt="PHILOMATRIX Loading"
          className="w-full h-full object-contain"
        />
      </div>

      {showText && (
        <div className="text-center">
          <p className="text-sm font-semibold text-slate-700 animate-pulse">
            Loading PHILOMATRIX...
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Please wait
          </p>
        </div>
      )}
    </div>
  );
};
