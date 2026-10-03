# LunchSignal

GTM Hackathon Berlin, 3 Oct 2026. Employees sign up with a work e-mail. When 5 people from one company have signed up, n8n raises a demand alert. Apify then pulls that company's job ads, Featherless extracts the listed benefits, and code sorts the company into **Gap** (perks but no food), **Switch** (already pays a meal card) or **Skip** (has food or unclear). Sales gets the result with evidence and the €7.67/workday tax-free figure.

```
n8n form ─► normalize e-mail ─► Supabase signups ─► count per company domain
   └─► 5+? ─► alert (once per company) ─► app /api/enrich (Apify job ads → Featherless → segment)
          └─► Gap / Switch / demand only ─► Slack to sales ─► Pingen letter to HR (disabled until set up)
```

## Setup (about 20 minutes once the credits are in)

1. **Supabase:** create a project and run `supabase/schema.sql` in the SQL editor.
2. **Keys** (the vault isn't set up yet: run `keys setup <infisical-project-id>` and `infisical login` in a real terminal):
   `cd app && keys new-app lunchsignal --needs supabase APIFY_TOKEN FEATHERLESS_API_KEY FEATHERLESS_MODEL ENRICH_SECRET N8N_ALERT_WEBHOOK_URL`
   The names are listed in `app/.env.example`.
3. **App:** `cd app && keys run -- npm run dev`, or deploy to Vercel. Pages: `/` is the sign-up page, `/ops` is the sales view.
4. **n8n:** import `n8n/lunchsignal-workflow.json` (Workflows → Import from file), then:
   - Set the Supabase credential on the three Supabase nodes.
   - On "Scan benefits", set a Header Auth credential: name `x-enrich-secret`, value = the app's `ENRICH_SECRET`.
   - Replace `YOUR-APP.vercel.app` and the Slack webhook URL. Or edit `n8n/build_workflow.py` and run `python3 build_workflow.py` again.
   - Activate the workflow and share the form's production URL as a QR code.
5. **First real run:** check which field names the Apify job actor returns. `app/src/lib/server/jobs.ts` logs the keys of the first result and has fallbacks. The default is `misceres/indeed-scraper`; override it with `APIFY_JOBS_ACTOR`.

## Variant: Google Form → n8n → e-mail to sales (`n8n/google-form-to-sales.json`)

1. Create the Google Form with the questions "Work email", "Office city" and a required consent checkbox. In the Responses tab, link it to a Google Sheet.
2. In `n8n/build_google_form.py`, set `SHEET_URL` (the responses sheet), `SALES_EMAIL` and optionally `APP_URL`, then run `python3 build_google_form.py`.
3. In n8n: Workflows → Import from file → `google-form-to-sales.json`. Connect Google OAuth on the trigger and on "Read all responses", and Gmail OAuth on "E-mail sales team".
4. Activate the workflow. The trigger polls every minute. On exactly the 5th different work e-mail from one company, sales gets one e-mail. The benefit scan is optional: if it fails, the e-mail still goes out.

## Main flow: Google Form → Apps Script → n8n agent (`n8n/lunchsignal-agent.json`)

1. Link the Google Form to a response Sheet. In the Sheet, open **Extensions → Apps Script** and paste `google/apps-script.gs`.
2. In Script Properties, set `N8N_WEBHOOK_URL` (the production URL of the "Form sign-up" node) and `N8N_SECRET`. Run `installTrigger()` once.
3. Set `SALES_EMAIL` and `FEATHERLESS_MODEL` in `n8n/build_agent.py`, then run `python3 build_agent.py` and import the result into n8n.
4. Credentials in n8n:
   - Header Auth `x-lunchsignal-secret` (the same value as `N8N_SECRET`)
   - Header Auth `Authorization: Bearer <Apify token>`
   - Header Auth `Authorization: Bearer <Featherless key>`
   - Gmail OAuth
5. What happens:
   - At exactly the 5th colleague, the workflow pulls the LinkedIn company profile and checks that its website matches the sign-up domain.
   - It then pulls 20 company posts and the job titles of People/HR roles.
   - Featherless writes an analysis: culture, structure, buying committee as roles, angle, a 0–100 score, and an email to the sign-ups.
   - The agent emails the people who signed up, all in BCC.
   - Sales gets a briefing when the score is 70 or higher, when the LinkedIn company can't be verified, or when the LLM output can't be used.
   - Replies are classified. Interested replies and questions go to a human.

## Checks

`cd app && npm test && npm run typecheck && npm run lint && npm run build`

## Reliability and GDPR

- The model only extracts. `src/lib/segment.ts` decides, and abstains unless there are 3+ ads with 3+ perks each.
- A food quote the model didn't copy from the ad is discarded. A failed extraction never counts as "no food".
- Ads from recruitment agencies are ignored.
- Sign-ups need consent. Freemail addresses are never grouped by company. Sales only sees counts per company, never e-mail addresses.
- No e-mail is sent to companies (UWG §7). The outreach channel is a letter to the HR department, with a suppression list.
