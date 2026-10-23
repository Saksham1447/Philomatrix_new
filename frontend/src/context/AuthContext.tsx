import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserProfile, UserRole, Student } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  activeRole: UserRole | null;
  activeChild: Student | null;
  linkedChildren: Student[];
  isLoading: boolean;
  login: (token: string, profile: UserProfile) => void;
  logout: () => void;
  setActiveRole: (role: UserRole) => void;
  selectChild: (childId: string) => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem('philomatrix_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('philomatrix_access_token');
  });
  const [activeRole, setActiveRoleState] = useState<UserRole | null>(() => {
    const saved = localStorage.getItem('philomatrix_active_role');
    return (saved as UserRole) || null;
  });
  const [linkedChildren, setLinkedChildren] = useState<Student[]>([]);
  const [activeChild, setActiveChild] = useState<Student | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchProfileAndChildren = async () => {
    if (!localStorage.getItem('philomatrix_access_token')) {
      setIsLoading(false);
      return;
    }
    try {
      const profile = await api.get<UserProfile>('/auth/me');
      setUser(profile);
      localStorage.setItem('philomatrix_user', JSON.stringify(profile));

      // Determine initial active role
      const savedRole = localStorage.getItem('philomatrix_active_role') as UserRole;
      if (savedRole && profile.roles.includes(savedRole)) {
        setActiveRoleState(savedRole);
      } else if (profile.roles.length > 0) {
        setActiveRoleState(profile.roles[0]);
        localStorage.setItem('philomatrix_active_role', profile.roles[0]);
      }

      // If user has PARENT role, fetch linked children
      if (profile.roles.includes('PARENT')) {
        try {
          const childrenData = await api.get<Student[]>('/students/my-children');
          setLinkedChildren(childrenData);
          if (childrenData.length > 0) {
            const savedChildId = localStorage.getItem('philomatrix_active_child_id');
            const found = childrenData.find(c => c.id === savedChildId);
            setActiveChild(found || childrenData[0]);
          }
        } catch (err) {
          console.error("Failed to fetch linked children", err);
        }
      }
    } catch (err) {
      console.error("Failed to verify user session", err);
      logout();
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProfileAndChildren();

    const handleUnauthorized = () => {
      logout();
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  const login = (newToken: string, newProfile: UserProfile) => {
    localStorage.setItem('philomatrix_access_token', newToken);
    localStorage.setItem('philomatrix_user', JSON.stringify(newProfile));
    setToken(newToken);
    setUser(newProfile);
    const initialRole = newProfile.roles[0] || 'STUDENT';
    setActiveRoleState(initialRole);
    localStorage.setItem('philomatrix_active_role', initialRole);
    fetchProfileAndChildren();
  };

  const logout = () => {
    localStorage.removeItem('philomatrix_access_token');
    localStorage.removeItem('philomatrix_user');
    localStorage.removeItem('philomatrix_active_role');
    localStorage.removeItem('philomatrix_active_child_id');
    setUser(null);
    setToken(null);
    setActiveRoleState(null);
    setLinkedChildren([]);
    setActiveChild(null);
  };

  const setActiveRole = (role: UserRole) => {
    setActiveRoleState(role);
    localStorage.setItem('philomatrix_active_role', role);
  };

  const selectChild = (childId: string) => {
    const child = linkedChildren.find(c => c.id === childId);
    if (child) {
      setActiveChild(child);
      localStorage.setItem('philomatrix_active_child_id', child.id);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        activeRole,
        activeChild,
        linkedChildren,
        isLoading,
        login,
        logout,
        setActiveRole,
        selectChild,
        refreshProfile: fetchProfileAndChildren,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
