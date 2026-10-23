import json, re, sys
if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

plat = json.loads(Path(r"D:\anonym\deliverables\master_20261023T141238867952Z\PLATFORM_APPLICATION_LEADS.json").read_text(encoding="utf-8"))
fl = [l for l in plat if l.get("platform") == "Freelancer"]

def max_budget_usd(lead):
    b = lead.get("budget") or ""
    nums = re.findall(r'[\d.]+', b)
    if not nums: return 0
    mx = max(float(x) for x in nums)
    if "INR" in b: mx = mx / 85
    return mx

fl.sort(key=max_budget_usd, reverse=True)

# Already bid on these two
already = {
    "https://www.freelancer.com/projects/full-stack-development/Build-Powered-Diagnostics-SaaS-Beta",
    "https://www.freelancer.com/projects/n8n/Complete-Workflow-Automation",
}

remaining = [l for l in fl if l.get("source_url") not in already]

print(f"Total Freelancer leads: {len(fl)}")
print(f"Already bid: {len(already)}")
print(f"Remaining: {len(remaining)}")
print()

for i, l in enumerate(remaining[:15], 1):
    print(f"#{i}")
    print(f"  Title: {l.get('title')}")
    print(f"  Budget: {l.get('budget')}")
    print(f"  URL: {l.get('source_url')}")
    print(f"  Brief: {l.get('brief_snippet','')[:400]}")
    print()
