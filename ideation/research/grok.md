I'll ground the five ideas in real public sources and actual Apify Store actors so the demo path is buildable in six hours, not generic scraping advice.Unsolicited B2B email needs consent under UWG §7. Every idea below stops inside the building: a CRM task, a Slack card, a proposal draft. A human sends anything outward. That is the version a German revenue team can turn on Monday.

## A. Five ideas

### 1. Speiseplan Swap — Weird Signals, customer Bella&Bona

**Signal.** The incumbent caterer is named on a public menu, and that name just vanished. Employers and operators (Sodexo, Eurest/Compass, Aramark, Dussmann, Klüh) publish the weekly Speiseplan. A 404, "Kantine geschlossen", or the operator string disappearing means the food contract is in play.

**Scrape.** One-time discovery with `apify/google-search-scraper` (`Speiseplan Kantine Berlin`). Then `apify/website-content-crawler` on a schedule, diff the text. Live second source: `compass/crawler-google-places` for canteen/cafeteria with permanently-closed set. OSM `amenity=canteen` via Overpass is a free extra; mapper deletions are noisy, so treat them as weak.

**Action.** n8n writes one CRM card: operator, last menu date, address, inside the delivery area or not, confidence. A Featherless pass extracts the operator and abstains if it cannot name one. No email, no tasting dispatched.

**Monday.** Catering deals are won on displacements. A rep will work "Sodexo fell off the PDF" before another hybrid-work job ad.

**GDPR.** Corporate pages and map places. Strip personal names before storage. Keep company, address, operator, URL, date.

**60s.** A real Speiseplan beside yesterday's crawl, or a Maps canteen marked closed. Slack card shows the quoted line and "nothing sent".

### 2. Subsidy Gap — customer Bella&Bona

**Signal.** Benefits already include Deutschlandticket, Jobrad, or Wellpass, and do not mention Essenszuschuss, while the role is on-site. Absence is the signal. The buyer is HR/payroll, which is who turns office lunch on. Bella&Bona's published setup is a daily meal subsidy under §8 and §40 EStG; quote their page, don't invent tax advice.

**Scrape.** `clearpath/stepstone-de-job-scraper` (structured benefits, home-office flag, company size band). Careers page via `apify/website-content-crawler` only if StepStone is thin.

**Action.** Drop if the size band is under ~30 or the city is outside Berlin, Munich, and NRW. Otherwise draft their proposal skeleton into a CRM task.

**Monday.** A fresh list every morning, matched to how they already sell: one invoice and a subsidy, not "you have no restaurants".

**GDPR.** Store company, title, benefit tags, URL. Drop recruiter names and any email in the ad. No message goes out, so §7 is not triggered. Delete after 90 days.

**60s.** Live StepStone pull. A too-small company is rejected on screen. One passing firm produces the CRM payload.

### 3. Second seat in the Impressum — customer Bella&Bona

**Signal.** The legally required Impressum gained a Berlin or Munich address, or the registered seat moved. Earlier than a press release.

**Scrape.** `apify/website-content-crawler` on `/impressum`, diffed in an Apify key-value store. Confirm with `corent1robert/germany-handelsregister-scraper` (current seat, legal form). That actor is a snapshot, not a history; the diff has to be yours.

**Action.** CRM task quoting the old line and the new line. Suppress known virtual-office providers and tiny headcount.

**Monday.** "New office" is the trigger reps already hunt by hand.

**GDPR.** Keep the address change. Managing-director names are personal data even though published: leave them out of the draft, and do not build a director file.

**60s.** Two Impressum versions in, only the new Berlin line highlighted. A domiciliation address is rejected.

### 4. Unanswered Scrape — customer Apify

**Signal.** Someone asked today how to scrape a specific site, and the Store has no maintained actor for that domain. Marketplace demand, visible before the wrong actor gets built.

**Scrape.** Hacker News Algolia API (`search_by_date` on "scrape") — no actor needed. Optional: `korado_labs/reddit-scraper`. Match the domain with `apify/google-search-scraper` (`site:apify.com/store {domain}`) or `apify/rag-web-browser`.

**Action.** Fully unattended, because the recipient is Apify. n8n posts a Store-gaps Slack card and a draft actor brief (domain, example URL, input fields, README stub via Featherless). Do not message the person who asked.

**Monday.** DevRel can sponsor or recruit an actor author from a queue instead of scrolling HN.

**GDPR.** Store domain, post URL, timestamp. Discard usernames.

**60s.** Today's HN hit, Store search returns nothing, the brief lands in Slack.

### 5. Dated all-hands — customer Bella&Bona (catering wedge)

**Signal.** A public page names a date, a city, and a reason the whole office will be in one room within 21 days: all-hands, office warming, Teamtag. One catering job is the door into daily lunch.

**Scrape.** `apify/google-search-scraper` (past week) plus `apify/website-content-crawler` on the hits. Featherless extracts date, city, and headcount only when the page states them.

**Action.** Catering-desk card. Unknown headcount stays "unknown". Do not post into their contact form; that is the same §7 problem as email.

**Monday.** Events expire, so the list does not rot.

**GDPR.** Public company announcements only. Drop organizer emails. Skip a private person's LinkedIn post.

**60s.** A real event page in, card out, headcount blank, no send button.

## B. Lunch Desert Radar

- Auto-booking a tasting at an office that did not ask is the defect. A drafted, evidence-cited German note in the CRM is fine. Dispatch is not. The demo should show the system refusing to send.
- A count of lunch places within 400 m points at the wrong buildings. Buyers are offices of about 30+ in Berlin and Munich, which are full of restaurants. They pay for the subsidy, one invoice, and dietary coverage. The score will up-rank business parks and miss the real competitor, an in-house canteen, which does not look like a restaurant cluster.
- "3 days in office" and Workplace Manager ads are standard copy. A template edit across every req looks like a change and is not. Essenszuschuss already in the ad often means they already have a vendor.
- Backtesting on public case-study logos cannot show that it works. Those are the wins, the sample is small, and nothing shows the companies that matched and never bought. Run the same rules on non-customers, and suppress current customers, or the score flatters you.
- Failure behavior is missing, and the inputs are personal. Recruiter names, ad emails, and Handelsregister directors will sit in the CRM unless stripped. An ambiguous diff should create no task. It wins if it keeps company-level fields only, adds a confidence floor, replaces the radius with a named incumbent canteen, and shows one wrong input producing nothing.

## C. Best bet

Build **Speiseplan Swap**. It is the only signal here that means a food contract is actually moving, a judge can see it in one before/after quote, and half the room will scrape job ads. Use the Maps closed-canteen query so the live demo does not depend on catching a rare 404 during the show, and let the agent abstain whenever it cannot name an operator.