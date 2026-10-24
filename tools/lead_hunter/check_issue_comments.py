import os
import sys
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

tok = os.environ.get("GITHUB_TOKEN") or "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"
h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}

repo = "ubiquity/pay.ubq.fi"
num = 386

url = f"https://api.github.com/repos/{repo}/issues/{num}/comments"
r = requests.get(url, headers=h)
comments = r.json()

print(f"Total comments on {repo}#{num}: {len(comments)}", flush=True)
for c in comments:
    author = c.get("user", {}).get("login")
    created = c.get("created_at")[:10]
    body = c.get("body", "").strip()
    print(f"\n--- @{author} ({created}) ---", flush=True)
    print(body[:500], flush=True)
