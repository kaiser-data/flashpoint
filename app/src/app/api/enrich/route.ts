import { z } from "zod";
import { enrichCompany } from "@/lib/server/enrich";
import { maxTaxFreeLunchBudgetEur, TAX_FREE_PER_WORKDAY_EUR } from "@/lib/roi";

// Called by n8n after a demand alert, or by hand to scan one company.
const Body = z.object({
  domain: z.string().min(3).max(120),
  name: z.string().max(120).optional(),
  city: z.string().max(80).optional(),
});

export const maxDuration = 300;

export async function POST(request: Request) {
  if (request.headers.get("x-enrich-secret") !== process.env.ENRICH_SECRET || !process.env.ENRICH_SECRET) {
    return Response.json({ error: "Missing or wrong x-enrich-secret header." }, { status: 401 });
  }
  const parsed = Body.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return Response.json({ error: "Send {domain, name?, city?}." }, { status: 400 });

  try {
    const result = await enrichCompany(parsed.data.domain, parsed.data);
    return Response.json({
      ...result,
      roi: {
        taxFreePerWorkdayEur: TAX_FREE_PER_WORKDAY_EUR,
        maxTaxFreeBudgetPer50EmployeesEur: maxTaxFreeLunchBudgetEur(50),
      },
    });
  } catch (err) {
    return Response.json({ error: `Enrichment failed: ${(err as Error).message}` }, { status: 502 });
  }
}
