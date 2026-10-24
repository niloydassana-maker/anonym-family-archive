import os
import sys
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

tok = os.environ.get("GITHUB_TOKEN") or "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"
h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}

targets = [
    ("alfrexo95/bounty-bot", 21),
    ("SlopDotCash/slopdotcash", 905),
    ("devpool-directory/devpool-directory", 5066)
]

for repo, num in targets:
    url = f"https://api.github.com/repos/{repo}/issues/{num}"
    try:
        r = requests.get(url, headers=h, timeout=10)
    except Exception as e:
        print(f"Error fetching {repo}#{num}: {e}", flush=True)
        continue
    if r.status_code != 200:
        print(f"Failed {repo}#{num}: {r.status_code}", flush=True)
        continue
    data = r.json()
    print("=" * 80, flush=True)
    print(f"REPO: {repo} #{num}", flush=True)
    print(f"TITLE: {data.get('title')}", flush=True)
    print(f"URL: {data.get('html_url')}", flush=True)
    print(f"STATE: {data.get('state')}", flush=True)
    print(f"AUTHOR: {data.get('user', {}).get('login')}", flush=True)
    print(f"LABELS: {[l['name'] for l in data.get('labels', [])]}", flush=True)
    print(f"COMMENTS: {data.get('comments')}", flush=True)
    print("BODY:", flush=True)
    print(data.get("body", "")[:1200], flush=True)
    print("\n", flush=True)
