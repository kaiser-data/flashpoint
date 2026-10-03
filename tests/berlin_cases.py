"""Runs Berlin universities through the live Flashpoint workflow, one case at a time, and saves a summary per run.

Run from the project root:  bash -c 'set -a; . ./.env; set +a; python3 tests/berlin_cases.py'
Only SALES_EMAIL is used as sign-up address, so the agent never e-mails real university staff.
"""
import datetime, json, os, time, urllib.request

BASE = os.environ["N8N_BASE_URL"].rstrip("/")
WID = "mMu1Ou5McdRbUAR9"
ME = os.environ["SALES_EMAIL"]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "berlin_results.json")

# (case, domain, institution typed in the form, roles, partnership call?, colleagues)
CASES = [
    ("full buying committee",         "tu-berlin.de",     "Technische Universität Berlin",   ["International office", "Admissions", "Finance"], False, 3),
    ("partnership call requested",    "fu-berlin.de",     "Freie Universität Berlin",        ["International office", "Leadership", "Other"],   True,  3),
    ("single role only",              "hu-berlin.de",     "Humboldt-Universität zu Berlin",  ["Other", "Other", "Other"],                       False, 3),
    ("domain differs from name",      "bht-berlin.de",    "Berliner Hochschule für Technik", ["Admissions", "Admissions", "Finance"],           False, 3),
    ("university of applied sciences","htw-berlin.de",    "HTW Berlin",                      ["International office", "Admissions", "Other"],   False, 3),
    ("arts university",               "udk-berlin.de",    "Universität der Künste Berlin",   ["Admissions", "Other", "Other"],                  False, 3),
    ("medical university",            "charite.de",       "Charité – Universitätsmedizin Berlin", ["International office", "Finance", "Other"], False, 3),
    ("private, no institution typed", "hertie-school.org", "",                               ["Leadership", "Admissions", "Finance"],           True,  3),
    ("wrong institution typed",       "hwr-berlin.de",    "Technische Universität München",  ["Admissions", "Other", "Other"],                  False, 3),
    ("threshold not reached",         "ash-berlin.eu",    "Alice Salomon Hochschule Berlin", ["International office", "Admissions"],            False, 2),
]

def api(path):
    req = urllib.request.Request(BASE + path, headers={"X-N8N-API-KEY": os.environ["N8N_API_KEY"], "user-agent": "flashpoint-test"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def latest_id():
    d = api(f"/api/v1/executions?workflowId={WID}&limit=1")["data"]
    return int(d[0]["id"]) if d else 0

def send(domain, org, roles, call, colleagues):
    notes = [(org + (" | wants partnership call" if call and i == 1 else "")) for i in range(len(roles))] if org else \
            (["wants partnership call"] if call else [])
    body = {"email": ME, "city": "Berlin", "company_domain": domain, "colleagues": colleagues, "threshold": 3,
            "colleague_emails": [ME], "roles": roles, "notes": notes, "source": "test-berlin",
            "submitted_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    req = urllib.request.Request(BASE + "/webhook/critical-mass", data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json", "x-signal-secret": os.environ["SIGNAL_SECRET"],
                                          "user-agent": "flashpoint-test"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status

def summarise(ex):
    rd = ex["data"]["resultData"]["runData"]
    def out(n):
        try: return [i["json"] for i in rd[n][-1]["data"]["main"][0]]
        except Exception: return []
    errors = {n: (r[-1].get("error") or {}).get("message", "")[:160] for n, r in rd.items() if r[-1].get("error")}
    item_errors = {n: str(o[0]["error"])[:160] for n in rd for o in [out(n)] if o and isinstance(o[0], dict) and "error" in o[0]}
    p = (out("Parse analysis") or [{}])[0]
    c = (out("Build context") or [{}])[0]
    a = p.get("analysis") or {}
    return {
        "status": ex["status"], "seconds": round((datetime.datetime.fromisoformat(ex["stoppedAt"].replace("Z", "+00:00")) -
                                                 datetime.datetime.fromisoformat(ex["startedAt"].replace("Z", "+00:00"))).total_seconds()),
        "stopped_at_threshold": "LinkedIn company" not in rd,
        "verified": p.get("verified"), "linkedin_name": (p.get("company") or {}).get("name"),
        "employees": (p.get("company") or {}).get("employeeCount"),
        "posts": c.get("postsAnalysed"), "news": len(c.get("news") or []), "roles_found": len(c.get("roleTitles") or []),
        "pain_hits": len(c.get("painSignal") or []), "voice_hits": len(c.get("customerVoice") or []), "dropped_hits": c.get("droppedHits"),
        "score": p.get("score"), "auto_email": p.get("autoSend"), "to_human": p.get("handToHuman"), "handoff_reason": p.get("handoffReason"),
        "angle": a.get("angle"), "pain_evidence": a.get("pain_evidence"), "news_summary": a.get("news_summary"),
        "buying_committee": a.get("buying_committee"), "score_reasons": a.get("score_reasons"),
        "email_subject": a.get("champion_email_subject"), "email_html": a.get("champion_email_html"),
        "context": {k: c.get(k) for k in ("company", "roles", "notes", "topPosts", "roleTitles", "news", "painSignal", "customerVoice")},
        "node_errors": errors, "item_errors": item_errors,
    }

results = []
for case, domain, org, roles, call, colleagues in CASES:
    before = latest_id()
    code = send(domain, org, roles, call, colleagues)
    ex_id = None
    for _ in range(90):  # up to 15 minutes per case
        time.sleep(10)
        lid = latest_id()
        if lid > before:
            ex_id = lid
            ex = api(f"/api/v1/executions/{ex_id}?includeData=true")
            if ex["status"] not in ("running", "new", "waiting"):
                break
    row = {"case": case, "domain": domain, "institution_typed": org, "roles_signed_up": roles, "call_requested": call,
           "colleagues": colleagues, "webhook": code, "execution_id": ex_id}
    row.update(summarise(ex) if ex_id else {"status": "no execution found"})
    results.append(row)
    json.dump(results, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"{case:<32} {domain:<18} {row['status']:<8} verified={row.get('verified')} score={row.get('score')} "
          f"human={row.get('to_human')} ({row.get('handoff_reason')}) {row.get('seconds')}s", flush=True)
print("saved", OUT)
