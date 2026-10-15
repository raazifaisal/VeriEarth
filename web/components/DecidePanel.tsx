'use client';

import { useMemo, useState } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, PlansResponse, PlanSummary, pct } from '@/lib/api';

const KIND_LABEL: Record<string, string> = { prebuild: 'Pre-build', alternate: 'Alternate', unmet: 'Accept shortage' };
const MODE_LABEL: Record<string, string> = { road_truck: 'truck', sea_container: 'sea', air_cargo: 'air', '-': '' };

function Verdict({ v }: { v: PlanSummary['verification'] }) {
  return v.ok ? (
    <span className="rounded-full bg-water-wash px-2 py-0.5 text-[11px] font-semibold text-water">Verifier: pass</span>
  ) : (
    <span className="rounded-full bg-hazard px-2 py-0.5 text-[11px] font-semibold text-white">Verifier: fail</span>
  );
}

export default function DecidePanel({ data }: { data: PlansResponse }) {
  const [open, setOpen] = useState<string | null>(data.plans[0]?.plan_id ?? null);
  const [edit, setEdit] = useState<{ need: string; option: string; units: number }>({ need: '', option: '', units: 0 });
  const [edited, setEdited] = useState<PlanSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const base = data.plans[0];
  const needs = base?.detail?.needs ?? {};
  const needKeys = Object.keys(needs);
  const opts = useMemo(() => (edit.need ? needs[edit.need]?.options.filter((o) => o.kind !== 'unmet') ?? [] : []), [edit.need, needs]);
  const t = data.timing;

  async function tryEdit() {
    if (!base || !edit.need || !edit.option || edit.units <= 0) return;
    setBusy(true);
    try {
      setEdited(await api.adjust({ plan_id: base.plan_id, part_at_plant: edit.need, option_key: edit.option, units: edit.units }));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="h-full space-y-4 overflow-y-auto pr-1">
      {t.decide_now && t.decide_after_event && (
        <div className="card overflow-hidden">
          <p className="eyebrow px-4 pt-3">Act on the forecast, or wait for the flood?</p>
          <div className="grid grid-cols-2 divide-x divide-paper-line">
            <div className="p-4">
              <p className="text-xs text-subtle">Decide now · {t.warning_days.toFixed(0)} days of warning</p>
              <p className="font-display text-3xl font-bold text-water">฿{t.decide_now.total_cost_million_thb.toFixed(1)}M</p>
              <p className="text-sm">{t.decide_now.co2_tonnes.toFixed(1)} t CO₂ · covers {pct(t.decide_now.coverage)}</p>
            </div>
            <div className="p-4">
              <p className="text-xs text-subtle">Decide after the event hits</p>
              <p className="font-display text-3xl font-bold text-hazard-dark">฿{t.decide_after_event.total_cost_million_thb.toFixed(1)}M</p>
              <p className="text-sm">{t.decide_after_event.co2_tonnes.toFixed(1)} t CO₂ · covers {pct(t.decide_after_event.coverage)}</p>
            </div>
          </div>
          <p className="border-t border-paper-line bg-paper-3 px-4 py-2 text-xs text-muted">
            Total cost = mitigation spend + revenue lost to shortages. Waiting removes pre-building and slow, low-carbon
            options, leaving air freight.
          </p>
        </div>
      )}

      <div className="flex flex-col gap-2">
        <p className="eyebrow">Options from the solver (OR-Tools)</p>
        {data.plans.map((p) => (
          <div key={p.plan_id} className={`card ${open === p.plan_id ? 'border-ink' : ''}`}>
            <button className="flex w-full items-center gap-4 px-4 py-3 text-left" onClick={() => setOpen(open === p.plan_id ? null : p.plan_id)}>
              <span className="flex-1">
                <span className="block font-semibold">{p.name}</span>
                <span className="block text-xs text-subtle">{p.objective}</span>
              </span>
              <span className="text-right">
                <span className="block font-mono text-sm">฿{p.total_cost_million_thb.toFixed(1)}M</span>
                <span className="block text-xs text-subtle">{p.co2_tonnes.toFixed(2)} t CO₂ · {pct(p.coverage)}</span>
              </span>
              <Verdict v={p.verification} />
            </button>
            {open === p.plan_id && (
              <div className="border-t border-paper-line px-4 py-3 text-xs">
                {Object.entries(p.actions).map(([need, acts]) => (
                  <div key={need} className="flex gap-3 py-1">
                    <span className="w-32 shrink-0 font-mono">{need}</span>
                    <span className="flex flex-wrap gap-1">
                      {acts.map((a) => (
                        <span key={a.option} className={`rounded px-1.5 py-0.5 ${a.kind === 'unmet' ? 'bg-hazard-wash text-hazard-dark'
                          : a.mode === 'air_cargo' ? 'bg-hazard/15' : 'bg-water-wash text-water'}`}>
                          {KIND_LABEL[a.kind]} {a.kind === 'alternate' ? a.supplier.replace('A-', '') : ''} {MODE_LABEL[a.mode]} ·{' '}
                          {Math.round(a.units).toLocaleString()}
                        </span>
                      ))}
                    </span>
                  </div>
                ))}
                <p className="mt-2 text-subtle">
                  Spend ฿{p.spend_million_thb.toFixed(1)}M · lost revenue ฿{p.lost_revenue_million_thb.toFixed(1)}M
                </p>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="card p-4">
        <p className="eyebrow">Try an edit: the verifier checks it</p>
        <div className="mt-2 grid grid-cols-[1fr_1fr_90px_auto] gap-2 text-sm">
          <select className="rounded border border-paper-line bg-white px-2 py-1" value={edit.need}
            onChange={(e) => setEdit({ need: e.target.value, option: '', units: 0 })}>
            <option value="">Shortage…</option>
            {needKeys.map((k) => <option key={k} value={k}>{k}</option>)}
          </select>
          <select className="rounded border border-paper-line bg-white px-2 py-1" value={edit.option}
            onChange={(e) => setEdit({ ...edit, option: e.target.value })}>
            <option value="">Option…</option>
            {opts.map((o) => <option key={o.key} value={o.key}>{o.kind} {o.supplier} {MODE_LABEL[o.mode]} (cap {Math.round(o.capacity_units)})</option>)}
          </select>
          <input type="number" className="rounded border border-paper-line bg-white px-2 py-1" value={edit.units || ''}
            placeholder="units" onChange={(e) => setEdit({ ...edit, units: Number(e.target.value) })} />
          <button disabled={busy} onClick={tryEdit} className="rounded bg-ink px-3 py-1 font-semibold text-paper disabled:opacity-50">
            Apply
          </button>
        </div>
        {edited && (
          <div className={`mt-3 rounded-lg p-3 text-sm ${edited.verification.ok ? 'bg-water-wash' : 'bg-hazard-wash'}`}>
            <div className="flex items-center gap-2">
              <Verdict v={edited.verification} />
              <span className="font-mono text-xs">{edited.plan_id} · ฿{edited.total_cost_million_thb.toFixed(1)}M · {edited.co2_tonnes.toFixed(2)} t</span>
            </div>
            {edited.verification.issues.map((i) => <p key={i} className="mt-1 font-mono text-xs text-hazard-dark">{i}</p>)}
          </div>
        )}
      </div>

      {data.pareto.length > 1 && (
        <div className="card p-3">
          <p className="eyebrow">Cost of carbon: total cost vs CO₂ cap</p>
          <ResponsiveContainer width="100%" height={190}>
            <LineChart data={data.pareto.map((p) => ({ co2: +(p.co2_cap_kg / 1000).toFixed(2), cost: +(p.total_cost_thb / 1e6).toFixed(1) }))}
              margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
              <CartesianGrid stroke="#E8E4D8" />
              <XAxis dataKey="co2" tick={{ fontSize: 11 }} unit=" t" />
              <YAxis tick={{ fontSize: 11 }} width={48} tickFormatter={(v) => `฿${v}M`} />
              <Tooltip formatter={(v: number) => [`฿${v}M`, 'total cost']} labelFormatter={(l) => `CO₂ cap ${l} t`} />
              <Line isAnimationActive={false} type="monotone" dataKey="cost" stroke="#2F6F8F" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
