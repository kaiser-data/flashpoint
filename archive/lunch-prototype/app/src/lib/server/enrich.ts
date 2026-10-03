import "server-only";
import { db } from "./supabase";
import { fetchJobAds } from "./jobs";
import { extractBenefits } from "./extract";
import { segmentCompany, type AdBenefits } from "../segment";
import { guessCompanyName } from "../domain";

// One company: job ads -> extracted benefits -> segment -> stored -> alert when actionable.
export async function enrichCompany(domain: string, opts: { name?: string; city?: string } = {}) {
  const name = opts.name ?? guessCompanyName(domain);
  const city = opts.city ?? "Berlin";

  const { ads, costUsd, runId } = await fetchJobAds(name, city);
  const extracted: AdBenefits[] = [];
  for (const ad of ads) {
    const ben = await extractBenefits(ad.url, ad.text);
    await db().from("job_ads").upsert(
      { company_domain: domain, source_url: ad.url, title: ad.title, city: ad.city, extracted: ben },
      { onConflict: "company_domain,source_url" },
    );
    if (ben) extracted.push(ben);
  }

  const result = segmentCompany(extracted);
  await db().from("companies").upsert({
    domain, name, city,
    segment: result.segment,
    segment_reasons: result.reasons,
    perks: result.perks,
    evidence: result.evidence,
    ads_analysed: result.adsAnalysed,
    scan_cost_usd: costUsd,
    updated_at: new Date().toISOString(),
  });

  if (result.segment === "gap" || result.segment === "switch") {
    await db().from("alerts").upsert(
      { company_domain: domain, kind: result.segment, payload: { name, city, reasons: result.reasons } },
      { onConflict: "company_domain,kind", ignoreDuplicates: true },
    );
  }

  return { domain, name, city, adsFound: ads.length, costUsd, apifyRunId: runId, ...result };
}
