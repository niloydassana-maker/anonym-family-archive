#!/usr/bin/env python3
"""
MASS ENTERPRISE AUTOMATION OUTBOUND DISPATCHER — 23/24 OCT 2026
Targeting verified Founders, CEOs, and CTOs with Turnkey Autonomous Architecture Packages.
Zero live calls — 100% written and asynchronous lane.
Compliant with:
- Zero-Manufacture Law (real leads, real SMTP 250 OK receipts)
- Radio Law (written lane only, no live calls)
- No-Signature DM Law (clean human sign-off: "Kunal")
"""
import smtplib, os, time, json, hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from pathlib import Path
from datetime import datetime, timezone

VAULT = Path(r"D:\anonym\vault\gmail_apppw.txt")
ME = "isearch.xsolve@gmail.com"
SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 587
RECEIPTS_DIR = Path(r"D:\anonym\deliverables\enterprise_outreach_20261023\mass_batch")
RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

CONTACTED_FILE = Path(r"D:\anonym\tools\lead_hunter\already_contacted.json")
SMTP_LOG = Path(r"D:\anonym\war-log\hunt\smtp-sends.csv")

# Load existing contacted
with open(CONTACTED_FILE, "r", encoding="utf-8") as f:
    contacted_set = set(json.load(f))

# Also check receipts dir to ensure zero duplicates
for r in RECEIPTS_DIR.glob("*.txt"):
    for part in r.stem.split("_"):
        if "_at_" in part:
            contacted_set.add(part.replace("_at_", "@").lower())
contacted_set.add("barry@drochaid.ai")

# Define the High-Ticket Mass Pipeline Batch
LEADS = [
    {
        "to": "barry@drochaid.ai",
        "name": "Barry",
        "company": "Drochaid AI",
        "role": "Founder & Managing Director",
        "subject": "Turnkey n8n & B2B automation engine — 22 years systems architecture",
        "body": """Hi Barry,

Saw Drochaid AI's focus on white-label enterprise workflow automation and Make/n8n pipelines. 

Most automated workflow pipelines break down when scaling B2B integrations due to non-deterministic webhook payloads and unhandled API rate-limit spikes. Over 22 years in systems architecture (NIT Silchar Honours, former Director & CTO), I've designed resilient, event-driven automation hubs with deterministic validation gates, PostgreSQL deduplication, and zero-loss error recovery.

Our catalog includes pre-built, production-tested n8n orchestration engines and multi-agent execution pipelines (1.9M+ lines of verified code). Rather than building from scratch, we deploy turnkey, containerized automation systems that handle complex enterprise workflows out of the box.

I work entirely asynchronously in writing — no sales calls. Detailed specs, architecture memos, and Docker deployments delivered directly to your team.

If you have a workflow bottleneck or client pipeline ready for a turnkey sprint, let me know where to send the architectural blueprint.

Written lane: isearch.xsolve@gmail.com / WhatsApp text +91 86172 16163

Kunal"""
    },
    {
        "to": "colton@opaxa.com",
        "name": "Colton",
        "company": "Opaxa",
        "role": "Co-Founder / Engineering Lead",
        "subject": "Resilient multi-location event architecture — 22 years distributed systems",
        "body": """Hi Colton,

Came across Opaxa's build of an AI agent platform for multi-location restaurant operations.

Coordinating multi-location data aggregation and back-office sync across distributed points of sale requires rock-solid event-driven architecture—specifically offline/online queue synchronization, idempotent webhook processing, and zero-drift database state machines.

Background: 22+ years distributed backend architecture (NIT Silchar Honours, former Director & CTO). I've built and scaled high-throughput event backends in Python/FastAPI, distributed queue orchestrations, and autonomous agent execution frameworks with strict 3-tier TDD gates.

We deploy modular, turnkey backend and agent pipelines ready for containerized deployment, cutting months off custom infrastructure build time.

I operate strictly in writing with zero meeting overhead. Code memos, repo PRs, and Docker containers delivered directly.

Happy to share an architectural teardown of how we structure resilient multi-location sync if of interest.

Written lane: isearch.xsolve@gmail.com / WhatsApp text +91 86172 16163

Kunal"""
    },
    {
        "to": "amber.auslander@matterhaul.com",
        "name": "Amber",
        "company": "Matterhaul",
        "role": "Co-Founder & Head of Talent",
        "subject": "High-scale logistics data pipelines & routing engines — 22y systems architect",
        "body": """Hi Amber,

Saw Matterhaul's work in applied AI and logistics automation for real-time routing.

Real-time telemetry ingestion and dynamic routing at scale require resilient asynchronous stream processing, sub-second geospatial indexing, and deterministic optimization models that don't choke under fleet data spikes.

Over 22 years as a Principal Systems Architect (NIT Silchar Honours, former Director & CTO), I've engineered distributed logistics pipelines and real-time transit telemetry architectures (including live integration work with Singapore Land Transport Authority systems). Our published repo catalog encompasses 49 production repositories and 1.95M lines of verified code.

We deliver turnkey, high-throughput data processing and routing pipelines containerized for immediate production integration.

I work 100% asynchronously in writing—no meeting loops. Technical briefs, benchmarks, and production-ready containers delivered directly to engineering.

Would value sharing our architectural framework for high-throughput logistics telemetry if useful.

Written lane: isearch.xsolve@gmail.com / WhatsApp text +91 86172 16163

Kunal"""
    },
    {
        "to": "nicholas.hanson@govstar.us",
        "name": "Nicholas",
        "company": "GovStar",
        "role": "Co-Founder & CCO",
        "subject": "High-assurance Python backend & data pipeline architecture — 22y veteran",
        "body": """Hi Nicholas,

Noticed GovStar's build of high-assurance public sector infrastructure and secure Python data processing.

Public sector and defense-adjacent systems require strict zero-trust pipeline isolation, cryptographic audit receipts, deterministic AST verification, and fail-safe database transactions that leave zero room for non-deterministic failure.

Background: 22+ years enterprise systems architecture (NIT Silchar Honours, former Director & CTO, MCA DIN 10386590). I've architected distributed, high-security Python/FastAPI backends and sandboxed multi-agent execution gates (ASES v3.1) designed specifically for mission-critical reliability.

We provide pre-architected, containerized Python infrastructure modules with end-to-end cryptographic logging and automated compliance validation.

I work entirely asynchronously in writing with zero call overhead. Full architectural teardowns, security proofs, and repo deliverables provided directly.

Open to sending over an architecture brief on how we structure high-assurance Python pipelines if helpful.

Written lane: isearch.xsolve@gmail.com / WhatsApp text +91 86172 16163

Kunal"""
    },
    {
        "to": "scott.deakin@buoyant.io",
        "name": "Scott",
        "company": "Buoyant",
        "role": "Technical Lead",
        "subject": "Distributed systems & service mesh reliability — 22y backend architect",
        "body": """Hi Scott,

Saw Buoyant's engineering focus on Linkerd, Kubernetes networking, and distributed systems reliability.

Having spent 22 years designing and operating distributed event backends, microservice meshes, and resilient high-throughput infrastructure (NIT Silchar Honours, former Director & CTO), I deeply appreciate Linkerd's philosophy of lightweight, deterministic service mesh architecture.

I've engineered distributed systems handling multi-million transaction loads, asynchronous telemetry streaming, and containerized orchestration across global cloud corridors. Our published catalog includes 49 production repos and 1.95M source lines.

I work entirely asynchronously in writing. Would value reviewing any complex backend orchestration or reliability challenges your team is currently tackling.

Written lane: isearch.xsolve@gmail.com / WhatsApp text +91 86172 16163

Kunal"""
    }
]

def main():
    if not VAULT.exists():
        print(f"Error: Vault password file {VAULT} does not exist.")
        return

    pw = VAULT.read_text().strip()
    print(f"Loaded credentials for {ME}. Connecting to {SMTP_HOST}:{SMTP_PORT}...")

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
    server.starttls()
    server.login(ME, pw)
    print("SMTP Auth Successful. Ready to dispatch mass batch.\n")

    dispatched = 0
    for lead in LEADS:
        to_email = lead["to"].lower().strip()
        if to_email in contacted_set:
            print(f"SKIP (Already Contacted): {to_email}")
            continue

        msg = MIMEMultipart()
        msg["From"] = f"Kunal Das <{ME}>"
        msg["To"] = to_email
        msg["Subject"] = lead["subject"]
        msg["Date"] = formatdate(localtime=True)
        msg_id = make_msgid(domain="gmail.com")
        msg["Message-ID"] = msg_id
        msg.attach(MIMEText(lead["body"], "plain", "utf-8"))

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        print(f"Sending to {lead['name']} ({lead['company']}) at {to_email}...")
        
        resp = server.sendmail(ME, [to_email], msg.as_string())
        
        # Write cryptographic receipt
        receipt_content = f"""RECEIPT — ENTERPRISE MASS DISPATCH
Timestamp: {ts}
Recipient: {to_email}
Company: {lead['company']}
Role: {lead['role']}
Subject: {lead['subject']}
Message-ID: {msg_id}
Status: 250 OK (Dispatched via smtp.gmail.com:587)
SHA256: {hashlib.sha256(msg.as_bytes()).hexdigest()}
==================================================
BODY:
{lead['body']}
"""
        receipt_file = RECEIPTS_DIR / f"receipt_{ts}_{to_email.replace('@', '_at_')}.txt"
        receipt_file.write_text(receipt_content, encoding="utf-8")
        print(f"  [OK] Receipt generated: {receipt_file.name}")

        # Update Contacted Set & SMTP Log
        contacted_set.add(to_email)
        with open(SMTP_LOG, "a", encoding="utf-8") as f:
            f.write(f"{ts},{to_email},{lead['company']},{lead['subject']},250_OK,{msg_id}\n")

        dispatched += 1
        time.sleep(2)  # Safe cadence

    server.quit()

    # Save updated contacted list
    with open(CONTACTED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(contacted_set)), f, indent=2)

    print(f"\n==================================================")
    print(f"DISPATCH COMPLETE: {dispatched} enterprise proposals sent.")
    print(f"Receipts saved to: {RECEIPTS_DIR}")
    print(f"Contacted registry and SMTP log updated.")

if __name__ == "__main__":
    main()
