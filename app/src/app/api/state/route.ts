import { db } from "@/lib/server/supabase";
import { CLUSTER_THRESHOLD } from "@/lib/server/env";

// Company-level only: the ops view never receives e-mail addresses.
export async function GET() {
  const [demand, companies, alerts] = await Promise.all([
    db().from("demand_by_company").select("*").order("signups", { ascending: false }).limit(50),
    db().from("companies").select("domain,name,city,segment,segment_reasons,perks,evidence,ads_analysed,scan_cost_usd,updated_at").limit(200),
    db().from("alerts").select("id,company_domain,kind,payload,delivered,created_at").order("created_at", { ascending: false }).limit(30),
  ]);
  const error = demand.error ?? companies.error ?? alerts.error;
  if (error) return Response.json({ error: error.message }, { status: 500 });

  return Response.json({
    threshold: CLUSTER_THRESHOLD,
    demand: demand.data,
    companies: companies.data,
    alerts: alerts.data,
  });
}
