'use client';

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { pct, SiteDetail } from '@/lib/api';

const TERM_LABEL: Record<string, string> = { rain: 'Forecast rain', wet_ground: 'Wet ground', low_lying: 'Low-lying', high_ground: 'High ground' };

export default function SiteCard({ d, asOf, onClose }: { d: SiteDetail; asOf: string; onClose: () => void }) {
  const start = new Date(asOf + 'T00:00:00');
  const days = d.forecast_daily_mm[0].map((_, i) => {
    const dt = new Date(start);
    dt.setDate(start.getDate() + i + 1);
    const row: Record<string, number | string> = { day: `${dt.getDate()} ${dt.toLocaleString('en', { month: 'short' })}` };
    d.forecast_daily_mm.forEach((m, k) => { row[k === 0 ? 'Latest run' : `Run −${k}d`] = m[i]; });
    return row;
  });
  const terms = Object.entries(d.model_terms_at_median_forecast).filter(([k]) => k in TERM_LABEL);

  return (
    <div className="card w-[380px] bg-paper-2/95 p-4 shadow-lg backdrop-blur">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="eyebrow">Site</p>
          <p className="font-display text-lg font-bold leading-tight">{d.name}</p>
          <p className="text-xs text-subtle">{d.estate} · {d.elevation_m.toFixed(0)} m elevation</p>
        </div>
        <button onClick={onClose} className="rounded px-2 text-subtle hover:bg-paper-3" aria-label="Close">×</button>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-paper-3 p-2"><p className="font-display text-xl font-bold text-hazard-dark">{pct(d.simulated_p_down)}</p><p className="text-[11px] text-subtle">P(down)</p></div>
        <div className="rounded-lg bg-paper-3 p-2"><p className="font-display text-xl font-bold">{d.simulated_median_downtime_days || '–'}d</p><p className="text-[11px] text-subtle">median downtime</p></div>
        <div className="rounded-lg bg-paper-3 p-2"><p className="font-display text-xl font-bold">{Math.round(d.antecedent_14d_mm)}</p><p className="text-[11px] text-subtle">mm, last 14 days</p></div>
      </div>
      <p className="mt-3 text-xs font-semibold">Forecast daily rain (mm), three successive runs</p>
      <div>
        <ResponsiveContainer width="100%" height={144}>
          <BarChart data={days} margin={{ top: 4, right: 0, bottom: 0, left: -24 }}>
            <CartesianGrid stroke="#E8E4D8" vertical={false} />
            <XAxis dataKey="day" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend wrapperStyle={{ fontSize: 10 }} />
            <Bar isAnimationActive={false} dataKey="Latest run" fill="#D9622B" />
            <Bar isAnimationActive={false} dataKey="Run −1d" fill="#E8894F" />
            <Bar isAnimationActive={false} dataKey="Run −2d" fill="#F2D9C4" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs font-semibold">Why (contributions to log-odds, prior model)</p>
      <div className="mt-1 space-y-1">
        {terms.map(([k, v]) => (
          <div key={k} className="flex items-center gap-2 text-xs">
            <span className="w-24 text-subtle">{TERM_LABEL[k]}</span>
            <span className="h-2 flex-1 rounded bg-paper-3">
              <span className={`block h-2 rounded ${v >= 0 ? 'bg-hazard' : 'bg-water'}`} style={{ width: `${Math.min(100, Math.abs(v) * 25)}%` }} />
            </span>
            <span className="w-10 text-right font-mono">{v > 0 ? '+' : ''}{v}</span>
          </div>
        ))}
      </div>
      <p className="mt-3 text-[11px] text-subtle">
        Hindcast check: {d.observed_max_3day_mm} mm actually fell in the worst 3 days (reanalysis). Forecasts: Open-Meteo
        archived runs.
      </p>
    </div>
  );
}
