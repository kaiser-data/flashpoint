"""Critical Mass: generic GTM account-signal workflow. Edit the CONFIG block, run, import critical-mass.json into n8n.
Chain A: Apps Script webhook -> IF exactly 5 colleagues -> Apify LinkedIn (company, posts, People/HR roles)
         -> Featherless analysis -> agent e-mails the consented sign-ups -> hot leads handed to a human.
Chain B: replies to the agent's e-mails -> Featherless classifies -> interested replies handed to a human.
Edit the constants, run `python3 build_agent.py`, import the JSON into n8n."""
import json, os, uuid

# ============================ CONFIG: change only this block per use case ============================
WORKFLOW_NAME = "Flashpoint · Kredible (universities)"
WEBHOOK_PATH = "critical-mass"
SALES_EMAIL = ",".join(x.strip() for x in [os.environ.get("SALES_EMAIL") or "sales@example.com", *os.environ.get("SALES_TEAM", "").split(",")] if x.strip())                  # receives briefings and hot replies
FEATHERLESS_MODEL = os.environ.get("FEATHERLESS_MODEL") or "Qwen/Qwen2.5-72B-Instruct"     # exact id from the Featherless model catalogue
THRESHOLD = 3                                       # same value as THRESHOLD in the Apps Script
HOT_SCORE = 70                                      # hand to a human at or above this score
SUBJECT = "Kredible for your university"            # subject of the agent e-mail; replies are matched on it
ORG_TYPE = "university"                             # what an account is: company, university, hospital, school ...
PRODUCT = (
  "Kredible finances the blocked account (Sperrkonto), tuition fees and first-year living costs for admitted non-EU students "
  "at German universities. For the university it costs nothing: no fees, no revenue share, no repayment risk; tuition is paid "
  "directly to the institution and the university is told when a student's funding is secured. Main benefits: fewer admitted "
  "students lost between offer and enrolment, a wider talent pool, graduates who stay in Germany."
)
DECISION_ROLES = ["International Office", "International Relations", "Admissions", "Zulassung", "Studierendenservice",
                  "Vice President International", "Vizepräsident", "Kanzler", "Finance", "Head of Finance"]
SCORE_HINTS = ("Score much higher when pain_signal shows extended or reopened application deadlines (unfilled seats) or customer_voice shows admitted students who cannot fund their studies. Score higher when more distinct roles signed up (International Office + Admissions + Finance is a full buying committee), "
               "when someone asked for a call, and when news or posts show a strong international student focus.")
EMAIL_BRIEF = ("Thank them, mention that colleagues from their organisation signed up too (no names), explain in three sentences how "
               "the product helps them at no cost or risk, offer a 20-minute call, and end with: Reply STOP to unsubscribe. "
               "Write in German for German organisations, otherwise English.")
NEWS_DAYS = 120                                     # how far back "latest news" goes
# The signal nobody uses: public evidence of the pain, searched per account. {domain} and {name} are filled in.
PAIN_SIGNAL_QUERY = 'site:{domain} ("Bewerbungsfrist verlängert" OR "Frist verlängert" OR "deadline extended" OR "application period reopened")'
PAIN_SIGNAL_LABEL = "Application deadline extensions (empty seats)"
VOICE_QUERY = 'site:reddit.com "{name}" ("blocked account" OR Sperrkonto OR "proof of funds" OR "can\'t afford")'
VOICE_LABEL = "Admitted students struggling to fund their studies (Reddit)"
# ====================================================================================================

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
            "credentials": APIFY_AUTH, "onError": "continueRegularOutput", "alwaysOutputData": True, "executeOnce": True, "notes": notes,
            "parameters": {"method": "POST",
                           "url": f"https://api.apify.com/v2/acts/{actor.replace('/', '~')}/run-sync-get-dataset-items",
                           "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
                           "sendBody": True, "specifyBody": "json", "jsonBody": body_expr,
                           "options": {"timeout": 300000}}}

def featherless(name, pos, messages_expr):
    return {"id": uid(), "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": pos,
            "credentials": FL_AUTH, "onError": "continueRegularOutput", "executeOnce": True,
            "parameters": {"method": "POST", "url": "https://api.featherless.ai/v1/chat/completions",
                           "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
                           "sendBody": True, "specifyBody": "json",
                           "jsonBody": "={{ JSON.stringify({ model: '" + FEATHERLESS_MODEL + "', temperature: 0.2, max_tokens: 3000, messages: " + messages_expr + " }) }}",
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
  signups: signup.signups || (signup.colleague_emails || []).map((e, i) => ({ name: '', email: e, role: (signup.roles || [])[i] || '' })),
  verified: Boolean(match),
  company: match ? {
    name: match.name, id: match.id ? String(match.id) : null, website: match.website, linkedinUrl: match.linkedinUrl, employeeCount: match.employeeCount,
    industries: match.industries, specialities: match.specialities, tagline: match.tagline,
    description: String(match.description || '').slice(0, 1500),
    locations: (match.locations || []).map(l => l.city || l.parsed?.city).filter(Boolean).slice(0, 10),
  } : null,
}}];
'''

context_js = (r'''
// Context for the LLM (titles only) and the contact list for sales (real names, ranked in code).
const base = $('Verify company match').first().json;
const posts = $('LinkedIn posts').all().map(i => i.json).filter(p => p && (p.content || p.text));
const people = $('Decision-maker roles').all().map(i => i.json).filter(p => p && p.firstName && !p.error);
const orgName = String(base.company?.name || '').toLowerCase();
const orgUrl = String(base.company?.linkedinUrl || '').toLowerCase().replace(/\/$/, '');
// The person's current position at THIS organisation; people whose current job is elsewhere are dropped.
// Matches by LinkedIn company id, profile URL, or name prefix (faculties: "Freie Universität Berlin, Fachbereich ...").
const orgId = String(base.company?.id || '');
const position = (p) => (p.currentPositions || []).find(x => x.current !== false && (
  (orgId && String(x.companyId || '') === orgId) ||
  String(x.companyLinkedinUrl || '').toLowerCase().replace(/\/$/, '') === orgUrl ||
  (orgName && String(x.companyName || '').toLowerCase().startsWith(orgName)))) || null;
// Rank: earlier entries in DECISION_ROLES weigh more; seniority words add weight.
const ROLE_ORDER = DECISION_ROLES_JSON.map(r => r.toLowerCase());
const SENIOR = /(head|leiter|leitung|director|direktor|vice|vize|präsident|president|kanzler|chief|dean|dekan)/i;
const ASSISTANT = /(referent|assistent|assistant|sekretariat|secretary|werkstudent|student|praktikant|intern\b|trainee|hilfskraft)/i;
const ACADEMIC = /(lecturer|professor|researcher|wissenschaftlich|doktorand|phd|postdoc|dozent)/i;
const contacts = people.filter(p => position(p)).map(p => {
  const title = String(position(p).title || '').trim();
  const roleIdx = ROLE_ORDER.findIndex(r => title.toLowerCase().includes(r));
  const rank = (roleIdx === -1 ? 0 : 100 - roleIdx * 5) + (SENIOR.test(title) ? 30 : 0)
             - (ASSISTANT.test(title) ? 60 : 0) - (ACADEMIC.test(title) && !SENIOR.test(title) ? 40 : 0);
  return { name: `${p.firstName} ${p.lastName || ''}`.trim(), title, linkedin: p.linkedinUrl || '',
           location: p.location?.linkedinText || '', matched_role: roleIdx === -1 ? '' : DECISION_ROLES_JSON[roleIdx], rank };
}).filter(c => c.title).sort((a, b) => b.rank - a.rank).slice(0, 10)
  .map((c, i) => ({ ...c, priority: i < 3 && c.rank >= 100 ? 'A' : c.rank >= 70 ? 'B' : 'C' }));
const topPosts = posts
  .map(p => ({ text: String(p.content || p.text).slice(0, 400),
               engagement: (p.engagement?.likes || 0) + 3 * (p.engagement?.comments || 0) + 2 * (p.engagement?.shares || 0) }))
  .sort((a, b) => b.engagement - a.engagement).slice(0, 8);
const roleTitles = [...new Set(contacts.map(c => c.title))].slice(0, 12);
const news = $('Latest news').all().map(i => i.json).filter(n => n && n.metadata && n.markdown)
  .map(n => ({ title: n.metadata.title, url: n.metadata.url, excerpt: String(n.markdown).slice(0, 600) })).slice(0, 5);
const site = $('Website').all().map(i => i.json).find(w => w && w.markdown);
const website = site ? String(site.markdown).slice(0, 2000) : null;
// Search engines sometimes ignore site: filters. Keep only hits that are really about this account.
const domainRoot = String(base.domain || '').split('.')[0].replace(/-/g, ' ').toLowerCase();
const names = [String(base.company?.name || '').toLowerCase(), domainRoot].filter(x => x.length > 2);
const mentions = (h) => names.some(n => (String(h.metadata.title) + ' ' + String(h.markdown)).toLowerCase().includes(n));
const hits = (n, keep) => $(n).all().map(i => i.json).filter(h => h && h.metadata && h.markdown && keep(h))
  .map(h => ({ title: String(h.metadata.title).slice(0, 160), url: h.metadata.url,
               excerpt: String(h.markdown).replace(/u\/[A-Za-z0-9_-]+/g, '').replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, '[e-mail]').slice(0, 400) })).slice(0, 5);
const painSignal = hits('Pain signal', h => String(h.metadata.url).includes(base.domain) || String(h.metadata.url).includes(String(base.company?.website || '#none#').replace(/^https?:\/\/(www\.)?/, '').split('/')[0]));
const customerVoice = hits('Customer voice', h => /reddit\.com/.test(h.metadata.url) && mentions(h));
const droppedHits = $('Pain signal').all().length + $('Customer voice').all().length - painSignal.length - customerVoice.length;
return [{ json: { ...base, topPosts, roleTitles, contacts, news, website, painSignal, customerVoice, droppedHits, postsAnalysed: posts.length } }];
''').replace("DECISION_ROLES_JSON", json.dumps(DECISION_ROLES, ensure_ascii=False))

analysis_system = (
  "You are a B2B analyst. Product: " + PRODUCT + " "
  "Several people from one " + ORG_TYPE + " signed up on our landing page. Use ONLY the facts given; write 'unknown' instead of guessing. "
  "Return ONLY JSON: {\\\"culture\\\": string, \\\"structure\\\": string, \\\"news_summary\\\": string (what is happening at the organisation right now, from the news), "
  "\\\"buying_committee\\\": string[] (roles only, no names), \\\"angle\\\": string (the one benefit to lead with, tied to their news or posts if possible), "
  "\\\"outreach_templates\\\": [{\\\"for_role\\\": string (one buying-committee role), \\\"channel\\\": \\\"LinkedIn\\\" or \\\"E-mail\\\", \\\"subject\\\": string, \\\"body\\\": string (max 120 words, starts with {first_name}, ties the product to this role's goals and to the news or pain evidence)}] (exactly 3, written for a salesperson to send personally), "
  "\\\"pain_evidence\\\": string (what pain_signal and customer_voice show, with counts; 'none found' if empty), \\\"interest_score\\\": integer 0-100, \\\"score_reasons\\\": string[], \\\"champion_email_subject\\\": string, \\\"champion_email_html\\\": string}. "
  + SCORE_HINTS + " The champion e-mail goes only to the people who signed up. " + EMAIL_BRIEF
)
analysis_msgs = ("[{ role: 'system', content: \"" + analysis_system + "\" }, "
                 "{ role: 'user', content: JSON.stringify({ domain: $json.domain, colleagues_subscribed: $json.colleagues, roles: $json.roles, form_notes: $json.notes, partnership_call_requested: $json.partnershipRequested, "
                 "linkedin_verified: $json.verified, company: $json.company, top_posts: $json.topPosts, people_roles: $json.roleTitles, latest_news: $json.news, website: $json.website, pain_signal: { label: '" + PAIN_SIGNAL_LABEL + "', hits: $json.painSignal }, customer_voice: { label: '" + VOICE_LABEL.replace("'", "") + "', hits: $json.customerVoice } }) }]")

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
  handToHuman: !ok || !ctx.verified || ctx.partnershipRequested || score >= {HOT_SCORE} || (ctx.contacts || []).length > 0,
  handoffReason: !ok ? "LLM output unusable" : !ctx.verified ? "LinkedIn profile not verified" : ctx.partnershipRequested ? "Partnership call requested" : score >= {HOT_SCORE} ? "Hot lead (score " + score + ")" : (ctx.contacts || []).length ? "Contact list for sales" : null }} }}];
'''

brief_js = (r'''
const d = $('Parse analysis').first().json;
const a = d.analysis || {};
const li = (xs) => (xs || []).map(x => `<li>${x}</li>`).join("");
const html = `
<h3>${d.colleagues} people at ${d.domain} signed up</h3>
<p><b>Roles:</b> ${(d.roles || []).join(', ')}</p>
<p><b>Why you are getting this:</b> ${d.handoffReason}</p>
<p><b>Score:</b> ${d.score ?? "n/a"} · <b>LinkedIn verified:</b> ${d.verified ? "yes" : "no"} · posts analysed: ${d.postsAnalysed ?? 0}</p>
${d.company ? `<p><b>${d.company.name}</b> · ${d.company.employeeCount ?? "?"} employees · ${(d.company.industries || []).join(", ")} · ${(d.company.locations || []).join(", ")}</p>` : ""}
<p><b>Signal nobody uses:</b> ${a.pain_evidence ?? "n/a"}</p><ul>${[...(d.painSignal || []), ...(d.customerVoice || [])].map(n => `<li><a href=\"${n.url}\">${n.title}</a></li>`).join("")}</ul>
<p><b>Latest news:</b> ${a.news_summary ?? "n/a"}</p><ul>${(d.news || []).map(n => `<li><a href="${n.url}">${n.title}</a></li>`).join("")}</ul>
<p><b>Culture:</b> ${a.culture ?? "n/a"}</p><p><b>Structure:</b> ${a.structure ?? "n/a"}</p>
<h3>Who signed up (${(d.signups || []).length})</h3>
<table border="1" cellpadding="6" style="border-collapse:collapse;font-size:14px"><tr><th>Name</th><th>E-mail</th><th>Role</th></tr>
${(d.signups || []).map(p => `<tr><td>${p.name || '–'}</td><td>${p.email}</td><td>${p.role || '–'}</td></tr>`).join('')}</table>
<p style="color:#666">They gave consent on the sign-up form and already received the agent's e-mail${d.autoSend ? '' : ' (not sent this time, see above)'}.</p>
<h3>Decision makers on LinkedIn</h3>
${(d.contacts || []).length ? `<table border="1" cellpadding="6" style="border-collapse:collapse;font-size:14px">
<tr><th>Prio</th><th>Name</th><th>Title</th><th>Location</th><th>Matched role</th></tr>
${d.contacts.map(c => `<tr><td><b>${c.priority}</b></td><td><a href="${c.linkedin}">${c.name}</a></td><td>${c.title}</td><td>${c.location}</td><td>${c.matched_role || '–'}</td></tr>`).join('')}
</table>` : '<p>No decision makers found on LinkedIn for this account.</p>'}
<h3>Outreach templates (send personally)</h3>
${(() => {
  const tpl = a.outreach_templates || [];
  if (!tpl.length) return '<p>No templates generated.</p>';
  const words = (t) => String(t).toLowerCase().split(/[^a-zäöüß]+/).filter(w => w.length > 3);
  const best = (c) => tpl.map(t => ({ t, hit: words(t.for_role).filter(w => (c.title + ' ' + c.matched_role).toLowerCase().includes(w)).length }))
                         .sort((x, y) => y.hit - x.hit)[0].t;
  const targets = (d.contacts || []).filter(c => c.priority !== 'C').slice(0, 5);
  const blocks = targets.length ? targets.map(c => ({ c, t: best(c) })) : tpl.map(t => ({ c: null, t }));
  return blocks.map(({ c, t }) => `<div style="border-left:3px solid #c2410c;padding:6px 12px;margin:10px 0">
<p style="margin:0"><b>${c ? `<a href="${c.linkedin}">${c.name}</a> · ${c.title}` : t.for_role}</b> · ${t.channel}${t.subject ? ' · <i>' + t.subject + '</i>' : ''}</p>
<p style="white-space:pre-wrap;margin:6px 0 0">${String(t.body).replace(/\{first_name\}/g, c ? c.name.split(' ')[0] : '{first_name}')}</p></div>`).join('');
})()}
<p><b>Buying committee (roles):</b></p><ul>${li(a.buying_committee)}</ul>
<p><b>Suggested angle:</b> ${a.angle ?? "n/a"}</p><ul>${li(a.score_reasons)}</ul>
<p><b>Agent e-mail to the sign-ups:</b> ${d.autoSend ? "sent automatically" : "NOT sent, please review"}</p>
<p style="color:#666">Contacts come from public LinkedIn profiles (name, title, location). Reach out personally (LinkedIn, phone, event); no automated e-mails to them.
When you first contact someone, tell them where you found their details and how to object (GDPR Art. 14). Subscriber addresses are not included.</p>`;
const prio = !d.analysis ? 'REVIEW' : d.score >= HOT_SCORE_VALUE ? 'HOT' : d.score >= 50 ? 'WARM' : 'FYI';
return [{ json: { subject: `[${prio} ${d.score ?? ''}] ${d.company?.name || d.domain}: ${d.colleagues} sign-ups, ${(d.contacts || []).length} contacts`, html } }];
''').replace("HOT_SCORE_VALUE", str(HOT_SCORE))

# --- Chain B ---------------------------------------------------------------
reply_system = ("Classify a reply to our e-mail. Return ONLY JSON: {\\\"label\\\": \\\"interested\\\"|\\\"question\\\"|\\\"not_interested\\\"|\\\"stop\\\", \\\"summary\\\": string}. "
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
   "parameters": {"httpMethod": "POST", "path": WEBHOOK_PATH, "authentication": "headerAuth", "options": {}}},
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
        "={{ JSON.stringify({ profileScraperMode: 'Short ($4 per 1k)', maxItems: 15, companies: $('Verify company match').first().json.company ? [$('Verify company match').first().json.company.linkedinUrl] : [], jobTitles: " + json.dumps(DECISION_ROLES).replace('\"', "'") + " }) }}",
        [1100, 200], "Only job titles reach the LLM (buying committee as roles). Check the exact profileScraperMode value in the actor input."),
  apify("Latest news", "apify/rag-web-browser",
        "={{ JSON.stringify({ query: '\"' + ($('Verify company match').first().json.company?.name || $('Verify company match').first().json.domain) + '\" after:' + new Date(Date.now() - " + str(NEWS_DAYS) + " * 864e5).toISOString().slice(0, 10), maxResults: 5, scrapingTool: 'raw-http', outputFormats: ['markdown'] }) }}",
        [1320, 120], "Google search + page text for recent news. ~$0.01 per run."),
  apify("Website", "apify/rag-web-browser",
        "={{ JSON.stringify({ query: 'https://' + $('Verify company match').first().json.domain, scrapingTool: 'raw-http', outputFormats: ['markdown'] }) }}",
        [1540, 120], "The organisation's own homepage as Markdown."),
  apify("Pain signal", "apify/rag-web-browser",
        "={{ JSON.stringify({ query: " + json.dumps(PAIN_SIGNAL_QUERY) + ".replace('{domain}', $('Verify company match').first().json.domain).replace('{name}', $('Verify company match').first().json.company?.name || $('Verify company match').first().json.domain), maxResults: 5, scrapingTool: 'raw-http', outputFormats: ['markdown'] }) }}",
        [1760, 120], PAIN_SIGNAL_LABEL),
  apify("Customer voice", "apify/rag-web-browser",
        "={{ JSON.stringify({ query: " + json.dumps(VOICE_QUERY) + ".replace('{domain}', $('Verify company match').first().json.domain).replace('{name}', $('Verify company match').first().json.company?.name || $('Verify company match').first().json.domain), maxResults: 5, scrapingTool: 'raw-http', outputFormats: ['markdown'] }) }}",
        [1980, 120], VOICE_LABEL + ". Only counts and short excerpts reach the LLM; no usernames."),
  {"id": uid(), "name": "Build context", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [1760, 300],
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
         ("LinkedIn posts", 0, "Decision-maker roles"), ("Decision-maker roles", 0, "Latest news"), ("Latest news", 0, "Website"), ("Website", 0, "Pain signal"), ("Pain signal", 0, "Customer voice"), ("Customer voice", 0, "Build context"),
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

wf = {"name": WORKFLOW_NAME,
      "nodes": nodes, "connections": connections, "settings": {"executionOrder": "v1"}, "pinData": {}}
json.dump(wf, open("critical-mass.json", "w"), ensure_ascii=False, indent=2)
print(f"{len(nodes)} nodes, {len(links)} links")
