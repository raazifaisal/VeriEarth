'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';
import AgentPanel from '@/components/AgentPanel';
import CriticalityPanel from '@/components/CriticalityPanel';
import DecidePanel from '@/components/DecidePanel';
import IntakePanel from '@/components/IntakePanel';
import ObservePanel from '@/components/ObservePanel';
import SiteCard from '@/components/SiteCard';
import { api, Assessment, fmtM, pct, PlansResponse, SiteDetail } from '@/lib/api';

const MapView = dynamic(() => import('@/components/MapView'), { ssr: false });

const DATES = ['2026-09-18', '2026-09-19', '2026-09-20', '2026-09-21', '2026-09-22', '2026-09-23', '2026-09-24'];
const TABS = ['Criticality', 'Decide', 'Agent', 'Observe', 'Intake'] as const;
type Tab = (typeof TABS)[number];

function fmtDate(d: string) {
  return new Date(d + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

export default function Home() {
  const [asOf, setAsOf] = useState('2026-09-22');
  const [a, setA] = useState<Assessment | null>(null);
  const [plans, setPlans] = useState<PlansResponse | null>(null);
  const [tab, setTab] = useState<Tab>('Criticality');
  const [selected, setSelected] = useState<string | null>(null);
  const [site, setSite] = useState<SiteDetail | null>(null);
  const [gemini, setGemini] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.health().then((h) => setGemini(h.gemini_configured)).catch(() => setErr('API unreachable'));
    // Deep links for demos: ?date=2026-09-22&tab=Decide&site=S-RESIN
    const q = new URLSearchParams(window.location.search);
    const d = q.get('date');
    const t = q.get('tab') as Tab | null;
    if (d && DATES.includes(d)) setAsOf(d);
    if (t && TABS.includes(t)) setTab(t);
    if (q.get('site')) setSelected(q.get('site'));
  }, []);

  useEffect(() => {
    setErr(null);
    api.assessment(asOf).then(setA).catch((e) => setErr(String(e)));
    setPlans(null);
    api.plans(asOf).then(setPlans).catch((e) => setErr(String(e)));
  }, [asOf]);

  useEffect(() => {
    if (!selected) return setSite(null);
    api.site(selected, asOf).then(setSite).catch(() => setSite(null));
  }, [selected, asOf]);

  const rr = a?.overview.revenue_at_risk;
  const actNow = a?.criticality.filter((c) => c.quadrant === 'act_now').length ?? 0;
  const late = a?.overview.orders.filter((o) => o.p_late >= 0.5).length ?? 0;

  return (
    <main className="flex h-screen flex-col gap-3 p-4">
      <header className="flex flex-wrap items-center gap-x-8 gap-y-3">
        <div>
          <p className="font-display text-2xl font-extrabold tracking-tight">VeriEarth</p>
          <p className="text-xs text-subtle">Live supplier criticality and decision support</p>
        </div>

        <div className="min-w-[340px] flex-1">
          <div className="flex items-baseline justify-between">
            <p className="eyebrow">Decision date</p>
            <p className="text-xs text-subtle">Real event: 25–27 Sep 2026 rain, Amata City Chonburi floods</p>
          </div>
          <div className="mt-1 flex gap-1">
            {DATES.map((d) => (
              <button key={d} onClick={() => setAsOf(d)}
                className={`flex-1 rounded-md border px-2 py-1 text-xs font-semibold transition ${
                  d === asOf ? 'border-ink bg-ink text-paper' : 'border-paper-line bg-paper-2 hover:border-ink'}`}>
                {fmtDate(d)}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-6">
          <div>
            <p className="text-[11px] text-subtle">Revenue at risk, 28 days</p>
            <p className="font-display text-2xl font-bold text-hazard-dark">{rr ? fmtM(rr.expected_revenue_at_risk_thb) : '…'}</p>
            <p className="text-[11px] text-subtle">P90 {rr ? fmtM(rr.p90_thb) : '…'}</p>
          </div>
          <div>
            <p className="text-[11px] text-subtle">Act-now suppliers</p>
            <p className="font-display text-2xl font-bold">{a ? actNow : '…'}</p>
            <p className="text-[11px] text-subtle">of {a?.criticality.length ?? '…'}</p>
          </div>
          <div>
            <p className="text-[11px] text-subtle">Orders likely late</p>
            <p className="font-display text-2xl font-bold">{a ? late : '…'}</p>
            <p className="text-[11px] text-subtle">of {a?.overview.orders.length ?? '…'}</p>
          </div>
        </div>
      </header>

      {err && <p className="rounded bg-hazard-wash px-3 py-2 font-mono text-xs text-hazard-dark">{err}</p>}

      <section className="grid min-h-0 flex-1 grid-cols-[minmax(0,1.35fr)_minmax(420px,1fr)] gap-3">
        <div className="flex min-h-0 flex-col gap-3">
          <div className="relative min-h-0 flex-1">
            {a && <MapView sites={a.sites} edges={a.edges} selected={selected} onSelect={setSelected} />}
            <div className="pointer-events-none absolute left-3 top-3 z-[500] flex flex-col gap-2">
              <div className="card pointer-events-auto bg-paper-2/95 px-3 py-2 text-[11px] shadow">
                <p className="font-semibold">Siam Interior Components <span className="font-normal text-subtle">· illustrative network, real hazard data</span></p>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-subtle">
                  <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-[#F2D9C4] ring-1 ring-ink" />P(down) &lt;10%</span>
                  <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-[#E8894F] ring-1 ring-ink" />30–50%</span>
                  <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-[#A8401A] ring-1 ring-ink" />≥70%</span>
                  <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-sm bg-water" />Own plant</span>
                  <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-ink" />Customer</span>
                  <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full ring-2 ring-water" />Alternate</span>
                </div>
              </div>
            </div>
            {site && (
              <div className="absolute bottom-3 left-3 z-[500]">
                <SiteCard d={site} asOf={asOf} onClose={() => setSelected(null)} />
              </div>
            )}
          </div>

          {a && (
            <div className="card flex gap-2 overflow-x-auto p-2">
              {a.overview.orders.map((o) => (
                <div key={o.id} className="min-w-[132px] rounded-lg bg-paper-3 px-2 py-1.5">
                  <p className="truncate text-[11px] font-semibold">{o.customer}</p>
                  <p className="text-[10px] text-subtle">{o.product} · due {fmtDate(o.due)}</p>
                  <p className={`font-mono text-xs font-semibold ${o.p_late >= 0.5 ? 'text-hazard-dark' : 'text-water'}`}>P(late) {pct(o.p_late)}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card flex min-h-0 flex-col p-3">
          <nav className="mb-3 flex gap-1 rounded-lg bg-paper-3 p-1">
            {TABS.map((t) => (
              <button key={t} onClick={() => setTab(t)}
                className={`flex-1 rounded-md px-3 py-1.5 text-sm font-semibold transition ${t === tab ? 'bg-paper-2 shadow' : 'text-subtle hover:text-ink'}`}>
                {t}
              </button>
            ))}
          </nav>
          <div className="min-h-0 flex-1">
            {tab === 'Criticality' && a && <CriticalityPanel rows={a.criticality} onSelect={setSelected} />}
            {tab === 'Decide' && (plans ? <DecidePanel data={plans} /> : <p className="text-sm text-subtle">Solving…</p>)}
            <div className={tab === 'Agent' ? 'h-full' : 'hidden'}><AgentPanel asOf={asOf} geminiReady={gemini} /></div>
            {tab === 'Observe' && <ObservePanel />}
            {tab === 'Intake' && <IntakePanel />}
          </div>
        </div>
      </section>
    </main>
  );
}
