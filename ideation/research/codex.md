**My recommendation: build around a temporary loss of lunch supply.** It creates a dated reason to buy, and the demo can show both a useful action and a correctly rejected false positive. These are hypotheses to validate, not proven predictors.

**A) Five ideas**

**1. Canteen Blackout — Bella&Bona; Capture + Act**

- **Signal:** An office campus’s canteen announces a closure while tenant companies remain operational.
- **Source/scraping:** Campus dining pages, such as Adlershof’s public menu PDFs, plus tenant directories. Use [`apify/cheerio-scraper`](https://apify.com/apify/cheerio-scraper) to discover links and a custom Actor to extract PDF text. An [indexed closure notice](https://www.adlershof.de/fileadmin/user_upload/downloads/essen/sonnenschein.pdf) is historical—useful for testing stale-date rejection.
- **Action:** Match affected offices; check delivery coverage; create an evidence-cited CRM opportunity and a dated replacement-lunch offer in an authorized customer portal.
- **Monday Test:** Workplace managers face a specific service gap. Exclude holidays when offices also close.
- **GDPR:** Store company locations and closure dates; discard personal contact details.
- **60-second demo:** Fetch notice → extract dates → identify offices → publish sandbox offer; reject the old PDF.

**2. Catering Promise Monitor — Bella&Bona; Capture + Act**

- **Signal:** A company-hosted event adds another day or increases announced capacity while continuing to promise lunch.
- **Source/scraping:** Public Luma pages and corporate event calendars. [This Berlin HackDay page](https://lu.ma/6zgt3qp8) illustrates explicit agenda and food information, though it is historical. Use `apify/cheerio-scraper` for accessible HTML or `apify/playwright-scraper` for rendered pages; retain snapshots.
- **Action:** Identify the organizer, estimate incremental portions as a range, and generate a capacity-checked catering quote in its authorized portal.
- **Monday Test:** An event owner has a deadline and a changed requirement. Suppress events with a named exclusive caterer.
- **GDPR:** Never scrape attendee lists; capacity is not confirmed attendance.
- **60-second demo:** Agenda diff → portion range → quote; unchanged event produces no duplicate.

**3. Scraper Maintenance Tax — Apify; Capture + Act**

- **Signal:** A company repeatedly patches selectors or pagination in its public scraper, suggesting recurring maintenance expense.
- **Source/scraping:** Company-owned public GitHub repositories: commit diffs, dependency manifests and issues. A custom Apify Actor calls GitHub’s API against a small repository allowlist.
- **Action:** Match the extraction target to an existing Store Actor, run a capped sample against permitted public data, compare output fields, and create a migration opportunity with working sample data.
- **Monday Test:** Apify sells relief from demonstrated maintenance work. Require repeated repairs and verified company ownership; hobby projects are weak leads.
- **GDPR:** Remove author identities and emails; no automated promotional issue comments.
- **60-second demo:** Repair history → matching Actor → successful dataset → CRM opportunity, with failure blocking the recommendation.

**4. Lunch Drawbridge — Bella&Bona; Weird Signals**

- **Signal:** A pedestrian bridge closure suddenly makes nearby lunch options a long walk away.
- **Source/scraping:** Official Berlin bridge notices plus OpenStreetMap pedestrian paths and eateries. The [Dunckerbrücke notice](https://www.berlin.de/sen/uvk/mobilitaet-und-verkehr/infrastruktur/brueckenbau/dunckerbruecke/) explicitly describes pedestrian diversions. Scrape notices with Cheerio; fetch OSM through Overpass.
- **Action:** Recalculate walking access, rank affected offices, verify delivery access, and generate temporary lunch offers for authorized customer accounts.
- **Monday Test:** Detects a change that restaurant counts within a radius miss. Employee demand remains an inference.
- **GDPR:** Use office addresses, never employee movement data.
- **60-second demo:** Remove one bridge edge; routes lengthen; affected accounts appear. A vehicle-only closure correctly triggers nothing.

**5. Nobody Bid — commercial cleaning suppliers; Capture**

- **Signal:** A procurement lot receives no bids, then reappears with relaxed requirements or smaller lots.
- **Source/scraping:** TED result notices and subsequent tenders. A custom Actor uses the [public Search API](https://docs.ted.europa.eu/api/latest/search.html), downloads notice XML and links procedure identifiers.
- **Action:** Compare changed requirements against supplier capabilities; automatically create a qualified bid workspace, evidence checklist and deadline reminders.
- **Monday Test:** Suppliers see newly attainable opportunities. A cancelled requirement without a live replacement is rejected.
- **GDPR:** Retain institutional requirements; strip named procurement contacts.
- **60-second demo:** Failed lot → replacement notice → changed eligibility → populated bid workspace. Formal bid submission remains outside the prototype.

Across all five, public personal data still needs a lawful basis, minimization, retention limits and applicable transparency/objection handling under [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj). Email requires a separately verified permission basis under [UWG §7](https://www.gesetze-im-internet.de/uwg_2004/__7.html); a public address or existing CRM record is insufficient.

**B) Lunch Desert Radar: five critiques**

- **Too many weak proxies:** Remote-policy wording, workplace hiring and benefits mentions need not indicate new demand. Make one dated operational change the trigger.
- **Address ambiguity:** Registered-seat changes do not prove an occupied office moved. Corroborate the actual workplace and delivery address.
- **“400 metres” misleads:** Check walking routes, lunchtime opening hours, affordability and private canteens. Missing map data is uncertainty, not zero supply.
- **Auto-booking undermines reliability:** Never dispatch an unsolicited tasting. Automatically create a bookable offer; schedule only after explicit acceptance and capacity checks.
- **Case studies cannot establish predictiveness:** They are selected positives. Add matched noncustomers, use evidence predating purchase, and measure precision, lead time and false positives.

**C) Best overall**

Choose **Canteen Blackout**: it connects a dated operational problem to a named buyer and a straightforward product. It offers a credible six-hour build using one campus, one extractor and one n8n workflow, with Featherless limited to evidence-backed extraction. Spend the first 30 minutes finding a current qualifying notice; demonstrate a real offer workflow and explicit abstention when evidence is stale or ambiguous.
