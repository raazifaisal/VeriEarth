export const API = process.env.NEXT_PUBLIC_VERI_API ?? 'http://localhost:8080';

export type Quadrant = 'act_now' | 'build_buffers' | 'monitor' | 'low';

export interface SiteRow {
  id: string;
  name: string;
  kind: 'own_plant' | 'supplier' | 'customer' | 'port' | 'airport';
  estate: string;
  lat: number;
  lon: number;
  alternate: boolean;
  overseas: boolean;
  category: string;
  p_down: number | null;
  elevation_m: number | null;
  forecast_max3_mm: number | null;
  quadrant: Quadrant | null;
}

export interface Edge {
  from: string;
  to: string;
  kind: 'supplies' | 'alternate' | 'delivers';
  part?: string;
  product?: string;
}

export interface CritRow {
  supplier: string;
  name: string;
  estate: string;
  parts: string[];
  time_to_survive_days: number;
  has_alternate: boolean;
  structural_rar_thb: number;
  exposure_p_down: number;
  median_downtime_days: number;
  live_expected_rar_thb: number;
  live_p90_rar_thb: number;
  quadrant: Quadrant;
}

export interface Assessment {
  overview: {
    as_of: string;
    company: string;
    horizon_days: number;
    warning_days: number;
    revenue_at_risk: { expected_revenue_at_risk_thb: number; p50_thb: number; p90_thb: number; p_any_loss: number };
    orders: { id: string; customer: string; product: string; qty: number; due: string; p_late: number }[];
    joint_failure: { primary: string; alternate: string; p_both_down: number }[];
  };
  criticality: CritRow[];
  sites: SiteRow[];
  edges: Edge[];
  hazard_source: string;
}

export interface PlanSummary {
  plan_id: string;
  name: string;
  objective: string;
  total_cost_million_thb: number;
  spend_million_thb: number;
  lost_revenue_million_thb: number;
  co2_tonnes: number;
  coverage: number;
  actions: Record<string, { option: string; kind: string; supplier: string; mode: string; units: number }[]>;
  verification: { ok: boolean; issues: string[] };
  detail?: PlanDetail;
}

export interface PlanOption {
  key: string;
  kind: string;
  supplier: string;
  mode: string;
  lead_days: number;
  capacity_units: number;
  unit_cost_thb: number;
  unit_co2_kg: number;
  note: string;
}

export interface PlanDetail {
  needs: Record<string, { supplier: string; units: number; shortage_days_p80: number; starts_in_days: number; options: PlanOption[] }>;
}

export interface PlansResponse {
  plans: PlanSummary[];
  timing: {
    warning_days: number;
    decide_now: { total_cost_million_thb: number; co2_tonnes: number; coverage: number } | null;
    decide_after_event: { total_cost_million_thb: number; co2_tonnes: number; coverage: number } | null;
  };
  pareto: { co2_cap_kg: number; co2_kg: number; total_cost_thb: number; coverage: number }[];
}

export interface SiteDetail {
  site: string;
  name: string;
  estate: string;
  elevation_m: number;
  antecedent_14d_mm: number;
  forecast_max_3day_mm_by_member: number[];
  observed_max_3day_mm: number;
  forecast_daily_mm: number[][];
  model_terms_at_median_forecast: Record<string, number>;
  simulated_p_down: number;
  simulated_median_downtime_days: number;
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`, { cache: 'no-store' });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export const api = {
  assessment: (asOf: string) => get<Assessment>(`/api/v1/assessment?as_of=${asOf}`),
  plans: (asOf: string) => get<PlansResponse>(`/api/v1/plans?as_of=${asOf}`),
  site: (id: string, asOf: string) => get<SiteDetail>(`/api/v1/site/${id}?as_of=${asOf}`),
  health: () => get<{ status: string; gemini_configured: boolean; model: string }>(`/api/v1/health`),
  adjust: async (body: { plan_id: string; part_at_plant: string; option_key: string; units: number }) => {
    const r = await fetch(`${API}/api/v1/plans/adjust`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json() as Promise<PlanSummary>;
  },
};

export const fmtM = (thb: number) => `฿${(thb / 1e6).toFixed(1)}M`;
export const pct = (x: number) => `${Math.round(x * 100)}%`;

export const QUADRANT_LABEL: Record<Quadrant, string> = {
  act_now: 'Act now',
  build_buffers: 'Build buffers',
  monitor: 'Monitor',
  low: 'Low',
};
