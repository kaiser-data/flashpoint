"""Generates lunchsignal-workflow.json for import into n8n (Workflows -> Import from file)."""
import json, uuid

APP_URL = "https://YOUR-APP.vercel.app"           # edit after deploying the Next.js app
SLACK_WEBHOOK = "https://hooks.slack.com/services/REPLACE/ME"
THRESHOLD = 5

def uid(): return str(uuid.uuid4())
def cond(left, op, right=None, typ="string"):
    c = {"id": uid(), "leftValue": left, "operator": {"type": typ, "operation": op}}
    if right is None: c["operator"]["singleValue"] = True; c["rightValue"] = ""
    else: c["rightValue"] = right
    return c
def conds(*cs): return {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                        "conditions": list(cs), "combinator": "and"}

SUPA = {"supabaseApi": {"id": "", "name": "Supabase (set me)"}}

normalize_js = r'''
const FREEMAIL = new Set(["gmail.com","googlemail.com","gmx.de","gmx.net","web.de","yahoo.com","yahoo.de",
  "outlook.com","outlook.de","hotmail.com","hotmail.de","live.com","icloud.com","me.com","t-online.de",
  "posteo.de","mailbox.org","proton.me","protonmail.com","aol.com","freenet.de"]);
const MULTI = new Set(["co.uk","com.au","co.at","ac.uk"]);
const j = $input.first().json;
const key = Object.keys(j).find(k => /mail/i.test(k));
const email = String(j[key] ?? "").trim().toLowerCase();
const host = email.includes("@") ? email.split("@").pop() : "";
const labels = host.split(".");
const lastTwo = labels.slice(-2).join(".");
const reg = MULTI.has(lastTwo) && labels.length >= 3 ? labels.slice(-3).join(".") : lastTwo;
const company_domain = host && !FREEMAIL.has(reg) ? reg : null;
return [{ json: { email, city: j["Office city"] ?? null, company_domain, consent_at: new Date().toISOString() } }];
'''.strip()

count_js = f'''
const domain = $('Normalize e-mail').first().json.company_domain;
const city = $('Normalize e-mail').first().json.city;
const signups = $input.all().length;
return [{{ json: {{ domain, city, signups, threshold: {THRESHOLD}, reached: signups >= {THRESHOLD} }} }}];
'''.strip()

nodes = [
  {"id": uid(), "name": "Lunch sign-up form", "type": "n8n-nodes-base.formTrigger", "typeVersion": 2.2,
   "position": [0, 300], "webhookId": uid(),
   "parameters": {
     "formTitle": "Want proper lunch at your office?",
     "formDescription": f"Sign up with your work e-mail. When {THRESHOLD} colleagues from your company ask, we tell your People team how a tax-free lunch benefit of up to €7.67 per workday works. GTM Hackathon Berlin demo; data deleted after the event.",
     "formFields": {"values": [
       {"fieldLabel": "Work email", "fieldType": "email", "placeholder": "you@company.com", "requiredField": True},
       {"fieldLabel": "Office city", "fieldType": "dropdown", "requiredField": True,
        "fieldOptions": {"values": [{"option": c} for c in ["Berlin", "München", "Düsseldorf", "Köln", "Other"]]}},
       {"fieldLabel": "Consent", "fieldType": "dropdown", "requiredField": True,
        "fieldOptions": {"values": [{"option": "Yes, store my e-mail to count sign-ups per company and contact me once"}]}},
     ]},
     "responseMode": "onReceived",
     "options": {"respondWithOptions": {"values": {"formSubmittedText": "You're on the list. Thanks!"}}}}},
  {"id": uid(), "name": "Normalize e-mail", "type": "n8n-nodes-base.code", "typeVersion": 2,
   "position": [220, 300], "parameters": {"jsCode": normalize_js}},
  {"id": uid(), "name": "Save sign-up", "type": "n8n-nodes-base.supabase", "typeVersion": 1,
   "position": [440, 300], "credentials": SUPA, "onError": "continueErrorOutput",
   "notes": "Unique e-mail: a repeat sign-up goes to the error output and stops here.",
   "parameters": {"resource": "row", "operation": "create", "tableId": "signups", "dataToSend": "autoMapInputData"}},
  {"id": uid(), "name": "Company e-mail?", "type": "n8n-nodes-base.if", "typeVersion": 2.2,
   "position": [660, 280],
   "parameters": {"conditions": conds(cond("={{ $('Normalize e-mail').first().json.company_domain }}", "notEmpty")), "options": {}}},
  {"id": uid(), "name": "Colleagues signed up", "type": "n8n-nodes-base.supabase", "typeVersion": 1,
   "position": [880, 260], "credentials": SUPA, "alwaysOutputData": True,
   "parameters": {"resource": "row", "operation": "getAll", "tableId": "signups", "returnAll": True,
                  "filterType": "string",
                  "filterString": "=company_domain=eq.{{ $('Normalize e-mail').first().json.company_domain }}&select=id"}},
  {"id": uid(), "name": "Count", "type": "n8n-nodes-base.code", "typeVersion": 2,
   "position": [1100, 260], "parameters": {"jsCode": count_js}},
  {"id": uid(), "name": f"{THRESHOLD}+ colleagues?", "type": "n8n-nodes-base.if", "typeVersion": 2.2,
   "position": [1320, 260],
   "parameters": {"conditions": conds(cond("={{ $json.reached }}", "true", typ="boolean")), "options": {}}},
  {"id": uid(), "name": "Record demand alert", "type": "n8n-nodes-base.supabase", "typeVersion": 1,
   "position": [1540, 240], "credentials": SUPA, "onError": "continueErrorOutput",
   "notes": "Unique (company, kind): only the first time a company crosses the threshold continues.",
   "parameters": {"resource": "row", "operation": "create", "tableId": "alerts", "dataToSend": "defineBelow",
                  "fieldsUi": {"fieldValues": [
                    {"fieldId": "company_domain", "fieldValue": "={{ $('Count').first().json.domain }}"},
                    {"fieldId": "kind", "fieldValue": "demand_cluster"},
                    {"fieldId": "delivered", "fieldValue": "true"}]}}},
  {"id": uid(), "name": "Scan benefits (Apify + Featherless)", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
   "position": [1760, 220],
   "credentials": {"httpHeaderAuth": {"id": "", "name": "x-enrich-secret (set me)"}},
   "notes": "Header Auth credential: name x-enrich-secret, value = ENRICH_SECRET of the app.",
   "parameters": {"method": "POST", "url": f"{APP_URL}/api/enrich",
                  "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
                  "sendBody": True, "specifyBody": "json",
                  "jsonBody": "={{ JSON.stringify({ domain: $('Count').first().json.domain, city: $('Count').first().json.city }) }}",
                  "options": {"timeout": 300000}}},
  {"id": uid(), "name": "Segment", "type": "n8n-nodes-base.switch", "typeVersion": 3.2,
   "position": [1980, 220],
   "parameters": {"rules": {"values": [
       {"conditions": conds(cond("={{ $json.segment }}", "equals", "gap")), "renameOutput": True, "outputKey": "Gap"},
       {"conditions": conds(cond("={{ $json.segment }}", "equals", "switch")), "renameOutput": True, "outputKey": "Switch"},
     ]}, "options": {"fallbackOutput": "extra", "renameFallbackOutput": "Skip or unclear"}}},
]

def slack(name, y, text):
    return {"id": uid(), "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [2220, y],
            "parameters": {"method": "POST", "url": SLACK_WEBHOOK, "sendBody": True, "specifyBody": "json",
                           "jsonBody": "={{ JSON.stringify({ text: " + text + " }) }}", "options": {}}}

nodes += [
  slack("Tell sales: Gap", 80,
        "'🟢 Gap · ' + $('Count').first().json.signups + ' people at ' + $json.domain + ' asked for office lunch. ' + $json.reasons.join('; ') + '. Perks they already pay: ' + $json.perks.slice(0,6).join(', ') + '. Tax-free up to €7.67/workday per employee. Ads analysed: ' + $json.adsAnalysed + ', scan cost $' + ($json.costUsd ?? 'n/a')"),
  slack("Tell sales: Switch", 240,
        "'🟠 Switch · ' + $('Count').first().json.signups + ' people at ' + $json.domain + ' asked for office lunch, and the company already pays a meal benefit: ' + $json.reasons.join('; ') + '. Budget exists, pitch real food instead of a card.'"),
  slack("Tell sales: demand only", 400,
        "'⚪ ' + $('Count').first().json.signups + ' people at ' + $json.domain + ' asked for office lunch. Benefit scan: ' + $json.segment + ' (' + ($json.reasons ?? []).join('; ') + ').'"),
  {"id": uid(), "name": "Pingen letter to HR (configure)", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
   "position": [2440, 160], "disabled": True,
   "notes": "Replace with the Pingen node (n8n integration) or Pingen API. Letter to 'Personalabteilung', no named person. Keep a suppression list for opt-outs.",
   "parameters": {"method": "POST", "url": "https://api.pingen.com/", "options": {}}},
]

N = {n["name"]: n for n in nodes}
def link(a, b, out=0): return (a, out, b)
links = [
  link("Lunch sign-up form", "Normalize e-mail"),
  link("Normalize e-mail", "Save sign-up"),
  link("Save sign-up", "Company e-mail?"),
  link("Company e-mail?", "Colleagues signed up"),
  link("Colleagues signed up", "Count"),
  link("Count", f"{THRESHOLD}+ colleagues?"),
  link(f"{THRESHOLD}+ colleagues?", "Record demand alert"),
  link("Record demand alert", "Scan benefits (Apify + Featherless)"),
  link("Scan benefits (Apify + Featherless)", "Segment"),
  link("Segment", "Tell sales: Gap", 0),
  link("Segment", "Tell sales: Switch", 1),
  link("Segment", "Tell sales: demand only", 2),
  link("Tell sales: Gap", "Pingen letter to HR (configure)"),
  link("Tell sales: Switch", "Pingen letter to HR (configure)"),
]
connections = {}
for a, out, b in links:
    assert a in N and b in N, (a, b)
    main = connections.setdefault(a, {"main": []})["main"]
    while len(main) <= out: main.append([])
    main[out].append({"node": b, "type": "main", "index": 0})

wf = {"name": "LunchSignal · sign-up → demand alert → benefit scan → sales",
      "nodes": nodes, "connections": connections, "settings": {"executionOrder": "v1"}, "pinData": {}}
json.dump(wf, open("lunchsignal-workflow.json", "w"), ensure_ascii=False, indent=2)
print(f"{len(nodes)} nodes, {len(links)} links")
