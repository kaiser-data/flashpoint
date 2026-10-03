### A) 5 Original Hackathon Ideas

---

#### 1. The "Office Meetup Host" Emergency Catering Agent
*Target: Bella&Bona | Track: Act / Capture*
* **The Signal:** Companies hosting 40+ person after-hours events (AI demo nights, hackathons, founder breakfasts) at their corporate offices within the next 7–14 days. Event hosts have immediate, pre-allocated catering budgets and urgent stress.
* **Data Source & Scraping:** Scrape **lu.ma**, **Eventbrite**, and **Meetup.com** Berlin/Munich feeds using the Apify `apify/web-scraper` or community event actors. Filter venue addresses matching commercial office buildings (cross-referenced against corporate domains).
* **Automated Action:** n8n takes the event date, attendee count, and host company name, drafts a custom B2B finger-food catering proposal, and triggers a physical branded tasting package (or courier sample box via Wolt Drive / Sendcloud API) addressed directly to *"Event & Office Host @ [Company]"*.
* **Monday Test:** Immediate conversion: event budgets are approved instantly, and catering a successful evening meetup is the #1 trojan horse into daily team lunch contracts.
* **GDPR Angle:** Physical post/courier delivery to corporate addresses complies fully with German UWG §7 (unlike unsolicited cold emails).
* **60-Second Live Demo:** Input a live Berlin lu.ma URL for next Thursday $\rightarrow$ Agent parses venue, extracts host company $\rightarrow$ n8n outputs PDF quote for 65 portions + triggers a courier label in 5 seconds.

---

#### 2. The "Hygiene Pranger" Lunch Evacuation Radar
*Target: Bella&Bona | Track: Weird Signals*
* **The Signal:** German public food authorities publish mandatory consumer warnings (*Lebensmittelüberwachung / "Pranger"*, e.g., Berlin *Verbraucherschutzberichte* / *Pankow & Mitte Pranger*) citing neighborhood restaurants for severe hygiene/health violations. When a canteen or popular döner/salad spot on an office block gets cited, dozens of adjacent tech companies suddenly lose their primary lunch option.
* **Data Source & Scraping:** Scrape official regional food safety portals (*berlin.de/verbraucherschutz/aufsicht/lebensmittelueberwachung*) via Apify `cheerio-scraper`.
* **Automated Action:** Geocode the flagged eatery, find all companies within a 300m radius via OpenStreetMap/Google Places, and generate a hyper-localized B2B direct mailer: *"Your neighborhood lunch options just got complicated. Switch to verified, HACCP-certified daily office catering with zero kitchen hassle."*
* **Monday Test:** High emotional urgency and zero sales resistance; companies actively seek clean alternatives the same week.
* **GDPR Angle:** Geo-targeted LinkedIn InMail to local HR managers or physical B2B postcards; no illegal cold scraping of private emails.
* **60-Second Live Demo:** Scrape the latest official hygiene report $\rightarrow$ map flags 4 scale-ups within 300m $\rightarrow$ automated n8n pipeline spits out personalized postcards citing the exact local food void.

---

#### 3. The Kununu "Kantine & Microwave Queue" Frustration Monitor
*Target: Bella&Bona | Track: Capture*
* **The Signal:** Employee review sentiment drift. Detect negative review spikes on **Kununu** and **Glassdoor** explicitly complaining about *“Küche dreckig”*, *“keine Kantine”*, *“lange Schlangen an der Mikrowelle”*, or *“Benefits wurden gekürzt”*.
* **Data Source & Scraping:** Apify `apify/google-search-scraper` querying `site:kununu.com [Berlin OR Munich] "Küche" OR "Mittagessen" OR "Kantine"` or targeted Kununu page parsing.
* **Automated Action:** Featherless open-source LLM extracts specific workplace friction points, calculates the exact German tax advantage (§ 8 Abs. 2 EStG meal allowance: up to €7.23/day tax-free per employee), and generates an executive PDF briefing for the People Ops lead.
* **Monday Test:** Directly equips HR with an employer-branding solution to fix concrete public complaints harming their hiring score.
* **GDPR Angle:** B2B outreach via LinkedIn connection requests citing public review trends; no PII harvesting.
* **60-Second Live Demo:** Agent ingests a real 2-star Kununu review mentioning poor lunch options $\rightarrow$ instantly produces a 1-page ROI flyer showing how a Bella&Bona subsidy fixes employee retention.

---

#### 4. The "403 Forbidden" Broken Scraper Interceptor
*Target: Apify | Track: Capture / Act*
* **The Signal:** Engineering teams pushing desperate commits or opening public issues struggling with Cloudflare, DataDome, or IP bans when scraping competitors/APIs.
* **Data Source & Scraping:** Scrape **GitHub public commits & issues**, **StackOverflow**, and **Hacker News** via Apify `apify/github-issues-scraper` matching queries: `status 403 Cloudflare scraper`, `Puppeteer blocked`, or `Playwright bot detection`.
* **Automated Action:** Agent extracts the target site, matches it against existing actors in the Apify Store (e.g., ready-made Instagram/Amazon scrapers or Apify Proxy with anti-scraping bypass), and drafts a tailored technical PR or GitHub comment with a runnable 10-line code fix.
* **Monday Test:** Targets developers at the exact micro-moment of tool failure when their willingness to adopt a paid cloud scraper platform is at 100%.
* **GDPR Angle:** Public developer interactions on open-source repositories; zero personal email marketing.
* **60-Second Live Demo:** Live search finds a GitHub issue opened 3 hours ago complaining about scraping blocks $\rightarrow$ Agent benchmarks target URL $\rightarrow$ outputs ready-to-deploy Apify SDK script bypassing the bot wall.

---

#### 5. The "Pricing Page Stealth A/B" Hunter
*Target: Apify | Track: Act*
* **The Signal:** Fast-growing e-commerce & B2B SaaS companies changing their pricing models or launching unannounced tier tests.
* **Data Source & Scraping:** Apify `apify/web-scraper` monitoring the `/pricing` subdirectories of top 1,000 EU scale-ups, diffing DOM changes.
* **Automated Action:** Featherless LLM summarizes competitor price hikes or feature tiering changes and drafts a ready-to-sell intelligence report for competitive intelligence teams, pitching Apify’s automated site-monitoring infrastructure.
* **Monday Test:** Solves enterprise competitive intelligence pain out of the box.
* **GDPR Angle:** Fully public corporate web data; outreach directed to B2B company accounts.
* **60-Second Live Demo:** Run diff on a live site that updated prices yesterday $\rightarrow$ LLM extracts pricing strategy shifts $\rightarrow$ dispatches Slack alert with complete competitive breakdown.

---

### B) Critique of "Lunch Desert Radar" (5 Bullets)

1. **Pipeline Over-Engineering for 6 Hours:** Combining four complex data sources (Handelsregister corporate moves, career page diffs, job board scraping, and OSM radius calculation) creates severe pipeline fragility; a single timeout or schema break during the live demo will kill the presentation.
2. **Handelsregister Sitzverlegung is a Lagging Signal:** Corporate register updates in Germany often take 4–12 weeks to be published; by the time a *Sitzverlegung* is gazetted, the company has already moved in and established office habits.
3. **The "Auto-Book Free Lunch" Operational Flaw:** Unsolicited catering drop-offs create food waste and security friction (receptionists reject unannounced packages, unknown allergies, dietary splits); auto-booking must be downgraded to **auto-shipping an unperishable tasting kit** or generating a **one-click voucher code**.
4. **German UWG §7 Compliance Risk:** Automated cold emailing to newly discovered Office Managers without prior consent violates German anti-spam regulations. The action must switch to physical postal marketing (*Infopost / Postkarte*) or LinkedIn invitations.
5. **What Makes It Win:** Cut data sources down to just **Job Posts (Office Manager / Back-to-Office) $\times$ Google Maps Restaurant Density**, and present it as an interactive live "Lunch Desert Map" of Berlin calculating the exact tax-free Sachbezug savings on the fly.

---

### C) Single Best Idea Overall

**Idea #1 (The "Office Meetup Host" Emergency Catering Agent)** is the strongest hackathon winner because it targets immediate, non-negotiable catering budgets with hard deadlines (<14 days), converting public event organizers who are actively stressed about food. It sidesteps German cold-emailing legal hurdles by triggering high-value physical sample boxes or courier vouchers straight to the office venue. Most importantly, it is 100% buildable and provable in a 60-second live demo using standard Apify event scrapers, an n8n webhook, and Featherless LLM parsing.
