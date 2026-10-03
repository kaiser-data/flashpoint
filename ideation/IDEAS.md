# GTM Hackathon Berlin: ideas from four models

## Ratings (2026-10-03, after the fact check)

Score = the four judging criteria at 1–5 each, maximum 20. "Proposed by" counts how many of the four models suggested the idea; the more of them, the more teams are likely to build it too.

| # | Idea | Originality | Monday Test | Reliability/GDPR | Runs live | Total | Proposed by |
|---|---|---|---|---|---|---|---|
| 1 | **Benefit Gap × office return**: job ads in Bella&Bona's cities (including NRW, launched 1 Oct) that list other benefits but no meal subsidy, plus "days in office" wording | 3 | 5 | 4 | 5 | **17** | Grok, Claude |
| 2 | **Apify Store gap**: people asking how to scrape a site that has no Store actor yet; the agent writes an actor brief for Apify | 4 | 4 | 5 | 4 | **17** | Grok |
| 3 | **Office event host**: Luma or Meetup events at company offices | 2 | 4 | 4 | 5 | **15** | all 4 |
| 4 | **Canteen closure**: Google Maps closed status or a menu page change | 5 | 4 | 3 | 2 | **14** | Codex, Grok |
| 5 | **Competitor shutdown** (Smunch customers) | 4 | 3 | 4 | 1 | 12 | research agent |
| 6 | **Restaurant hygiene notices** | 5 | 1 | 1 | 4 | 11 | Gemini |
| 7 | **Apify: GitHub issues about 403s and captchas** | 2 | 3 | 2 | 4 | 11 | all 4 |
| 8 | **Lunch Desert Radar** (original) | 3 | 2 | 2 | 3 | 10 | Claude |

Recommendation: idea 1 as the core, with idea 3 as a second lane that shows a new signal arriving live during the demo. Run idea 4 only if a probe on the morning shows real data. Pick idea 2 instead if the team would rather build for the Apify judges.
Facts behind the ratings:
- Bella&Bona opened NRW on 1 Oct 2026.
- The tax-free meal subsidy is €7.67 per day in 2026.
- The case-studies page is a 404. Only 5 customer logos are public.
- Only 46 canteens are mapped in Berlin on OpenStreetMap, nearly all university Mensas.
- About 1 in 20 Berlin events on Luma is hosted at a company office.

Event: https://luma.com/co-9b47 · Partners: Apify (main), Bella&Bona, n8n, Featherless.
Tracks: Capture / Act / Weird Signals.
Judging: Originality, Monday Test, Reliability (including GDPR), It Runs.
Raw answers are in `research/` (`codex.md`, `grok.md`, `gemini-antigravity.md`). All four models (Claude, Codex, Grok, Gemini) got the same brief: `research/00-brief.md`.

## Where the models agree

| Idea | Proposed by | Comment |
|---|---|---|
| **Companies hosting events in their own office** (Luma or Meetup event at a company office, with food) | Claude, Gemini (its top pick), Codex, Grok | All four came up with it, so other teams will too. Strong as a second lane, not as the main idea. |
| **A company's lunch supply disappears**: a canteen closes, a caterer vanishes from the menu page, a nearby restaurant is shut down for hygiene | Grok (its top pick), Codex (its top pick), Gemini | The newest and strongest signal. It means food budget is about to move, so a sales team can act on it on Monday. |
| **Apify finds companies whose own scrapers keep breaking**: GitHub issues about 403s or captchas, selector fixes | Claude, Codex, Gemini, Grok (variant: "nobody has built a scraper for this site yet") | A good pitch to the Apify judges. |

## What they all criticised in "Lunch Desert Radar"

1. **Auto-booking a tasting lunch** for an office that never asked is the weak point. Create a bookable offer and a CRM task instead, and dispatch only after the office accepts. Gemini's alternative is a voucher code or a non-perishable kit.
2. **Counting restaurants within 400 m** is a poor measure in Berlin, where offices are surrounded by restaurants. The real competitor is the in-house canteen.
3. **Too many sources for 6 hours.** Also, Handelsregister has no ready-made feed of office moves (Sitzverlegung), the registered seat is not the same as the actual office, and the notices are published weeks late.
4. **The case-study backtest only contains wins.** It needs matched companies that never bought, and the result should be reported as precision and lead time.
5. **Show the agent holding back.** For the Reliability criterion, the demo should include one wrong input that produces no action.

## Recommendation: "Lunch Supply Shock" with one engine and two signal lanes

- **Lane A, lunch supply is gone (main idea):** use `compass/crawler-google-places` (630k users) to search "Kantine / Betriebsrestaurant Berlin" and check whether each result is marked permanently or temporarily closed. Add changes to company menu pages (Speiseplan) detected with `apify/website-content-crawler` plus a stored snapshot to compare against. Result: which nearby offices have lost their lunch option.
- **Lane B, a dated event needs food (second lane):** `lexis-solutions/lu-ma-scraper` and `filip_cicvarek/meetup-scraper` find events hosted at company offices in Berlin. Demo moment: the tool flags this hackathon.
- **Decision:** a Featherless model only extracts facts and abstains when unsure. Plain code does the scoring, and anything below the confidence threshold produces no action.
- **Act (n8n + `@apify/n8n-nodes-apify`):** a CRM card citing the evidence, a German message draft and a bookable tasting-offer link. **Nothing is sent automatically** (UWG §7). Physical mail or a courier is a possible later step.
- **Reliability slide:** precision measured on matched customers and non-customers, plus a live example of the agent rejecting a stale or ambiguous input.

## Facts checked vs. not checked

- **Verified by fetching the Apify Store pages:**
  - `compass/crawler-google-places`, `curious_coder/linkedin-jobs-scraper`, `lexis-solutions/lu-ma-scraper`, `filip_cicvarek/meetup-scraper`, `sian.agency/website-change-monitor`, `memo23/handelsregister-scraper`, `solidcode/northdata-scraper`, `glassventures/wayback-machine-scraper`
  - n8n integration: the Apify community node `@apify/n8n-nodes-apify`
  - Apify MCP server: https://mcp.apify.com
  - Featherless is OpenAI-compatible: `https://api.featherless.ai/v1`
- **Not checked:**
  - Actor names suggested by the models: `clearpath/stepstone-de-job-scraper`, `corent1robert/germany-handelsregister-scraper`, `korado_labs/reddit-scraper`, `apify/github-issues-scraper`. The last one is probably invented; the verified GitHub actor is `fetch_cat/github-issues-pull-requests-scraper`.
  - Gemini's "€7.23/day" is the 2024 value. For 2026 it is **€7.67** (€4.57 + €3.10; Haufe, and Bella&Bona's own office-lunch page).
  - Whether the Berlin food-inspection warning lists ("Pranger") still exist and can be scraped.
- **Weak actors** (few users, low success rate): Kununu, OSM, StepStone, GitHub. Run each one once in the morning.

## Round 2 (event day, with the official criteria and the point that ROI is the key factor)

- **Both reviewers:** A built on job ads is the hiring signal Clay already sells (originality 2). Drop the globe.
- **Grok:** build **F "Sachbezug Gap"** (16 points). Read company benefits pages: the company lists JobRad or Deutschlandticket but **no** meal subsidy. Add D ("event at their office this week") as a badge on the card.
- **Codex:** prefers B, reworked into a detector for public posts that describe what a scraping workaround costs (16).
- **Claude's synthesis:** F as the core. Signal → pain → decision:
  - The company already administers tax-free perks, so People Ops is used to deciding on them.
  - Q4 is when benefits are planned for 1 January.
  - ROI comes from Bella&Bona's own claim: 50 employees save about €33,000/year compared with a raise. This is their figure, not one we measured.
- **Scalability:** measure it live. Every Apify run returns its cost (`usageTotalUsd`). Show cost per 1,000 companies scanned and per qualified lead.
- Raw answers: `research/grok-review.md`, `research/codex-review.md`.

## Round 3: data probe at 10:50
- Careers pages are unreliable: Holidu (a Bella&Bona customer) lists no benefits, and trivago returns 403. StepStone ads list full benefits, including Pluxee meal vouchers and canteens.
- **F+ "Benefit Stack Radar"** (BuiltWith for employee benefits):
  - Benefits are read from job ads.
  - Segments: **Gap** (perks but no food), **Switch** (pays through a meal card: Pluxee, Edenred, Lunchit) and **Skip**.
  - A missing benefit only counts if the company has at least 3 ads, each listing at least 3 perks.
- **Act:** Pingen has an official n8n node, so n8n can send a letter to the HR department with a QR code to the company's ROI page. No email (UWG §7).
- **Cost:**
  - Featherless is a flat subscription ($25 a month, 4 parallel requests, unlimited tokens).
  - Job-ad actors cost $1–5 per 1,000 ads.
  - Letters are the only variable cost. The price per letter in Germany is unknown.

## GTM leaders' problems → Apify + n8n (round 4)
1. Everyone uses the same signals (Clay templates) → own sources, own scoring
2. Signals arrive too late → scheduled runs + webhooks → instant action in n8n
3. Bad, decaying CRM data → regular re-crawls, deduplication
4. AI personalization without proof → a source for every statement
5. Deliverability + UWG §7 → other channels (letter, ads, CRM task)
6. Tool costs / unclear ROI → pay per result, live cost per lead
7. **Churn goes unnoticed → Customer watch: the same pipeline on existing customers** (new lane for F+)
8. New markets with no map → full scan of NRW
