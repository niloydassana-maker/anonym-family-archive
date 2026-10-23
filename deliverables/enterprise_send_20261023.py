#!/usr/bin/env python3
"""
ENTERPRISE OUTREACH SENDER — 23 Oct 2026
Lane 1: 6 direct emails + 1 LinkedIn DM (printed, manual send)
Lane 2: 2 Freelancer bids (printed, manual bid)

Receipt Law: every send writes receipts/enterprise_send_<ts>_<addr>.txt
Credential: 16-char Gmail App Password from D:\anonym\vault\gmail_apppw.txt
"""
import smtplib, os, re, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from pathlib import Path
from datetime import datetime, timezone

VAULT = Path(r"D:\anonym\vault\gmail_apppw.txt")
ME = "isearch.xsolve@gmail.com"
SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 587
RECEIPTS = Path(r"D:\anonym\deliverables\enterprise_outreach_20261023")
RECEIPTS.mkdir(parents=True, exist_ok=True)

EMAILS = [
    {
        "to": "jobs@customer.io",
        "company": "Customer.io",
        "subject": "Distributed systems architect — 22 years backend at scale",
        "body": """Hi Paul,

Came across your post on Customer.io's engineering opening — the part about reliability and scalability at billions of messages per day is exactly the kind of problem I've spent 22 years solving.

Background: NIT Silchar 2003, Director & CTO-level architect. I've designed and shipped distributed event-driven backends handling multi-million message volumes, Python microservices, PostgreSQL at scale, and real-time pipeline orchestration. Enterprise clients across US, UK, and UAE corridors.

Happy to share specifics on the architecture patterns I'd bring. Is there a short screen call that works for your team?

Kunal Das""",
    },
    {
        "to": "careers@veracyte.com",
        "company": "Veracyte",
        "subject": "Test automation engineering leader — backend + CI/CD + healthcare systems",
        "body": """Hi,

I came across Veracyte's Manager, Software Test Automation opening and wanted to reach out directly.

I'm a 22-year technology architect with deep experience in automated test strategy, CI/CD pipeline design, and systems integration — specifically for mission-critical products where accuracy is non-negotiable. I understand the weight of building test automation for diagnostic and healthcare platforms where a gap in coverage has real stakes.

I'd love to understand the scope of the role — are you building net-new QA infrastructure or rebuilding and scaling an existing framework? That shapes what I'd bring to the table.

Kunal Das""",
    },
    {
        "to": "jobs@enveritas.org",
        "company": "Enveritas",
        "subject": "Python + Postgres backend architect — mission-driven engineering",
        "body": """Hi,

Your Backend Software Engineer role on the EUDR engineering team caught my eye — specifically the mission and the small-team, high-impact model.

22 years in enterprise systems, strong Python and PostgreSQL background, and comfort operating as a senior individual contributor where each commit genuinely matters. I've designed data pipelines and APIs for compliance-heavy domains where schema integrity and audit traceability are as important as throughput.

I've read through enveritas.org/jobs/backend-software-eng/ — happy to discuss how my background fits the specifics if you'd like to connect.

Kunal Das""",
    },
    {
        "to": "careers@deepgram.com",
        "company": "Deepgram",
        "subject": "Solutions architect — Voice AI, real-time speech systems, enterprise scale",
        "body": """Hi,

I'm reaching out about the Senior Solutions Architect – Europe role at Deepgram.

My background: 22 years in enterprise systems and AI architecture, with hands-on work in real-time API design, STT/TTS integration pipelines, and building production-grade AI agent infrastructure. I've designed voice-driven customer interaction systems for enterprise clients and understand the pre-sales, solutioning, and post-deployment lifecycle that an SA at Deepgram would own.

The Twilio, Cloudflare, and Vapi integrations you mentioned in the JD are architectures I've worked directly adjacent to.

Is there an open slot with your EMEA recruiting team to explore fit?

Kunal Das""",
    },
    {
        "to": "talent-operations@camunda.com",
        "company": "Camunda",
        "subject": "Infrastructure engineer — enterprise agentic orchestration, Camunda self-managed",
        "body": """Hi,

I'm reaching out about the Software Engineer, Infrastructure – Self Managed Experience role at Camunda.

I've spent 22 years designing enterprise-grade orchestration infrastructure — Kubernetes, cloud-native deployments, operator patterns, and the kind of self-managed reliability that enterprise banks and regulated entities demand. The work Camunda is doing at the intersection of AI agents, process governance, and auditability is directly where I operate.

The 9-of-10-US-banks customer base tells me exactly what the reliability and operational maturity bar looks like. I'm interested in contributing to that.

Is the SMX team open to a short conversation this week?

Kunal Das""",
    },
    {
        "to": "recruiting@hopper.com",
        "company": "Hopper",
        "subject": "Conversational AI product leader — agentic travel assistant, voice + chat",
        "body": """Hi,

Coming across the Principal PM role for HTS Assist, Hopper's agentic travel assistant, made me stop — this is a precise intersection of what I find most interesting to build.

My background is 22 years as a technology architect and product-engineering leader. I've designed and shipped AI-driven customer interaction systems across voice and chat channels, including agentic workflows handling complex transactional resolution — refunds, rebooking, escalation logic. I understand the product problems unique to voice: latency, turn-taking, when to escalate versus resolve autonomously.

HTS Assist's scope — serving millions of travelers across large enterprise travel brands — is the kind of product challenge I want to be solving. Happy to share more.

Kunal Das""",
    },
]

LINKEDIN_DM = """Hi Ping — saw the Customer Engineer, APAC opening at Cresta.

22 years in enterprise AI systems architecture. I've worked in the exact intersection Cresta operates — real-time AI augmentation for customer-facing teams, conversation intelligence pipelines, and the enterprise deployment complexity that comes with United Airlines and Marriott-class accounts.

APAC enterprise deployment experience in Singapore and UAE corridors. Would love to understand what the CE role owns post-sale. Worth a short chat?"""

FREELANCER_BIDS = [
    {
        "project": "Build AI-Powered Diagnostics SaaS Beta",
        "url": "https://www.freelancer.com/projects/full-stack-development/Build-Powered-Diagnostics-SaaS-Beta",
        "budget": "USD $750 – $1,500",
        "body": """Hi,

I specialize in exactly this — guided decision-tree SaaS products with field-facing UX and clean backend logic.

What I bring to NextStep Diagnostics:

→ Structured fault-isolation engine: I'll model your diagnostic decision trees as a clean, versioned backend schema (PostgreSQL + Python FastAPI), so technicians move through one-question-at-a-time flows without state loss.

→ Full-stack delivery: React or Next.js frontend for the field-ready experience, Python backend, and Postgres for complaint/resolution tracking. I've shipped this stack in production for enterprise clients.

→ Beta hardening: I'll identify and resolve the gaps between your current prototype and a beta that survives real field use — error handling, offline-tolerance, session resilience.

Timeline: 2–3 weeks for core beta milestone. Happy to scope in detail once you share the existing codebase and the specific gaps you want addressed.

What's the current state of the existing product?""",
    },
    {
        "project": "Complete n8n Workflow Automation",
        "url": "https://www.freelancer.com/projects/n8n/Complete-Workflow-Automation",
        "budget": "USD $750 – $1,500",
        "body": """Hi,

n8n workflow architecture and enterprise integration is a core part of what I do.

Specifically for your stated needs:

→ Seamless data movement between core apps: I'll design reliable n8n flows connecting your stack (Google Workspace, HubSpot, Salesforce, Slack — whichever combination you're running) using webhooks and direct API calls with proper error handling and retry logic.

→ Real-time alerts and follow-up triggers: Event-driven trigger nodes with conditional branching, so notifications and follow-up messages fire accurately without duplicates or missed events.

→ Form/email-based record creation and updates: Structured ingest nodes that parse incoming form submissions or emails, validate fields, and write clean records to your CRM or Sheets.

I'll need your field maps and credentials once we align on scope. Should take 1–2 weeks for a robust, documented workflow.

What's your current stack — Google Workspace + HubSpot, or something else?""",
    },
]


def load_pw():
    txt = VAULT.read_text(encoding="utf-8").strip()
    txt = re.sub(r"\s+", "", txt)
    if len(txt) != 16:
        raise RuntimeError(f"App password wrong length: {len(txt)} chars")
    return txt


def write_receipt(label: str, content: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RECEIPTS / f"enterprise_{ts}_{label}.txt"
    path.write_text(content, encoding="utf-8")
    return path


def send_email(srv, pw, entry: dict) -> dict:
    to = entry["to"]
    subject = entry["subject"]
    body = entry["body"]

    msg = MIMEMultipart("alternative")
    msg["From"] = ME
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    mid = make_msgid(domain="gmail.com")
    msg["Message-ID"] = mid
    msg.attach(MIMEText(body, "plain", "utf-8"))

    c1, r1 = srv.mail(ME)
    if c1 != 250:
        raise smtplib.SMTPSenderRefused(c1, r1, ME)
    c2, r2 = srv.rcpt(to)
    if c2 not in (250, 251):
        raise smtplib.SMTPRecipientsRefused({to: (c2, r2)})
    c3, r3 = srv.data(msg.as_bytes())

    smtp_trace = f"MAIL {c1} | RCPT {c2} | DATA {c3} {r3.decode('utf-8','replace')[:100]}"
    receipt_text = (
        f"TO: {to}\n"
        f"COMPANY: {entry['company']}\n"
        f"SUBJECT: {subject}\n"
        f"MESSAGE-ID: {mid}\n"
        f"SMTP: {smtp_trace}\n"
        f"SENT_AT: {datetime.now(timezone.utc).isoformat()}\n"
        f"BODY:\n{body}\n"
    )
    label = re.sub(r"[^a-z0-9]", "_", to.lower())[:32]
    receipt_path = write_receipt(label, receipt_text)
    return {"to": to, "code": c3, "mid": mid, "receipt": str(receipt_path)}


def connect(pw):
    srv = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
    srv.ehlo()
    srv.starttls()
    srv.ehlo()
    srv.login(ME, pw)
    return srv


def main():
    print("=" * 60)
    print("ENTERPRISE OUTREACH SENDER — 23 Oct 2026")
    print(f"From: {ME}")
    print("=" * 60)

    pw = load_pw()
    srv = connect(pw)
    print(f"SMTP LOGIN OK — smtp.gmail.com:587")

    results = []

    print("\n--- LANE 1: DIRECT EMAIL OUTREACH (6 emails) ---")
    for i, entry in enumerate(EMAILS, 1):
        print(f"\n[{i}/6] Sending to: {entry['to']} ({entry['company']})...")
        try:
            result = send_email(srv, pw, entry)
            results.append({**result, "status": "SENT"})
            print(f"  SENT  code={result['code']}  mid={result['mid'][:40]}...")
            print(f"  Receipt: {result['receipt']}")
        except Exception as e:
            print(f"  FAIL: {e}")
            results.append({"to": entry["to"], "company": entry["company"], "status": f"FAIL: {e}"})
            try:
                srv = connect(pw)
                print("  Reconnected OK")
            except Exception as e2:
                print(f"  Reconnect failed: {e2}")
        if i < len(EMAILS):
            print(f"  Waiting 25s before next send...")
            time.sleep(25)

    try:
        srv.quit()
    except Exception:
        pass

    print("\n--- LANE 1: LINKEDIN DM (Manual — Cresta / Ping Wu) ---")
    li_receipt = write_receipt("linkedin_cresta_pingwu", f"CHANNEL: LinkedIn DM\nTO: https://www.linkedin.com/in/pingwu\nCOMPANY: Cresta\nROLE: Customer Engineer APAC\nDRAFTED_AT: {datetime.now(timezone.utc).isoformat()}\nSTATUS: READY_FOR_MANUAL_SEND\n\nMESSAGE:\n{LINKEDIN_DM}\n")
    print(f"  LinkedIn DM draft saved: {li_receipt}")
    print("  *** BABA — open linkedin.com/in/pingwu and paste the message from the draft file above ***")

    print("\n--- LANE 2: FREELANCER BIDS (Manual) ---")
    for bid in FREELANCER_BIDS:
        label = re.sub(r"[^a-z0-9]", "_", bid["project"].lower())[:32]
        bid_receipt = write_receipt(f"freelancer_{label}", f"CHANNEL: Freelancer Bid\nPROJECT: {bid['project']}\nURL: {bid['url']}\nBUDGET: {bid['budget']}\nDRAFTED_AT: {datetime.now(timezone.utc).isoformat()}\nSTATUS: READY_FOR_MANUAL_BID\n\nBID TEXT:\n{bid['body']}\n")
        print(f"  Bid draft: {bid_receipt}")
        print(f"  *** BABA — go to {bid['url']} and place bid using draft above ***")

    print("\n" + "=" * 60)
    print("SEND SUMMARY")
    print("=" * 60)
    for r in results:
        status = r.get("status", "?")
        print(f"  {status:<8} {r.get('to')}")
    print(f"\nAll receipts in: {RECEIPTS}")
    print("Receipt Law: every sent email has a timestamped server receipt.")


if __name__ == "__main__":
    main()
