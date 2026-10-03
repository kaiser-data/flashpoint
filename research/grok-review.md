**Do not ship A as specified.** Job ads are a hiring signal with extra parsing. Judges just said Clay already owns that. Pivot the source, keep the €7.67 math.

### 1. Re-score (Originality / Real / Reliability / Wild = total)

| | Orig | Real | Rel | Wild | **Σ** | Why it moved |
|---|---|---|---|---|---|---|
| **A** NRW Radar (job ads) | 2 | 5 | 4 | 3 | **14** | Same object Clay sells. Benefit-gap is a footnote on a hiring crawl. Globe is 6h waste. |
| **B** Store Gap | 4 | 4 | 4 | 4 | **16** | Fresh, legal closed loop (internal Slack). ROI is “actor might sell,” not a buyer number. |
| **C** Canteen closed | 4 | 2 | 2 | 3 | **11** | Right idea, no data. Dies on “runs today.” |
| **D** HQ events only | 4 | 4 | 3 | 3 | **14** | Not hiring. Coworking false positives. No € without a second source. |
| **E** Hygiene PDFs | 3 | 2 | 2 | 2 | **9** | Unexpected, not predictive, PDF hell. |

### 2. A’s core is too close. Make it *not* hiring.

Yes. Clay’s hiring signal is “open reqs ⇒ budget/growth.” You are still watching vacancies.

**Change the object.** Do not count jobs, teams, or headcount. Read the **benefits catalog** (Karriere / “What we offer” / Benefits), not the req. You are scoring which tax-free perks they already administer.

Drop: open-role volume, “they’re hiring in NRW,” the 3D globe.
Keep: Deutschlandticket / JobRad present, Essenszuschuss / Edenred / Sodexo / Lunchit / Bella absent. Optional enrich: HQ is a Luma/Meetup venue *this week* (proof they assemble people — still not hiring).
Action stays: n8n lead card + German draft, **never send** (UWG §7).

### 3. Two new ideas (fresher than hiring/funding, 6h)

**F. Sachbezug Gap** (build this)
- **Signal:** Benefits page lists JobRad and/or Deutschlandticket Job, does **not** list a meal subsidy.
- **Source:** Apify crawl of `/karriere` + `/benefits` (seed: Google `Deutschlandticket Job Arbeitgeber` Berlin/MUC/NRW). Featherless: perk NER, yes/no meal.
- **Action:** n8n → CRM/Slack card + draft. No email.
- **ROI:** Unused statutory meal Sachbezug **€7.67/workday = €1,687/FTE/year** (×220). They already run payroll perks; this is one more line, not a new category.

**G. Office lunch pain**
- **Signal:** Google Maps reviews of a named HQ: “kein Kantine,” “nichts zu essen,” or the site canteen is `permanentlyClosed` while the office is open.
- **Source:** Apify Maps reviews + hours. Featherless classifies lunch-pain vs noise.
- **Action:** Same card/draft, no send.
- **ROI:** External lunch ~€15 vs **€7.67** tax-free; gap ~€7–8/head/day. Thin in Berlin — enricher, not the spine.

### 4. Final pick

**F, with D as a this-week badge on the card.** Skip A’s job crawl. B is the Apify-prize backup, not the GTM story.

**Pitch:** We ignore hiring and funding. We find employers who already run tax-free perks and still leave the meal Sachbezug empty — and we only surface them when their HQ is gathering people this week.

**Demo number:** **€1,687 unused per employee per year.**
