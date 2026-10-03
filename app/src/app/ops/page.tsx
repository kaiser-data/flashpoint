"use client";

import { useEffect, useState } from "react";

type Demand = { company_domain: string; signups: number; cities: string[] | null; last_signup_at: string };
type Company = {
  domain: string; name: string | null; city: string | null; segment: string;
  segment_reasons: string[]; perks: string[]; evidence: { url: string; quote: string }[];
  ads_analysed: number; scan_cost_usd: number | null;
};
type Alert = { id: number; company_domain: string; kind: string; delivered: boolean; created_at: string };
type State = { threshold: number; demand: Demand[]; companies: Company[]; alerts: Alert[] };

const SEGMENT_STYLE: Record<string, string> = {
  gap: "bg-[var(--accent-soft)] text-[var(--accent)]",
  switch: "bg-[var(--warn-soft)] text-[var(--warn)]",
  skip: "bg-[var(--line)] text-[var(--muted)]",
  unknown: "bg-[var(--line)] text-[var(--muted)]",
};

export default function OpsPage() {
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    async function poll() {
      try {
        const res = await fetch("/api/state", { cache: "no-store" });
        const body = await res.json();
        if (!res.ok) throw new Error(body.error);
        if (alive) { setState(body); setError(null); }
      } catch (err) {
        if (alive) setError(`Live update failed: ${(err as Error).message}. Showing the last data.`);
      }
    }
    poll();
    const id = setInterval(poll, 3000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const byDomain = new Map(state?.companies.map((c) => [c.domain, c]) ?? []);

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-5 py-8">
      <header className="flex flex-col gap-1">
        <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)]">LunchSignal · sales view</p>
        <h1 className="text-2xl font-bold">Who wants lunch, and who already pays for it</h1>
        {error && <p role="alert" className="text-sm text-[var(--bad)]">{error}</p>}
      </header>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Alerts</h2>
        {state?.alerts.length ? (
          <ul className="flex flex-col gap-2">
            {state.alerts.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--line)] bg-[var(--surface)] px-4 py-3">
                <span className={`rounded-full px-2 py-1 text-xs font-semibold uppercase ${SEGMENT_STYLE[a.kind] ?? SEGMENT_STYLE.gap}`}>
                  {a.kind.replace("_", " ")}
                </span>
                <span className="font-medium">{a.company_domain}</span>
                <span className="text-sm text-[var(--muted)]">{new Date(a.created_at).toLocaleTimeString("de-DE")}</span>
                {!a.delivered && a.kind === "demand_cluster" && (
                  <span className="text-xs text-[var(--warn)]">not yet sent to n8n</span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[var(--muted)]">No alerts yet. One appears when {state?.threshold ?? 5} people from one company sign up.</p>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Demand by company</h2>
        <div className="overflow-x-auto rounded-lg border border-[var(--line)] bg-[var(--surface)]">
          <table className="w-full text-left text-sm tabular-nums">
            <thead className="text-xs uppercase tracking-wide text-[var(--muted)]">
              <tr><th className="px-4 py-2">Company</th><th className="px-4 py-2">Sign-ups</th><th className="px-4 py-2">Segment</th><th className="px-4 py-2">Evidence</th></tr>
            </thead>
            <tbody>
              {state?.demand.map((d) => {
                const c = byDomain.get(d.company_domain);
                return (
                  <tr key={d.company_domain} className="border-t border-[var(--line)] align-top">
                    <td className="px-4 py-3 font-medium">{d.company_domain}<div className="text-xs text-[var(--muted)]">{d.cities?.join(", ")}</div></td>
                    <td className="px-4 py-3">
                      {d.signups} / {state.threshold}
                      <div className="mt-1 h-1.5 w-24 rounded bg-[var(--line)]">
                        <div className="h-1.5 rounded bg-[var(--accent)]" style={{ width: `${Math.min(100, (d.signups / state.threshold) * 100)}%` }} />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {c ? <span className={`rounded-full px-2 py-1 text-xs font-semibold uppercase ${SEGMENT_STYLE[c.segment]}`}>{c.segment}</span>
                         : <span className="text-[var(--muted)]">not scanned</span>}
                    </td>
                    <td className="max-w-sm px-4 py-3 text-[var(--muted)]">
                      {c?.segment_reasons?.[0]}
                      {c && <div className="text-xs">{c.ads_analysed} ads{c.scan_cost_usd != null && ` · $${Number(c.scan_cost_usd).toFixed(3)}`}</div>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
