'use client';

import { useOrganization } from '@/lib/organization-context';
import { DashboardHeader } from '@/components/dashboard-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Checkbox } from '@/components/ui/checkbox';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Network, TrendingUp, AlertTriangle, Leaf, Wind, AlertCircle, Filter, RefreshCcw } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTheme } from 'next-themes';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import coseBilkent from 'cytoscape-cose-bilkent';
import apiClient from '@/lib/api';
import type { AxiosError } from 'axios';

cytoscape.use(coseBilkent);

const TRANSPORT_MODE_OPTIONS = [
  { value: 'road_truck', label: 'Road Truck', hint: 'Long-haul freight' },
  { value: 'road_van', label: 'Road Van', hint: 'Last-mile delivery' },
  { value: 'rail_freight', label: 'Rail Freight', hint: 'Rail corridors' },
  { value: 'sea_container', label: 'Sea Container', hint: 'Ocean freight' },
  { value: 'sea_bulk', label: 'Sea Bulk', hint: 'Bulk shipments' },
  { value: 'air_cargo', label: 'Air Cargo', hint: 'Express air' },
  { value: 'pipeline', label: 'Pipeline', hint: 'Fluid transport' },
] as const;

const modeLabelMap = TRANSPORT_MODE_OPTIONS.reduce<Record<string, string>>((acc, option) => {
  acc[option.value] = option.label;
  return acc;
}, {});

export default function AnalyticsPage() {
  const { orgId } = useOrganization();
  const [activeTab, setActiveTab] = useState('graph');
  
  // Graph viz state
  const [q, setQ] = useState('');
  const [modes, setModes] = useState<string[]>([]);
  const [includeSup, setIncludeSup] = useState(true);
  const [includeFac, setIncludeFac] = useState(true);
  const [includeRoutes, setIncludeRoutes] = useState(true);
  const [minKm, setMinKm] = useState('');
  const [maxKm, setMaxKm] = useState('');
  const [availableModes, setAvailableModes] = useState<string[]>(TRANSPORT_MODE_OPTIONS.map(o => o.value));
  const [graph, setGraph] = useState<{nodes:any[];edges:any[]}>({nodes:[],edges:[]});
  const [loading, setLoading] = useState(false);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [graphEmpty, setGraphEmpty] = useState(false);
  const cyRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Analytics state
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [facilityBetweenness, setFacilityBetweenness] = useState<any[]>([]);
  const [facilityPagerank, setFacilityPagerank] = useState<any[]>([]);
  const [facilityCommunities, setFacilityCommunities] = useState<any[]>([]);
  const [routePagerank, setRoutePagerank] = useState<any[]>([]);
  const [prefixSpanPatterns, setPrefixSpanPatterns] = useState<any[]>([]);
  const [eoHotspots, setEoHotspots] = useState<any[]>([]);
  const [graphStatus, setGraphStatus] = useState<any>(null);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  
  // Path comparison
  const [srcFacility, setSrcFacility] = useState('');
  const [dstFacility, setDstFacility] = useState('');
  const [pathWeight, setPathWeight] = useState('distance');
  const [pathResult, setPathResult] = useState<any>(null);
  const [pathLoading, setPathLoading] = useState(false);

  const cyElements = useMemo(() => {
    const nodes = graph.nodes.map(n => ({ data: { id: n.id, label: n.name || n.id, type: n.type, ...n } }));
    const edges = graph.edges.map(e => ({ data: { id: e.id || `${e.type}:${e.source}->${e.target}`, source: e.source, target: e.target, type: e.type, ...e } }));
    return [...nodes, ...edges];
  }, [graph]);

  const routeEdgeCount = useMemo(() => graph.edges.filter(e => e.type === 'route').length, [graph.edges]);
  const supplierEdgeCount = useMemo(() => graph.edges.filter(e => e.type === 'supplies').length, [graph.edges]);

  const { resolvedTheme } = useTheme();
  const isDark = (resolvedTheme ?? 'light') === 'dark';

  const graphPalette = useMemo(() => ({
    facility: isDark ? '#3b82f6' : '#60a5fa',
    supplier: isDark ? '#16a34a' : '#22c55e',
    label: isDark ? '#f8fafc' : '#0f172a',
    outline: isDark ? 'rgba(15,23,42,0.55)' : 'rgba(255,255,255,0.7)',
    nodeBorder: isDark ? '#93c5fd' : '#0f172a',
    edge: isDark ? '#64748b' : '#94a3b8',
    supplyEdge: isDark ? '#34d399' : '#10b981',
  }), [isDark]);

  const graphStyles = useMemo(() => ([
    {
      selector: 'node',
      style: {
        'width': 46,
        'height': 46,
        'border-width': 1.5,
        'border-color': graphPalette.nodeBorder,
        'font-size': 14,
        'text-wrap': 'wrap',
        'text-max-width': 130,
        'text-valign': 'center',
        'text-halign': 'center',
        'color': graphPalette.label,
        'font-weight': 600,
        'padding': 6,
        'text-outline-width': 1.5,
        'text-outline-color': graphPalette.outline,
        'background-color': graphPalette.facility,
      }
    },
    {
      selector: 'node[type="facility"]',
      style: {
        'shape': 'ellipse',
        'label': 'data(label)',
        'background-color': graphPalette.facility,
      }
    },
    {
      selector: 'node[type="supplier"]',
      style: {
        'shape': 'hexagon',
        'label': 'data(label)',
        'background-color': graphPalette.supplier,
      }
    },
    {
      selector: 'edge',
      style: {
        'curve-style': 'bezier',
        'line-color': graphPalette.edge,
        'width': 2,
        'target-arrow-shape': 'triangle',
        'target-arrow-color': graphPalette.edge,
        'opacity': 0.95,
      }
    },
    {
      selector: 'edge[type="supplies"]',
      style: {
        'line-style': 'dashed',
        'line-color': graphPalette.supplyEdge,
        'target-arrow-color': graphPalette.supplyEdge,
      }
    },
  ]), [graphPalette]);

  useEffect(() => {
    setGraph(prev => ({
      nodes: prev.nodes.map((node: any) => {
        if (node.type === 'supplier') {
          return { ...node, color: graphPalette.supplier };
        }
        if (node.type === 'facility') {
          return { ...node, color: graphPalette.facility };
        }
        return { ...node, color: graphPalette.facility };
      }),
      edges: prev.edges,
    }));
  }, [graphPalette]);

  const modeOptionsToRender = useMemo(() => {
    const source = availableModes.length ? availableModes : TRANSPORT_MODE_OPTIONS.map(option => option.value);
    return source
      .filter((value) => value !== 'pipeline')
      .map((value) => {
        const meta = TRANSPORT_MODE_OPTIONS.find(option => option.value === value);
        return {
          value,
          label: meta?.label ?? value.replace(/_/g, ' '),
          hint: meta?.hint ?? '',
        };
      });
  }, [availableModes]);

  function resetFilters() {
    setQ('');
    setModes([]);
    setIncludeSup(true);
    setIncludeFac(true);
    setIncludeRoutes(true);
    setMinKm('');
    setMaxKm('');
    setGraphError(null);
    setGraphEmpty(false);
    void fetchGraph({
      q: '',
      modes: [],
      includeSup: true,
      includeFac: true,
      includeRoutes: true,
      minKm: '',
      maxKm: '',
    });
  }

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;
    if (cy.elements().length === 0) {
      return;
    }
    setTimeout(() => {
      if (cy.destroyed()) return;
      if (cy.elements().length === 0) return;
      cy.layout({
        name: 'cose-bilkent',
        animate: true,
        randomize: true,
        fit: true,
        padding: 50,
        nodeDimensionsIncludeLabels: true,
        idealEdgeLength: 150,
        nodeRepulsion: 80000,
        edgeElasticity: 0.1
      }).run();
      cy.fit(undefined, 60);
    }, 0);
  }, [cyElements]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const cy = cyRef.current;
      if (cy && !cy.destroyed()) {
        cy.resize();
        if (cy.elements().length > 0) {
          cy.fit(undefined, 60);
        }
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!orgId) return;
    void fetchGraph();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  async function fetchGraph(overrides?: {
    q?: string;
    modes?: string[];
    includeSup?: boolean;
    includeFac?: boolean;
    includeRoutes?: boolean;
    minKm?: string;
    maxKm?: string;
  }) {
    if (!orgId) return;
    setLoading(true);
    setGraphError(null);
    setGraphEmpty(false);
    try {
      const search = overrides?.q ?? q;
      const modeFilters = overrides?.modes ?? modes;
      const includeSuppliers = overrides?.includeSup ?? includeSup;
      const includeFacilities = overrides?.includeFac ?? includeFac;
      const includeRoutesOption = overrides?.includeRoutes ?? includeRoutes;
      const minDistance = overrides?.minKm ?? minKm;
      const maxDistance = overrides?.maxKm ?? maxKm;

      const params: Record<string, any> = { org_id: orgId, q: search, limit: 500 };
      if (modeFilters.length) params.modes = modeFilters.join(',');
      params.include_suppliers = includeSuppliers;
      params.include_facilities = includeFacilities;
      params.include_routes = includeRoutesOption;
      if (minDistance.trim()) params.min_km = Number(minDistance);
      if (maxDistance.trim()) params.max_km = Number(maxDistance);

      const res = await apiClient.get('/api/kg/graph', { params });
      const data = res.data ?? { nodes: [], edges: [] };

      const normalizedSelectedModes = modeFilters.map((m) => m.toLowerCase());
      const selectedModeSet = new Set(normalizedSelectedModes);

      const rawEdges = (data.edges ?? []).map((edge: any) => ({
        ...edge,
        transport_mode: edge.transport_mode ? edge.transport_mode.toString().toLowerCase() : undefined,
      }));

      const modesInData = Array.from(new Set(rawEdges
        .map((edge: any) => edge.transport_mode)
        .filter((mode: unknown): mode is string => typeof mode === 'string' && mode.length > 0)
      )) as string[];
      if (modesInData.length) {
        setAvailableModes(modesInData);
      }

      const filteredEdges = rawEdges.filter((edge: any) => {
        if (edge.type === 'route') {
          if (!includeRoutesOption) return false;
          if (normalizedSelectedModes.length === 0) return true;
          return edge.transport_mode ? selectedModeSet.has(edge.transport_mode) : false;
        }
        if (edge.type === 'supplies') return includeSuppliers;
        return true;
      });

      const requiredFacilityIds = new Set<string>();
      filteredEdges.forEach((edge: any) => {
        requiredFacilityIds.add(edge.source);
        requiredFacilityIds.add(edge.target);
      });

      const filteredNodes = (data.nodes ?? []).filter((node: any) => {
        if (node.type === 'supplier') return includeSuppliers;
        if (node.type === 'facility') {
          if (includeFacilities) return true;
          return requiredFacilityIds.has(node.id);
        }
        return true;
      });

      const themedNodes = filteredNodes.map((node: any) => {
        if (node.type === 'supplier') {
          return { ...node, color: graphPalette.supplier };
        }
        if (node.type === 'facility') {
          return { ...node, color: graphPalette.facility };
        }
        return { ...node, color: graphPalette.facility };
      });

      setGraph({ nodes: themedNodes, edges: filteredEdges });
      setGraphEmpty(filteredNodes.length === 0);
    } catch (e) {
      const err = e as AxiosError<{ detail?: string }>;
      const detail = err.response?.data?.detail;
      const message = detail || (err.message === 'Network Error' ? 'Unable to reach graph API. Is the backend running?' : err.message) || 'Failed to load graph.';
      setGraphError(message ?? 'Failed to load graph.');
      setGraph({ nodes: [], edges: [] });
      setGraphEmpty(true);
    } finally {
      setLoading(false);
    }
  }

  async function loadNeighbors(nodeId: string) {
    if (!orgId) return;
    const res = await apiClient.get('/api/kg/neighbors', { params: { org_id: orgId, node_id: nodeId, hops: 1 } });
    const addNodes = new Map(graph.nodes.map(n => [n.id, n]));
    res.data.nodes.forEach((n: any) => addNodes.set(n.id, { ...n, type: n.type || (n.tier_level ? 'supplier' : 'facility') }));
    const addEdges = [...graph.edges];
    res.data.edges.forEach((e: any) => {
      if (!addEdges.find(x => (x.id||`${x.type}:${x.source}->${x.target}`) === (e.id||`${e.type}:${e.source}->${e.target}`))) addEdges.push(e);
    });
    setGraph({ nodes: Array.from(addNodes.values()), edges: addEdges });
  }

  async function loadAnalytics() {
    if (!orgId || analyticsLoading) return;
    setAnalyticsLoading(true);
    setAnalyticsError(null);
    try {
      await apiClient.post('/api/kg/analytics/graphs/build', null, { params: { org_id: orgId } });

      const [
        betRes,
        prRes,
        commRes,
        routePrRes,
        psRes,
        eoRes,
        statusRes
      ] = await Promise.all([
        apiClient.get('/api/kg/analytics/facilities/betweenness', { params: { org_id: orgId, limit: 15 } }),
        apiClient.get('/api/kg/analytics/facilities/pagerank', { params: { org_id: orgId, limit: 15 } }),
        apiClient.get('/api/kg/analytics/facilities/communities', { params: { org_id: orgId } }),
        apiClient.get('/api/kg/analytics/routes/pagerank', { params: { org_id: orgId, limit: 15 } }),
        apiClient.post('/api/kg/analytics/sequences/prefixspan', null, { params: { org_id: orgId, min_support: 2, max_len: 5, top_k: 15 } }),
        apiClient.get('/api/kg/analytics/eo/hotspots', { params: { org_id: orgId, limit: 10 } }),
        apiClient.get('/api/kg/analytics/graphs/status', { params: { org_id: orgId } })
      ]);
      setFacilityBetweenness(betRes.data || []);
      setFacilityPagerank(prRes.data || []);
      setFacilityCommunities(commRes.data || []);
      setRoutePagerank(routePrRes.data || []);
      setPrefixSpanPatterns(psRes.data?.patterns || []);
      setEoHotspots(eoRes.data || []);
      setGraphStatus(statusRes.data);
    } catch (e) {
      console.error('Analytics load error:', e);
      const err = e as AxiosError<{ detail?: string }>;
      const detail = err.response?.data?.detail;
      const message = detail || (err.message === 'Network Error' ? 'Unable to reach analytics API. Is the backend running?' : err.message) || 'Failed to load analytics.';
      setAnalyticsError(message ?? 'Failed to load analytics.');
      setFacilityBetweenness([]);
      setFacilityPagerank([]);
      setFacilityCommunities([]);
      setRoutePagerank([]);
      setPrefixSpanPatterns([]);
      setEoHotspots([]);
      setGraphStatus(null);
    } finally {
      setAnalyticsLoading(false);
    }
  }

  async function findPath() {
    if (!orgId || !srcFacility || !dstFacility) return;
    setPathLoading(true);
    try {
      const res = await apiClient.post('/api/kg/analytics/shortest-path', null, {
        params: { org_id: orgId, srcNode: srcFacility, dstNode: dstFacility, weight: pathWeight }
      });
      setPathResult(res.data);
    } catch (e) {
      console.error('Path find error:', e);
      setPathResult(null);
    } finally {
      setPathLoading(false);
    }
  }

  useEffect(() => {
    if (activeTab === 'analytics' && !analyticsLoading && facilityBetweenness.length === 0) {
      loadAnalytics();
    }
  }, [activeTab, orgId]);

  if (!orgId) {
    return (
      <div>
        <DashboardHeader />
        <main className="min-h-screen w-full px-4 md:px-6 lg:px-8 pt-24 pb-8">
          <div className="text-center">
            <p className="text-muted-foreground">Please select an organization to view analytics.</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div>
      <DashboardHeader />
      <main className="min-h-screen w-full px-4 md:px-6 lg:px-8 pt-24 pb-32">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="graph">
              <Network className="w-4 h-4 mr-2" />
              Network Graph
            </TabsTrigger>
            <TabsTrigger value="analytics">
              <TrendingUp className="w-4 h-4 mr-2" />
              Analytics
            </TabsTrigger>
          </TabsList>

          <TabsContent value="graph" className="space-y-6">
            {graphError && (
              <Alert variant="destructive" className="border-destructive/40 bg-destructive/10">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Unable to load the graph</AlertTitle>
                <AlertDescription>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <span className="text-sm">{graphError}</span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => void fetchGraph()}
                      disabled={loading}
                    >
                      Retry
                    </Button>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            <div className="flex items-start gap-6">
              <Card className="w-80 flex-shrink-0 border-dashed border-amber-200/60 bg-amber-50/40 dark:border-emerald-900/40 dark:bg-emerald-950/40">
                <CardHeader className="space-y-1">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Filter className="h-4 w-4" />
                    Filters
                  </CardTitle>
                  <CardDescription>Shape the network view</CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="space-y-1.5">
                    <Label htmlFor="graph-search">Search</Label>
                    <Input
                      id="graph-search"
                      placeholder="Facility or supplier"
                      value={q}
                      onChange={e=>setQ(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">Matches against IDs or names.</p>
                  </div>
                  <div className="space-y-2">
                    <Label>Transport modes</Label>
                    <ToggleGroup
                      type="multiple"
                      value={modes}
                      onValueChange={setModes}
                      className="flex flex-wrap gap-2"
                    >
                      {modeOptionsToRender.map((mode) => (
                        <ToggleGroupItem
                          key={mode.value}
                          value={mode.value}
                          className="data-[state=on]:bg-primary data-[state=on]:text-primary-foreground text-xs"
                          aria-label={mode.label}
                        >
                          <div className="flex flex-col text-left">
                            <span className="font-medium">{mode.label}</span>
                            <span className="text-[10px] text-muted-foreground">{mode.hint}</span>
                          </div>
                        </ToggleGroupItem>
                      ))}
                    </ToggleGroup>
                    <p className="text-xs text-muted-foreground">
                      {modes.length ? `Filtering ${modes.length} transport mode${modes.length === 1 ? '' : 's'}.` : 'All transport modes included.'}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label htmlFor="min-distance">Min distance (km)</Label>
                      <Input
                        id="min-distance"
                        type="number"
                        inputMode="decimal"
                        placeholder="0"
                        value={minKm}
                        onChange={e=>setMinKm(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="max-distance">Max distance (km)</Label>
                      <Input
                        id="max-distance"
                        type="number"
                        inputMode="decimal"
                        placeholder="1500"
                        value={maxKm}
                        onChange={e=>setMaxKm(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <Checkbox id="filter-facilities" checked={includeFac} onCheckedChange={checked => setIncludeFac(Boolean(checked))} />
                      <div className="space-y-1">
                        <Label htmlFor="filter-facilities">Facilities</Label>
                        <p className="text-xs text-muted-foreground">Include facility nodes in the graph.</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <Checkbox id="filter-routes" checked={includeRoutes} onCheckedChange={checked => setIncludeRoutes(Boolean(checked))} />
                      <div className="space-y-1">
                        <Label htmlFor="filter-routes">Routes</Label>
                        <p className="text-xs text-muted-foreground">Show transportation legs between facilities.</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <Checkbox id="filter-suppliers" checked={includeSup} onCheckedChange={checked => setIncludeSup(Boolean(checked))} />
                      <div className="space-y-1">
                        <Label htmlFor="filter-suppliers">Suppliers</Label>
                        <p className="text-xs text-muted-foreground">Show supplier relationships to facilities.</p>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Button onClick={() => void fetchGraph()} disabled={loading || !orgId} className="gap-2 sm:flex-1">
                      {loading ? (
                        'Applying…'
                      ) : (
                        <>
                          <Filter className="h-4 w-4" />
                          Apply filters
                        </>
                      )}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      className="gap-2 sm:w-auto"
                      onClick={resetFilters}
                      disabled={loading}
                    >
                      <RefreshCcw className="h-4 w-4" />
                      Reset
                    </Button>
                  </div>
                </CardContent>
              </Card>
              <Card className="flex-1">
                <CardHeader className="pb-2">
                  <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                    <div className="space-y-1">
                      <CardTitle>Network Graph</CardTitle>
                      <CardDescription>Drag, zoom, and expand neighbors</CardDescription>
                      <div className="flex flex-wrap gap-2 pt-1">
                        {(modes.length ? modes : ['all']).map(mode => (
                          <Badge key={mode} variant={mode === 'all' ? 'outline' : 'secondary'} className="text-xs">
                            {mode === 'all' ? 'All transport modes' : modeLabelMap[mode] ?? mode}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <div className="flex flex-col items-start gap-1 text-xs text-muted-foreground lg:items-end">
                      <Badge variant="outline">{graph.nodes.length} nodes</Badge>
                      <span>{routeEdgeCount} routes · {supplierEdgeCount} supplier links</span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div ref={containerRef} className="relative h-[600px] w-full border rounded overflow-hidden">
                    <div className="flex justify-end gap-2 p-2">
                      <Button variant="outline" size="sm" onClick={()=>{ const cy = cyRef.current; if(cy){ cy.fit(undefined, 30); } }}>Fit</Button>
                      <Button variant="outline" size="sm" onClick={()=>{ const cy = cyRef.current; if(cy){ cy.layout({ name:'cose-bilkent', animate:true, padding:50, nodeDimensionsIncludeLabels:true, idealEdgeLength:150, nodeRepulsion:80000 }).run(); } }}>Re-layout</Button>
                    </div>
                    {graphEmpty && !loading && !graphError ? (
                      <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
                        <p>No nodes match the current filters.</p>
                        <p className="text-xs">Try widening transport modes or distance range.</p>
                      </div>
                    ) : (
                      <CytoscapeComponent
                        cy={(cy: any)=>{ cyRef.current = cy; cy.off('tap'); cy.on('tap','node',(evt: any)=>{ const id = evt.target.id(); void loadNeighbors(id); }); }}
                        elements={cyElements}
                        style={{ width: '100%', height: '100%' }}
                        layout={{ name: 'cose-bilkent' }}
                        stylesheet={graphStyles} />
                    )}
                    {loading && (
                      <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-background/70 text-sm font-medium">
                        Refreshing graph…
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            {analyticsError && (
              <Alert variant="destructive" className="border-destructive/40 bg-destructive/10">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Unable to load analytics</AlertTitle>
                <AlertDescription>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <span className="text-sm">{analyticsError}</span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => void loadAnalytics()}
                      disabled={analyticsLoading}
                    >
                      Retry
                    </Button>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {analyticsLoading && (
              <div className="flex items-center justify-center py-12">
                <div className="text-center space-y-3">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
                  <p className="text-sm text-muted-foreground">Building graphs and loading analytics...</p>
                </div>
              </div>
            )}

            {!analyticsLoading && !analyticsError && (
              <>
                {/* KPI Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <Card>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardDescription>Top Chokepoint</CardDescription>
                        <AlertTriangle className="w-4 h-4 text-orange-500" />
                      </div>
                    </CardHeader>
                    <CardContent>
                      {facilityBetweenness[0] ? (
                        <>
                          <div className="text-2xl font-bold">{facilityBetweenness[0].facilityId}</div>
                          <p className="text-xs text-muted-foreground">Score: {facilityBetweenness[0].score.toFixed(2)}</p>
                        </>
                      ) : <Skeleton className="h-8 w-20" />}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardDescription>Top Hub</CardDescription>
                        <TrendingUp className="w-4 h-4 text-blue-500" />
                      </div>
                    </CardHeader>
                    <CardContent>
                      {facilityPagerank[0] ? (
                        <>
                          <div className="text-2xl font-bold">{facilityPagerank[0].facilityId}</div>
                          <p className="text-xs text-muted-foreground">Score: {facilityPagerank[0].score.toFixed(3)}</p>
                        </>
                      ) : <Skeleton className="h-8 w-20" />}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardDescription>Top Emission Pattern</CardDescription>
                        <Leaf className="w-4 h-4 text-green-600" />
                      </div>
                    </CardHeader>
                    <CardContent>
                      {prefixSpanPatterns[0] ? (
                        <>
                          <div className="text-2xl font-bold">{prefixSpanPatterns[0].emission_sum.toFixed(1)} kg</div>
                          <p className="text-xs text-muted-foreground">{prefixSpanPatterns[0].pattern.join(' → ')}</p>
                        </>
                      ) : <Skeleton className="h-8 w-20" />}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardDescription>AQI Alerts</CardDescription>
                        <Wind className="w-4 h-4 text-red-500" />
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{eoHotspots.filter(h => h.aqi >= 100).length}</div>
                      <p className="text-xs text-muted-foreground">Facilities with AQI ≥100</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Facility Analytics */}
                <Card>
                  <CardHeader>
                    <CardTitle>Facility Analytics</CardTitle>
                    <CardDescription>Structural importance and risk scores</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Facility</TableHead>
                          <TableHead>Betweenness</TableHead>
                          <TableHead>PageRank</TableHead>
                          <TableHead>Community</TableHead>
                          <TableHead>Risk</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {facilityBetweenness.slice(0, 10).map((f, i) => {
                          const pr = facilityPagerank.find(p => p.facilityId === f.facilityId);
                          const comm = facilityCommunities.find(c => c.members.includes(f.facilityId));
                          const isHighRisk = i < Math.ceil(facilityBetweenness.length * 0.1);
                          return (
                            <TableRow key={f.facilityId}>
                              <TableCell className="font-medium">{f.facilityId}</TableCell>
                              <TableCell>{f.score.toFixed(2)}</TableCell>
                              <TableCell>{pr ? pr.score.toFixed(3) : '-'}</TableCell>
                              <TableCell>{comm ? comm.communityId : '-'}</TableCell>
                              <TableCell>{isHighRisk && <Badge variant="destructive" className="text-xs">High Risk</Badge>}</TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                {/* Route Analytics */}
                <Card>
                  <CardHeader>
                    <CardTitle>Route Analytics</CardTitle>
                    <CardDescription>Important corridors by PageRank</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Route ID</TableHead>
                          <TableHead>PageRank Score</TableHead>
                          <TableHead>Importance</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {routePagerank.slice(0, 10).map((r, i) => (
                          <TableRow key={r.routeId}>
                            <TableCell className="font-medium">{r.routeId}</TableCell>
                            <TableCell>{r.score.toFixed(3)}</TableCell>
                            <TableCell>
                              {i < 3 && <Badge className="text-xs">Critical</Badge>}
                              {i >= 3 && i < 6 && <Badge variant="secondary" className="text-xs">High</Badge>}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                {/* PrefixSpan Patterns */}
                <Card>
                  <CardHeader>
                    <CardTitle>Frequent Emission Patterns</CardTitle>
                    <CardDescription>Routes that occur often and accumulate high emissions</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Pattern</TableHead>
                          <TableHead>Occurrences</TableHead>
                          <TableHead>Total Emissions</TableHead>
                          <TableHead>Avg per Trip</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {prefixSpanPatterns.map((p, i) => (
                          <TableRow key={i}>
                            <TableCell className="font-mono text-xs">{p.pattern.join(' → ')}</TableCell>
                            <TableCell>{p.support_count}</TableCell>
                            <TableCell className="font-semibold">{p.emission_sum.toFixed(2)} kg CO₂</TableCell>
                            <TableCell>{p.emission_avg?.toFixed(2) || '-'} kg</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                {/* Path Comparison */}
                <Card>
                  <CardHeader>
                    <CardTitle>Path Comparison</CardTitle>
                    <CardDescription>Find optimal routes between facilities</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                      <Input placeholder="Source (e.g., F001)" value={srcFacility} onChange={e=>setSrcFacility(e.target.value)} />
                      <Input placeholder="Destination (e.g., F003)" value={dstFacility} onChange={e=>setDstFacility(e.target.value)} />
                      <Select value={pathWeight} onValueChange={setPathWeight}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="distance">Distance (km)</SelectItem>
                          <SelectItem value="duration">Duration (hours)</SelectItem>
                          <SelectItem value="emission">Emission (kg CO₂)</SelectItem>
                        </SelectContent>
                      </Select>
                      <Button onClick={findPath} disabled={pathLoading || !srcFacility || !dstFacility}>
                        {pathLoading ? 'Finding...' : 'Find Path'}
                      </Button>
                    </div>
                    {pathResult && pathResult.facilityIds.length > 0 && (
                      <div className="p-4 border rounded bg-muted/30">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium">Path Found</span>
                          <Badge>{pathResult.weight}</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mb-1">Route: {pathResult.facilityIds.join(' → ')}</p>
                        <p className="text-lg font-semibold">Total Cost: {pathResult.totalCost.toFixed(2)} {pathResult.weight === 'distance' ? 'km' : pathResult.weight === 'duration' ? 'hours' : 'kg CO₂'}</p>
                      </div>
                    )}
                    {pathResult && pathResult.facilityIds.length === 0 && (
                      <p className="text-sm text-muted-foreground">No path found between facilities.</p>
                    )}
                  </CardContent>
                </Card>

                {/* EO Hotspots */}
                <Card>
                  <CardHeader>
                    <CardTitle>Environmental Hotspots</CardTitle>
                    <CardDescription>Facilities with high air quality index</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Facility</TableHead>
                          <TableHead>Latest AQI</TableHead>
                          <TableHead>3-Month Trend</TableHead>
                          <TableHead>Status</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {eoHotspots.map((h) => (
                          <TableRow key={h.facility_id}>
                            <TableCell className="font-medium">{h.facility_id}</TableCell>
                            <TableCell className="font-semibold">{h.aqi.toFixed(1)}</TableCell>
                            <TableCell className={h.trend3m > 0 ? 'text-red-600' : 'text-green-600'}>
                              {h.trend3m > 0 ? '+' : ''}{h.trend3m.toFixed(1)}
                            </TableCell>
                            <TableCell>
                              {h.aqi >= 100 && <Badge variant="destructive" className="text-xs">Alert</Badge>}
                              {h.aqi < 100 && h.aqi >= 50 && <Badge variant="secondary" className="text-xs">Moderate</Badge>}
                              {h.aqi < 50 && <Badge variant="outline" className="text-xs">Good</Badge>}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                {/* Graph Health */}
                {graphStatus && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Graph Health</CardTitle>
                      <CardDescription>Status of projected graphs</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {graphStatus.graphs?.map((g: any) => (
                          <div key={g.graphName} className="p-3 border rounded">
                            <p className="text-sm font-medium mb-1">{g.graphName.includes('facility') ? 'Facility Graph' : 'Route Graph'}</p>
                            <p className="text-xs text-muted-foreground">{g.nodeCount} nodes, {g.relationshipCount} relationships</p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
