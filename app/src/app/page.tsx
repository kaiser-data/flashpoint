"use client";

import { useState } from "react";

type Result = { colleagues: number; threshold: number };

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [city, setCity] = useState("Berlin");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/signup", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, city, consent }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error ?? "Sign-up failed.");
      setResult(body);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col gap-6 px-5 py-10">
      <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)]">GTM Hackathon Berlin · demo</p>
      <h1 className="text-3xl font-bold leading-tight text-balance">Want proper lunch at your office?</h1>
      <p className="text-[var(--muted)]">
        Sign up with your work e-mail. When five colleagues from your company ask, we let your People team know how a
        tax-free lunch benefit of up to €7.67 per workday would work.
      </p>

      {result ? (
        <section className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5">
          <p className="text-lg font-semibold">You&apos;re on the list.</p>
          {result.colleagues > 0 ? (
            <p className="mt-2 text-[var(--muted)]">
              {Math.min(result.colleagues, result.threshold)} of {result.threshold} colleagues from your company have
              signed up.
            </p>
          ) : (
            <p className="mt-2 text-[var(--muted)]">Private e-mail addresses are not grouped by company.</p>
          )}
        </section>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1 text-sm font-medium" htmlFor="email">
            Work e-mail
            <input id="email" type="email" required autoComplete="email" value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-3 text-base" />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium" htmlFor="city">
            Office city
            <select id="city" value={city} onChange={(e) => setCity(e.target.value)}
              className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-3 text-base">
              {["Berlin", "München", "Düsseldorf", "Köln", "Other"].map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          <label className="flex gap-3 text-sm text-[var(--muted)]" htmlFor="consent">
            <input id="consent" type="checkbox" required checked={consent} onChange={(e) => setConsent(e.target.checked)}
              className="mt-1 h-4 w-4" />
            I agree that this hackathon demo stores my e-mail to count sign-ups per company and may contact me once
            about it. Only company-level counts are shared. Data is deleted after the event.
          </label>
          {error && <p role="alert" className="text-sm text-[var(--bad)]">{error}</p>}
          <button type="submit" disabled={busy}
            className="rounded-lg bg-[var(--accent)] px-4 py-3 font-semibold text-[var(--on-accent)] disabled:opacity-60">
            {busy ? "Saving…" : "Ask for lunch"}
          </button>
        </form>
      )}
      <a href="/ops" className="text-sm text-[var(--muted)] underline">Sales view</a>
    </main>
  );
}
