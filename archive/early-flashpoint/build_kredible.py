"""Generates kredible-agent.json (Kredible university account signal).
Chain A: Apps Script webhook -> IF exactly 5 colleagues -> Apify LinkedIn (company, posts, People/HR roles)
         -> Featherless analysis -> agent e-mails the consented sign-ups -> hot leads handed to a human.
Chain B: replies to the agent's e-mails -> Featherless classifies -> interested replies handed to a human.
Edit the constants, run `python3 build_agent.py`, import the JSON into n8n."""
import json, uuid

SALES_EMAIL = "sales@example.com"
FEATHERLESS_MODEL = "Qwen/Qwen2.5-72B-Instruct"   # check the exact id in the Featherless catalogue
HOT_SCORE = 70                                     # hand to a human at or above this score
THRESHOLD = 3                                      # same value as THRESHOLD in the Apps Script
SUBJECT = "Kredible for your university"           # chain B watches replies to this subject

def uid(): return str(uuid.uuid4())
def cond(left, op, right=None, typ="string"):
    c = {"id": uid(), "leftValue": left, "operator": {"type": typ, "operation": op}}
    if right is None: c["operator"]["singleValue"] = True; c["rightValue"] = ""
    else: c["rightValue"] = right
    return c
def conds(*cs, combinator="and"):
    return {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
            "conditions": list(cs), "combinator": combinator}
APIFY_AUTH = {"httpHeaderAuth": {"id": "", "name": "Apify (Authorization: Bearer <token>)"}}
FL_AUTH = {"httpHeaderAuth": {"id": "", "name": "Featherless (Authorization: Bearer <key>)"}}
GMAIL = {"gmailOAuth2": {"id": "", "name": "Gmail (set me)"}}

def apify(name, actor, body_expr, pos, notes):
    return {"id": uid(), "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": pos,
            "credentials": APIFY_AUTH, "onError": "continueRegularOutput", "alwaysOutputData": True, "notes": notes,
            "parameters": {"method": "POST",
                           "url": f"https://api.apify.com/v2/acts/{actor.replace('/', '~')}/run-sync-get-dataset-items",
                           "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
                           "sendBody": True, "specifyBody": "json", "jsonBody": body_expr,
                           "options": {"timeout": 300000}}}

def featherless(name, pos, messages_expr):
    return {"id": uid(), "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": pos,
            "credentials": FL_AUTH, "onError": "continueRegularOutput",
            "parameters": {"method": "POST", "url": "https://api.featherless.ai/v1/chat/completions",
                           "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
                           "sendBody": True, "specifyBody": "json",
                           "jsonBody": "={{ JSON.stringify({ model: '" + FEATHERLESS_MODEL + "', temperature: 0.2, max_tokens: 1200, messages: " + messages_expr + " }) }}",
                           "options": {"timeout": 120000}}}

# --- Chain A ---------------------------------------------------------------
check_company_js = r'''
// Accept the LinkedIn match only if its website is the sign-up domain. Otherwise abstain.
const signup = $('Form sign-up').first().json.body;
const items = $input.all().map(i => i.json).filter(c => c && c.name);
const institution = String((signup.notes || [])[0] || '').split(' | ')[0].toLowerCase().trim();
const match = items.find(c => String(c.website || '').toLowerCase().includes(signup.company_domain))
  || (institution ? items.find(c => String(c.name || '').toLowerCase() === institution) : undefined);
return [{ json: {
  domain: signup.company_domain, city: signup.city, colleagues: signup.colleagues,
  roles: signup.roles || [], notes: signup.notes || [],
  partnershipRequested: (signup.notes || []).some(n => /partnership call/i.test(n)),
  colleague_emails: signup.colleague_emails,
  verified: Boolean(match),
  company: match ? {
    name: match.name, linkedinUrl: match.linkedinUrl, employeeCount: match.employeeCount,
    industries: match.industries, specialities: match.specialities, tagline: match.tagline,
    description: String(match.description || '').slice(0, 1500),
    locations: (match.locations || []).map(l => l.city || l.parsed?.city).filter(Boolean).slice(0, 10),
  } : null,
}}];
'''

context_js = r'''
// Company-level context for the LLM. People appear only as roles, never as names.
const base = $('Verify company match').first().json;
const posts = $('LinkedIn posts').all().map(i => i.json).filter(p => p && (p.content || p.text));
const roles = $('Decision-maker roles').all().map(i => i.json).filter(p => p && p.headline);
const topPosts = posts
  .map(p => ({ text: String(p.content || p.text).slice(0, 400),
               engagement: (p.engagement?.likes || 0) + 3 * (p.engagement?.comments || 0) + 2 * (p.engagement?.shares || 0) }))
  .sort((a, b) => b.engagement - a.engagement).slice(0, 8);
const roleTitles = [...new Set(roles.map(r => r.headline).filter(Boolean))].slice(0, 12);
return [{ json: { ...base, topPosts, roleTitles, postsAnalysed: posts.length } }];
'''

analysis_system = (
  "You are a B2B analyst for Kredible. Kredible finances the blocked account (Sperrkonto), tuition fees and first-year living costs "
  "for admitted non-EU students at German universities. For the university it costs nothing: no fees, no revenue share, no repayment risk; "
  "tuition is paid directly to the institution and the university is told when a student's funding is secured. "
  "Main university benefits: fewer admitted students lost between offer and enrolment, a wider talent pool, graduates who stay in Germany. "
  "Several staff members of one university subscribed to Kredible's newsletter. Use ONLY the facts given; say 'unknown' instead of guessing. "
  "Return ONLY JSON: {\\\"culture\\\": string (internationalisation focus, tone of their posts), \\\"structure\\\": string (size, faculties, how international admissions seem organised), "
  "\\\"buying_committee\\\": string[] (roles only, no names), \\\"angle\\\": string (the one benefit to lead with for this university), "
  "\\\"interest_score\\\": integer 0-100, \\\"score_reasons\\\": string[], \\\"champion_email_subject\\\": string, \\\"champion_email_html\\\": string}. "
  "Score higher when more distinct roles subscribed (International Office + Admissions + Finance is a full buying committee), when someone asked for a partnership call, "
  "and when posts show a strong international student focus. "
  "The champion e-mail goes only to the staff who subscribed: thank them, mention that colleagues from their university subscribed too (no names), "
  "explain in three sentences how Kredible helps admitted non-EU students enrol at no cost or risk to the university, "
  "offer a 20-minute call, and end with: Reply STOP to unsubscribe. Write it in German for German universities, otherwise English."
)
analysis_msgs = ("[{ role: 'system', content: \"" + analysis_system + "\" }, "
                 "{ role: 'user', content: JSON.stringify({ domain: $json.domain, colleagues_subscribed: $json.colleagues, roles: $json.roles, form_notes: $json.notes, partnership_call_requested: $json.partnershipRequested, "
                 "linkedin_verified: $json.verified, company: $json.company, top_posts: $json.topPosts, people_roles: $json.roleTitles }) }]")

parse_js = f'''
// Parse the model's JSON. Anything unparseable goes to a human, never to a customer.
const ctx = $('Build context').first().json;
const raw = $input.first().json.choices?.[0]?.message?.content ?? "";
let a = null;
try {{ a = JSON.parse(raw.slice(raw.indexOf("{{"), raw.lastIndexOf("}}") + 1)); }} catch (e) {{}}
const ok = a && typeof a.interest_score === "number" && a.champion_email_html && a.champion_email_subject;
const score = ok ? Math.max(0, Math.min(100, Math.round(a.interest_score))) : null;
return [{{ json: {{ ...ctx, analysis: ok ? a : null, score,
  autoSend: Boolean(ok && ctx.verified && ctx.colleague_emails.length),
  handToHuman: !ok || !ctx.verified || ctx.partnershipRequested || score >= {HOT_SCORE},
  handoffReason: !ok ? "LLM output unusable" : !ctx.verified ? "LinkedIn profile not verified" : ctx.partnershipRequested ? "Partnership call requested" : score >= {HOT_SCORE} ? "Hot lead (score " + score + ")" : null }} }}];
'''

brief_js = r'''
const d = $('Parse analysis').first().json;
const a = d.analysis || {};
const li = (xs) => (xs || []).map(x => `<li>${x}</li>`).join("");
const html = `
<h3>${d.colleagues} staff at ${d.domain} subscribed to Kredible</h3>
<p><b>Roles:</b> ${(d.roles || []).join(', ')}</p>
<p><b>Why you are getting this:</b> ${d.handoffReason}</p>
<p><b>Score:</b> ${d.score ?? "n/a"} · <b>LinkedIn verified:</b> ${d.verified ? "yes" : "no"} · posts analysed: ${d.postsAnalysed ?? 0}</p>
${d.company ? `<p><b>${d.company.name}</b> · ${d.company.employeeCount ?? "?"} employees · ${(d.company.industries || []).join(", ")} · ${(d.company.locations || []).join(", ")}</p>` : ""}
<p><b>Culture:</b> ${a.culture ?? "n/a"}</p><p><b>Structure:</b> ${a.structure ?? "n/a"}</p>
<p><b>Buying committee (roles):</b></p><ul>${li(a.buying_committee)}</ul>
<p><b>Suggested angle:</b> ${a.angle ?? "n/a"}</p><ul>${li(a.score_reasons)}</ul>
<p><b>Agent e-mail to the sign-ups:</b> ${d.autoSend ? "sent automatically" : "NOT sent, please review"}</p>
<p style="color:#666">Account-level briefing. Subscriber addresses are not included.</p>`;
return [{ json: { subject: `[${d.score ?? "review"}] ${d.colleagues} staff at ${d.domain} subscribed to Kredible`, html } }];
'''

# --- Chain B ---------------------------------------------------------------
reply_system = ("Classify a reply to our Kredible e-mail to university staff. Return ONLY JSON: {\\\"label\\\": \\\"interested\\\"|\\\"question\\\"|\\\"not_interested\\\"|\\\"stop\\\", \\\"summary\\\": string}. "
                "STOP, unsubscribe, abmelden or any request not to be contacted is \\\"stop\\\".")
reply_msgs = "[{ role: 'system', content: \"" + reply_system + "\" }, { role: 'user', content: String($json.text || $json.snippet || '').slice(0, 4000) }]"
reply_parse_js = r'''
const mail = $('Reply received').first().json;
const raw = $input.first().json.choices?.[0]?.message?.content ?? "";
let r = null;
try { r = JSON.parse(raw.slice(raw.indexOf("{"), raw.lastIndexOf("}") + 1)); } catch (e) {}
const label = r?.label ?? "question"; // unclear replies go to a human
return [{ json: { label, summary: r?.summary ?? "Could not classify", from: mail.from?.text ?? mail.from, subject: mail.subject,
                  html: `<p><b>${label.toUpperCase()}</b> reply from ${mail.from?.text ?? ""}</p><p>${r?.summary ?? ""}</p><blockquote>${String(mail.text || mail.snippet || "").slice(0, 2000)}</blockquote>` } }];
'''

nodes = [
  {"id": uid(), "name": "Form sign-up", "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 300],
   "webhookId": uid(), "credentials": {"httpHeaderAuth": {"id": "", "name": "x-signal-secret (set me)"}},
   "notes": "Called by google/apps-script.gs on every Google Form response.",
   "parameters": {"httpMethod": "POST", "path": "kredible-signal", "authentication": "headerAuth", "options": {}}},
  {"id": uid(), "name": f"Exactly {THRESHOLD} colleagues?", "type": "n8n-nodes-base.if", "typeVersion": 2.2, "position": [220, 300],
   "parameters": {"conditions": conds(cond("={{ $json.body.colleagues }}", "equals", THRESHOLD, typ="number"),
                                      cond("={{ $json.body.company_domain }}", "notEmpty")), "options": {}}},
  apify("LinkedIn company", "harvestapi/linkedin-company",
        "={{ JSON.stringify({ searches: [ String(($json.body.notes || [])[0] || '').split(' | ')[0] || $json.body.company_domain.split('.')[0] ] }) }}", [440, 300],
        "~$0.004 per search. Searched by the institution name from the form; the next step checks the match."),
  {"id": uid(), "name": "Verify company match", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [660, 300],
   "parameters": {"jsCode": check_company_js}},
  apify("LinkedIn posts", "harvestapi/linkedin-company-posts",
        "={{ JSON.stringify({ targetUrls: $json.company ? [$json.company.linkedinUrl] : [], maxPosts: 20 }) }}", [880, 200],
        "$1.50 / 1k posts. Engagement per post; commenters are not stored."),
  apify("Decision-maker roles", "harvestapi/linkedin-company-employees",
        "={{ JSON.stringify({ profileScraperMode: 'Short ($1.5 per 1k)', maxItems: 15, companies: $('Verify company match').first().json.company ? [$('Verify company match').first().json.company.linkedinUrl] : [], jobTitles: ['International Office', 'International Relations', 'Admissions', 'Zulassung', 'Studierendenservice', 'Vice President International', 'Vizepräsident', 'Kanzler', 'Finance', 'Head of Finance'] }) }}",
        [1100, 200], "Only job titles reach the LLM (buying committee as roles). Check the exact profileScraperMode value in the actor input."),
  {"id": uid(), "name": "Build context", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [1320, 300],
   "parameters": {"jsCode": context_js}},
  featherless("Featherless analysis", [1540, 300], analysis_msgs),
  {"id": uid(), "name": "Parse analysis", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [1760, 300],
   "parameters": {"jsCode": parse_js}},
  {"id": uid(), "name": "Send automatically?", "type": "n8n-nodes-base.if", "typeVersion": 2.2, "position": [1980, 200],
   "parameters": {"conditions": conds(cond("={{ $json.autoSend }}", "true", typ="boolean")), "options": {}}},
  {"id": uid(), "name": "Agent e-mails the sign-ups", "type": "n8n-nodes-base.gmail", "typeVersion": 2.1, "position": [2200, 180],
   "credentials": GMAIL, "notes": "Recipients are the people who signed up (consent). BCC so nobody sees colleagues' addresses.",
   "parameters": {"resource": "message", "operation": "send", "sendTo": "={{ '" + SALES_EMAIL + "' }}",
                  "subject": "={{ $json.analysis.champion_email_subject || '" + SUBJECT + "' }}",
                  "emailType": "html", "message": "={{ $json.analysis.champion_email_html }}",
                  "options": {"appendAttribution": False, "bccList": "={{ $json.colleague_emails.join(',') }}"}}},
  {"id": uid(), "name": "Hand to a human?", "type": "n8n-nodes-base.if", "typeVersion": 2.2, "position": [1980, 420],
   "parameters": {"conditions": conds(cond("={{ $json.handToHuman }}", "true", typ="boolean")), "options": {}}},
  {"id": uid(), "name": "Write briefing", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [2200, 420],
   "parameters": {"jsCode": brief_js}},
  {"id": uid(), "name": "Briefing to sales", "type": "n8n-nodes-base.gmail", "typeVersion": 2.1, "position": [2420, 420],
   "credentials": GMAIL,
   "parameters": {"resource": "message", "operation": "send", "sendTo": SALES_EMAIL, "subject": "={{ $json.subject }}",
                  "emailType": "html", "message": "={{ $json.html }}", "options": {"appendAttribution": False}}},
  # Chain B
  {"id": uid(), "name": "Reply received", "type": "n8n-nodes-base.gmailTrigger", "typeVersion": 1.2, "position": [0, 760],
   "credentials": GMAIL,
   "parameters": {"pollTimes": {"item": [{"mode": "everyMinute"}]}, "simple": False,
                  "filters": {"q": f"in:inbox is:unread subject:\"{SUBJECT}\"", "readStatus": "unread"}, "options": {}}},
  featherless("Classify reply", [220, 760], reply_msgs),
  {"id": uid(), "name": "Parse reply", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [440, 760],
   "parameters": {"jsCode": reply_parse_js}},
  {"id": uid(), "name": "Interested or question?", "type": "n8n-nodes-base.if", "typeVersion": 2.2, "position": [660, 760],
   "parameters": {"conditions": conds(cond("={{ $json.label }}", "equals", "interested"),
                                      cond("={{ $json.label }}", "equals", "question"), combinator="or"), "options": {}}},
  {"id": uid(), "name": "Hand reply to a human", "type": "n8n-nodes-base.gmail", "typeVersion": 2.1, "position": [880, 740],
   "credentials": GMAIL,
   "parameters": {"resource": "message", "operation": "send", "sendTo": SALES_EMAIL,
                  "subject": "={{ '[' + $json.label + '] reply: ' + $json.subject }}", "emailType": "html",
                  "message": "={{ $json.html }}", "options": {"appendAttribution": False}}},
]

links = [("Form sign-up", 0, f"Exactly {THRESHOLD} colleagues?"), (f"Exactly {THRESHOLD} colleagues?", 0, "LinkedIn company"),
         ("LinkedIn company", 0, "Verify company match"), ("Verify company match", 0, "LinkedIn posts"),
         ("LinkedIn posts", 0, "Decision-maker roles"), ("Decision-maker roles", 0, "Build context"),
         ("Build context", 0, "Featherless analysis"), ("Featherless analysis", 0, "Parse analysis"),
         ("Parse analysis", 0, "Send automatically?"), ("Parse analysis", 0, "Hand to a human?"),
         ("Send automatically?", 0, "Agent e-mails the sign-ups"), ("Hand to a human?", 0, "Write briefing"),
         ("Write briefing", 0, "Briefing to sales"),
         ("Reply received", 0, "Classify reply"), ("Classify reply", 0, "Parse reply"),
         ("Parse reply", 0, "Interested or question?"), ("Interested or question?", 0, "Hand reply to a human")]
names = {n["name"] for n in nodes}
connections = {}
for a, out, b in links:
    assert a in names and b in names, (a, b)
    main = connections.setdefault(a, {"main": []})["main"]
    while len(main) <= out: main.append([])
    main[out].append({"node": b, "type": "main", "index": 0})

wf = {"name": "Kredible · university account signal → LinkedIn → Featherless → agent e-mail → human when hot",
      "nodes": nodes, "connections": connections, "settings": {"executionOrder": "v1"}, "pinData": {}}
json.dump(wf, open("kredible-agent.json", "w"), ensure_ascii=False, indent=2)
print(f"{len(nodes)} nodes, {len(links)} links")
