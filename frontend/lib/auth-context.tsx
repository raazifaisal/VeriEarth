'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { apiRequest } from './api-secure';
import { toast } from 'sonner';

interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  organizations: any[];
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const PUBLIC_ROUTES = ['/signin', '/signup', '/verify-email', '/'];
const PROTECTED_PREFIXES = [
  '/dashboard',
  '/analytics',
  '/ingestion',
  '/data-management',
  '/enrichment',
  '/settings',
];
const ALLOWED_UNVERIFIED_ROUTES = ['/signin', '/signup', '/verify-email', '/'];

const isProtectedRoute = (path: string) => {
  if (PUBLIC_ROUTES.includes(path)) {
    return false;
  }
  return PROTECTED_PREFIXES.some((prefix) => path.startsWith(prefix));
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const checkAuth = async () => {
    try {
      const response = await apiRequest('http://localhost:8000/auth/me');
      
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        
        // Redirect unverified users to verification page
        if (!userData.is_verified && pathname && isProtectedRoute(pathname)) {
          router.push('/verify-email');
          return;
        }
      } else {
        setUser(null);
        if (pathname && isProtectedRoute(pathname)) {
          router.push('/signin');
        }
      }
    } catch (error) {
      setUser(null);
      if (pathname && isProtectedRoute(pathname)) {
        router.push('/signin');
      }
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await apiRequest('http://localhost:8000/auth/logout', {
        method: 'POST',
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      toast.success('Logged out successfully');
      router.push('/signin');
    }
  };

  const refreshUser = async () => {
    await checkAuth();
  };

  useEffect(() => {
    checkAuth();
    
    // Check auth status every 5 minutes
    const interval = setInterval(() => {
      checkAuth();
    }, 5 * 60 * 1000);

    // Listen for unauthorized events
    const handleUnauthorized = () => {
      setUser(null);
      if (pathname && isProtectedRoute(pathname)) {
        router.push('/signin');
      }
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);

    return () => {
      clearInterval(interval);
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, [pathname]);

  // Redirect authenticated users away from auth pages
  useEffect(() => {
    if (!loading && user) {
      // Allow unverified users to access signin/signup/verify-email pages
      if (!user.is_verified && ALLOWED_UNVERIFIED_ROUTES.includes(pathname || '')) {
        return; // Allow access to these pages
      }
      // Redirect unverified users to verification page from protected routes
      if (!user.is_verified && pathname && isProtectedRoute(pathname)) {
        router.push('/verify-email');
        return;
      }
      // Redirect verified users away from auth pages
      if (user.is_verified && (pathname === '/signin' || pathname === '/signup')) {
        router.push('/dashboard');
      }
    }
  }, [user, loading, pathname]);

  return (
    <AuthContext.Provider value={{ user, loading, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

