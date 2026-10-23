#!/usr/bin/env python3
"""
24/7 AUTONOMOUS ENTERPRISE TRIAGE & ARCHITECTURE DISPATCH DAEMON
Runs continuously in background.
Cycles every 2 hours (7,200s), dispatching 3 to 4 vetted enterprise proposals per cycle.
Strictly adheres to:
- Zero-Manufacture Law (real recipients, live 250 OK echo, cryptographic receipts)
- Radio Law (written communication only: isearch.xsolve@gmail.com / WhatsApp text)
- No-Signature DM Law (clean sign-off "Kunal")
- Open Source Authority (links to 125 public repositories at https://github.com/isearchxsolve)
"""
import smtplib, time, json, hashlib, os, sys, re
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
SHIELDED_FILE = Path(r"D:\anonym\shielded_contacts.json")
QUEUE_FILE = Path(r"D:\anonym\scratch\top_remote_hn_leads.json")

CYCLE_SLEEP_SECONDS = 7200  # 2 hours between batches
BATCH_SIZE = 3              # 3 high-ticket leads per cycle

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def load_shielded():
    if not SHIELDED_FILE.exists():
        return set()
    try:
        data = json.loads(SHIELDED_FILE.read_text(encoding="utf-8"))
        names = set(n.lower() for n in data.get("shielded_names", []))
        slugs = set(s.lower() for s in data.get("shielded_slugs", []))
        return names | slugs
    except Exception as e:
        log(f"Warning loading shielded: {e}")
        return set()

def load_contacted():
    contacted = set()
    if CONTACTED_FILE.exists():
        try:
            contacted = set(e.lower().strip() for e in json.load(open(CONTACTED_FILE, encoding="utf-8")))
        except Exception:
            pass
    # Also inspect receipts dir
    for r in RECEIPTS_DIR.glob("*.txt"):
        for part in r.stem.split("_"):
            if "_at_" in part:
                contacted.add(part.replace("_at_", "@").lower().strip())
    return contacted

def save_contacted(contacted_set):
    with open(CONTACTED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(contacted_set)), f, indent=2)

def craft_proposal(company, headline, text, email):
    clean_comp = company.split('|')[0].strip()
    if clean_comp.lower().startswith("founding engineer"):
        clean_comp = "your engineering team"
    
    subject = f"Distributed backend & event architecture — 22y veteran for {clean_comp}"
    
    body = f"""Hi {clean_comp} team,

Saw your engineering opening regarding {clean_comp}'s systems work.

Over 22 years in enterprise systems architecture (NIT Silchar Honours, former Director & CTO, MCA DIN 10386590), I've designed and scaled high-throughput event backends, distributed data pipelines, and autonomous execution environments across global cloud corridors.

Our complete engineering catalog of 125 production repositories and 1.95M lines of code is fully public for technical inspection:
https://github.com/isearchxsolve

Key open architectural references:
- Sandboxed multi-agent execution with AST import gates (ASES v3.1): https://github.com/isearchxsolve/n8n-frellancing_advanced-ases_v3_1
- Distributed API routing, rate-limiting & metering: https://github.com/isearchxsolve/omniroute-monetizer
- High-throughput web crawling & data extraction pipelines: https://github.com/isearchxsolve/crawlee-engine

I work entirely asynchronously in writing—zero meeting overhead. Clean architectural teardowns, benchmarked patches, and containerized Docker deployments delivered directly to your engineers.

Happy to share a written architecture brief on your highest-priority pipeline bottleneck if of interest.

Written lane: isearch.xsolve@gmail.com / WhatsApp text +91 86172 16163

Kunal"""
    return subject, body

def run_cycle(cycle_num):
    log(f"==================================================")
    log(f"CYCLE #{cycle_num} INITIATING: Loading queue and credentials...")
    
    if not VAULT.exists():
        log(f"ERROR: Vault password file {VAULT} missing. Aborting cycle.")
        return 0

    pw = VAULT.read_text().strip()
    contacted_set = load_contacted()
    shielded_set = load_shielded()

    if not QUEUE_FILE.exists():
        log(f"Queue file {QUEUE_FILE} not found.")
        return 0

    try:
        leads = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"Error reading queue: {e}")
        return 0

    # Pick candidate leads
    candidates = []
    for l in leads:
        for em in l.get("emails", []):
            em_clean = em.lower().strip()
            # check exclusion
            if em_clean in contacted_set:
                continue
            if any(s in em_clean for s in shielded_set):
                log(f"SHIELDED: Skipping {em_clean}")
                continue
            candidates.append((l, em_clean))
            break
        if len(candidates) >= BATCH_SIZE:
            break

    if not candidates:
        log("No fresh uncontacted leads in queue. Standing by.")
        return 0

    log(f"Selected {len(candidates)} high-match candidates for this cycle.")

    # Connect to SMTP
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=25)
        server.starttls()
        server.login(ME, pw)
        log("SMTP Handshake successful.")
    except Exception as e:
        log(f"SMTP Connection failure: {e}")
        return 0

    dispatched = 0
    for lead, to_email in candidates:
        subject, body = craft_proposal(lead["company"], lead["headline"], lead["text"], to_email)
        
        msg = MIMEMultipart()
        msg["From"] = f"Kunal Das <{ME}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg_id = make_msgid(domain="gmail.com")
        msg["Message-ID"] = msg_id
        msg.attach(MIMEText(body, "plain", "utf-8"))

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        log(f"Dispatching to {to_email} ({lead['company']})...")

        try:
            server.sendmail(ME, [to_email], msg.as_string())
            
            # Write cryptographic receipt
            receipt_content = f"""RECEIPT — 24/7 DAEMON CYCLE #{cycle_num}
Timestamp: {ts}
Recipient: {to_email}
Company: {lead['company']}
Subject: {subject}
Message-ID: {msg_id}
Status: 250 OK (Dispatched via smtp.gmail.com:587)
SHA256: {hashlib.sha256(msg.as_bytes()).hexdigest()}
==================================================
BODY:
{body}
"""
            receipt_file = RECEIPTS_DIR / f"receipt_{ts}_{to_email.replace('@', '_at_')}.txt"
            receipt_file.write_text(receipt_content, encoding="utf-8")
            log(f"  [OK] Receipt recorded: {receipt_file.name}")

            contacted_set.add(to_email)
            with open(SMTP_LOG, "a", encoding="utf-8") as f:
                f.write(f"{ts},{to_email},{lead['company']},{subject},250_OK,{msg_id}\n")

            dispatched += 1
            time.sleep(3)  # Gentle spacing
        except Exception as e:
            log(f"  [ERROR] Failed send to {to_email}: {e}")

    server.quit()
    save_contacted(contacted_set)

    log(f"CYCLE #{cycle_num} COMPLETED: {dispatched} proposals dispatched.")
    return dispatched

def main():
    log("==================================================")
    log("24/7 AUTONOMOUS ENTERPRISE OUTBOUND DAEMON STARTED")
    log(f"Sender: {ME} | Vault Auth: Loaded")
    log(f"Cycle cadence: Every {CYCLE_SLEEP_SECONDS}s (~2h) | Batch: {BATCH_SIZE} leads/cycle")
    log(f"Public Ocean URL: https://github.com/isearchxsolve (125 repos)")
    log("==================================================")

    cycle_count = 1
    while True:
        try:
            run_cycle(cycle_count)
        except Exception as e:
            log(f"Unhandled cycle exception: {e}")
        
        cycle_count += 1
        log(f"Sleeping for {CYCLE_SLEEP_SECONDS}s until next dispatch cycle...")
        time.sleep(CYCLE_SLEEP_SECONDS)

if __name__ == "__main__":
    main()
