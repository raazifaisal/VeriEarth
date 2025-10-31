'use client';

import { useOrganization } from '@/lib/organization-context';
import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/lib/api';
import { DashboardHeader } from '@/components/dashboard-header';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import {
  Factory,
  Package,
  Route as RouteIcon,
  Cloud,
  Wind,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area, BarChart, Bar } from 'recharts';
const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444'];

function KPICard({
  title,
  value,
  icon: Icon,
  suffix = '',
  loading = false,
  trend,
  trendValue,
}: {
  title: string;
  value: number | string;
  icon: any;
  suffix?: string;
  loading?: boolean;
  trend?: 'up' | 'down';
  trendValue?: string;
}) {
  return (
    <Card className="transition-all hover:shadow-md">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className="h-8 w-8 rounded-md bg-muted flex items-center justify-center">
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <>
            <div className="flex items-baseline gap-2 mb-2">
              {value === 0 || value === null || value === undefined ? (
                <div className="text-lg md:text-xl text-muted-foreground italic">No data</div>
              ) : (
                <>
                  <div className="text-2xl md:text-3xl font-bold">
                    {typeof value === 'number' ? value.toLocaleString() : value}
                  </div>
                  {suffix && <span className="text-sm text-muted-foreground">{suffix}</span>}
                </>
              )}
            </div>
            {trend && trendValue && value !== 0 && value !== null && value !== undefined && (
              <div className="flex items-center gap-1 text-xs">
                {trend === 'up' ? (
                  <>
                    <Badge variant="secondary" className="gap-1 bg-red-100 text-red-700 hover:bg-red-100">
                      <TrendingUp className="h-3 w-3" />
                      {trendValue}
                    </Badge>
                  </>
                ) : (
                  <>
                    <Badge variant="secondary" className="gap-1 bg-green-100 text-green-700 hover:bg-green-100">
                      <TrendingDown className="h-3 w-3" />
                      {trendValue}
                    </Badge>
                  </>
                )}
                <span className="text-muted-foreground">vs last month</span>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { orgId } = useOrganization();

  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ['dashboard-kpis', orgId],
    queryFn: () => dashboardApi.getKPIs(orgId as string),
    enabled: !!orgId,
  });

  const { data: emissionsTrendRaw, isLoading: emissionsLoading } = useQuery({
    queryKey: ['dashboard-emissions-trend', orgId],
    queryFn: () => dashboardApi.getEmissionsTrend(orgId as string),
    enabled: !!orgId,
  });

  const { data: transportDistributionRaw, isLoading: transportLoading } = useQuery({
    queryKey: ['dashboard-transport-distribution', orgId],
    queryFn: () => dashboardApi.getTransportDistribution(orgId as string),
    enabled: !!orgId,
  });

  const { data: facilitiesAqi = [] } = useQuery({
    queryKey: ['dashboard-facilities-aqi', orgId],
    queryFn: async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/dashboard/facilities-aqi?org_id=${orgId}`, {
        credentials: 'include',
      });
      return res.json();
    },
    enabled: !!orgId,
  });

  const poorAqiCount = (facilitiesAqi || []).filter((f: any) => (f.latest_aqi || 0) >= 120).length;

  const emissionsTrend = (emissionsTrendRaw || []).map((r: any) => ({
    month: new Date(r.period_start).toLocaleDateString(undefined, { month: 'short', year: '2-digit' }),
    emissions: r.emissions_kg,
  }));

  const transportDistribution = (transportDistributionRaw || []).map((r: any) => ({
    mode: r.transport_mode,
    count: r.shipments,
    percentage: Math.round((r.share_shipments || 0) * 100),
  }));

  if (!orgId) {
    return (
      <div>
        <DashboardHeader />
        <main className="min-h-screen w-full px-4 md:px-6 lg:px-8 pt-24 pb-8">
          <div className="text-center">
            <p className="text-muted-foreground">Please select an organization to view the dashboard.</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div>
      <DashboardHeader />
      <main className="min-h-screen w-full px-4 md:px-6 lg:px-8 pt-24 pb-32 space-y-6 md:space-y-8">
        <div>
          <h1 className="text-2xl md:text-3xl lg:text-4xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-2 text-sm md:text-base">
            Overview of your supply chain carbon footprint and air quality metrics
          </p>
        </div>

        <div className="grid gap-3 md:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          <KPICard
            title="Total Facilities"
            value={kpis?.total_facilities || 0}
            icon={Factory}
            loading={kpisLoading}
            trend="up"
            trendValue="+12%"
          />
          <KPICard
            title="Total Shipments"
            value={kpis?.total_shipments || 0}
            icon={Package}
            loading={kpisLoading}
            trend="up"
            trendValue="+8%"
          />
          <KPICard
            title="Total Routes"
            value={(kpis as any)?.active_routes ?? (kpis as any)?.total_routes ?? 0}
            icon={RouteIcon}
            loading={kpisLoading}
            trend="down"
            trendValue="-5%"
          />
          <KPICard
            title="Total CO₂ Emissions"
            value={(kpis as any)?.total_emissions_kg ?? (kpis as any)?.total_co2_emissions ?? 0}
            icon={Cloud}
            suffix="kg"
            loading={kpisLoading}
            trend="up"
            trendValue="+9%"
          />
          <KPICard
            title="Average AQI"
            value={(((kpis as any)?.avg_aqi_recent ?? (kpis as any)?.average_aqi) ? Number(((kpis as any)?.avg_aqi_recent ?? (kpis as any)?.average_aqi)).toFixed(1) : 0) as any}
            icon={Wind}
            loading={kpisLoading}
            trend="down"
            trendValue="-12%"
          />
          <KPICard
            title="Poor Air Quality"
            value={poorAqiCount || 0}
            icon={AlertTriangle}
            suffix="facilities"
            loading={kpisLoading}
            trend="down"
            trendValue="-15%"
          />
        </div>

        <Separator className="my-6" />

        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="grid w-full grid-cols-2 lg:grid-cols-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="emissions">Emissions</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
              <Card className="overflow-hidden border-2 hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg md:text-xl">CO₂ Emissions Trend</CardTitle>
                      <CardDescription className="mt-1">Monthly emissions overview</CardDescription>
                    </div>
                    <Badge variant="outline" className="ml-auto">
                      <TrendingUp className="h-3 w-3 mr-1" />
                      Active
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={emissionsTrend ?? []}>
                      <defs>
                        <linearGradient id="colorEmissions" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="month" className="text-sm" />
                      <YAxis className="text-sm" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--background))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '6px',
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="emissions"
                        stroke="#3B82F6"
                        strokeWidth={2}
                        fill="url(#colorEmissions)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card className="overflow-hidden border-2 hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg md:text-xl">Transport Mode Distribution</CardTitle>
                      <CardDescription className="mt-1">Shipment breakdown by mode</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={transportDistribution ?? []}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ mode, percentage }) => `${mode} (${percentage}%)`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="count"
                      >
                        {(transportDistribution ?? []).map((entry: any, index: number) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--background))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '6px',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="emissions" className="space-y-4">
            <Card className="overflow-hidden border-2">
              <CardHeader>
                <div>
                  <CardTitle className="text-lg md:text-xl">Detailed Emissions Analysis</CardTitle>
                  <CardDescription className="mt-1">Breakdown of emissions by transport mode</CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={transportDistribution ?? []}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="mode" className="text-sm" />
                    <YAxis className="text-sm" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '6px',
                      }}
                    />
                    <Bar dataKey="count" fill="#3B82F6" radius={[8, 8, 0, 0]}>
                      {(transportDistribution ?? []).map((entry: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analytics" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Recent Activity</CardTitle>
                  <CardDescription>Latest supply chain updates</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-start gap-4">
                      <div className="rounded-full bg-blue-100 p-2">
                        <Package className="h-4 w-4 text-blue-600" />
                      </div>
                      <div className="flex-1 space-y-1">
                        <p className="text-sm font-medium">New shipment created</p>
                        <p className="text-xs text-muted-foreground">2 hours ago</p>
                      </div>
                    </div>
                    <Separator />
                    <div className="flex items-start gap-4">
                      <div className="rounded-full bg-green-100 p-2">
                        <Factory className="h-4 w-4 text-green-600" />
                      </div>
                      <div className="flex-1 space-y-1">
                        <p className="text-sm font-medium">Facility enriched with EO data</p>
                        <p className="text-xs text-muted-foreground">5 hours ago</p>
                      </div>
                    </div>
                    <Separator />
                    <div className="flex items-start gap-4">
                      <div className="rounded-full bg-yellow-100 p-2">
                        <AlertTriangle className="h-4 w-4 text-yellow-600" />
                      </div>
                      <div className="flex-1 space-y-1">
                        <p className="text-sm font-medium">High AQI detected</p>
                        <p className="text-xs text-muted-foreground">1 day ago</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Quick Actions</CardTitle>
                  <CardDescription>Common tasks</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <button className="w-full flex items-center justify-between rounded-lg border p-3 hover:bg-muted transition-colors">
                    <span className="text-sm font-medium">Enrich Facilities</span>
                    <ArrowUpRight className="h-4 w-4" />
                  </button>
                  <button className="w-full flex items-center justify-between rounded-lg border p-3 hover:bg-muted transition-colors">
                    <span className="text-sm font-medium">View Analytics</span>
                    <ArrowUpRight className="h-4 w-4" />
                  </button>
                  <button className="w-full flex items-center justify-between rounded-lg border p-3 hover:bg-muted transition-colors">
                    <span className="text-sm font-medium">Export Report</span>
                    <ArrowUpRight className="h-4 w-4" />
                  </button>
                  <button className="w-full flex items-center justify-between rounded-lg border p-3 hover:bg-muted transition-colors">
                    <span className="text-sm font-medium">Configure Alerts</span>
                    <ArrowUpRight className="h-4 w-4" />
                  </button>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
