import { z } from "zod";
import { db } from "@/lib/server/supabase";
import { CLUSTER_THRESHOLD } from "@/lib/server/env";
import { companyDomainFromEmail } from "@/lib/domain";

const Body = z.object({
  email: z.string().email().max(200),
  city: z.string().max(80).optional(),
  consent: z.literal(true),
});

export async function POST(request: Request) {
  const parsed = Body.safeParse(await request.json().catch(() => null));
  if (!parsed.success) {
    return Response.json({ error: "Enter a valid e-mail and tick the consent box." }, { status: 400 });
  }
  const { email, city } = parsed.data;
  const domain = companyDomainFromEmail(email);

  const { error } = await db().from("signups").upsert(
    { email: email.toLowerCase(), company_domain: domain, city: city ?? null, consent_at: new Date().toISOString() },
    { onConflict: "email", ignoreDuplicates: true },
  );
  if (error) return Response.json({ error: "Could not save the sign-up. Try again." }, { status: 500 });

  if (!domain) return Response.json({ ok: true, colleagues: 0, threshold: CLUSTER_THRESHOLD });

  const { count } = await db()
    .from("signups")
    .select("id", { count: "exact", head: true })
    .eq("company_domain", domain);
  const colleagues = count ?? 0;

  if (colleagues >= CLUSTER_THRESHOLD) await raiseDemandAlert(domain, colleagues);
  return Response.json({ ok: true, colleagues, threshold: CLUSTER_THRESHOLD });
}

// Inserted once per company (unique constraint). n8n is told only on the first insert.
async function raiseDemandAlert(domain: string, signups: number) {
  const { data } = await db()
    .from("alerts")
    .upsert(
      { company_domain: domain, kind: "demand_cluster", payload: { signups } },
      { onConflict: "company_domain,kind", ignoreDuplicates: true },
    )
    .select("id");
  if (!data?.length) return; // already alerted

  const hook = process.env.N8N_ALERT_WEBHOOK_URL;
  if (!hook) return;
  try {
    await fetch(hook, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ kind: "demand_cluster", domain, signups, alertId: data[0].id }),
      signal: AbortSignal.timeout(5000),
    });
    await db().from("alerts").update({ delivered: true }).eq("id", data[0].id);
  } catch (err) {
    // The alert row stays with delivered=false; the ops view shows it as undelivered.
    console.warn(`[signup] n8n webhook failed for ${domain}: ${(err as Error).message}`);
  }
}
