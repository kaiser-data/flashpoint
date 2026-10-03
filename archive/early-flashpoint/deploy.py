"""Deploys Critical Mass to n8n from .env. Never prints secret values.

Run from the project root:  bash -c 'set -a; . ./.env; set +a; python3 n8n/deploy.py'
Steps: check keys -> check Featherless model -> build workflow -> create credentials -> import workflow -> try to activate.
Gmail cannot be connected through the API (Google sign-in); the script tells you where to click.
"""
import json, os, subprocess, sys, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REQUIRED = ["N8N_BASE_URL", "N8N_API_KEY", "APIFY_TOKEN", "FEATHERLESS_API_KEY", "FEATHERLESS_MODEL", "SALES_EMAIL", "SIGNAL_SECRET"]


def env(name):
    return os.environ.get(name, "").strip()


def call(method, url, headers, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"content-type": "application/json", "user-agent": "critical-mass-deploy/1.0", **headers})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]


def step(msg):
    print(f"\n== {msg}")


missing = [n for n in REQUIRED if not env(n) or "YOUR-NAME" in env(n)]
if missing:
    sys.exit("Missing in .env: " + ", ".join(missing))

base = env("N8N_BASE_URL").rstrip("/")
n8n = {"X-N8N-API-KEY": env("N8N_API_KEY")}

step("Checking keys")
s, me = call("GET", "https://api.apify.com/v2/users/me", {"Authorization": f"Bearer {env('APIFY_TOKEN')}"})
print("Apify:", "ok, user " + me["data"]["username"] if s == 200 else f"FAILED ({s})")
s, _ = call("POST", "https://api.featherless.ai/v1/chat/completions", {"Authorization": f"Bearer {env('FEATHERLESS_API_KEY')}"},
            {"model": env("FEATHERLESS_MODEL"), "max_tokens": 3, "messages": [{"role": "user", "content": "Say ok"}]})
print("Featherless:", f"ok, model {env('FEATHERLESS_MODEL')} answers" if s == 200 else f"FAILED ({s})")
s, _ = call("GET", f"{base}/api/v1/workflows?limit=1", n8n)
print("n8n API:", "ok" if s == 200 else f"FAILED ({s})")
if s != 200:
    sys.exit("Fix the n8n URL or API key first.")

step("Building workflow")
subprocess.run([sys.executable, os.path.join(HERE, "build_critical_mass.py")], check=True, cwd=HERE)
wf = json.load(open(os.path.join(HERE, "critical-mass.json")))

step("Creating credentials")
creds = {
    "x-signal-secret (set me)": ("Critical Mass · signal secret", "x-signal-secret", env("SIGNAL_SECRET")),
    "Apify (Authorization: Bearer <token>)": ("Critical Mass · Apify", "Authorization", f"Bearer {env('APIFY_TOKEN')}"),
    "Featherless (Authorization: Bearer <key>)": ("Critical Mass · Featherless", "Authorization", f"Bearer {env('FEATHERLESS_API_KEY')}"),
}
s, existing = call("GET", f"{base}/api/v1/credentials?limit=100", n8n)
by_name = {c["name"]: c["id"] for c in (existing.get("data", []) if isinstance(existing, dict) else [])}
created = {}
for placeholder, (name, header, value) in creds.items():
    if name in by_name:
        created[placeholder] = {"id": by_name[name], "name": name}
        print("reused:", name)
        continue
    s, res = call("POST", f"{base}/api/v1/credentials", n8n,
                  {"name": name, "type": "httpHeaderAuth", "data": {"name": header, "value": value}})
    if s not in (200, 201):
        sys.exit(f"Could not create credential '{name}' ({s}): {res}")
    created[placeholder] = {"id": res["id"], "name": name}
    print("created:", name)

for node in wf["nodes"]:
    refs = node.get("credentials", {})
    for ctype, ref in list(refs.items()):
        if ctype == "httpHeaderAuth" and ref["name"] in created:
            refs[ctype] = created[ref["name"]]
        elif not ref.get("id"):
            del refs[ctype]  # Gmail: connected by hand in the n8n UI (Google sign-in)
    if not refs:
        node.pop("credentials", None)

step("Importing workflow")
body = {k: wf[k] for k in ("name", "nodes", "connections", "settings")}
s, res = call("POST", f"{base}/api/v1/workflows", n8n, body)
if s not in (200, 201):
    sys.exit(f"Import failed ({s}): {res}")
wid = res["id"]
print("imported:", f"{base}/workflow/{wid}")

step("Activating")
s, res = call("POST", f"{base}/api/v1/workflows/{wid}/activate", n8n)
if s == 200:
    print("active")
else:
    print(f"not active yet ({s}). Usually because Gmail is not connected. Open the workflow, connect Gmail on the 5 Gmail nodes, then toggle Active.")

path = next(n["parameters"]["path"] for n in wf["nodes"] if n["type"] == "n8n-nodes-base.webhook")
print("\nWebhook URL for Apps Script (N8N_WEBHOOK_URL):", f"{base}/webhook/{path}")
print("Apps Script N8N_SECRET: the SIGNAL_SECRET value from .env (copy it from the file, not from here).")
