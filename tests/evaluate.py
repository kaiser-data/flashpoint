"""Grades tests/berlin_results.json with the same rule checks and LLM judge as the n8n eval workflow,
then writes tests/berlin_report.html.

Run from the project root:  bash -c 'set -a; . ./.env; set +a; python3 tests/evaluate.py'
"""
import html, importlib.util, json, os, re, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fp", os.path.join(HERE, "..", "n8n", "flashpoint.py"))
fp = importlib.util.module_from_spec(spec); spec.loader.exec_module(fp)
JUDGE_SYSTEM = fp.judge_system.replace('\\"', '"')
DIMS = ["groundedness", "relevance", "actionability", "email_quality", "compliance", "calibration"]


def rule_checks(r):
    """Same 7 checks as the 'Rule checks' node in the eval workflow."""
    email = r.get("email_html") or ""
    urls = [h.get("url", "") for k in ("painSignal", "customerVoice", "news") for h in (r["context"].get(k) or [])]
    score = r.get("score")
    reasons = r.get("score_reasons") or []
    checks = {
        "stop_line_present": "STOP" in email or email == "",
        "no_email_addresses_in_text": not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", email),
        "email_length_ok": email == "" or 300 <= len(email) <= 4000,
        "score_in_range": isinstance(score, (int, float)) and 0 <= score <= 100,
        "high_score_has_reasons": not (isinstance(score, (int, float)) and score >= 70) or len(reasons) >= 2,
        "pain_claim_has_evidence": not re.search(r"\b[1-9]\d* hits?\b", r.get("pain_evidence") or "", re.I)
                                   or any(r["domain"] in u or "reddit.com" in u for u in urls),
        "auto_email_only_if_verified": not r.get("auto_email") or r.get("verified") is True,
    }
    return [k for k, ok in checks.items() if not ok], len(checks)


def judge(r):
    analysis = {k: r.get(k) for k in ("domain", "linkedin_name", "score", "angle", "news_summary", "pain_evidence",
                                       "buying_committee", "score_reasons", "email_subject", "email_html")}
    analysis["decision"] = " + ".join(x for x, on in (("auto-email", r.get("auto_email")), ("human", r.get("to_human"))) if on)
    body = {"model": fp.JUDGE_MODEL, "temperature": 0, "max_tokens": 700, "messages": [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": "CONTEXT:\n" + json.dumps(r["context"], ensure_ascii=False)[:14000] +
                                    "\n\nANALYSIS:\n" + json.dumps(analysis, ensure_ascii=False)}]}
    req = urllib.request.Request("https://api.featherless.ai/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + os.environ["FEATHERLESS_API_KEY"],
                                          "content-type": "application/json", "user-agent": "flashpoint-eval"})
    try:
        with urllib.request.urlopen(req, timeout=180) as res:
            raw = json.loads(res.read())["choices"][0]["message"]["content"]
        return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
    except Exception as e:
        return {"error": str(e)[:200]}


def expected_path(r):
    """What the workflow should have done for this case, so the report can show whether it did."""
    if r["colleagues"] < 3: return "stop at threshold"
    if r["case"] == "wrong institution typed": return "not verified → human"
    if r["call_requested"]: return "call → human"
    return "research + decide"


def actual_path(r):
    if r.get("stopped_at_threshold"): return "stop at threshold"
    if r.get("verified") is False: return "not verified → human"
    if r.get("handoff_reason") == "Partnership call requested": return "call → human"
    return "research + decide"


rows = json.load(open(os.path.join(HERE, "berlin_results.json")))
for r in rows:
    r["expected_path"], r["actual_path"] = expected_path(r), actual_path(r)
    r["path_ok"] = r["expected_path"] == r["actual_path"] or (r["expected_path"] == "research + decide" and r["actual_path"] != "stop at threshold")
    if r.get("stopped_at_threshold") or not r.get("email_html"):
        r["rule_failures"], r["rule_total"], r["judge"], r["verdict"] = [], 0, {}, "n/a"
        continue
    r["rule_failures"], r["rule_total"] = rule_checks(r)
    j = judge(r)
    r["judge"] = j
    grades = [j.get(d) for d in DIMS if isinstance(j.get(d), (int, float))]
    r["overall"] = round(sum(grades) / len(grades), 1) if grades else None
    r["verdict"] = "judge-error" if "error" in j else (
        "pass" if not r["rule_failures"] and r["overall"] >= 3.5 and j.get("groundedness", 0) >= 3 and j.get("compliance", 0) >= 4 else "fail")
    print(f"{r['domain']:<18} rules {r['rule_total'] - len(r['rule_failures'])}/{r['rule_total']} judge {r['overall']} → {r['verdict']}", flush=True)
json.dump(rows, open(os.path.join(HERE, "berlin_results_graded.json"), "w"), ensure_ascii=False, indent=2)

# ---------------------------------------------------------------- report
judged = [r for r in rows if r["verdict"] in ("pass", "fail")]
avg = lambda d: (sum(r["judge"][d] for r in judged if isinstance(r["judge"].get(d), (int, float))) /
                 max(1, sum(1 for r in judged if isinstance(r["judge"].get(d), (int, float)))))
fails = {}
for r in judged:
    for f in r["rule_failures"]: fails[f] = fails.get(f, 0) + 1
e = html.escape
def pill(v):
    cls = {"pass": "ok", "fail": "bad", "judge-error": "warn", "n/a": "mute"}.get(v, "mute")
    return f'<span class="pill {cls}">{e(v)}</span>'
def bar(v):
    return "" if v is None else f'<span class="bar"><i style="width:{v / 5 * 100:.0f}%"></i></span> {v}'

table_rows = "".join(f"""
<tr>
  <td><b>{e(r['domain'])}</b><div class="sub">{e(r['case'])}</div></td>
  <td>{e(str(r.get('linkedin_name') or '–'))}<div class="sub">{'verified' if r.get('verified') else ('not verified' if r.get('verified') is False else '–')} · {r.get('employees') or '?'} employees</div></td>
  <td class="num">{r.get('score') if r.get('score') is not None else '–'}</td>
  <td>{e(r['actual_path'])}<div class="sub">{'as expected' if r['path_ok'] else 'expected: ' + e(r['expected_path'])}</div></td>
  <td class="num">{r.get('pain_hits', '–')} / {r.get('voice_hits', '–')}<div class="sub">{r.get('dropped_hits') or 0} dropped</div></td>
  <td class="num">{(str(r['rule_total'] - len(r['rule_failures'])) + '/' + str(r['rule_total'])) if r['rule_total'] else '–'}</td>
  <td>{bar(r.get('overall'))}</td>
  <td>{pill(r['verdict'])}</td>
  <td class="note">{e('; '.join(r['rule_failures'] + list(r.get('judge', {}).get('issues') or []))[:300]) or '–'}</td>
</tr>""" for r in rows)

dim_rows = "".join(f"<tr><td>{d.replace('_', ' ')}</td><td>{bar(round(avg(d), 1)) if judged else '–'}</td></tr>" for d in DIMS)
fail_rows = "".join(f"<li><code>{e(k)}</code> · {v}×</li>" for k, v in sorted(fails.items(), key=lambda x: -x[1])) or "<li>none</li>"
passed = sum(1 for r in judged if r["verdict"] == "pass")
paths_ok = sum(1 for r in rows if r["path_ok"])
avg_secs = round(sum(r.get("seconds") or 0 for r in rows if not r.get("stopped_at_threshold")) /
                 max(1, sum(1 for r in rows if not r.get("stopped_at_threshold"))))

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Flashpoint Berlin Test</title><style>
:root{{--bg:#f4f5f7;--surface:#fff;--ink:#1a1d24;--muted:#5d6472;--line:#dde0e6;--accent:#c2410c;--ok:#15803d;--ok-soft:#dcfce7;--bad:#b91c1c;--bad-soft:#fee2e2;--warn:#a16207;--warn-soft:#fef3c7;--mute-soft:#eceef2}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111318;--surface:#1a1d24;--ink:#e8eaee;--muted:#9aa1ad;--line:#2c313b;--accent:#fb923c;--ok:#4ade80;--ok-soft:#14321f;--bad:#f87171;--bad-soft:#3b1717;--warn:#facc15;--warn-soft:#3a2f0d;--mute-soft:#252932;color-scheme:dark}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Avenir Next","Segoe UI",system-ui,sans-serif}}
.wrap{{max-width:1240px;margin:0 auto;padding-inline:20px;padding-block:32px 64px;display:grid;gap:28px}}
h1{{margin:0;font-size:1.9rem}}h2{{margin:0 0 12px;font-size:1.1rem}}.eyebrow{{font:600 .72rem/1 ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}}
.tile{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px}}.tile b{{display:block;font-size:1.7rem;font-variant-numeric:tabular-nums}}.tile span{{color:var(--muted);font-size:.85rem}}
.box{{background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}}tr:last-child td{{border-bottom:0}}
.num{{text-align:right;white-space:nowrap}}.sub{{color:var(--muted);font-size:.8rem}}.note{{font-size:.82rem;color:var(--muted);max-width:340px}}
.pill{{font:600 .72rem/1 ui-monospace,monospace;padding:5px 8px;border-radius:99px;text-transform:uppercase}}.ok{{background:var(--ok-soft);color:var(--ok)}}.bad{{background:var(--bad-soft);color:var(--bad)}}.warn{{background:var(--warn-soft);color:var(--warn)}}.mute{{background:var(--mute-soft);color:var(--muted)}}
.bar{{display:inline-block;width:70px;height:7px;background:var(--line);border-radius:4px;vertical-align:middle;overflow:hidden}}.bar i{{display:block;height:100%;background:var(--accent)}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}}.pad{{padding:16px}}ul{{margin:0;padding-left:1.2em}}
</style></head><body><div class="wrap">
<header><div class="eyebrow">Flashpoint · live test · Berlin universities</div><h1>Berlin test run</h1>
<p class="sub">{len(rows)} cases through the live n8n workflow. Graded by 7 rule checks and an LLM judge ({e(fp.JUDGE_MODEL)}), the same as the eval workflow. Sign-up address in every case: the team's own inbox.</p></header>
<section class="tiles">
<div class="tile"><b>{paths_ok}/{len(rows)}</b><span>cases took the expected path</span></div>
<div class="tile"><b>{passed}/{len(judged)}</b><span>analyses passed the eval</span></div>
<div class="tile"><b>{round(avg('groundedness'), 1) if judged else '–'}</b><span>average groundedness (1–5)</span></div>
<div class="tile"><b>{avg_secs}s</b><span>average research + analysis time per account</span></div>
</section>
<section><h2>Per university</h2><div class="box"><table><thead><tr><th>Account / case</th><th>LinkedIn match</th><th class="num">Score</th><th>Path</th><th class="num">Pain / voice hits</th><th class="num">Rules</th><th>Judge</th><th>Verdict</th><th>Issues</th></tr></thead><tbody>{table_rows}</tbody></table></div></section>
<section class="grid2">
<div class="box pad"><h2>Judge averages</h2><table>{dim_rows}</table></div>
<div class="box pad"><h2>Rule failures</h2><ul>{fail_rows}</ul>
<h2 style="margin-top:16px">How to read this</h2><ul><li><b>Pass</b>: all rules green, average at least 3.5, groundedness at least 3, compliance at least 4.</li><li><b>Path</b> checks the agent's decision logic: stop below threshold, abstain on a wrong LinkedIn match, hand calls to a human.</li><li><b>Dropped</b>: search hits removed in code because they were not about this university.</li></ul></div>
</section></div></body></html>"""
open(os.path.join(HERE, "berlin_report.html"), "w").write(page)
print("report:", os.path.join(HERE, "berlin_report.html"))
