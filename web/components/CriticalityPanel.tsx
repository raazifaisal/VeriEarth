'use client';

import { CartesianGrid, ReferenceArea, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts';
import { CritRow, fmtM, pct, QUADRANT_LABEL } from '@/lib/api';
import { riskColor } from './MapView';

const EXPOSURE_HIGH = 0.3;

export default function CriticalityPanel({ rows, onSelect }: { rows: CritRow[]; onSelect: (id: string) => void }) {
  const structural = rows.map((r) => r.structural_rar_thb).sort((a, b) => a - b);
  const threshold = structural[Math.floor(structural.length / 2)] / 1e6;
  const maxY = Math.max(...structural, 1) / 1e6;
  const data = rows.map((r) => ({
    id: r.supplier, name: r.name, x: r.exposure_p_down, y: r.structural_rar_thb / 1e6,
    z: Math.max(r.live_expected_rar_thb / 1e6, 0.5), quadrant: r.quadrant, live: r.live_expected_rar_thb,
  }));
  const maxLive = Math.max(...rows.map((r) => r.live_expected_rar_thb), 1);

  return (
    <div className="h-full space-y-4 overflow-y-auto pr-1">
      <div>
        <p className="eyebrow">Live criticality</p>
        <p className="mt-1 text-sm text-muted">
          Structural criticality (14-day stress test, slow-changing) against today's exposure (forecast P(site down)).
          Bubble size is expected revenue at risk from the simulation.
        </p>
      </div>
      <div className="card p-2">
        <ResponsiveContainer width="100%" height={260}>
          <ScatterChart margin={{ top: 12, right: 16, bottom: 22, left: 4 }}>
            <ReferenceArea x1={EXPOSURE_HIGH} x2={1} y1={threshold} y2={maxY * 1.1} fill="#FBEDE3" fillOpacity={0.9} />
            <CartesianGrid stroke="#E8E4D8" />
            <XAxis type="number" dataKey="x" domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 11 }}
              label={{ value: 'Exposure now: P(site down)', position: 'insideBottom', offset: -12, fontSize: 11, fill: '#5C6563' }} />
            <YAxis type="number" dataKey="y" domain={[0, Math.ceil(maxY * 1.1)]} tick={{ fontSize: 11 }} width={44}
              tickFormatter={(v) => `฿${v}M`} />
            <ZAxis type="number" dataKey="z" range={[60, 600]} />
            <ReferenceLine x={EXPOSURE_HIGH} stroke="#B5481A" strokeDasharray="4 4" />
            <ReferenceLine y={threshold} stroke="#B5481A" strokeDasharray="4 4" />
            <Tooltip cursor={false} content={({ payload }) => {
              const d = payload?.[0]?.payload;
              if (!d) return null;
              return (
                <div className="card px-3 py-2 text-xs shadow">
                  <b>{d.name}</b><br />
                  Exposure {pct(d.x)} · structural ฿{d.y.toFixed(1)}M<br />
                  Live E[revenue at risk] {fmtM(d.live)} · {QUADRANT_LABEL[d.quadrant as keyof typeof QUADRANT_LABEL]}
                </div>
              );
            }} />
            <Scatter isAnimationActive={false} data={data} onClick={(d) => onSelect((d as unknown as { id: string }).id)}
              shape={(props: { cx?: number; cy?: number; size?: number; payload?: { x: number } }) => {
                const r = Math.sqrt((props.size ?? 60) / Math.PI);
                return <circle cx={props.cx} cy={props.cy} r={r} fill={riskColor(props.payload?.x ?? 0)} stroke="#10201F" strokeWidth={1} style={{ cursor: 'pointer' }} />;
              }} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-subtle">Shaded corner = act now: high structural criticality and high exposure.</p>

      <div className="flex flex-col gap-1.5">
        {rows.map((r, i) => (
          <button key={r.supplier} onClick={() => onSelect(r.supplier)}
            className="card flex items-center gap-3 px-3 py-2 text-left transition hover:border-ink">
            <span className="w-4 font-mono text-xs text-subtle">{i + 1}</span>
            <span className="h-3 w-3 shrink-0 rounded-full border border-ink" style={{ background: riskColor(r.exposure_p_down) }} />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold">{r.name}</span>
              <span className="block truncate text-xs text-subtle">
                {r.estate} · {r.parts.join(', ')} · survives {r.time_to_survive_days}d vs recovers ~{r.median_downtime_days}d
                {r.has_alternate ? '' : ' · single source'}
              </span>
            </span>
            <span className="w-28 shrink-0">
              <span className="block text-right font-mono text-xs">{fmtM(r.live_expected_rar_thb)}</span>
              <span className="mt-1 block h-1.5 rounded bg-paper-3">
                <span className="block h-1.5 rounded bg-hazard" style={{ width: `${(100 * r.live_expected_rar_thb) / maxLive}%` }} />
              </span>
            </span>
            <span className={`w-24 shrink-0 rounded-full px-2 py-0.5 text-center text-[11px] font-semibold ${
              r.quadrant === 'act_now' ? 'bg-hazard text-white' : r.quadrant === 'monitor' ? 'bg-hazard-wash text-hazard-dark'
                : r.quadrant === 'build_buffers' ? 'bg-water-wash text-water' : 'bg-paper-3 text-subtle'}`}>
              {QUADRANT_LABEL[r.quadrant]}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
