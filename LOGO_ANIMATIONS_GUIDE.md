# PHILOMATRIX Logo Animation System

## 🎬 Overview

The PHILOMATRIX application now features sophisticated animated logo implementations across three key user experience moments:

1. **Login Splash Screen** — Welcome animation after successful login
2. **Loading States** — Animated logo during API calls and buffering
3. **Initialization** — Animated logo while app initializes

---

## 🎨 Animation Variants

### 1. **Spin Animation** ⟳
- **Use Case:** Loading states, buffering, API calls
- **Duration:** 2 seconds (continuous loop)
- **Effect:** Smooth 360° rotation

```tsx
<AnimatedLogo size="lg" variant="spin" />
```

### 2. **Pulse Animation** 💫
- **Use Case:** Loading indicators, gentle emphasis
- **Duration:** 2 seconds (continuous loop)
- **Effect:** Glow effect with opacity oscillation

```tsx
<AnimatedLogo size="md" variant="pulse" />
```

### 3. **Bounce Animation** 🎈
- **Use Case:** Welcome screens, splash animations
- **Duration:** 1.5 seconds (continuous loop)
- **Effect:** Vertical bouncing with opacity fade

```tsx
<AnimatedLogo size="xl" variant="bounce" />
```

---

## 📦 Components & Their Usage

### 1. **AnimatedLogo Component**
Standalone animated logo that can be used anywhere in the app.

**File:** `src/components/common/AnimatedLogo.tsx`

**Props:**
- `size?: 'sm' | 'md' | 'lg' | 'xl'` — Logo dimensions (default: 'md')
  - `sm`: 48px (w-12 h-12)
  - `md`: 64px (w-16 h-16)
  - `lg`: 96px (w-24 h-24)
  - `xl`: 128px (w-32 h-32)
- `variant?: 'spin' | 'pulse' | 'bounce'` — Animation type (default: 'spin')
- `showText?: boolean` — Display "Loading PHILOMATRIX..." text (default: false)

**Example:**
```tsx
import { AnimatedLogo } from '@/components/common';

function MyLoadingComponent() {
  return (
    <div className="flex flex-col items-center gap-4">
      <AnimatedLogo size="lg" variant="spin" showText />
      <p>Fetching data...</p>
    </div>
  );
}
```

---

### 2. **LoginSplash Component**
Full-screen welcome animation shown immediately after successful login.

**File:** `src/components/common/LoginSplash.tsx`

**Props:**
- `userFullName: string` — User's display name (e.g., "Arjun Sharma")
- `userRole: string` — User's role (e.g., "STUDENT", "PRINCIPAL")
- `institutionName?: string` — Institution name (optional)
- `onComplete: () => void` — Callback when animation completes
- `duration?: number` — Animation duration in milliseconds (default: 3000)

**Features:**
- Bouncing logo animation (3 seconds)
- Personalized welcome message with user name
- Role and institution display
- Progress bar indicator
- Automatic navigation after completion
- Gradient background with animated orbs

**Example Flow:**
```tsx
// In LoginPage.tsx
const handleLogin = async () => {
  // ... login logic ...
  
  // Show splash screen
  setSplashData({
    fullName: profile.full_name,
    role: profile.roles[0],
    institution: profile.institution_name,
  });
  setShowSplash(true);

  // Navigate after splash completes
  setTimeout(() => {
    navigate('/dashboard');
  }, 3000);
};

return (
  <>
    {showSplash && (
      <LoginSplash
        userFullName={splashData.fullName}
        userRole={splashData.role}
        institutionName={splashData.institution}
        onComplete={() => setShowSplash(false)}
        duration={3000}
      />
    )}
    {/* Rest of login form... */}
  </>
);
```

---

### 3. **LoadingOverlay Component**
Reusable loading overlay for any component that needs a loading state.

**File:** `src/components/common/LoadingOverlay.tsx`

**Props:**
- `isVisible: boolean` — Show/hide the overlay
- `message?: string` — Custom loading message (default: "Loading...")
- `variant?: 'spin' | 'pulse' | 'bounce'` — Animation type (default: 'spin')
- `fullScreen?: boolean` — Full screen or relative positioning (default: false)

**Example:**
```tsx
function DashboardPage() {
  const [isLoading, setIsLoading] = useState(false);

  const handleFetchData = async () => {
    setIsLoading(true);
    try {
      const data = await api.get('/data');
      // Process data...
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative">
      <LoadingOverlay 
        isVisible={isLoading}
        message="Fetching dashboard data..."
        variant="spin"
        fullScreen={false}
      />
      {/* Content */}
    </div>
  );
}
```

---

## 🔄 Integration Points

### 1. **Login Flow**
```
User enters credentials
    ↓
[Submit Button Clicked]
    ↓
[API: POST /auth/login]
    ↓
[Fetch user profile: GET /auth/me]
    ↓
[SHOW: LoginSplash with bounce animation] ⭐ 3 seconds
    ↓
[Hide splash, perform login, navigate to /dashboard]
```

### 2. **Page Loading**
```
AppLayout renders
    ↓
[Check auth status]
    ↓
[isLoading = true]
    ↓
[SHOW: AnimatedLogo with spin animation] ⭐
    ↓
[isLoading = false]
    ↓
[Render page content]
```

### 3. **API Buffering (Optional)**
```
Component makes API call
    ↓
[setLoading(true)]
    ↓
[SHOW: LoadingOverlay with spin animation] ⭐
    ↓
[API completes]
    ↓
[setLoading(false)]
    ↓
[Show result]
```

---

## 🎯 User Experience Flow

### Login Sequence
1. User logs in successfully
2. **[SPLASH SCREEN APPEARS]**
   - Full-screen dark gradient background with animated orbs
   - Logo bounces gently in center
   - Message: "Welcome back, [Name]! 👋"
   - Shows role and institution
   - Progress bar fills over 3 seconds
3. **[AUTOMATIC REDIRECT]**
   - After 3 seconds, dashboard loads
   - User sees navbar with logo
   - Smooth transition to their personalized dashboard

### Dashboard Loading
1. User clicks link or refreshes page
2. **[LOADING STATE]**
   - Spinning logo appears in center
   - "Initializing PHILOMATRIX ERP..." message
   - Page blocks until auth is verified
3. **[CONTENT LOADS]**
   - Navbar and sidebar appear
   - Main content renders
   - Logo visible in navbar (static, non-animated)

---

## 🎨 CSS Animation Definitions

All animations use pure CSS with no external dependencies:

### Spin Animation
```css
@keyframes spin-smooth {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.logo-spin {
  animation: spin-smooth 2s linear infinite;
}
```

### Pulse Animation
```css
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

.logo-pulse {
  animation: pulse-glow 2s ease-in-out infinite;
}
```

### Bounce Animation
```css
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

.logo-bounce {
  animation: bounce-gentle 1.5s ease-in-out infinite;
}
```

---

## 🔌 Hook for API Loading

A custom hook `useApiLoading` is available for managing loading states:

**File:** `src/hooks/useApiLoading.ts`

**Usage:**
```tsx
import { useApiLoading } from '@/hooks/useApiLoading';

function MyComponent() {
  const { isLoading, error, withLoading } = useApiLoading({
    onSuccess: () => console.log('Success!'),
    onError: (err) => console.error(err),
  });

  const handleFetch = async () => {
    const data = await withLoading(async () => {
      return await api.get('/data');
    });
  };

  return (
    <>
      <LoadingOverlay 
        isVisible={isLoading}
        message="Fetching..."
        variant="spin"
      />
      <button onClick={handleFetch}>Fetch Data</button>
    </>
  );
}
```

---

## 📁 File Structure

```
frontend/src/
├── components/common/
│   ├── AnimatedLogo.tsx        ⭐ Main animated logo component
│   ├── LoginSplash.tsx          ⭐ Login welcome screen
│   ├── LoadingOverlay.tsx       ⭐ Reusable loading overlay
│   ├── Navbar.tsx               ✏️ Updated with static logo
│   ├── Sidebar.tsx
│   └── index.ts                 ✏️ Exports all components
│
├── pages/
│   └── LoginPage.tsx            ✏️ Updated with splash screen
│
├── layouts/
│   └── AppLayout.tsx            ✏️ Updated with animated logo loader
│
├── hooks/
│   └── useApiLoading.ts         ⭐ Loading state management hook
│
├── services/
│   └── api.ts                   (unchanged, ready for integration)
│
└── public/assets/logos/
    └── philomatrix-logo.png     (official logo image)
```

**Legend:**
- ⭐ New component/file
- ✏️ Modified/updated file

---

## 🚀 Performance Notes

- **No external animation libraries** — Uses pure CSS animations
- **GPU-accelerated** — CSS transforms and opacity changes
- **Low memory footprint** — Static PNG logo image
- **Responsive** — Works on all screen sizes
- **Accessible** — Animations respect `prefers-reduced-motion` preference (can be added)

---

## 🎯 Future Enhancements

1. **Accessibility:**
   - Add `prefers-reduced-motion` media query support
   - Add ARIA labels for screen readers

2. **Extended Usage:**
   - Error states with red pulse animation
   - Success states with green pulse animation
   - Custom animation speeds per component

3. **Analytics:**
   - Track splash screen completion time
   - Monitor average login-to-dashboard time

4. **Customization:**
   - Allow theme-based animation colors
   - Configurable animation speeds
   - SVG-based logo animations (if needed)

---

## ✅ Testing Checklist

- [x] Logo animation displays on login
- [x] Splash screen shows user name and role
- [x] Splash screen auto-closes after 3 seconds
- [x] Dashboard redirect works after splash
- [x] Loading spinner appears during page initialization
- [x] Logo renders correctly in navbar (static)
- [x] Browser favicon displays logo
- [x] All animations are smooth and performant
- [x] Mobile responsive layouts work
- [x] Animations loop infinitely until replaced

---

**Last Updated:** 2026-10-18  
**Status:** ✅ Live Implementation Complete
