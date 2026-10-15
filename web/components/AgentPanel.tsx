'use client';

import { useRef, useState } from 'react';
import { API } from '@/lib/api';

type Step =
  | { type: 'tool_call'; author: string; name: string; args: Record<string, unknown> }
  | { type: 'tool_result'; author: string; name: string; result: unknown }
  | { type: 'text'; author: string; text: string; final?: boolean }
  | { type: 'error'; error: string };

interface Turn {
  question: string;
  steps: Step[];
  done: boolean;
}

const SUGGESTIONS = [
  'Which suppliers should I worry about this week, and why?',
  'Why is Eastern Resin Compounds so risky?',
  'What should I do about the resin shortage? Keep carbon low.',
  'Move 3,000 kg of foam to the Rayong alternate and verify it.',
];

const AGENT_LABEL: Record<string, string> = {
  veriearth: 'Coordinator',
  hazard_analyst: 'Hazard analyst',
  criticality_analyst: 'Criticality analyst',
  mitigation_planner: 'Mitigation planner',
  plan_verifier: 'Verifier',
};

export default function AgentPanel({ asOf, geminiReady }: { asOf: string; geminiReady: boolean }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const session = useRef<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  async function ask(q: string) {
    if (!q.trim() || busy) return;
    setBusy(true);
    setInput('');
    setTurns((t) => [...t, { question: q, steps: [], done: false }]);
    const push = (s: Step) =>
      setTurns((t) => t.map((turn, i) => (i === t.length - 1 ? { ...turn, steps: [...turn.steps, s] } : turn)));
    try {
      const r = await fetch(`${API}/api/v1/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: q, session_id: session.current, as_of: asOf }),
      });
      const reader = r.body!.getReader();
      const dec = new TextDecoder();
      let buf = '';
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const chunks = buf.split('\n\n');
        buf = chunks.pop() ?? '';
        for (const c of chunks) {
          const line = c.replace(/^data: /, '');
          if (!line) continue;
          const ev = JSON.parse(line);
          if (ev.type === 'session') session.current = ev.session_id;
          else if (ev.type !== 'done') push(ev);
          bottom.current?.scrollIntoView({ behavior: 'smooth' });
        }
      }
    } catch (e) {
      push({ type: 'error', error: String(e) });
    } finally {
      setTurns((t) => t.map((turn, i) => (i === t.length - 1 ? { ...turn, done: true } : turn)));
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-5 overflow-y-auto pr-1">
        {turns.length === 0 && (
          <div className="space-y-3">
            <p className="eyebrow">Gemini agent team</p>
            <p className="text-sm text-muted">
              A coordinator delegates to hazard, criticality, planning and verification agents. Agents choose and explain;
              every number comes from an engine tool, and no plan is recommended until the verifier passes it.
            </p>
            {!geminiReady && (
              <p className="rounded-lg bg-hazard-wash p-3 text-xs text-hazard-dark">
                Gemini is not configured on the API yet (set GEMINI_API_KEY). The rest of the app works without it.
              </p>
            )}
            <div className="flex flex-col gap-2">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => ask(s)} className="card px-3 py-2 text-left text-sm hover:border-ink">{s}</button>
              ))}
            </div>
          </div>
        )}
        {turns.map((t, i) => {
          const answer = [...t.steps].reverse().find((s) => s.type === 'text' && s.author === 'veriearth') as
            | Extract<Step, { type: 'text' }>
            | undefined;
          const trace = t.steps.filter((s) => s.type === 'tool_call');
          const err = t.steps.find((s) => s.type === 'error') as Extract<Step, { type: 'error' }> | undefined;
          return (
            <div key={i} className="space-y-2">
              <p className="ml-auto w-fit max-w-[85%] rounded-xl bg-ink px-3 py-2 text-sm text-paper">{t.question}</p>
              {trace.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {trace.map((s, j) => (
                    <span key={j} className="rounded-full border border-paper-line bg-paper-2 px-2 py-0.5 font-mono text-[11px] text-muted">
                      {AGENT_LABEL[s.author] ?? s.author} → {(s as Extract<Step, { type: 'tool_call' }>).name}
                    </span>
                  ))}
                </div>
              )}
              {answer && <div className="card whitespace-pre-wrap px-4 py-3 text-sm leading-relaxed">{answer.text}</div>}
              {!t.done && !answer && <p className="animate-pulse text-xs text-subtle">Agents working…</p>}
              {err && <p className="rounded bg-hazard-wash p-2 font-mono text-xs text-hazard-dark">{err.error}</p>}
            </div>
          );
        })}
        <div ref={bottom} />
      </div>
      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); ask(input); }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about suppliers, risk or what to do…"
          className="flex-1 rounded-lg border border-paper-line bg-white px-3 py-2 text-sm outline-none focus:border-ink" />
        <button disabled={busy} className="rounded-lg bg-hazard px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Ask</button>
      </form>
    </div>
  );
}
