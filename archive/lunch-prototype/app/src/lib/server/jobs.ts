import "server-only";
import { ApifyClient } from "apify-client";
import { requireEnv } from "./env";

export type RawAd = { url: string; title: string; city: string; company: string; text: string };

// Default: misceres/indeed-scraper (verified in the Apify Store, $3 / 1k results).
// Input and output field names differ per actor; check the first run's log and adjust the mapping below.
const ACTOR = process.env.APIFY_JOBS_ACTOR ?? "misceres/indeed-scraper";

function pick(item: Record<string, unknown>, keys: string[]): string {
  for (const k of keys) {
    const v = item[k];
    if (typeof v === "string" && v.trim()) return v;
  }
  return "";
}

export async function fetchJobAds(companyName: string, city: string, maxItems = 15) {
  const client = new ApifyClient({ token: requireEnv("APIFY_TOKEN") });
  const run = await client.actor(ACTOR).call(
    { position: companyName, country: "DE", location: city, maxItems, parseCompanyDetails: false },
    { waitSecs: 240 },
  );
  const { items } = await client.dataset(run.defaultDatasetId).listItems();
  if (items[0]) console.log(`[jobs] ${ACTOR} item keys:`, Object.keys(items[0]).join(", "));

  const ads: RawAd[] = items
    .map((it) => it as Record<string, unknown>)
    .map((it) => ({
      url: pick(it, ["url", "externalApplyLink", "jobUrl", "link"]),
      title: pick(it, ["positionName", "title", "jobTitle"]),
      city: pick(it, ["location", "city"]),
      company: pick(it, ["company", "companyName"]),
      text: pick(it, ["description", "descriptionText", "jobDescription", "descriptionHTML"]),
    }))
    .filter((a) => a.url && a.text)
    // Keep only ads whose employer name contains the search term, so other companies' ads don't leak in.
    .filter((a) => a.company.toLowerCase().includes(companyName.toLowerCase().split(" ")[0]));

  const usd = (run as { usageTotalUsd?: number }).usageTotalUsd ?? null;
  return { ads, costUsd: usd, runId: run.id };
}
