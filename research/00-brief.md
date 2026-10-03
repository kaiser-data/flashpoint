You are brainstorming for a one-day hackathon team. Answer in English, plain markdown, max ~900 words. You may use web search if you have it.

EVENT: "GTM Hackathon Berlin — Detect the signal. Build the agent." Main partner Apify (web scraping / Apify Store actors). Hosts include Bella&Bona (Berlin/Munich B2B office-lunch + corporate catering company, ~150+ Berlin/Munich client companies, app-ordered daily lunch delivered to offices, tax-advantaged meal benefit). Other partners: n8n (workflow automation), Featherless (serverless open-source LLMs). ~6 hours of build time (11:00–17:30), live demo required.

TRACKS:
1. Capture — find a buying signal nobody is using (job posts, changelogs, GitHub activity, regulatory filings, ...). Judged on originality and predictiveness.
2. Act — signal → enrichment → decision → action, end-to-end with no human in the loop. Must run live.
3. Weird Signals — most unexpected data source that genuinely works (audience vote).

JUDGING: Originality; "The Monday Test" (would a revenue team actually deploy it Monday?); Reliability (behaviour when wrong, GDPR compliance — Germany/EU); It Runs (live demo, no slides-only).

Note German law: unsolicited B2B cold email generally needs consent (UWG §7), so pure auto-emailing is a liability.

TASK:
A) Give 5 ORIGINAL hackathon ideas (not generic "scrape LinkedIn jobs + send email"). At least 2 should target Bella&Bona as the customer (who buys office lunch / catering?), at least 1 should target Apify itself as the customer, at least 1 should be a strong "Weird Signals" contender. For each: the signal, the concrete public data source and how to scrape it (name Apify Store actors if you know real ones), the automated action, why it passes the Monday Test, the GDPR angle, and what the 60-second live demo shows.
B) Critique this existing candidate in 5 bullets (weaknesses, what would make it win): "Lunch Desert Radar" — detect companies newly bringing people back to an office (careers-page diff remote→'3 days in office', Handelsregister Sitzverlegung/office move, Office/Workplace-Manager job posts, 'Essenszuschuss'/lunch-benefit mentions in job ads) × count of lunch options within 400 m of the office (OSM/Google Maps) → score → n8n creates CRM task + German evidence-cited message + auto-books a free tasting lunch to the office. Backtest against Bella&Bona's public case-study customers.
C) Pick your single best idea overall and say why in 3 sentences.
