"""Generates docs/flashpoint-docs.html from the build scripts, so the page always matches what is deployed.

Run from the project root:  python3 n8n/docs.py
"""
import html, json, os, runpy, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
os.environ.pop("SALES_EMAIL", None); os.environ.pop("SALES_TEAM", None)  # keep personal addresses out of the page

cwd = os.getcwd(); os.chdir(HERE)
B = runpy.run_path("build_critical_mass.py")          # analyst prompt, signal queries, config
os.chdir(cwd)
import flashpoint as F
from node_docs import MAIN, EVAL
import watch as W

main = F.build_main()
ev = F.build_eval()
e = html.escape

def unescape(s):
    return s.replace('\\\\\\"', '"').replace('\\"', '"')

def jsbody(wf, name):
    node = next(n for n in wf["nodes"] if n["name"] == name)
    return node["parameters"].get("jsonBody", "")

def code(wf, name):
    return next(n for n in wf["nodes"] if n["name"] == name)["parameters"]["jsCode"].strip()

def pre(text, lang=""):
    return f'<pre class="code" data-lang="{e(lang)}"><code>{e(text)}</code></pre>'

def node_table(docs):
    rows, phase = [], None
    for name, (ph, what, api, cost) in docs.items():
        if ph != phase:
            rows.append(f'<tr class="phase"><td colspan="4">{e(ph)}</td></tr>'); phase = ph
        rows.append(f"<tr><td><b>{e(name)}</b></td><td>{e(what)}</td><td><code>{e(api)}</code></td><td class='num'>{e(cost)}</td></tr>")
    return '<div class="box"><table><thead><tr><th>Node</th><th>What it does</th><th>API / tool</th><th class="num">Cost</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"

apify_rows = []
for name in ["LinkedIn company", "LinkedIn posts", "Decision-maker roles", "Latest news", "Website", "Pain signal", "Customer voice"]:
    node = next(n for n in main["nodes"] if n["name"] == name)
    actor = node["parameters"]["url"].split("/acts/")[1].split("/")[0].replace("~", "/")
    apify_rows.append(f"<tr><td><b>{e(name)}</b></td><td><a href='https://apify.com/{e(actor)}'>{e(actor)}</a></td><td>{e(MAIN[name][3])}</td></tr>")

webhook_example = {
    "email": "newest sign-up", "city": "Berlin", "company_domain": "tu-berlin.de", "colleagues": 3, "threshold": 3,
    "colleague_emails": ["a@tu-berlin.de", "b@tu-berlin.de", "c@tu-berlin.de"],
    "roles": ["International office", "Admissions", "Finance"],
    "notes": ["Technische Universität Berlin | wants partnership call"], "source": "google-sheet",
    "submitted_at": "2026-10-03T12:00:00Z"}

sections = [
    ("overview", "Overview", f"""
<p>One sign-up is curiosity. When <b>{B['THRESHOLD']} different people</b> from the same organisation sign up, Flashpoint researches the
organisation, scores it, writes to the people who signed up and hands hot accounts to a human. Every analysis is logged and graded
by a second model.</p>
<div class="flow">
  <span>Landing page / Google Form</span><b>→</b><span>Google Sheet</span><b>→</b><span>Apps Script<br><small>count per domain</small></span><b>→</b>
  <span>n8n webhook</span><b>→</b><span>Apify research<br><small>7 sources</small></span><b>→</b><span>Featherless analyst</span><b>→</b>
  <span>Code decides</span><b>→</b><span>Gmail + Sheet log</span><b>→</b><span>Eval: rules + LLM judge</span>
</div>"""),
    ("nodes-main", "Main workflow · every node", node_table(MAIN)),
    ("nodes-eval", "Eval workflow · every node", node_table(EVAL)),
    ("nodes-watch", "Signal Watch · every node", f"<p>Runs <code>{e(W.SCHEDULE)}</code> (Mon–Fri 08:00, 12:00, 15:00 Berlin). Signals rated {W.RELEVANT}+ go to sales.</p>" + node_table(W.DOCS)),
    ("prompts", "Prompts", f"""
<h3>1 · Analyst (Featherless · <code>{e(B['FEATHERLESS_MODEL'])}</code>, temperature 0.2)</h3>
<p class="sub">System prompt. The user message is a JSON object with the context listed under it.</p>
{pre(unescape(B['analysis_system']), 'system prompt')}
<p class="sub">User message fields: domain, colleagues_subscribed, roles, form_notes, partnership_call_requested, linkedin_verified, company,
top_posts, people_roles, latest_news, website, pain_signal, customer_voice.</p>
<h3>2 · Reply classifier (Featherless · same model)</h3>
{pre(unescape(B['reply_system']), 'system prompt')}
<h3>3 · LLM judge (Featherless · <code>{e(F.JUDGE_MODEL)}</code>, temperature 0)</h3>
<p class="sub">A different model family from the analyst, so the analyst never grades itself.</p>
{pre(unescape(F.judge_system), 'system prompt')}
<p class="sub">User message: <code>CONTEXT:</code> the full context the analyst saw, then <code>ANALYSIS:</code> the analyst's output.</p>
<h3>4 · Signal rater (Signal Watch, temperature 0)</h3>
{pre(unescape(W.rate_system), 'system prompt')}
<p class="sub">User message: up to 6 earlier hits sales marked useful / not useful (self-learning), then the article.</p>
<h3>5 · Account matcher (Signal Watch)</h3>
{pre(unescape(W.match_system), 'system prompt')}
<h3>Default watch searches</h3><ul>{''.join('<li><code>' + e(q) + '</code></li>' for q in W.DEFAULT_QUERIES)}</ul>
<h3>Self-learning rules</h3><ul><li>Every search keeps runs, hits, relevant hits and precision in the <b>Watch queries</b> tab.</li>
<li>A search with {W.RETIRE_AFTER_RUNS} runs and no relevant hit is retired.</li>
<li>Strong signals propose up to 2 new searches each; they are added as <code>learned</code> (max {W.MAX_ACTIVE_QUERIES} active).</li>
<li>Rows sales marks <code>useful</code> yes/no in the <b>Signals</b> tab are shown to the rater as examples.</li></ul>"""),
    ("signals", "Signal queries", f"""
<p>Search queries sent to <code>apify/rag-web-browser</code>. <code>{{domain}}</code> and <code>{{name}}</code> are filled per account.</p>
<div class="box"><table><thead><tr><th>Signal</th><th>Query</th></tr></thead><tbody>
<tr><td><b>Pain signal</b><div class="sub">{e(B['PAIN_SIGNAL_LABEL'])}</div></td><td><code>{e(B['PAIN_SIGNAL_QUERY'])}</code></td></tr>
<tr><td><b>Customer voice</b><div class="sub">{e(B['VOICE_LABEL'])}</div></td><td><code>{e(B['VOICE_QUERY'])}</code></td></tr>
<tr><td><b>Latest news</b></td><td><code>"{{name}}" after:{{today − {B['NEWS_DAYS']} days}}</code></td></tr>
<tr><td><b>Website</b></td><td><code>https://{{domain}}</code></td></tr>
</tbody></table></div>
<h3>Decision-maker roles searched on LinkedIn</h3><p>{e(', '.join(B['DECISION_ROLES']))}</p>"""),
    ("apis", "APIs and services", f"""
<div class="box"><table><thead><tr><th>Service</th><th>Endpoint</th><th>Auth</th><th>Used for</th></tr></thead><tbody>
<tr><td><b>Apify</b></td><td><code>POST https://api.apify.com/v2/acts/{{actor}}/run-sync-get-dataset-items</code></td><td>Bearer token (credential "Critical Mass · Apify")</td><td>All research steps</td></tr>
<tr><td><b>Featherless</b></td><td><code>POST https://api.featherless.ai/v1/chat/completions</code> (OpenAI-compatible)</td><td>Bearer key ("Critical Mass · Featherless")</td><td>Analyst, reply classifier, judge</td></tr>
<tr><td><b>n8n webhook</b></td><td><code>POST /webhook/{e(B['WEBHOOK_PATH'])}</code></td><td>Header <code>x-signal-secret</code></td><td>Entry point from the sheet script</td></tr>
<tr><td><b>Gmail</b></td><td>n8n Gmail node (OAuth)</td><td>Google sign-in</td><td>Agent e-mail, briefings, replies, eval report</td></tr>
<tr><td><b>Google Sheets</b></td><td>n8n Sheets node (OAuth) and Apps Script</td><td>Google sign-in</td><td>Sign-ups, Analyses log, Evals</td></tr>
</tbody></table></div>
<h3>Apify actors</h3>
<div class="box"><table><thead><tr><th>Node</th><th>Actor</th><th>Cost per account</th></tr></thead><tbody>{''.join(apify_rows)}</tbody></table></div>"""),
    ("data", "Data contracts", f"""
<h3>Webhook payload (sheet script → n8n)</h3>{pre(json.dumps(webhook_example, indent=2, ensure_ascii=False), 'json')}
<h3>Analyses tab</h3><p><code>{e(' · '.join(F.ANALYSES_HEADERS))}</code></p>
<h3>Evals tab</h3><p><code>{e(' · '.join(F.EVALS_HEADERS))}</code></p>
<h3>Signals tab</h3><p><code>{e(' · '.join(W.SIGNALS_HEADERS))}</code></p>
<h3>Watch queries tab</h3><p><code>{e(' · '.join(W.QUERIES_HEADERS))}</code></p>"""),
    ("logic", "Decision logic (code, not the model)", f"""
<h3>Parse analysis: auto e-mail or human</h3>{pre(code(main, 'Parse analysis'), 'javascript')}
<h3>Build context: drop off-target search hits</h3>{pre(code(main, 'Build context'), 'javascript')}
<h3>Eval rule checks</h3>{pre(code(ev, 'Rule checks'), 'javascript')}
<h3>Eval verdict</h3>{pre(code(ev, 'Parse verdict'), 'javascript')}"""),
    ("privacy", "Privacy and compliance", """
<ul>
<li>Sign-ups need consent; rows without it are marked <code>no consent</code> and never sent.</li>
<li>Private e-mail domains (gmail, gmx, web.de …) are never grouped by organisation.</li>
<li>The agent only writes to people who signed up, in BCC, with an unsubscribe line. No cold e-mail (UWG §7).</li>
<li>Decision makers from LinkedIn (name, title, profile URL, location) go to the sales briefing and the Analyses log. The LLM only sees their job titles.</li>
<li>Contacts found on LinkedIn are never e-mailed automatically. Sales reaches out personally and tells them where the details came from (GDPR Art. 14).</li>
<li>Reddit usernames and e-mail addresses are removed before the LLM.</li>
<li>Sales briefings do not contain the sign-ups' addresses.</li>
<li>Secrets live in n8n credentials and Apps Script properties, never in the repo.</li>
</ul>"""),
]

nav = "".join(f'<a href="#{sid}">{e(title)}</a>' for sid, title, _ in sections)
body = "".join(f'<section id="{sid}"><h2>{e(title)}</h2>{content}</section>' for sid, title, content in sections)

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Flashpoint Reference</title><style>
/* Layout: sticky side index on wide screens, single column on phones; reference-manual feel with mono for anything literal. */
:root{{--bg:#f5f4f1;--surface:#fff;--ink:#1b1c1f;--muted:#5f6168;--line:#dcdad4;--accent:#c2410c;--accent-soft:#fdeee5;--code:#f1efea;
--display:"Avenir Next","Segoe UI",system-ui,sans-serif;--body:"Iowan Old Style","Charter",Georgia,serif;--mono:ui-monospace,"SF Mono",Menlo,monospace}}
@media (prefers-color-scheme:dark){{:root{{--bg:#121315;--surface:#1b1c20;--ink:#e9e8e4;--muted:#a09fa6;--line:#2e2f35;--accent:#fb923c;--accent-soft:#3a2416;--code:#16171a;color-scheme:dark}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 var(--body)}}
.layout{{max-width:1280px;margin:0 auto;padding-inline:20px;padding-block:32px 80px;display:grid;grid-template-columns:220px minmax(0,1fr);gap:40px}}
nav{{position:sticky;top:24px;align-self:start;display:grid;gap:6px;font:500 .9rem var(--display)}}nav a{{color:var(--muted);text-decoration:none}}nav a:hover{{color:var(--accent)}}
header{{grid-column:1/-1;display:grid;gap:8px}}.eyebrow{{font:600 .72rem/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}}
h1,h2,h3{{font-family:var(--display);line-height:1.25;text-wrap:balance}}h1{{margin:0;font-size:2.2rem}}h2{{font-size:1.4rem;margin:0 0 14px;padding-top:8px;border-top:2px solid var(--ink)}}h3{{font-size:1.02rem;margin:22px 0 8px}}
main{{display:grid;gap:44px;min-width:0}}section{{min-width:0}}p{{max-width:72ch;margin:0 0 10px}}.sub{{color:var(--muted);font-size:.88rem}}
code{{font:.85em var(--mono);background:var(--code);padding:1px 5px;border-radius:4px}}
pre.code{{background:var(--code);border:1px solid var(--line);border-radius:8px;padding:14px 16px;overflow-x:auto;font:.8rem/1.55 var(--mono);white-space:pre-wrap;word-break:break-word;position:relative}}
pre.code::before{{content:attr(data-lang);position:absolute;top:6px;right:10px;font-size:.68rem;color:var(--muted);text-transform:uppercase}}pre.code code{{background:none;padding:0}}
.box{{background:var(--surface);border:1px solid var(--line);border-radius:8px;overflow-x:auto}}table{{border-collapse:collapse;width:100%;font:.9rem/1.45 var(--display)}}
th,td{{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}}th{{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}}tr:last-child td{{border-bottom:0}}
tr.phase td{{background:var(--accent-soft);color:var(--accent);font:600 .75rem var(--mono);letter-spacing:.08em;text-transform:uppercase}}.num{{text-align:right;white-space:nowrap}}
.flow{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font:600 .85rem var(--display);margin-top:14px}}.flow span{{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:8px 10px}}.flow small{{font-weight:400;color:var(--muted)}}.flow b{{color:var(--accent)}}
ul{{max-width:72ch;padding-left:1.2em}}a{{color:var(--accent)}}
@media (max-width:820px){{.layout{{grid-template-columns:minmax(0,1fr)}}nav{{position:static;grid-auto-flow:row}}}}
</style></head><body><div class="layout">
<header><div class="eyebrow">Flashpoint · technical reference · generated from the build scripts</div><h1>Flashpoint Reference</h1>
<p class="sub">Every node, prompt, API, signal query, data field and decision rule used by the Flashpoint n8n workflows.</p></header>
<nav>{nav}</nav><main>{body}</main></div></body></html>"""

os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
out = os.path.join(ROOT, "docs", "flashpoint-docs.html")
open(out, "w").write(page)
print("written", out, f"({len(page) // 1024} KB)")
