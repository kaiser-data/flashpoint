"""Flashpoint · Signal Watch: checks the news three times a day, rates every new hit, saves everything,
matches strong signals to known accounts, e-mails sales, and learns which searches are worth running.

Self-learning loop (all visible in the sheet, nothing hidden):
  Signals tab        every scraped and rated hit (the knowledge base); sales can mark `useful` yes/no
  Watch queries tab  every search with its run count, hits and precision; the model proposes new queries
                     from strong signals, queries that never find anything relevant are retired
  Rating prompt      includes the latest hits sales marked useful / not useful as examples
"""
import json, uuid

SCHEDULE = "0 8,12,15 * * 1-5"          # Mon–Fri at 08:00, 12:00 and 15:00 (Europe/Berlin)
LOOKBACK_DAYS = 3
RELEVANT = 60                             # rating from which a signal goes to sales
MAX_ACTIVE_QUERIES = 25
RETIRE_AFTER_RUNS = 6                     # retire a query after this many runs without one relevant hit

SIGNALS_HEADERS = ["signal_id", "found_at", "query", "query_origin", "title", "url", "excerpt", "event_type", "region",
                   "sector", "relevance", "urgency", "action", "summary", "affected_accounts", "useful"]
QUERIES_HEADERS = ["query", "status", "origin", "added_at", "runs", "hits", "relevant_hits", "precision", "last_run", "note"]

# Seed searches for the Kredible preset. They are written to the Watch queries tab on the first run,
# where anyone can edit, pause (status = paused) or add searches.
DEFAULT_QUERIES = [
    "Haushaltssperre Hochschulen",
    "Haushaltssperre aufgehoben Wissenschaft",
    "Landeshaushalt Hochschulen beschlossen",
    "Zukunftsvertrag Studium und Lehre Mittel",
    "DAAD Förderprogramm Ausschreibung internationale Studierende",
    "Sperrkonto Betrag Studienvisum Erhöhung",
    "Studiengebühren Nicht-EU Studierende",
    "Fachkräfteeinwanderungsgesetz Studierende Visum",
    "internationale Studierende Einschreibung Rückgang",
    "Visa Terminvergabe Studierende Botschaft Wartezeit",
]

RATING_FOCUS = (
    "Product: Kredible finances the blocked account, tuition and first-year living costs for admitted non-EU students at "
    "German universities, at no cost or risk to the university. Buyers: international offices, admissions, university "
    "leadership and finance. Signals that matter: funding frozen or released (Haushaltssperre, Landeshaushalt, DAAD and "
    "federal programmes), changes to the blocked account, student visas or tuition fees for non-EU students, enrolment "
    "trends of international students, universities extending application deadlines."
)


def uid(): return str(uuid.uuid4())


plan_js = f'''
// Active searches = the Watch queries tab plus any default not yet in it. Paused and retired ones are skipped.
const DEFAULTS = {json.dumps(DEFAULT_QUERIES, ensure_ascii=False)};
const rows = $('Read watch queries').all().map(i => i.json).filter(r => r.query);
const known = new Set(rows.map(r => String(r.query).trim().toLowerCase()));
const all = rows.concat(DEFAULTS.filter(q => !known.has(q.toLowerCase())).map(q => ({{ query: q, status: 'active', origin: 'default' }})));
const since = new Date(Date.now() - {LOOKBACK_DAYS} * 864e5).toISOString().slice(0, 10);
return all.filter(r => !r.status || r.status === 'active').slice(0, {MAX_ACTIVE_QUERIES})
  .map(r => ({{ json: {{ query: String(r.query).trim(), origin: r.origin || 'manual', search: String(r.query).trim() + ' after:' + since }} }}));
'''

new_hits_js = r'''
// Pair each search with its result (one response per search), drop hits already in the Signals tab.
const plans = $('Plan searches').all().map(i => i.json);
const seen = new Set($('Read signals').all().map(i => String(i.json.url || '')).filter(Boolean));
const examples = $('Read signals').all().map(i => i.json)
  .filter(r => /^(yes|no)$/i.test(String(r.useful || '').trim())).slice(-6)
  .map(r => ({ title: r.title, summary: r.summary, sales_said_useful: /yes/i.test(r.useful) }));
const out = [];
$input.all().forEach((item, idx) => {
  let hits = [];
  try { hits = JSON.parse(item.json.data || '[]'); } catch (e) {}
  (Array.isArray(hits) ? hits : []).forEach(h => {
    const url = h?.metadata?.url;
    if (!url || seen.has(url)) return;
    seen.add(url);
    out.push({ json: { query: plans[idx]?.query, query_origin: plans[idx]?.origin, url,
      title: String(h.metadata.title || '').slice(0, 200),
      excerpt: String(h.markdown || h.text || '').replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, '[e-mail]').replace(/\s+/g, ' ').slice(0, 1200),
      examples } });
  });
});
return out.slice(0, 30);
'''

rate_system = (
    "You rate news for a B2B sales team. " + RATING_FOCUS + " "
    "Return ONLY JSON: {\\\"event_type\\\": \\\"funding_released\\\"|\\\"funding_frozen\\\"|\\\"regulation_change\\\"|\\\"market_trend\\\"|\\\"deadline_extension\\\"|\\\"other\\\", "
    "\\\"region\\\": string (German state, 'federal', 'EU' or 'unknown'), \\\"sector\\\": string, "
    "\\\"relevance\\\": integer 0-100 (how much this changes whether a buyer should act now), "
    "\\\"urgency\\\": \\\"now\\\"|\\\"this_month\\\"|\\\"watch\\\", "
    "\\\"action\\\": string (one sentence for sales: contact now, hold, or inform), \\\"summary\\\": string (max 2 sentences), "
    "\\\"new_queries\\\": string[] (0-2 short German or English search queries that would find MORE signals like this one: new programme names, ministries, terms; empty if not relevant)}. "
    "Use only the article text. Old or off-topic articles get relevance below 20."
)
rate_body = ("={{ JSON.stringify({ model: 'MODEL', temperature: 0, max_tokens: 600, messages: ["
             "{ role: 'system', content: \"" + rate_system + "\" }, "
             "{ role: 'user', content: (($json.examples || []).length ? 'Earlier ratings sales gave feedback on: ' + JSON.stringify($json.examples) + '\\n\\n' : '') + "
             "'ARTICLE (found with search: ' + $json.query + ')\\nTitle: ' + $json.title + '\\nURL: ' + $json.url + '\\nText: ' + $json.excerpt }] }) }}")

parse_js = r'''
// One row per rated hit for the Signals tab. Unparseable ratings are kept with relevance 0, so nothing is lost.
const hit = $('New hits only').item.json;
const raw = $input.item.json.choices?.[0]?.message?.content ?? '';
let r = null;
try { r = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1)); } catch (e) {}
const rel = r && Number.isFinite(+r.relevance) ? Math.max(0, Math.min(100, Math.round(+r.relevance))) : 0;
let h = 0; for (const ch of hit.url) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
return { json: {
  signal_id: 'S' + h.toString(36), found_at: new Date().toISOString(), query: hit.query, query_origin: hit.query_origin,
  title: hit.title, url: hit.url, excerpt: hit.excerpt.slice(0, 600),
  event_type: r?.event_type ?? 'unrated', region: r?.region ?? '', sector: r?.sector ?? '', relevance: rel,
  urgency: r?.urgency ?? '', action: r?.action ?? '', summary: r?.summary ?? raw.slice(0, 200),
  affected_accounts: '', useful: '',
  _new_queries: Array.isArray(r?.new_queries) ? r.new_queries.slice(0, 2) : [],
}};
'''

learn_js = f'''
// Self-learning: update every search's stats from the full history, retire searches that never find anything
// relevant, and add searches the model proposed from strong signals.
const now = new Date().toISOString();
const history = $('Read signals').all().map(i => i.json).concat($('Rate signal').all().map(i => i.json));
const planned = $('Plan searches').all().map(i => i.json);
const tab = $('Read watch queries').all().map(i => i.json).filter(r => r.query);
const rows = new Map(tab.map(r => [String(r.query).trim().toLowerCase(), {{ ...r }}]));
planned.forEach(p => {{
  const k = p.query.toLowerCase();
  const r = rows.get(k) || {{ query: p.query, status: 'active', origin: p.origin, added_at: now, runs: 0 }};
  r.runs = Number(r.runs || 0) + 1;
  r.last_run = now;
  rows.set(k, r);
}});
rows.forEach((r, k) => {{
  const mine = history.filter(h => String(h.query || '').toLowerCase() === k);
  r.hits = mine.length;
  r.relevant_hits = mine.filter(h => Number(h.relevance) >= {RELEVANT}).length;
  r.precision = r.hits ? Math.round(r.relevant_hits / r.hits * 100) + '%' : '';
  if (r.status === 'active' && Number(r.runs) >= {RETIRE_AFTER_RUNS} && r.relevant_hits === 0) {{
    r.status = 'retired'; r.note = 'no relevant hit in ' + r.runs + ' runs';
  }}
}});
const active = [...rows.values()].filter(r => r.status === 'active').length;
let room = {MAX_ACTIVE_QUERIES} - active;
$('Rate signal').all().map(i => i.json).filter(s => s.relevance >= {RELEVANT})
  .flatMap(s => (s._new_queries || []).map(q => ({{ q: String(q).trim(), from: s.signal_id }})))
  .forEach(({{ q, from }}) => {{
    const k = q.toLowerCase();
    if (!q || q.length > 80 || rows.has(k) || room <= 0) return;
    rows.set(k, {{ query: q, status: 'active', origin: 'learned', added_at: now, runs: 0, hits: 0, relevant_hits: 0,
                  precision: '', last_run: '', note: 'proposed from signal ' + from }});
    room--;
  }});
const cols = {json.dumps(QUERIES_HEADERS)};
return [...rows.values()].map(r => ({{ json: Object.fromEntries(cols.map(c => [c, r[c] ?? ''])) }}));
'''

signal_rows_js = f'''
const cols = {json.dumps(SIGNALS_HEADERS)};
return $('Rate signal').all().map(i => ({{ json: Object.fromEntries(cols.map(c => [c, i.json[c] ?? ''])) }}));
'''

relevant_js = f'''
// Strong signals only. Accounts come from the Analyses tab, with their saved contact lists.
const strong = $('Rate signal').all().map(i => i.json).filter(s => s.relevance >= {RELEVANT})
  .sort((a, b) => b.relevance - a.relevance).slice(0, 10);
if (!strong.length) return [];
const accounts = [];
const seen = new Set();
$('Read analyses').all().map(i => i.json).reverse().forEach(a => {{
  if (!a.domain || seen.has(a.domain)) return;
  seen.add(a.domain);
  accounts.push({{ domain: a.domain, organisation: a.organisation, locations: a.locations || '', score: a.score, contacts: a.contacts || '' }});
}});
return [{{ json: {{ strong, accounts }} }}];
'''

match_system = (
    "Match news signals to sales accounts. A signal affects an account when the account is in the signal's region "
    "(cities count as their German state), in its sector, or the signal is federal or EU-wide and relevant to the sector. "
    "Return ONLY JSON: {\\\"matches\\\": [{\\\"signal_id\\\": string, \\\"domains\\\": string[], \\\"why\\\": string}]}. "
    "Use only domains from the account list."
)
match_body = ("={{ JSON.stringify({ model: 'MODEL', temperature: 0, max_tokens: 1500, messages: ["
              "{ role: 'system', content: \"" + match_system + "\" }, "
              "{ role: 'user', content: 'SIGNALS: ' + JSON.stringify($json.strong.map(s => ({ signal_id: s.signal_id, title: s.title, region: s.region, sector: s.sector, event_type: s.event_type }))) + "
              "'\\nACCOUNTS: ' + JSON.stringify($json.accounts.map(a => ({ domain: a.domain, organisation: a.organisation, locations: a.locations }))) }] }) }}")

digest_js = r'''
// Sales digest: each strong signal with its action and the affected accounts, including saved contacts.
const { strong, accounts } = $('Strong signals').first().json;
const raw = $input.first().json.choices?.[0]?.message?.content ?? '';
let m = { matches: [] };
try { m = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1)); } catch (e) {}
const byId = Object.fromEntries((m.matches || []).map(x => [x.signal_id, x]));
const acc = Object.fromEntries(accounts.map(a => [a.domain, a]));
const label = { funding_released: '🟢 Funding released', funding_frozen: '⛔ Funding frozen', regulation_change: '⚖️ Regulation',
                market_trend: '📈 Market trend', deadline_extension: '📅 Deadline extension', other: 'Other' };
const blocks = strong.map(s => {
  const hit = byId[s.signal_id] || { domains: [], why: '' };
  const affected = (hit.domains || []).filter(d => acc[d]).map(d => {
    const a = acc[d];
    const people = String(a.contacts || '').split('\n').filter(Boolean).slice(0, 3)
      .map(line => { const [prio, name, title, url] = line.split(' · '); return `<li>${prio} · <a href="${url}">${name}</a> · ${title}</li>`; }).join('');
    return `<li><b>${a.organisation || d}</b> (score ${a.score})<ul>${people || '<li>no saved contacts</li>'}</ul></li>`;
  }).join('');
  return `<div style="border-left:4px solid #c2410c;padding:8px 14px;margin:14px 0">
<p style="margin:0"><b>${label[s.event_type] || s.event_type}</b> · relevance ${s.relevance} · ${s.urgency} · ${s.region}</p>
<p style="margin:6px 0"><a href="${s.url}">${s.title}</a></p>
<p style="margin:6px 0">${s.summary}</p>
<p style="margin:6px 0"><b>Action:</b> ${s.action}</p>
${affected ? `<p style="margin:6px 0"><b>Affected accounts</b> ${hit.why ? '· ' + hit.why : ''}</p><ul>${affected}</ul>` : '<p style="margin:6px 0;color:#666">No known account affected yet.</p>'}
</div>`;
}).join('');
const html = `<h2>Flashpoint signal watch: ${strong.length} new signal${strong.length > 1 ? 's' : ''}</h2>${blocks}
<p style="color:#666">All rated hits are saved in the <b>Signals</b> tab. Mark a row's <b>useful</b> column yes or no: the next ratings learn from it.
Searches and their precision are in <b>Watch queries</b>; new searches proposed from strong signals are added automatically.</p>`;
const top = strong[0];
return [{ json: { subject: `[Signal ${top.relevance}] ${label[top.event_type] || top.event_type}: ${top.title}`.slice(0, 150), html,
  affected: Object.fromEntries(strong.map(s => [s.signal_id, (byId[s.signal_id]?.domains || []).join(', ')])) } }];
'''


def build(sticky, connect, sheet_id, rl_id, rl_name, sheets_cred, gmail_cred, fl_cred, apify_cred, model, sales_email):
    n = lambda name, typ, ver, pos, params, **extra: {"id": uid(), "name": name, "type": typ, "typeVersion": ver,
                                                       "position": list(pos), "parameters": params, **extra}
    read = lambda name, tab, pos: n(name, "n8n-nodes-base.googleSheets", 4.5, pos,
                                    {"resource": "sheet", "operation": "read", "documentId": rl_id(sheet_id),
                                     "sheetName": rl_name(tab), "options": {}},
                                    credentials=sheets_cred, executeOnce=True, alwaysOutputData=True, onError="continueRegularOutput")
    append = lambda name, tab, pos, match=None: n(name, "n8n-nodes-base.googleSheets", 4.5, pos,
        {"resource": "sheet", "operation": "appendOrUpdate" if match else "append", "documentId": rl_id(sheet_id),
         "sheetName": rl_name(tab),
         "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [match] if match else [], "schema": []},
         "options": {}}, credentials=sheets_cred, onError="continueRegularOutput")
    llm = lambda name, pos, body, batch: n(name, "n8n-nodes-base.httpRequest", 4.2, pos,
        {"method": "POST", "url": "https://api.featherless.ai/v1/chat/completions",
         "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
         "sendBody": True, "specifyBody": "json", "jsonBody": body.replace("MODEL", model),
         "options": {"timeout": 120000, **({"batching": {"batch": {"batchSize": 1, "batchInterval": 300}}} if batch else {})}},
        credentials=fl_cred, onError="continueRegularOutput")

    nodes = [
        n("Morning, noon, afternoon", "n8n-nodes-base.scheduleTrigger", 1.2, (0, 170),
          {"rule": {"interval": [{"field": "cronExpression", "expression": SCHEDULE}]}}),
        n("Check now", "n8n-nodes-base.manualTrigger", 1, (0, 330), {}),
        read("Read watch queries", "Watch queries", (230, 250)),
        read("Read signals", "Signals", (440, 250)),
        n("Plan searches", "n8n-nodes-base.code", 2, (650, 250), {"jsCode": plan_js}, executeOnce=True),
        n("Search the web", "n8n-nodes-base.httpRequest", 4.2, (860, 250),
          {"method": "POST", "url": "https://api.apify.com/v2/acts/apify~rag-web-browser/run-sync-get-dataset-items",
           "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
           "sendBody": True, "specifyBody": "json",
           "jsonBody": "={{ JSON.stringify({ query: $json.search, maxResults: 5, scrapingTool: 'raw-http', outputFormats: ['markdown'] }) }}",
           "options": {"timeout": 180000, "batching": {"batch": {"batchSize": 2, "batchInterval": 500}},
                       "response": {"response": {"responseFormat": "text", "outputPropertyName": "data", "neverError": True}}}},
          credentials=apify_cred, onError="continueRegularOutput"),
        n("New hits only", "n8n-nodes-base.code", 2, (1070, 250), {"jsCode": new_hits_js}, executeOnce=True),
        llm("Rate signal", (1300, 250), rate_body, True),
        n("Parse rating", "n8n-nodes-base.code", 2, (1510, 250), {"mode": "runOnceForEachItem", "jsCode": parse_js}),
        n("Signal rows", "n8n-nodes-base.code", 2, (1760, 170), {"jsCode": signal_rows_js}, executeOnce=True),
        append("Save to Signals tab", "Signals", (1970, 170)),
        n("Learn searches", "n8n-nodes-base.code", 2, (1760, 330), {"jsCode": learn_js}, executeOnce=True),
        append("Update Watch queries tab", "Watch queries", (1970, 330), match="query"),
        read("Read analyses", "Analyses", (1760, 580)),
        n("Strong signals", "n8n-nodes-base.code", 2, (1970, 580), {"jsCode": relevant_js}, executeOnce=True),
        llm("Match to accounts", (2180, 580), match_body, False),
        n("Write digest", "n8n-nodes-base.code", 2, (2390, 580), {"jsCode": digest_js}),
        n("E-mail sales", "n8n-nodes-base.gmail", 2.1, (2600, 580),
          {"resource": "message", "operation": "send", "sendTo": sales_email, "subject": "={{ $json.subject }}",
           "emailType": "html", "message": "={{ $json.html }}", "options": {"appendAttribution": False}},
          credentials=gmail_cred),
    ]
    # "Rate signal" is referenced by name in later code nodes but the rows come out of "Parse rating"
    for x in nodes:
        if x["name"] == "Parse rating": x["name"] = "Rate signal output"
    for x in nodes:
        if x["type"] == "n8n-nodes-base.code":
            x["parameters"]["jsCode"] = x["parameters"]["jsCode"].replace("$('Rate signal')", "$('Rate signal output')")

    wf = {"name": "Flashpoint · Signal Watch (3× daily)", "nodes": nodes, "connections": {},
          "settings": {"executionOrder": "v1", "timezone": "Europe/Berlin"}}
    for a, b in [("Morning, noon, afternoon", "Read watch queries"), ("Check now", "Read watch queries"),
                 ("Read watch queries", "Read signals"), ("Read signals", "Plan searches"), ("Plan searches", "Search the web"),
                 ("Search the web", "New hits only"), ("New hits only", "Rate signal"), ("Rate signal", "Rate signal output"),
                 ("Rate signal output", "Signal rows"), ("Signal rows", "Save to Signals tab"),
                 ("Rate signal output", "Learn searches"), ("Learn searches", "Update Watch queries tab"),
                 ("Rate signal output", "Read analyses"), ("Read analyses", "Strong signals"),
                 ("Strong signals", "Match to accounts"), ("Match to accounts", "Write digest"), ("Write digest", "E-mail sales")]:
        connect(wf, a, b)
    return wf


DOCS = {
    "Morning, noon, afternoon": ("1 Collect", "Runs Mon–Fri at 08:00, 12:00 and 15:00 Berlin time.", "Schedule Trigger", "free"),
    "Check now": ("1 Collect", "Run the watch by hand.", "Manual Trigger", "free"),
    "Read watch queries": ("1 Collect", "The searches to run, with their stats. Editable by anyone.", "Google Sheets", "free"),
    "Read signals": ("1 Collect", "Every hit seen before, so nothing is rated twice, plus sales feedback.", "Google Sheets", "free"),
    "Plan searches": ("1 Collect", "Active searches plus defaults, limited to the last 3 days.", "Code", "free"),
    "Search the web": ("1 Collect", "Google search with page text for each query, 5 results each.", "Apify apify/rag-web-browser", "~$0.01 per search"),
    "New hits only": ("1 Collect", "Drops already-known URLs, strips e-mail addresses, adds sales feedback as examples.", "Code", "free"),
    "Rate signal": ("2 Rate", "Rates each hit: event type, region, relevance 0-100, urgency, action for sales, new search ideas.", "Featherless Qwen2.5-72B", "flat plan"),
    "Rate signal output": ("2 Rate", "Turns each rating into a Signals row. Unparseable ratings are kept with relevance 0.", "Code", "free"),
    "Signal rows": ("3 Save and learn", "Keeps only the Signals columns.", "Code", "free"),
    "Save to Signals tab": ("3 Save and learn", "Saves every rated hit: the growing knowledge base.", "Google Sheets", "free"),
    "Learn searches": ("3 Save and learn", "Updates runs, hits and precision per search, retires dead searches, adds learned ones.", "Code", "free"),
    "Update Watch queries tab": ("3 Save and learn", "Writes the search stats back, matched on the query text.", "Google Sheets", "free"),
    "Read analyses": ("4 Alert", "Known accounts with their locations and saved contact lists.", "Google Sheets", "free"),
    "Strong signals": ("4 Alert", "Keeps signals rated 60 or higher. Stops quietly if there are none.", "Code", "free"),
    "Match to accounts": ("4 Alert", "Finds which accounts each strong signal affects (region, sector, federal).", "Featherless Qwen2.5-72B", "flat plan"),
    "Write digest": ("4 Alert", "One e-mail: signal, action, affected accounts and their contacts.", "Code", "free"),
    "E-mail sales": ("4 Alert", "Sends the digest to the sales team.", "Gmail", "free"),
}
