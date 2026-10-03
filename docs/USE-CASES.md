# Where Flashpoint can go next

Lesson from the hackathon: the agent was solid, but its headline signal (colleagues signing up on Kredible's form) had no real data on the day. We generated it with `tests/fill-form.js`. So every use case below has to pass one test first:

> **Day-0 probe:** before building, find at least 5 real, current instances of the signal in public data, by hand or with one Apify run. No instances, no build.

## What can be reused

| Part | File | Reusable for |
|---|---|---|
| Config-driven main workflow (trigger → Apify research → scorecard → analysis → act) | `n8n/build_critical_mass.py`, `n8n/configs/` | Any account-scoring use case; change the CONFIG block |
| Signal Watch: scheduled searches that rate their own hit rate and retire dead queries | `n8n/watch.py` | Any public signal that shows up in news or on web pages |
| Scorecard in code, with the model only explaining it | main workflow, *Signal scorecard* node | Any use case where the model should not decide alone |
| Eval: 7 rule checks + a second-model judge | `n8n/flashpoint-eval.json`, `tests/evaluate.py` | Quality gate for any LLM sales output |
| Reply learning: positive-reply rate per signal and per angle | *Learned playbook* node | Any outbound loop |
| Domain clustering of sign-ups | `google/flashpoint-sheet.gs` | Only where a **real** sign-up stream exists |

## Candidates, ranked by how real the signal is today

| # | Use case | Signal (public) | Real today? | Buyer | Reuse |
|---|---|---|---|---|---|
| 1 | **Public tenders (B2G sales)** | New TED notices in your CPV codes; awards to competitors, with contract end dates (next re-tender window) | Yes: about 80,000 notices a month, TED API v3 is free and needs no key, several Apify TED actors exist | Any vendor that sells to the public sector | Signal Watch → TED; scorecard on CPV fit, value, deadline; briefing as is |
| 2 | **Kredible v2: unfilled seats** | A university's own pages: "Bewerbungsfrist verlängert", "Restplätze", "freie Plätze" after semester start | Yes: e.g. Gießen extended Master deadlines from 1 to 20 Sep 2026 | Kredible | Flip the scorecard: website signals lead, sign-ups become a bonus. Most of the build exists |
| 3 | **Bella&Bona: benefit gap** | Job ads in their cities that list benefits but no meal subsidy, plus office-attendance wording | Likely: job boards can be scraped with Apify. Needs the Day-0 probe | Bella&Bona | Ideation idea #1 (17/20), the strongest one we skipped |
| 4 | **PLG: several colleagues on a free plan** | Your own product's sign-ups, clustered by company domain | Only for a product with real sign-ups | Any SaaS with a free tier or newsletter | The critical-mass core unchanged. Proven pattern, so less original |
| 5 | **Leadership change → buying window** | New managing director or head of a function (LinkedIn posts, Handelsregister) | Yes, but the register refreshes about monthly, so it is slow, and it is crowded | Generic B2B | LinkedIn actors already wired in |

## Recommendation

1. **Tenders (#1)** if you want a product: the data is high-volume, structured and free, the buying intent is explicit, and there is no GDPR question because the contracting bodies are public bodies.
2. **Kredible v2 (#2)** if the Kredible relationship is the point: a 1–2 day change, and the demo no longer needs synthetic sign-ups.

## Sources

- [Uni Gießen: Master programmes with free places, extended deadlines](https://www.uni-giessen.de/de/studium/studienangebot/content/ma/frei_sommer)
- [Uni Saarland: current application deadlines WiSe 2026/27](https://www.uni-saarland.de/studium/bewerbung/aktuell.html)
- [TED in Germany, API v3 overview (auftrag.ai)](https://auftrag.ai/en/blog/ted-tenders-germany-guide)
- [Apify: TED Tender Scraper](https://apify.com/siccscha/ted-tender-scraper)
- [OpenRegister: Handelsregister coverage and update frequency](https://docs.openregister.de/coverage)
