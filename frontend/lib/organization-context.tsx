'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

interface OrganizationContextType {
  orgId: string | null;
  setOrgId: (id: string) => void;
}

const OrganizationContext = createContext<OrganizationContextType | undefined>(undefined);

export function OrganizationProvider({ children }: { children: React.ReactNode }) {
  const [orgId, setOrgIdState] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem('veriearth_org_id');
    if (stored) {
      setOrgIdState(stored);
    }
  }, []);

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
