'use client';

import { useState } from 'react';
import { API } from '@/lib/api';

interface Result {
  document: Record<string, unknown> & { items?: { description: string; quantity?: number; unit?: string; weight_kg?: number }[] };
  link: { matched_site: string | null; match_score: number };
}

const FIELDS: [string, string][] = [
  ['document_type', 'Type'], ['language', 'Language'], ['issuer_name', 'Issuer'], ['issuer_name_original', 'As written'],
  ['recipient_name', 'Recipient'], ['origin', 'Origin'], ['destination', 'Destination'], ['document_date', 'Date'],
  ['transport_mode', 'Mode'], ['gross_weight_kg', 'Gross weight (kg)'], ['electricity_kwh', 'Electricity (kWh)'],
];

export default function IntakePanel() {
  const [res, setRes] = useState<Result | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  async function upload(f: File) {
    setBusy(true);
    setErr(null);
    setRes(null);
    setPreview(f.type.startsWith('image/') ? URL.createObjectURL(f) : null);
    try {
      const fd = new FormData();
      fd.append('file', f);
      const r = await fetch(`${API}/api/v1/intake`, { method: 'POST', body: fd });
      if (!r.ok) throw new Error(await r.text());
      setRes(await r.json());
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="h-full space-y-4 overflow-y-auto pr-1">
      <div>
        <p className="eyebrow">Supplier documents in, graph updated</p>
        <p className="mt-1 text-sm text-muted">
          Drop a photo or PDF of a bill of lading, invoice or utility bill, in any language. Gemini reads it into a
          schema; matching to the supply graph is deterministic.
        </p>
      </div>
      <label className="card flex cursor-pointer flex-col items-center justify-center gap-2 border-dashed px-4 py-8 text-sm hover:border-ink">
        <input type="file" accept="image/*,application/pdf" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
        <span className="font-semibold">{busy ? 'Reading document…' : 'Choose a document'}</span>
        <span className="text-xs text-subtle">JPG, PNG or PDF up to 8 MB</span>
      </label>
      {preview && <img src={preview} alt="Uploaded document" className="max-h-48 w-full rounded-lg object-contain" />}
      {err && <p className="rounded bg-hazard-wash p-2 font-mono text-xs text-hazard-dark">{err}</p>}
      {res && (
        <div className="card p-4 text-sm">
          <dl className="grid grid-cols-[140px_1fr] gap-x-3 gap-y-1">
            {FIELDS.filter(([k]) => res.document[k] != null).map(([k, label]) => (
              <div key={k} className="contents">
                <dt className="text-subtle">{label}</dt>
                <dd className="font-medium">{String(res.document[k])}</dd>
              </div>
            ))}
          </dl>
          {res.document.items && res.document.items.length > 0 && (
            <ul className="mt-3 border-t border-paper-line pt-2 text-xs">
              {res.document.items.map((it, i) => (
                <li key={i}>{it.description} {it.quantity != null ? `· ${it.quantity} ${it.unit ?? ''}` : ''} {it.weight_kg != null ? `· ${it.weight_kg} kg` : ''}</li>
              ))}
            </ul>
          )}
          <p className={`mt-3 rounded px-2 py-1 text-xs ${res.link.matched_site ? 'bg-water-wash text-water' : 'bg-paper-3 text-muted'}`}>
            {res.link.matched_site ? `Linked to supplier ${res.link.matched_site} (name match ${res.link.match_score})` : `No confident supplier match (best ${res.link.match_score}); review needed`}
          </p>
        </div>
      )}
    </div>
  );
}
