'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from './auth-context';

interface OrganizationContextType {
  orgId: string | null;
  setOrgId: (id: string) => void;
}

const OrganizationContext = createContext<OrganizationContextType | undefined>(undefined);

export function OrganizationProvider({ children }: { children: React.ReactNode }) {
  const [orgId, setOrgIdState] = useState<string | null>(null);
  const { user, loading: authLoading } = useAuth();

  useEffect(() => {
    // Wait for auth to finish loading
    if (authLoading) {
      return;
    }

    const stored = localStorage.getItem('veriearth_org_id');
    
    // If we have a stored org ID, use it (but verify it's still in user's orgs)
    if (stored) {
      if (user?.organizations && user.organizations.some(org => org.id === stored)) {
        setOrgIdState(stored);
        return;
      } else {
        // Stored org ID is invalid, clear it
        localStorage.removeItem('veriearth_org_id');
      }
    }
    
    // Auto-select first organization if none is selected and user has orgs
    if (user?.organizations && user.organizations.length > 0) {
      const firstOrgId = user.organizations[0].id;
      setOrgIdState(firstOrgId);
      localStorage.setItem('veriearth_org_id', firstOrgId);
    } else {
      // No orgs available, clear selection
      setOrgIdState(null);
    }
  }, [user?.organizations, user, authLoading]);

  const setOrgId = (id: string) => {
    setOrgIdState(id);
    localStorage.setItem('veriearth_org_id', id);
  };

  return (
    <OrganizationContext.Provider value={{ orgId, setOrgId }}>
      {children}
    </OrganizationContext.Provider>
  );
}

export function useOrganization() {
  const context = useContext(OrganizationContext);
  if (context === undefined) {
    throw new Error('useOrganization must be used within OrganizationProvider');
  }
  return context;
}
