"""Generates google-form-to-sales.json: Google Form (responses sheet) -> n8n conditions -> e-mail to sales.
Edit the constants, run `python3 build_google_form.py`, import the JSON into n8n."""
import json, uuid

SHEET_URL = "https://docs.google.com/spreadsheets/d/REPLACE_SHEET_ID/edit#gid=0"  # the Form's responses sheet
SALES_EMAIL = "sales@example.com"
APP_URL = "https://YOUR-APP.vercel.app"   # optional benefit scan; leave as is to skip (step fails softly)
THRESHOLD = 5

def uid(): return str(uuid.uuid4())
def rl(url): return {"__rl": True, "mode": "url", "value": url}
def cond(left, op, right=None, typ="string"):
    c = {"id": uid(), "leftValue": left, "operator": {"type": typ, "operation": op}}
    if right is None: c["operator"]["singleValue"] = True; c["rightValue"] = ""
    else: c["rightValue"] = right
    return c
def conds(*cs): return {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                        "conditions": list(cs), "combinator": "and"}

DOMAIN_FN = r'''
const FREEMAIL = new Set(["gmail.com","googlemail.com","gmx.de","gmx.net","web.de","yahoo.com","yahoo.de",
  "outlook.com","outlook.de","hotmail.com","hotmail.de","live.com","icloud.com","me.com","t-online.de",
  "posteo.de","mailbox.org","proton.me","protonmail.com","aol.com","freenet.de"]);
const MULTI = new Set(["co.uk","com.au","co.at","ac.uk"]);
function emailOf(row) {
  const key = Object.keys(row).find(k => /mail/i.test(k));
  return String(row[key] ?? "").trim().toLowerCase();
}
function domainOf(email) {
  const host = email.includes("@") ? email.split("@").pop() : "";
  if (!/^[a-z0-9.-]+\.[a-z]{2,}$/.test(host)) return null;
  const labels = host.split(".");
  const lastTwo = labels.slice(-2).join(".");
  const reg = MULTI.has(lastTwo) && labels.length >= 3 ? labels.slice(-3).join(".") : lastTwo;
  return FREEMAIL.has(reg) ? null : reg;
}
'''.strip()

normalize_js = DOMAIN_FN + r'''

// One item per new form response. Private addresses get company_domain = null.
return $input.all().map(item => {
  const row = item.json;
  const email = emailOf(row);
  const cityKey = Object.keys(row).find(k => /city|stadt|office/i.test(k));
  return { json: { email, company_domain: domainOf(email), city: cityKey ? row[cityKey] : null, row_number: row.row_number } };
});
'''

count_js = DOMAIN_FN + f'''

// Distinct e-mails per company up to and including each new row. The alert fires on exactly the
// {THRESHOLD}th distinct colleague, so repeat sign-ups and later sign-ups never fire it again.
const all = $input.all().map(i => i.json);
const fresh = $('Company e-mail?').all().map(i => i.json);
const out = [];
for (const s of fresh) {{
  const seen = new Set();
  for (const r of all) {{
    if (s.row_number != null && r.row_number > s.row_number) continue;
    const e = emailOf(r);
    if (domainOf(e) === s.company_domain) seen.add(e);
  }}
  out.push({{ json: {{ ...s, colleagues: seen.size, reached: seen.size === {THRESHOLD} }} }});
}}
return out;
'''

compose_js = f'''
// Builds the sales e-mail. Works with or without a benefit scan result.
const scan = $input.item.json;
const base = $('Count colleagues').item.json;
const seg = scan && scan.segment ? scan.segment : null;
const label = {{ gap: "GAP: pays other perks, no food benefit", switch: "SWITCH: already pays a meal card",
                 skip: "SKIP: already provides food", unknown: "UNCLEAR: not enough evidence" }}[seg] ?? "Benefit scan not available";
const reasons = (scan.reasons ?? []).map(r => `<li>${{r}}</li>`).join("");
const perks = (scan.perks ?? []).slice(0, 8).join(", ");
const html = `
<p><b>${{base.colleagues}} people at ${{base.company_domain}}</b> signed up for office lunch (office city: ${{base.city ?? "n/a"}}).</p>
<p><b>Benefit scan:</b> ${{label}}</p>
${{reasons ? `<ul>${{reasons}}</ul>` : ""}}
${{perks ? `<p><b>Perks they already offer:</b> ${{perks}}</p>` : ""}}
<p>Tax-free lunch benefit 2026: up to €7.67 per employee per workday (§8 Abs. 2 / §40 Abs. 2 EStG).</p>
<p style="color:#666">Company-level signal only. Individual sign-ups are not shared. Contact the company's People team, not the people who signed up.</p>`;
return {{ json: {{ subject: `${{base.colleagues}} people at ${{base.company_domain}} want office lunch`, html }} }};
'''

nodes = [
  {"id": uid(), "name": "New Google Form response", "type": "n8n-nodes-base.googleSheetsTrigger", "typeVersion": 1,
   "position": [0, 300], "credentials": {"googleSheetsTriggerOAuth2Api": {"id": "", "name": "Google (set me)"}},
   "notes": "Point this at the Form's linked responses sheet. Polls every minute.",
   "parameters": {"pollTimes": {"item": [{"mode": "everyMinute"}]}, "documentId": rl(SHEET_URL),
                  "sheetName": rl(SHEET_URL), "event": "rowAdded", "options": {}}},
  {"id": uid(), "name": "Normalize e-mail", "type": "n8n-nodes-base.code", "typeVersion": 2,
   "position": [220, 300], "parameters": {"jsCode": normalize_js}},
  {"id": uid(), "name": "Company e-mail?", "type": "n8n-nodes-base.if", "typeVersion": 2.2,
   "position": [440, 300],
   "parameters": {"conditions": conds(cond("={{ $json.company_domain }}", "notEmpty")), "options": {}}},
  {"id": uid(), "name": "Read all responses", "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5,
   "position": [660, 280], "executeOnce": True, "credentials": {"googleSheetsOAuth2Api": {"id": "", "name": "Google (set me)"}},
   "parameters": {"resource": "sheet", "operation": "read", "documentId": rl(SHEET_URL), "sheetName": rl(SHEET_URL), "options": {}}},
  {"id": uid(), "name": "Count colleagues", "type": "n8n-nodes-base.code", "typeVersion": 2,
   "position": [880, 280], "parameters": {"jsCode": count_js}},
  {"id": uid(), "name": f"{THRESHOLD} colleagues reached?", "type": "n8n-nodes-base.if", "typeVersion": 2.2,
   "position": [1100, 280],
   "parameters": {"conditions": conds(cond("={{ $json.reached }}", "true", typ="boolean")), "options": {}}},
  {"id": uid(), "name": "Benefit scan (optional)", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
   "position": [1320, 260], "onError": "continueRegularOutput",
   "credentials": {"httpHeaderAuth": {"id": "", "name": "x-enrich-secret (set me)"}},
   "notes": "Calls the app: Apify job ads -> Featherless -> Gap/Switch/Skip. If it fails, the e-mail still goes out.",
   "parameters": {"method": "POST", "url": f"{APP_URL}/api/enrich",
                  "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
                  "sendBody": True, "specifyBody": "json",
                  "jsonBody": "={{ JSON.stringify({ domain: $json.company_domain, city: $json.city }) }}",
                  "options": {"timeout": 300000}}},
  {"id": uid(), "name": "Compose sales e-mail", "type": "n8n-nodes-base.code", "typeVersion": 2,
   "position": [1540, 260], "parameters": {"mode": "runOnceForEachItem", "jsCode": compose_js}},
  {"id": uid(), "name": "E-mail sales team", "type": "n8n-nodes-base.gmail", "typeVersion": 2.1,
   "position": [1760, 260], "credentials": {"gmailOAuth2": {"id": "", "name": "Gmail (set me)"}},
   "parameters": {"resource": "message", "operation": "send", "sendTo": SALES_EMAIL,
                  "subject": "={{ $json.subject }}", "emailType": "html", "message": "={{ $json.html }}",
                  "options": {"appendAttribution": False}}},
]
links = [("New Google Form response", 0, "Normalize e-mail"), ("Normalize e-mail", 0, "Company e-mail?"),
         ("Company e-mail?", 0, "Read all responses"), ("Read all responses", 0, "Count colleagues"),
         ("Count colleagues", 0, f"{THRESHOLD} colleagues reached?"),
         (f"{THRESHOLD} colleagues reached?", 0, "Benefit scan (optional)"),
         ("Benefit scan (optional)", 0, "Compose sales e-mail"), ("Compose sales e-mail", 0, "E-mail sales team")]
names = {n["name"] for n in nodes}
connections = {}
for a, out, b in links:
    assert a in names and b in names, (a, b)
    main = connections.setdefault(a, {"main": []})["main"]
    while len(main) <= out: main.append([])
    main[out].append({"node": b, "type": "main", "index": 0})

wf = {"name": "LunchSignal · Google Form → 5 colleagues → e-mail sales",
      "nodes": nodes, "connections": connections, "settings": {"executionOrder": "v1"}, "pinData": {}}
json.dump(wf, open("google-form-to-sales.json", "w"), ensure_ascii=False, indent=2)
print(f"{len(nodes)} nodes, {len(links)} links")
