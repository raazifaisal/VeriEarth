'use client';

import { useEffect, useState } from 'react';

interface Stats {
  stats: Record<string, { brightened_gt3db: number; darkened_gt3db: number }>;
  source: string;
}

const FRAMES = [
  { img: '/sat/sar_asc_20260915.png', label: '15 Sep · before', note: 'Reference pass' },
  { img: '/sat/sar_asc_20260927_change.png', label: '27 Sep · flood peak', key: 'asc:20260915->20260927' },
  { img: '/sat/sar_asc_20261009_change.png', label: '9 Oct · after', key: 'asc:20260915->20261009' },
];

export default function ObservePanel() {
  const [s, setS] = useState<Stats | null>(null);
  const [big, setBig] = useState(1);
  useEffect(() => {
    fetch('/sat/sar_stats.json').then((r) => r.json()).then(setS).catch(() => setS(null));
  }, []);
  const pctOf = (k?: string) => (k && s ? s.stats[k]?.brightened_gt3db : undefined);

  return (
    <div className="h-full space-y-4 overflow-y-auto pr-1">
      <div>
        <p className="eyebrow">Observed from space · Amata City Chonburi</p>
        <p className="mt-1 text-sm text-muted">
          Sentinel-1 radar sees through monsoon cloud. Flooded built-up areas get <b>brighter</b> (water and walls bounce
          the signal back), so we map areas that brightened by more than 3 dB against a same-orbit pass before the event.
        </p>
      </div>

      <div className="card overflow-hidden">
        <img src={FRAMES[big].img} alt={`Sentinel-1 radar change map, ${FRAMES[big].label}`} className="aspect-[900/801] w-full object-cover" />
        <div className="flex items-center justify-between px-4 py-2 text-sm">
          <span className="font-semibold">{FRAMES[big].label}</span>
          <span className="text-xs text-subtle">orange = brightened &gt;3 dB vs 15 Sep</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {FRAMES.map((f, i) => {
          const v = pctOf(f.key);
          return (
            <button key={f.img} onClick={() => setBig(i)} className={`card overflow-hidden text-left ${i === big ? 'border-ink' : ''}`}>
              <img src={f.img} alt={f.label} className="aspect-square w-full object-cover" />
              <div className="px-2 py-1.5">
                <p className="text-xs font-semibold">{f.label}</p>
                <p className="font-mono text-[11px] text-hazard-dark">{v == null ? f.note : `${(v * 100).toFixed(1)}% of area brightened`}</p>
              </div>
            </button>
          );
        })}
      </div>

      <div className="card space-y-2 p-4 text-sm">
        <p className="font-semibold">What this shows</p>
        <p className="text-muted">
          Brightening peaked during the flood ({((pctOf('asc:20260915->20260927') ?? 0) * 100).toFixed(1)}% of the area) and
          was back near the noise floor by 9 October ({((pctOf('asc:20260915->20261009') ?? 0) * 100).toFixed(1)}%). Reported
          production restarts came on 12–14 October: <b>operations recover after the water does</b>, which is why
          VeriEarth models time-to-recover separately from flood duration.
        </p>
        <p className="text-xs text-subtle">
          Estate-scale signal, not a per-factory measurement. Facility-level observed recovery (radar coherence, thermal,
          night lights) is on the roadmap. Source: {s?.source ?? 'Sentinel-1 RTC'}.
        </p>
      </div>
    </div>
  );
}
