"""Flashpoint: builds and deploys the two n8n workflows.

  python3 n8n/flashpoint.py            build flashpoint-main.json and flashpoint-eval.json
  python3 n8n/flashpoint.py --deploy   build, then create or update both workflows in n8n (reads .env)

Main workflow: sign-up threshold -> account research (Apify) -> AI analysis (Featherless) -> act -> document.
Eval workflow: reads the documented analyses, runs rule checks and an LLM judge, writes scores, e-mails a report.
Credentials that need a Google sign-in (Gmail, Google Sheets) are reused from n8n by type; nodes whose
credential is missing are disabled so the workflow can still be activated.
"""
import json, os, subprocess, sys, urllib.error, urllib.request, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from node_docs import MAIN as MAIN_DOCS, EVAL as EVAL_DOCS, legend
import watch as W

HERE = os.path.dirname(os.path.abspath(__file__))
SHEET_ID = os.environ.get("SHEET_ID") or "1Ev5RSeKo1slDfSgWdic-gZuwFynjbpAdi4__cpOi0rU"
JUDGE_MODEL = os.environ.get("JUDGE_MODEL") or "deepseek-ai/DeepSeek-V3-0324"   # different family from the analyst
EVAL_EMAIL = os.environ.get("EVAL_EMAIL") or os.environ.get("SALES_EMAIL") or "eval-team@example.com"
EVAL_NAME = "Flashpoint · Eval (LLM as a judge)"

ANALYSES_HEADERS = ["analysis_id", "logged_at", "domain", "organisation", "locations", "linkedin_verified", "colleagues", "roles", "score",
                    "decision", "handoff_reason", "angle", "news_summary", "pain_evidence", "culture", "structure",
                    "buying_committee", "score_reasons", "email_subject", "email_html", "contacts", "evidence_urls", "dropped_hits",
                    "context_json", "model"]
EVALS_HEADERS = ["analysis_id", "judged_at", "domain", "judge_model", "groundedness", "relevance", "actionability",
                 "email_quality", "compliance", "calibration", "llm_overall", "rule_checks_passed", "rule_failures",
                 "verdict", "issues", "judge_comment"]

# n8n sticky note colours: 1 yellow, 2 orange, 3 red, 4 green, 5 blue, 6 purple, 7 grey
def uid(): return str(uuid.uuid4())
def sticky(name, x, y, w, h, color, content):
    return {"id": uid(), "name": name, "type": "n8n-nodes-base.stickyNote", "typeVersion": 1, "position": [x, y],
            "parameters": {"content": content, "width": w, "height": h, "color": color}}
def rl_id(v): return {"__rl": True, "mode": "id", "value": v}
def rl_name(v): return {"__rl": True, "mode": "name", "value": v}
SHEETS = {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets (set me)"}}
GMAIL = {"gmailOAuth2": {"id": "", "name": "Gmail (set me)"}}
FL_AUTH = {"httpHeaderAuth": {"id": "", "name": "Featherless (Authorization: Bearer <key>)"}}

def connect(wf, a, b, out=0):
    main = wf["connections"].setdefault(a, {"main": []})["main"]
    while len(main) <= out: main.append([])
    main[out].append({"node": b, "type": "main", "index": 0})


# ------------------------------------------------------------------ main workflow
LAYOUT = {
    "Form sign-up": (0, 240), "Exactly 3 colleagues?": (220, 240),
    "LinkedIn company": (520, 240), "Verify company match": (730, 240), "LinkedIn posts": (940, 240),
    "Decision-maker roles": (1150, 240), "Latest news": (1360, 240), "Website": (1570, 240),
    "Pain signal": (1780, 240), "Customer voice": (1990, 240),
    "Build context": (2290, 240), "Featherless analysis": (2500, 240), "Parse analysis": (2710, 240),
    "Send automatically?": (3020, 120), "Agent e-mails the sign-ups": (3240, 120),
    "Hand to a human?": (3020, 280), "Write briefing": (3240, 280), "Briefing to sales": (3460, 280),
    "Prepare log row": (3020, 440), "Log analysis to sheet": (3240, 440),
    "Reply received": (0, 640), "Classify reply": (220, 640), "Parse reply": (440, 640),
    "Interested or question?": (660, 640), "Hand reply to a human": (880, 640),
}
NOTES = {
    "Exactly 3 colleagues?": "Fires once per organisation, on the exact threshold sign-up.",
    "Verify company match": "Abstains if the LinkedIn page is not this organisation.",
    "Pain signal": "Signal nobody uses: public evidence of the pain on the org's own site.",
    "Customer voice": "What the org's own customers say publicly (usernames removed).",
    "Parse analysis": "Code decides: auto-send, hand to a human, or both.",
    "Agent e-mails the sign-ups": "Only consented sign-ups, in BCC.",
    "Log analysis to sheet": "Every analysis is documented for the eval team.",
}

prepare_log_js = r'''
// One flat row per analysis for the "Analyses" tab. The eval workflow reads these rows.
const d = $('Parse analysis').first().json;
const a = d.analysis || {};
const join = (x) => Array.isArray(x) ? x.join(' | ') : (x ?? '');
const evidence = [...(d.painSignal || []), ...(d.customerVoice || []), ...(d.news || [])].map(h => h.url).filter(Boolean);
const context = { company: d.company, roles_signed_up: d.roles, notes: d.notes, top_posts: (d.topPosts || []).slice(0, 5),
  people_roles: d.roleTitles, news: d.news, pain_signal: d.painSignal, customer_voice: d.customerVoice,
  website_excerpt: String(d.website || '').slice(0, 1500) };
return [{ json: {
  analysis_id: $execution.id + '-' + d.domain,
  logged_at: new Date().toISOString(),
  domain: d.domain,
  organisation: d.company?.name ?? '',
  locations: (d.company?.locations || []).join(', '),
  linkedin_verified: d.verified ? 'yes' : 'no',
  colleagues: d.colleagues,
  roles: join(d.roles),
  score: d.score ?? '',
  decision: [d.autoSend ? 'auto-email' : null, d.handToHuman ? 'human' : null].filter(Boolean).join(' + ') || 'none',
  handoff_reason: d.handoffReason ?? '',
  angle: a.angle ?? '', news_summary: a.news_summary ?? '', pain_evidence: a.pain_evidence ?? '',
  culture: a.culture ?? '', structure: a.structure ?? '',
  buying_committee: join(a.buying_committee), score_reasons: join(a.score_reasons),
  email_subject: a.champion_email_subject ?? '', email_html: String(a.champion_email_html ?? '').slice(0, 8000),
  contacts: (d.contacts || []).map(c => `${c.priority} · ${c.name} · ${c.title} · ${c.linkedin}`).join('\n'),
  evidence_urls: evidence.join(' '), dropped_hits: d.droppedHits ?? 0,
  context_json: JSON.stringify(context).slice(0, 20000),
  model: 'MODEL_PLACEHOLDER',
}}];
'''

def build_main():
    subprocess.run([sys.executable, os.path.join(HERE, "build_critical_mass.py")], check=True, cwd=HERE,
                   stdout=subprocess.DEVNULL)
    wf = json.load(open(os.path.join(HERE, "critical-mass.json")))
    model = os.environ.get("FEATHERLESS_MODEL") or "Qwen/Qwen2.5-72B-Instruct"
    wf["nodes"] += [
        {"id": uid(), "name": "Prepare log row", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [0, 0],
         "parameters": {"jsCode": prepare_log_js.replace("MODEL_PLACEHOLDER", model)}},
        {"id": uid(), "name": "Log analysis to sheet", "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5,
         "position": [0, 0], "credentials": SHEETS, "onError": "continueRegularOutput",
         "parameters": {"resource": "sheet", "operation": "append", "documentId": rl_id(SHEET_ID),
                        "sheetName": rl_name("Analyses"),
                        "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []},
                        "options": {}}},
    ]
    connect(wf, "Parse analysis", "Prepare log row")
    connect(wf, "Prepare log row", "Log analysis to sheet")

    for n in wf["nodes"]:
        if n["name"] in LAYOUT: n["position"] = list(LAYOUT[n["name"]])
        if n["name"] in MAIN_DOCS:
            ph, what, api, cost = MAIN_DOCS[n["name"]]
            n["notes"], n["notesInFlow"] = f"{what}\n[{api} · {cost}]", True

    wf["nodes"] += [
        sticky("About Flashpoint", -60, -140, 1500, 230, 7,
               "# Flashpoint · account signal agent\n"
               "**One sign-up is curiosity. Three from the same organisation is a flashpoint.**\n\n"
               "When the threshold is reached, the agent researches the organisation, scores it, writes to the people who signed up "
               "and hands hot accounts to a human. Every analysis is logged to the **Analyses** tab and judged by the "
               "**Flashpoint · Eval** workflow.\n\n"
               "Input: Apps Script on the sign-up sheet · Research: Apify · Analysis: Featherless · Output: Gmail + Google Sheets"),
        sticky("1 · Trigger and threshold", -60, 110, 500, 300, 4,
               "## 1 · Trigger and threshold\nThe sheet script posts here when the **Nth distinct person** from one e-mail "
               "domain signs up. Secured by the `x-signal-secret` header. Private e-mail domains never reach this point."),
        sticky("2 · Account research", 460, 110, 1740, 300, 5,
               "## 2 · Account research (Apify)\nLinkedIn profile, posts and decision-maker roles, latest news, the website, "
               "and two signals nobody uses: **pain on the org's own site** and **its customers' public voice**. "
               "Each step runs once and fails soft: a missing source never stops the run."),
        sticky("3 · AI analysis", 2220, 110, 700, 300, 6,
               "## 3 · AI analysis (Featherless)\nOff-target search hits are filtered out in code before the LLM sees them. "
               "The model extracts culture, structure, buying committee, angle, score and the e-mail. "
               "**Code, not the model, decides** what happens next."),
        sticky("4 · Act and document", 2940, -20, 720, 560, 2,
               "## 4 · Act and document\n**Auto e-mail** only to consented sign-ups (BCC) when LinkedIn is verified.\n"
               "**Human hand-off** when a call was requested, the score is high or anything is uncertain.\n"
               "**Log** every analysis to the sheet for the eval team."),
        sticky("Legend", 3700, -140, 820, 1020, 7, legend(MAIN_DOCS, "Flashpoint main workflow")),
        sticky("5 · Replies", -60, 510, 1160, 280, 3,
               "## 5 · Replies\nUnread replies to the agent's e-mail are classified. Interested replies and questions go to "
               "a human. STOP is respected."),
    ]
    wf["name"] = "Flashpoint · Kredible (universities)"
    return wf


# ------------------------------------------------------------------ eval workflow
select_js = r'''
// Analyses that have not been judged yet (max 20 per run to stay inside the model's concurrency).
const judged = new Set($('Read evals').all().map(i => String(i.json.analysis_id || '')).filter(Boolean));
return $('Read analyses').all().map(i => i.json)
  .filter(r => r.analysis_id && !judged.has(String(r.analysis_id)))
  .slice(0, 20).map(r => ({ json: r }));
'''

rules_js = r'''
// Deterministic checks. No model involved, so these are the hard floor of quality.
const r = $input.item.json;
const email = String(r.email_html || '');
const urls = String(r.evidence_urls || '').split(/\s+/).filter(Boolean);
const score = Number(r.score);
const checks = {
  stop_line_present: /STOP/.test(email) || email === '',
  no_email_addresses_in_text: !/[\w.+-]+@[\w-]+\.[\w.]+/.test(email),
  email_length_ok: email === '' || (email.length >= 300 && email.length <= 4000),
  score_in_range: Number.isFinite(score) && score >= 0 && score <= 100,
  high_score_has_reasons: !(score >= 70) || String(r.score_reasons || '').split('|').filter(s => s.trim()).length >= 2,
  pain_claim_has_evidence: !/\b[1-9]\d* hits?\b/i.test(String(r.pain_evidence || '')) || urls.some(u => u.includes(String(r.domain)) || u.includes('reddit.com')),
  auto_email_only_if_verified: !String(r.decision).includes('auto-email') || r.linkedin_verified === 'yes',
};
const failures = Object.entries(checks).filter(([, ok]) => !ok).map(([k]) => k);
return { json: { ...r, rule_failures: failures, rule_checks_passed: Object.keys(checks).length - failures.length,
                 rule_checks_total: Object.keys(checks).length } };
'''

judge_system = (
    "You are a strict evaluator of B2B sales research produced by an AI agent. You get the CONTEXT the agent saw and the "
    "ANALYSIS it wrote. Grade each criterion from 1 (bad) to 5 (excellent): "
    "groundedness (every claim in the analysis is supported by the CONTEXT; invented facts or counts are a 1), "
    "relevance (the analysis is about this organisation and this product, not something else), "
    "actionability (a salesperson knows what to do next), "
    "email_quality (clear, specific, polite, right language, not pushy), "
    "compliance (no personal data of third parties, contains an unsubscribe line, no false promises), "
    "calibration (the 0-100 score matches the evidence; a high score with weak evidence is a 1). "
    "Return ONLY JSON: {\\\"groundedness\\\":int,\\\"relevance\\\":int,\\\"actionability\\\":int,\\\"email_quality\\\":int,"
    "\\\"compliance\\\":int,\\\"calibration\\\":int,\\\"issues\\\":string[],\\\"comment\\\":string}."
)
judge_body = ("={{ JSON.stringify({ model: '" + JUDGE_MODEL + "', temperature: 0, max_tokens: 700, messages: ["
              "{ role: 'system', content: \"" + judge_system + "\" }, "
              "{ role: 'user', content: 'CONTEXT:\\n' + String($json.context_json).slice(0, 14000) + "
              "'\\n\\nANALYSIS:\\n' + JSON.stringify({ domain: $json.domain, organisation: $json.organisation, score: $json.score, "
              "decision: $json.decision, angle: $json.angle, news_summary: $json.news_summary, pain_evidence: $json.pain_evidence, "
              "culture: $json.culture, structure: $json.structure, buying_committee: $json.buying_committee, "
              "score_reasons: $json.score_reasons, email_subject: $json.email_subject, email_html: $json.email_html }) }] }) }}")

verdict_js = r'''
// Combine the judge's grades with the rule checks into one verdict per analysis.
const row = $('Rule checks').item.json;
const raw = $input.item.json.choices?.[0]?.message?.content ?? '';
let j = null;
try { j = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1)); } catch (e) {}
const dims = ['groundedness', 'relevance', 'actionability', 'email_quality', 'compliance', 'calibration'];
const g = Object.fromEntries(dims.map(k => [k, j && Number.isFinite(+j[k]) ? Math.max(1, Math.min(5, +j[k])) : null]));
const vals = dims.map(k => g[k]).filter(v => v !== null);
const overall = vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length * 10) / 10 : null;
const verdict = !j ? 'judge-error'
  : (row.rule_failures.length === 0 && overall >= 3.5 && g.groundedness >= 3 && g.compliance >= 4) ? 'pass' : 'fail';
return { json: {
  analysis_id: row.analysis_id, judged_at: new Date().toISOString(), domain: row.domain, judge_model: 'JUDGE_PLACEHOLDER',
  ...g, llm_overall: overall ?? '',
  rule_checks_passed: row.rule_checks_passed + '/' + row.rule_checks_total, rule_failures: row.rule_failures.join(', '),
  verdict, issues: (j?.issues || []).join(' | '), judge_comment: j?.comment ?? raw.slice(0, 300),
}};
'''

report_js = r'''
// One summary e-mail for the eval team.
const rows = $('Parse verdict').all().map(i => i.json);
if (!rows.length) return [{ json: { skip: true } }];
const dims = ['groundedness', 'relevance', 'actionability', 'email_quality', 'compliance', 'calibration'];
const avg = (k) => { const v = rows.map(r => +r[k]).filter(Number.isFinite); return v.length ? (v.reduce((a, b) => a + b, 0) / v.length).toFixed(1) : 'n/a'; };
const pass = rows.filter(r => r.verdict === 'pass').length;
const fails = {};
rows.forEach(r => String(r.rule_failures || '').split(', ').filter(Boolean).forEach(f => fails[f] = (fails[f] || 0) + 1));
const worst = [...rows].sort((a, b) => (+a.llm_overall || 0) - (+b.llm_overall || 0)).slice(0, 3);
const html = `
<h2>Flashpoint eval: ${pass}/${rows.length} analyses passed</h2>
<p>Judge: JUDGE_PLACEHOLDER (a different model family from the analyst). Pass = all rule checks green, average grade at least 3.5, groundedness at least 3, compliance at least 4.</p>
<table border="1" cellpadding="6" style="border-collapse:collapse">
<tr><th>Criterion</th><th>Average (1-5)</th></tr>
${dims.map(k => `<tr><td>${k}</td><td>${avg(k)}</td></tr>`).join('')}
</table>
<h3>Rule check failures</h3>
<ul>${Object.entries(fails).map(([k, v]) => `<li>${k}: ${v}</li>`).join('') || '<li>none</li>'}</ul>
<h3>Weakest analyses</h3>
<ul>${worst.map(r => `<li><b>${r.domain}</b> (${r.llm_overall}, ${r.verdict}): ${r.issues || r.judge_comment}</li>`).join('')}</ul>
<p>All rows are in the <b>Evals</b> tab of the sign-up sheet.</p>`;
return [{ json: { subject: `Flashpoint eval: ${pass}/${rows.length} passed`, html } }];
'''

def build_eval():
    n = lambda name, typ, ver, pos, params, **extra: {"id": uid(), "name": name, "type": typ, "typeVersion": ver,
                                                       "position": list(pos), "parameters": params, **extra}
    read = lambda name, tab, pos: n(name, "n8n-nodes-base.googleSheets", 4.5, pos,
                                    {"resource": "sheet", "operation": "read", "documentId": rl_id(SHEET_ID),
                                     "sheetName": rl_name(tab), "options": {}},
                                    credentials=SHEETS, executeOnce=True, alwaysOutputData=True, onError="continueRegularOutput")
    nodes = [
        n("Run evaluation now", "n8n-nodes-base.manualTrigger", 1, (0, 160), {}),
        n("Every day at 18:00", "n8n-nodes-base.scheduleTrigger", 1.2, (0, 320), {"rule": {"interval": [{"triggerAtHour": 18}]}}),
        read("Read analyses", "Analyses", (260, 240)),
        read("Read evals", "Evals", (470, 240)),
        n("Select unjudged", "n8n-nodes-base.code", 2, (680, 240), {"jsCode": select_js}),
        n("Rule checks", "n8n-nodes-base.code", 2, (960, 240), {"mode": "runOnceForEachItem", "jsCode": rules_js},
          notes="7 deterministic checks: STOP line, no e-mail addresses, evidence behind claims ...", notesInFlow=True),
        n("LLM judge", "n8n-nodes-base.httpRequest", 4.2, (1170, 240),
          {"method": "POST", "url": "https://api.featherless.ai/v1/chat/completions",
           "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
           "sendBody": True, "specifyBody": "json", "jsonBody": judge_body,
           "options": {"timeout": 180000, "batching": {"batch": {"batchSize": 1, "batchInterval": 500}}}},
          credentials=FL_AUTH, onError="continueRegularOutput",
          notes=f"Judge model: {JUDGE_MODEL}", notesInFlow=True),
        n("Parse verdict", "n8n-nodes-base.code", 2, (1380, 240),
          {"mode": "runOnceForEachItem", "jsCode": verdict_js.replace("JUDGE_PLACEHOLDER", JUDGE_MODEL)}),
        n("Write to Evals tab", "n8n-nodes-base.googleSheets", 4.5, (1680, 160),
          {"resource": "sheet", "operation": "append", "documentId": rl_id(SHEET_ID), "sheetName": rl_name("Evals"),
           "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []}, "options": {}},
          credentials=SHEETS, onError="continueRegularOutput"),
        n("Build report", "n8n-nodes-base.code", 2, (1680, 320), {"jsCode": report_js.replace("JUDGE_PLACEHOLDER", JUDGE_MODEL)}),
        n("Anything judged?", "n8n-nodes-base.if", 2.2, (1890, 320),
          {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                          "conditions": [{"id": uid(), "leftValue": "={{ $json.skip }}", "rightValue": "",
                                          "operator": {"type": "boolean", "operation": "notTrue", "singleValue": True}}],
                          "combinator": "and"}, "options": {}}),
        n("E-mail eval team", "n8n-nodes-base.gmail", 2.1, (2100, 320),
          {"resource": "message", "operation": "send", "sendTo": EVAL_EMAIL, "subject": "={{ $json.subject }}",
           "emailType": "html", "message": "={{ $json.html }}", "options": {"appendAttribution": False}},
          credentials=GMAIL),
        sticky("About Eval", -60, -150, 1240, 200, 7,
               "# Flashpoint · Eval (LLM as a judge)\nChecks how well the agent performs. Every analysis logged by the main "
               "workflow is graded twice: by **7 hard rule checks** in code and by a **judge model from a different model "
               "family**, so the analyst never grades itself. Results go to the **Evals** tab and a summary e-mail."),
        sticky("1 · Load", -60, 70, 920, 400, 4,
               "## 1 · Load\nRuns daily at 18:00 or on demand. Reads the **Analyses** and **Evals** tabs and keeps only analyses "
               "that were not judged yet."),
        sticky("2 · Grade", 880, 70, 680, 400, 6,
               "## 2 · Grade\n**Rule checks** (no model): unsubscribe line, no e-mail addresses, evidence behind claims, "
               "score range, reasons for high scores, auto e-mail only when verified.\n**LLM judge**: groundedness, relevance, "
               "actionability, e-mail quality, compliance, calibration (1-5)."),
        sticky("3 · Report", 1580, 70, 720, 400, 2,
               "## 3 · Report\nPass = all rules green, average at least 3.5, groundedness at least 3, compliance at least 4. "
               "Rows go to **Evals**; the team gets averages, rule failures and the three weakest analyses."),
    ]
    wf = {"name": EVAL_NAME, "nodes": nodes, "connections": {}, "settings": {"executionOrder": "v1"}}
    for a, b in [("Run evaluation now", "Read analyses"), ("Every day at 18:00", "Read analyses"), ("Read analyses", "Read evals"),
                 ("Read evals", "Select unjudged"), ("Select unjudged", "Rule checks"), ("Rule checks", "LLM judge"),
                 ("LLM judge", "Parse verdict"), ("Parse verdict", "Write to Evals tab"), ("Parse verdict", "Build report")]:
        connect(wf, a, b)
    # Build report must run once over all verdicts, not per item
    for node in wf["nodes"]:
        if node["name"] == "Build report": node["executeOnce"] = True
        if node["name"] in EVAL_DOCS:
            ph, what, api, cost = EVAL_DOCS[node["name"]]
            node["notes"], node["notesInFlow"] = f"{what}\n[{api}]", True
    wf["nodes"].append(sticky("Legend", 2340, -150, 760, 760, 7, legend(EVAL_DOCS, "Flashpoint eval workflow")))
    connect(wf, "Build report", "Anything judged?")
    connect(wf, "Anything judged?", "E-mail eval team")
    return wf


# ------------------------------------------------------------------ signal watch workflow
def build_watch():
    model = os.environ.get("FEATHERLESS_MODEL") or "Qwen/Qwen2.5-72B-Instruct"
    sales = ",".join(x.strip() for x in [os.environ.get("SALES_EMAIL") or "sales@example.com", *os.environ.get("SALES_TEAM", "").split(",")] if x.strip())
    wf = W.build(sticky, connect, SHEET_ID, rl_id, rl_name, SHEETS, GMAIL, FL_AUTH,
                 {"httpHeaderAuth": {"id": "", "name": "Apify (Authorization: Bearer <token>)"}}, model, sales)
    for node in wf["nodes"]:
        if node["name"] in W.DOCS:
            ph, what, api, cost = W.DOCS[node["name"]]
            node["notes"], node["notesInFlow"] = f"{what}\n[{api} · {cost}]", True
    wf["nodes"] += [
        sticky("About Signal Watch", -60, -170, 1400, 230, 7,
               "# Flashpoint · Signal Watch\n**Funding released, budgets frozen, rules changed: react the same day.**\n\n"
               "Three times a day the watch searches the news, rates every new hit, saves all of it, and e-mails sales when a "
               "signal is strong, with the affected accounts and their contacts. It learns which searches work: every search "
               "has a precision score, dead ones are retired, and new ones are proposed from strong signals."),
        sticky("1 · Collect", -60, 80, 1300, 360, 4,
               "## 1 · Collect\nMon–Fri 08:00 · 12:00 · 15:00. Searches come from the **Watch queries** tab (editable) plus defaults. "
               "Only hits from the last 3 days that were never seen before go on."),
        sticky("2 · Rate", 1260, 80, 440, 360, 6,
               "## 2 · Rate\nEach hit is rated 0-100 with event type, region, urgency and an action. "
               "Hits sales marked useful or not are shown to the model as examples."),
        sticky("3 · Save and learn", 1720, 80, 480, 360, 5,
               "## 3 · Save and learn\nEvery rated hit goes to **Signals** (the knowledge base). Search stats go to "
               "**Watch queries**: precision per search, dead searches retired, learned searches added."),
        sticky("4 · Alert", 1720, 460, 1000, 260, 2,
               "## 4 · Alert\nSignals rated 60+ are matched to known accounts by region and sector; sales gets one digest "
               "with the action and the saved decision makers."),
        sticky("Legend", 2740, -170, 800, 1080, 7, legend(W.DOCS, "Flashpoint Signal Watch")),
    ]
    return wf


# ------------------------------------------------------------------ deploy
def call(method, path, body=None):
    base = os.environ["N8N_BASE_URL"].rstrip("/")
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"X-N8N-API-KEY": os.environ["N8N_API_KEY"], "content-type": "application/json",
                                          "user-agent": "flashpoint-deploy/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:400]

def deploy(wf, creds, existing):
    by_type = {}
    for c in creds:
        by_type.setdefault(c["type"], {"id": c["id"], "name": c["name"]})
    named = {c["name"]: {"id": c["id"], "name": c["name"]} for c in creds}
    header_map = {"Featherless (Authorization: Bearer <key>)": "Critical Mass · Featherless",
                  "Apify (Authorization: Bearer <token>)": "Critical Mass · Apify",
                  "x-signal-secret (set me)": "Critical Mass · signal secret"}
    disabled = []
    for node in wf["nodes"]:
        refs = node.get("credentials") or {}
        for ctype, ref in list(refs.items()):
            if ctype == "httpHeaderAuth":
                refs[ctype] = named.get(header_map.get(ref["name"], ref["name"]), ref)
            elif ctype in by_type:
                refs[ctype] = by_type[ctype]
            else:
                del refs[ctype]
                node["disabled"] = True
                disabled.append(f"{node['name']} (needs {ctype})")
        if "credentials" in node and not node["credentials"]: node.pop("credentials")
    body = {k: wf[k] for k in ("name", "nodes", "connections", "settings")}
    body["settings"] = {k: v for k, v in body["settings"].items() if k in ("executionOrder", "timezone")}
    match = next((w for w in existing if w["name"] == wf["name"]), None)
    if match:
        s, res = call("PUT", f"/api/v1/workflows/{match['id']}", body); wid = match["id"]
    else:
        s, res = call("POST", "/api/v1/workflows", body); wid = res["id"] if isinstance(res, dict) else None
    print(f"{wf['name']}: {'updated' if match else 'created'} ({s})" + ("" if s in (200, 201) else f" {res}"))
    if disabled: print("  disabled until the credential exists:", "; ".join(disabled))
    if wid:
        s, res = call("POST", f"/api/v1/workflows/{wid}/activate")
        print("  active" if s == 200 else f"  not active ({s}): {str(res)[:200]}")
        print("  " + os.environ["N8N_BASE_URL"].rstrip("/") + f"/workflow/{wid}")


if __name__ == "__main__":
    main, ev, wt = build_main(), build_eval(), build_watch()
    json.dump(main, open(os.path.join(HERE, "flashpoint-main.json"), "w"), ensure_ascii=False, indent=2)
    json.dump(ev, open(os.path.join(HERE, "flashpoint-eval.json"), "w"), ensure_ascii=False, indent=2)
    json.dump(wt, open(os.path.join(HERE, "flashpoint-watch.json"), "w"), ensure_ascii=False, indent=2)
    print(f"main: {len(main['nodes'])} nodes · eval: {len(ev['nodes'])} nodes · watch: {len(wt['nodes'])} nodes")
    if "--deploy" in sys.argv:
        s, creds = call("GET", "/api/v1/credentials?limit=100")
        s2, wfs = call("GET", "/api/v1/workflows?limit=100")
        existing = wfs.get("data", [])
        # the previously deployed main workflow may still carry an older name
        for w in existing:
            if w["name"].startswith(("Critical Mass", "Flashpoint · Kredible")): w["name"] = main["name"]
        deploy(main, creds.get("data", []), existing)
        deploy(ev, creds.get("data", []), existing)
        deploy(wt, creds.get("data", []), existing)
