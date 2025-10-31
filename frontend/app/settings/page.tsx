'use client';

import { useEffect, useState } from 'react';
import { dataManagementApi, dashboardApi, organizationApi, userApi } from '@/lib/api';
import apiClient from '@/lib/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { DashboardHeader } from '@/components/dashboard-header';
import { useOrganization } from '@/lib/organization-context';
import { useAuth } from '@/lib/auth-context';

export default function SettingsPage() {
  const { orgId } = useOrganization();
  const { user } = useAuth();
  const [active, setActive] = useState<string>('organization');
  const [orgName, setOrgName] = useState<string>('');
  const [orgDesc, setOrgDesc] = useState<string>('');
  const [orgAddr, setOrgAddr] = useState<string>('');
  const [orgDet, setOrgDet] = useState<string>('');
  // Originals for dirty check
  const [orgName0, setOrgName0] = useState<string>('');
  const [orgDesc0, setOrgDesc0] = useState<string>('');
  const [orgAddr0, setOrgAddr0] = useState<string>('');
  const [orgDet0, setOrgDet0] = useState<string>('');
  const [pwd, setPwd] = useState<string>('');
  const [busy, setBusy] = useState<boolean>(false);
  const [msg, setMsg] = useState<string>('');
  const [uName, setUName] = useState<string>('');
  const [uName0, setUName0] = useState<string>('');
  const [curPwd, setCurPwd] = useState<string>('');
  const [newPwd, setNewPwd] = useState<string>('');
  const [sudoCur, setSudoCur] = useState<string>('');
  const [sudoNew, setSudoNew] = useState<string>('');
  const [sudoErr, setSudoErr] = useState<string>('');

  useEffect(() => {
    if (!orgId) return;
    // Set name from user context if available
    const orgFromUser = user?.organizations?.find((o: any) => o.id === orgId);
    if (orgFromUser) setOrgName(orgFromUser.name || '');
    // Load org details
    organizationApi.get(orgId).then((o) => {
      if (!orgFromUser) setOrgName(o.name || '');
      setOrgDesc(o.description || '');
      setOrgAddr(o.address || '');
      setOrgDet(o.details ? JSON.stringify(o.details) : '');
      // Set originals for dirty tracking
      setOrgName0((orgFromUser?.name ?? o.name) || '');
      setOrgDesc0(o.description || '');
      setOrgAddr0(o.address || '');
      setOrgDet0(o.details ? JSON.stringify(o.details) : '');
    }).catch(()=>{});
    // Load user originals
    setUName(user?.full_name || '');
    setUName0(user?.full_name || '');
  }, [orgId, user]);

  const onClear = async () => {
    if (!orgId || !pwd) return;
    setBusy(true);
    setMsg('');
    try {
      const res = await dataManagementApi.clearOrganization(orgId, pwd);
      setMsg(res.message || 'Organization data cleared');
      // Also clear analytics graphs (facility + route) for this org
      try {
        await apiClient.delete('/api/kg/analytics/graphs/clear', { params: { org_id: orgId } });
      } catch (e: any) {
        // propagate visible error (generic), do not fail silently
        const detail = e?.response?.data?.detail || 'Failed to clear analytics graphs';
        setMsg(prev => (prev ? `${prev} · ${detail}` : detail));
        return; // keep busy false in finally
      }
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || e?.message || 'Failed to clear');
    } finally {
      setBusy(false);
      setPwd('');
    }
  };

  const onSaveOrg = async () => {
    if (!orgId) return;
    setBusy(true);
    setMsg('');
    try {
      let details: any = undefined;
      if (orgDet) {
        try { details = JSON.parse(orgDet); } catch { details = orgDet; }
      }
      await organizationApi.update(orgId, {
        name: orgName || undefined,
        description: orgDesc || undefined,
        address: orgAddr || undefined,
        details,
      });
      setMsg('Organization updated');
      // Update originals after successful save
      setOrgName0(orgName);
      setOrgDesc0(orgDesc);
      setOrgAddr0(orgAddr);
      setOrgDet0(orgDet);
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || e?.message || 'Failed to update organization');
    } finally {
      setBusy(false);
    }
  };

  const onSetSudo = async () => {
    if (!orgId || !sudoNew) return;
    setBusy(true);
    setMsg('');
    try {
      await organizationApi.setSudoPassword(orgId, { password: sudoNew, current_password: sudoCur || undefined });
      setMsg('Sudo password set');
      setSudoCur(''); setSudoNew('');
      setSudoErr('');
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || 'Failed to set sudo password';
      // Surface specific error when current password is wrong
      if (typeof detail === 'string' && detail.toLowerCase().includes('current password')) {
        setSudoErr('Current sudo password is incorrect');
      } else if (typeof detail === 'string' && detail.toLowerCase().includes('too short')) {
        setSudoErr('New password is too short');
      } else {
        setSudoErr(String(detail));
      }
      setMsg('');
    } finally {
      setBusy(false);
    }
  };

  const onSaveUser = async () => {
    setBusy(true);
    setMsg('');
    try {
      if (uName) await userApi.updateProfile({ full_name: uName });
      if (curPwd && newPwd) await userApi.changePassword({ current_password: curPwd, new_password: newPwd });
      setMsg('User settings updated');
      setCurPwd(''); setNewPwd('');
      setUName0(uName);
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || e?.message || 'Failed to update user');
    } finally {
      setBusy(false);
    }
  };

  // Dirty flags
  const normalizeDet = (s: string) => {
    if (!s) return '';
    try { return JSON.stringify(JSON.parse(s)); } catch { return s.trim(); }
  };
  const orgDirty = (
    orgName !== orgName0 ||
    orgDesc !== orgDesc0 ||
    orgAddr !== orgAddr0 ||
    normalizeDet(orgDet) !== normalizeDet(orgDet0)
  );
  const userDirty = (uName !== uName0) || (Boolean(curPwd) && Boolean(newPwd));

  return (
    <div>
      <DashboardHeader />
      <main className="min-h-screen w-full px-4 md:px-6 lg:px-8 pt-24 pb-16">
    <div className="space-y-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-muted-foreground">Manage organization, user, and administrative settings</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="md:sticky md:top-24 h-fit">
          <Card className="shadow-sm">
            <CardContent className="pt-4">
              <div className="mb-3">
                <div className="text-base font-medium">Sections</div>
                <div className="text-sm text-muted-foreground">Choose what to manage</div>
              </div>
              <div className="flex flex-col items-stretch w-full gap-3">
                {[
                  { key: 'organization', label: 'Organization' },
                  { key: 'user', label: 'User' },
                  { key: 'management', label: 'Organization Management' },
                ].map((it) => (
                  <button
                    key={it.key}
                    onClick={() => setActive(it.key)}
                    className={`justify-start w-full text-left rounded-lg border px-4 py-3 transition-colors ${
                      active === it.key
                        ? 'bg-accent text-accent-foreground'
                        : 'bg-background hover:bg-accent/40'
                    }`}
                  >
                    {it.label}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Content */}
        <div className="md:col-span-3">
            {active === 'organization' && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Organization</CardTitle>
                  <CardDescription>Update basic organization information</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-3 max-w-2xl">
                    <input className="border p-2 rounded" placeholder="Organization name" value={orgName} onChange={e=>setOrgName(e.target.value)} />
                    <input className="border p-2 rounded" placeholder="Description" value={orgDesc} onChange={e=>setOrgDesc(e.target.value)} />
                    <input className="border p-2 rounded" placeholder="Address" value={orgAddr} onChange={e=>setOrgAddr(e.target.value)} />
                    <textarea className="border p-2 rounded" placeholder="Details (JSON or text)" value={orgDet} onChange={e=>setOrgDet(e.target.value)} />
                    <div>
                      <Button onClick={onSaveOrg} disabled={!orgId || busy || !orgDirty}>
                        {busy ? 'Saving...' : 'Save'}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
            )}

            {active === 'user' && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>User Profile</CardTitle>
                  <CardDescription>Update your display name and password</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-3 max-w-xl">
                    <div className="text-sm text-muted-foreground">{user?.email}</div>
                    <input className="border p-2 rounded" placeholder="Display name" value={uName} onChange={e=>setUName(e.target.value)} />
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      <input type="password" className="border p-2 rounded" placeholder="Current password" value={curPwd} onChange={e=>setCurPwd(e.target.value)} />
                      <input type="password" className="border p-2 rounded" placeholder="New password" value={newPwd} onChange={e=>setNewPwd(e.target.value)} />
                    </div>
                    <div>
                      <Button onClick={onSaveUser} disabled={busy || !userDirty}>
                        {busy ? 'Saving...' : 'Save'}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
            )}

            {active === 'management' && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Sudo Password</CardTitle>
                  <CardDescription>Control access to privileged operations</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-3 max-w-md">
                    <input type="password" className="border p-2 rounded" placeholder="Current sudo password (if set)" value={sudoCur} onChange={e=>setSudoCur(e.target.value)} />
                    <input type="password" className="border p-2 rounded" placeholder="New sudo password" value={sudoNew} onChange={e=>setSudoNew(e.target.value)} />
                    {sudoErr && <div className="text-sm text-red-600">{sudoErr}</div>}
                    <div>
                      <Button onClick={onSetSudo} disabled={!orgId || !sudoNew || busy}>
                        {busy ? 'Saving...' : 'Set Sudo Password'}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-red-300">
                <CardHeader>
                  <CardTitle className="text-red-600">Danger Zone</CardTitle>
                  <CardDescription>Delete all data for this organization across Postgres, EO, and Neo4j</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 max-w-md">
                    <input type="password" className="border p-2 rounded w-full" placeholder="Organization sudo password" value={pwd} onChange={e=>setPwd(e.target.value)} />
                    <Button variant="destructive" onClick={onClear} disabled={!orgId || !pwd || busy}>
                      {busy ? 'Clearing...' : 'Clear All'}
                    </Button>
                    {msg && <p className="text-sm">{msg}</p>}
                  </div>
                </CardContent>
              </Card>
            </div>
            )}
        
        </div>
      </div>
      
    </div>
      </main>
    </div>
  );
}


