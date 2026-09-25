import json
import os

base_dir = r"D:\anonym\war-log"

# 1. Author D-20260922T083800Z.json
d_content = {
  "event": "WEB-20260922T030601721016.json",
  "class_or_NOVEL": "CLASS-6/THESIS",
  "draft_reply": "Hi Aarti Patel,\n\nDeliverables:\n1. End-to-end Python AI/ML pipeline architecture using Pandas, NumPy and PyTorch\n2. Data preprocessing, feature engineering and model training scripts\n3. Model evaluation metrics and validation report\n4. Clean REST API endpoint and deployment docs for AI projects\n\nPrice + Days: Rs 40,000 | 10 days\nSchedule:\nDay 1-2: Data ingestion, cleaning and feature extraction setup\nDay 3-5: Model development and hyperparameter tuning\nDay 6-7: API integration and evaluation report\nDay 8-10: Final validation and handover\n\nPhase-2 boundary: Cloud GPU hosting fees and ongoing infrastructure maintenance are NOT included.\nAccess list: GitHub repository access, dataset locations.\nTerms: 50% advance before kickoff tomorrow.\n\nSay the word and I begin. - Kunal",
  "send": True,
  "reason": "Rule 5 / Rule 18 OPEN BUYER QUEUE: Authoring THESIS proposal for Aarti Patel (AI/ML project, ML-B Rs 40,000/10d)."
}
d_path = os.path.join(base_dir, "directives", "D-20260922T083800Z.json")
with open(d_path, "w", encoding="utf-8") as f:
    json.dump(d_content, f, indent=2)

# 2. Author WEB-20260922T083800Z-propose-aarti-msg.json
web_content = {
  "action": "fill_and_send",
  "match_url_substring": "linkedin.com/messaging",
  "require_body_contains": "Aarti Patel",
  "text": "Hi Aarti Patel,\n\nDeliverables:\n1. End-to-end Python AI/ML pipeline architecture using Pandas, NumPy and PyTorch\n2. Data preprocessing, feature engineering and model training scripts\n3. Model evaluation metrics and validation report\n4. Clean REST API endpoint and deployment docs for AI projects\n\nPrice + Days: Rs 40,000 | 10 days\nSchedule:\nDay 1-2: Data ingestion, cleaning and feature extraction setup\nDay 3-5: Model development and hyperparameter tuning\nDay 6-7: API integration and evaluation report\nDay 8-10: Final validation and handover\n\nPhase-2 boundary: Cloud GPU hosting fees and ongoing infrastructure maintenance are NOT included.\nAccess list: GitHub repository access, dataset locations.\nTerms: 50% advance before kickoff tomorrow.\n\nSay the word and I begin. - Kunal",
  "reason": "Rule 5 / Rule 18 OPEN BUYER QUEUE & INBOX OWNERSHIP: Fill and send THESIS proposal to Aarti Patel via LinkedIn DM for AI/ML project (ML-B Rs 40,000/10d).",
  "done": False
}
web_path = os.path.join(base_dir, "directives", "WEB-20260922T083800Z-propose-aarti-msg.json")
with open(web_path, "w", encoding="utf-8") as f:
    json.dump(web_content, f, indent=2)

# 3. Update seen.json
seen_path = os.path.join(base_dir, "directives", "seen.json")
with open(seen_path, "r", encoding="utf-8") as f:
    seen_list = json.load(f)

new_events = [
    "WEB-20260922T025932809665.json",
    "WEB-20260922T025937622781.json",
    "WEB-20260922T025946101522.json",
    "WEB-20260922T030009325116.json",
    "WEB-20260922T030034565236.json",
    "WEB-20260922T030035256134.json",
    "WEB-20260922T030037246299.json",
    "WEB-20260922T030057189592.json",
    "WEB-20260922T030147460599.json",
    "WEB-20260922T030226778592.json",
    "WEB-20260922T030313190451.json",
    "WEB-20260922T030332011928.json",
    "WEB-20260922T030332004928.json",
    "WEB-20260922T030332009926.json",
    "WEB-20260922T030332006927.json",
    "WEB-20260922T030332000928.json",
    "WEB-20260922T030334243554.json",
    "WEB-20260922T030342211186.json",
    "WEB-20260922T030359368838.json",
    "WEB-20260922T030400873862.json",
    "WEB-20260922T030400254683.json",
    "WEB-20260922T030402734283.json",
    "WEB-20260922T030416166870.json",
    "WEB-20260922T030426297181.json",
    "WEB-20260922T030447998198.json",
    "WEB-20260922T030518556041.json",
    "WEB-20260922T030519936726.json",
    "WEB-20260922T030533980132.json",
    "WEB-20260922T030600944482.json",
    "WEB-20260922T030601721016.json"
]

added_count = 0
for ev in new_events:
    if ev not in seen_list:
        seen_list.append(ev)
        added_count += 1

with open(seen_path, "w", encoding="utf-8") as f:
    json.dump(seen_list, f, indent=2)

# 4. Append to kilo-say.log
kilo_path = os.path.join(base_dir, "kilo-say.log")
with open(kilo_path, "a", encoding="utf-8") as f:
    for ev in new_events:
        f.write(f"[2026-09-22T03:08:00Z] Processed {ev}: CONTEXT - marked seen\n")
    f.write("[2026-09-22T03:08:00Z] AGY-TRIAGE: Full ownership pass complete for 30 digest events. Authored D-20260922T083800Z.json and WEB-20260922T083800Z-propose-aarti-msg.json. Updated seen.json and heartbeat.\n")

# 5. Update triage-heartbeat.txt
hb_path = os.path.join(base_dir, "triage-heartbeat.txt")
with open(hb_path, "w", encoding="utf-8") as f:
    f.write("2026-09-22 03:08:00 UTC\n")

print(f"Success! Added {added_count} events to seen.json, authored directives, updated kilo-say.log and heartbeat.")
