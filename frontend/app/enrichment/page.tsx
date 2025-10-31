"use client";

import { useEffect, useMemo, useState } from "react";
import { useOrganization } from '@/lib/organization-context';
import { eoApi } from "@/lib/api";
import { DashboardHeader } from '@/components/dashboard-header';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Sparkles, Database, TrendingUp, Loader2, Trash2, Share2 } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';

type Availability = { facility_id: string; rows: number; min_ts: string | null; max_ts: string | null };
type SeriesPoint = {
  observed_at: string;
  aqi_score: number | null;
  no2: number | null;
  co: number | null;
  so2: number | null;
  o3: number | null;
  ch4: number | null;
  aod: number | null;
};

export default function EnrichmentPage() {
  const { orgId } = useOrganization();
  const [isBackfilling, setIsBackfilling] = useState(false);
  const [availability, setAvailability] = useState<Availability[]>([]);
  const [loadingAvail, setLoadingAvail] = useState(false);
  const [selectedFacility, setSelectedFacility] = useState<string | null>(null);
  const [series, setSeries] = useState<SeriesPoint[]>([]);
  const [seriesHasMore, setSeriesHasMore] = useState(true);
  const [seriesLoading, setSeriesLoading] = useState(false);
  const [seriesPage, setSeriesPage] = useState(0);
  const pageSize = 50;
  const [showClear, setShowClear] = useState(false);
  const [clearPwd, setClearPwd] = useState("");
  const [clearing, setClearing] = useState(false);
  const [kgSyncing, setKgSyncing] = useState(false);

  const canRun = useMemo(() => Boolean(orgId) && !isBackfilling, [orgId, isBackfilling]);

  async function refreshAvailability() {
    if (!orgId) return;
    setLoadingAvail(true);
    try {
      const data = await eoApi.availability(orgId);
      setAvailability(data);
    } catch (error: any) {
      toast.error('Failed to fetch availability: ' + (error.message || 'Unknown error'));
    } finally {
      setLoadingAvail(false);
    }
  }

  async function handleBackfill() {
    if (!orgId) return;
    setIsBackfilling(true);
    try {
      const result = await eoApi.backfill(orgId);
      toast.success(`Backfilled ${result.facilities} facilities with ${result.rows} EO records!`);
      await refreshAvailability();
    } catch (error: any) {
      toast.error('Backfill failed: ' + (error.message || 'Unknown error'));
    } finally {
      setIsBackfilling(false);
    }
  }

  async function loadSeries(reset = false) {
    if (!orgId || !selectedFacility) return;
    if (seriesLoading) return;
    setSeriesLoading(true);
    try {
      const nextOffset = reset ? 0 : seriesPage * pageSize;
      const chunk = await eoApi.timeseries(orgId, selectedFacility, {
        limit: pageSize,
        offset: nextOffset,
      });
      setSeries((prev) => (reset ? chunk : [...prev, ...chunk]));
      setSeriesHasMore(chunk.length === pageSize);
      setSeriesPage(reset ? 1 : seriesPage + 1);
    } catch (error: any) {
      toast.error('Failed to load timeseries: ' + (error.message || 'Unknown error'));
    } finally {
      setSeriesLoading(false);
    }
  }

  function selectFacility(fid: string) {
    setSelectedFacility(fid);
    setSeries([]);
    setSeriesHasMore(true);
    setSeriesPage(0);
    void loadSeries(true);
  }

  useEffect(() => {
    if (orgId) {
      void refreshAvailability();
    }
  }, [orgId]);

  async function handleKgSync() {
    if (!orgId) return;
    setKgSyncing(true);
    try {
      await apiClient.post(`/api/kg/organizations/${orgId}/sync`, undefined, { params: { phase: 1 } });
      await apiClient.post(`/api/kg/organizations/${orgId}/sync`, undefined, { params: { phase: 2 } });
      toast.success('Knowledge Graph synced (Phase 1 + 2)');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || e.message || 'KG sync failed');
    } finally {
      setKgSyncing(false);
    }
  }

  async function handleClear() {
    if (!orgId || !clearPwd) return;
    setClearing(true);
    try {
      const res = await eoApi.clear(orgId, clearPwd);
      toast.success(`Cleared ${res.deleted} EO rows`);
      setShowClear(false);
      setClearPwd("");
      setSelectedFacility(null);
      setSeries([]);
      await refreshAvailability();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || e.message || 'Failed to clear');
    } finally {
      setClearing(false);
    }
  }

  if (!orgId) {
    return (
      <div>
        <DashboardHeader />
        <main className="min-h-screen w-full px-4 md:px-6 lg:px-8 pt-24 pb-8">
          <div className="text-center">
            <p className="text-muted-foreground">
              Please select an organization to view EO enrichment.
            </p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div>
      <DashboardHeader />
      <main className="min-h-screen w-full px-4 md:px-6 lg:px-8 pt-24 pb-32 space-y-6 md:space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Earth Observation Enrichment</h1>
            <p className="text-muted-foreground mt-2">
              Generate and view synthetic EO timeseries data for your facilities
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={() => void refreshAvailability()}
              disabled={loadingAvail}
            >
              {loadingAvail ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Database className="mr-2 h-4 w-4" />}
              Refresh
            </Button>
            <Button
              variant="destructive"
              onClick={() => setShowClear(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Master Clear EO
            </Button>
            <Button
              variant="secondary"
              onClick={() => void handleKgSync()}
              disabled={!orgId || kgSyncing}
              title="Transfer enriched data to the Knowledge Graph (Neo4j)"
            >
              {kgSyncing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Syncing KG...
                </>
              ) : (
                <>
                  <Share2 className="mr-2 h-4 w-4" />
                  Sync to Knowledge Graph
                </>
              )}
            </Button>
            <Button
              size="lg"
              onClick={handleBackfill}
              disabled={!canRun}
            >
              {isBackfilling ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Backfilling...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Start EO Backfill
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Facilities
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{availability.length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total EO Records
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-emerald-600">
                {availability.reduce((sum, a) => sum + a.rows, 0)}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Date Range
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm">
                {availability.length > 0 ? (
                  <>
                    <div className="text-muted-foreground">From: {availability[0]?.min_ts?.split('T')[0] || '-'}</div>
                    <div className="text-muted-foreground">To: {availability[0]?.max_ts?.split('T')[0] || '-'}</div>
                  </>
                ) : (
                  <div className="text-muted-foreground">-</div>
                )}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Pipeline</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-1">
              <div>1) EO enrichment populates monthly timeseries per facility.</div>
              <div>2) Then data is synced into the Neo4j Knowledge Graph (Phase 1 + 2).</div>
              <div>3) Explore interactively under Knowledge Graph.</div>
            </CardContent>
          </Card>
        </div>

        {/* Facilities with EO data */}
        <Card>
          <CardHeader>
            <CardTitle>Facilities with EO Data</CardTitle>
            <CardDescription>
              Click on a facility to view its timeseries data
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingAvail && (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-20 w-full" />
                ))}
              </div>
            )}
            {!loadingAvail && availability.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                No EO data yet. Click "Start EO Backfill" to generate synthetic data.
              </div>
            )}
            {!loadingAvail && availability.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {availability.map((a) => (
                  <button
                    key={a.facility_id}
                    onClick={() => selectFacility(a.facility_id)}
                    className={`text-left p-4 rounded-lg border transition-all hover:shadow-md ${
                      selectedFacility === a.facility_id
                        ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950"
                        : "border-border hover:border-emerald-300"
                    }`}
                  >
                    <div className="font-medium text-lg">{a.facility_id}</div>
                    <div className="flex items-center gap-2 mt-2">
                      <TrendingUp className="h-4 w-4 text-emerald-600" />
                      <span className="text-sm text-muted-foreground">{a.rows} records</span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {a.min_ts?.split('T')[0]} → {a.max_ts?.split('T')[0]}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Timeseries Data */}
        {selectedFacility && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Timeseries: {selectedFacility}</CardTitle>
                  <CardDescription>
                    Lazy loaded {series.length} rows • Scroll to load more
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  onClick={() => void loadSeries(true)}
                  disabled={seriesLoading}
                >
                  {seriesLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Refresh"}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto rounded-lg border">
                <table className="min-w-full text-sm">
                  <thead className="bg-muted">
                    <tr>
                      {[
                        "Date",
                        "AQI",
                        "NO₂",
                        "CO",
                        "SO₂",
                        "O₃",
                        "CH₄",
                        "AOD",
                      ].map((h) => (
                        <th key={h} className="px-4 py-3 text-left font-medium">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {series.map((p, idx) => (
                      <tr key={`${p.observed_at}-${idx}`} className="border-t hover:bg-muted/50">
                        <td className="px-4 py-3 whitespace-nowrap">
                          {new Date(p.observed_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3">{p.aqi_score?.toFixed(1) ?? "-"}</td>
                        <td className="px-4 py-3">{p.no2?.toExponential(2) ?? "-"}</td>
                        <td className="px-4 py-3">{p.co?.toFixed(3) ?? "-"}</td>
                        <td className="px-4 py-3">{p.so2?.toFixed(4) ?? "-"}</td>
                        <td className="px-4 py-3">{p.o3?.toFixed(3) ?? "-"}</td>
                        <td className="px-4 py-3">{p.ch4?.toFixed(3) ?? "-"}</td>
                        <td className="px-4 py-3">{p.aod?.toFixed(3) ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-center mt-4">
                <Button
                  disabled={!seriesHasMore || seriesLoading}
                  onClick={() => void loadSeries(false)}
                  variant="outline"
                >
                  {seriesLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Loading...
                    </>
                  ) : seriesHasMore ? (
                    "Load More"
                  ) : (
                    "No More Data"
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {showClear && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-background rounded-lg p-6 w-full max-w-sm border">
              <h3 className="text-lg font-semibold mb-2">Confirm Master Clear</h3>
              <p className="text-sm text-muted-foreground mb-3">
                This will permanently delete all EO timeseries for this organization.
                Enter the organization sudo password to confirm.
              </p>
              <input
                type="password"
                className="w-full border rounded px-3 py-2 bg-background"
                placeholder="Organization sudo password"
                value={clearPwd}
                onChange={(e) => setClearPwd(e.target.value)}
              />
              <div className="flex items-center justify-end gap-2 mt-4">
                <Button variant="outline" onClick={() => { setShowClear(false); setClearPwd(""); }}>
                  Cancel
                </Button>
                <Button variant="destructive" disabled={!clearPwd || clearing} onClick={() => void handleClear()}>
                  {clearing ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Confirm Clear'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
