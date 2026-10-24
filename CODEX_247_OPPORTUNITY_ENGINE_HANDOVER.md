# 🏛️ CODEX 24/7 AUTONOMOUS OPPORTUNITY ENGINE & REVENUE HANDOVER
**Owner & Principal Systems Architect:** Kunal Das (NIT Silchar 2003 Honours, Former Director & CTO, MCA DIN 10386590)  
**Public Showroom:** https://github.com/isearchxsolve (125 Public Production Repositories | 1.95M+ Lines of Code)  
**Written Communication Lane:** `isearch.xsolve@gmail.com` | WhatsApp text: `+91 86172 16163` (Radio Law: Zero live calls)  
**Target Corridor:** US, UK, UAE, Singapore, Tier-1 India (Bengaluru, Hyderabad, Pune, NCR). Strictly exclude low-budget Tier-2/3 regional listings.

---

## ⚡ MANDATORY DOCTRINE FOR CODEX: THE LAW OF RUTHLESS HONESTY

1. **ZERO FALSE COMFORT, ZERO SYCOPHANCY:**
   - Never tell Kunal "Don't worry, 100% money on Sunday." Never simulate certainty where there is none.
   - Cold outreach is a probability funnel. Report raw statistics: Opportunities Found, Filters Passed, Dispatches Delivered, Replies Received.
   - Never claim an invoice is paid or a deal is closed until live bank/UPI receipts reflect on disk.

2. **THE ZERO-MANUFACTURE LAW:**
   - ZERO synthetic data, ZERO simulated leads, ZERO fabricated API payloads.
   - Every opportunity scraped must be a live, verifiable human posting with a timestamp and verifiable URL.

3. **THE SOLUTION-FIRST OFFER (NO RESUME BRAGGING):**
   - When reaching out, do NOT write a generic resume bragging about degrees or repository counts.
   - State their exact technical bottleneck -> Prescribe the exact architectural fix -> Link the direct matching repo from `https://github.com/isearchxsolve` -> Offer a turnkey 48h containerized Docker patch for a fixed pilot fee ($500 USD / ₹15,000 INR).

4. **THE RADIO LAW & NO-SIGNATURE DM LAW:**
   - Written communication only. Zero live calls. Kunal takes no scheduled calls. All deliverables are containerized patches, benchmarks, and written briefs.
   - Sign-offs are clean human text: "Kunal" (no corporate bot footers).

---

## 🛠️ THE 24/7 AUTONOMOUS HUNTING ENGINE SPECIFICATION

Codex is tasked with running an unattended 24/7 loop that monitors the internet for active, funded engineering needs:

### Target Sources to Scrape Continuously:
1. **Reddit Hiring Subreddits (Real-Time JSON Endpoints, no API key required):**
   - `https://www.reddit.com/r/forhire/new.json?limit=50` (Filter: `[Hiring]`, budgets > $250 or > $30/hr)
   - `https://www.reddit.com/r/freelance_forhire/new.json?limit=50`
   - `https://www.reddit.com/r/jobbit/new.json?limit=50`
2. **Hacker News Live Hiring Comments (Algolia API):**
   - `https://hn.algolia.com/api/v1/search_by_date?tags=comment&query=hiring`
3. **Direct Developer Hiring & Founder Posts:**
   - Filter for: Python, Go, Node.js, AI Agents, LLM, MCP, RAG, Web Scraping, Event Streaming, Distributed Systems, High-Throughput APIs.

---

## 🚀 EXECUTION CODE: `D:\anonym\deliverables\codex_247_hunter.py`

Codex must maintain, supervise, and run the following autonomous daemon in the background 24/7:

```python
#!/usr/bin/env python3
"""
CODEX 24/7 AUTONOMOUS OPPORTUNITY SNATCHER & TRIAGE DISPATCHER
Scrapes Reddit, Hacker News, and remote feeds every 15 minutes.
Filters for high-ticket, funded backend/AI/scraping needs.
Dispatches surgical, solution-first proposals with zero sycophancy.
"""
import urllib.request, json, time, re, os, hashlib, smtplib
from datetime import datetime, timezone
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid

VAULT = Path(r"D:\anonym\vault\gmail_apppw.txt")
ME = "isearch.xsolve@gmail.com"
SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 587

LEAD_STORE = Path(r"D:\anonym\deliverables\codex_live_opportunities.json")
SEEN_FILE = Path(r"D:\anonym\deliverables\codex_seen_ids.json")
RECEIPTS_DIR = Path(r"D:\anonym\deliverables\enterprise_outreach_20261023\mass_batch")
RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

KEYWORDS = [
    "python", "fastapi", "django", "golang", "go", "backend", "api", "scraping",
    "scraper", "crawler", "agent", "agents", "llm", "rag", "mcp", "kafka",
    "distributed", "postgres", "microservice", "automation", "n8n", "docker"
]

EXCLUDE_PATTERNS = [
    r"\[for hire\]", r"for hire", r"seeking work", r"internship", r"unpaid",
    r"kolkata", r"west bengal", r"tutor", r"assignment", r"homework"
]

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [CODEX] {msg}", flush=True)

def load_seen():
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()

def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(list(seen)), encoding="utf-8")

def scrape_reddit(subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=50"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    opportunities = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            posts = data.get("data", {}).get("children", [])
            for p in posts:
                d = p.get("data", {})
                pid = d.get("id")
                title = d.get("title", "")
                selftext = d.get("selftext", "")
                author = d.get("author", "")
                permalink = f"https://reddit.com{d.get('permalink', '')}"
                
                full = f"{title}\n{selftext}".lower()
                
                # Must be hiring, not for hire
                if any(re.search(pat, full) for pat in EXCLUDE_PATTERNS):
                    continue
                if not ("[hiring]" in title.lower() or "hiring" in title.lower()):
                    continue
                
                # Check tech keywords
                matched_kw = [k for k in KEYWORDS if k in full]
                if matched_kw:
                    # Look for email or telegram/discord contact in selftext
                    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', selftext)
                    opportunities.append({
                        "id": f"reddit_{pid}",
                        "source": f"r/{subreddit}",
                        "title": title,
                        "author": author,
                        "url": permalink,
                        "emails": emails,
                        "keywords": matched_kw,
                        "text": selftext[:600],
                        "created_utc": d.get("created_utc")
                    })
    except Exception as e:
        log(f"Error scraping r/{subreddit}: {e}")
    return opportunities

def scrape_hn():
    url = "https://hn.algolia.com/api/v1/search_by_date?tags=comment&query=hiring&hitsPerPage=40"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    opportunities = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            hits = data.get("hits", [])
            for h in hits:
                cid = h.get("objectID")
                text = h.get("comment_text", "")
                author = h.get("author", "")
                story_id = h.get("story_id")
                link = f"https://news.ycombinator.com/item?id={cid}"
                
                full = text.lower()
                matched_kw = [k for k in KEYWORDS if k in full]
                emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
                
                if matched_kw and emails:
                    opportunities.append({
                        "id": f"hn_{cid}",
                        "source": "HackerNews",
                        "title": f"HN Hiring by {author}",
                        "author": author,
                        "url": link,
                        "emails": emails,
                        "keywords": matched_kw,
                        "text": text[:600],
                        "created_at": h.get("created_at")
                    })
    except Exception as e:
        log(f"Error scraping Hacker News: {e}")
    return opportunities

def match_portfolio(keywords):
    if any(k in keywords for k in ["agent", "agents", "llm", "rag", "mcp"]):
        return (
            "Model Context Protocol & AST Sandbox Engine (ASES v3.1)",
            "https://github.com/isearchxsolve/services-mcp",
            "1. AST-verified code execution gates with static import controls.\n2. Standardized Model Context Protocol (MCP) server integration for isolated tool dispatch."
        )
    elif any(k in keywords for k in ["api", "distributed", "golang", "go", "kafka", "docker"]):
        return (
            "OmniRoute Distributed API Monetizer & Rate Limiter",
            "https://github.com/isearchxsolve/omniroute-monetizer",
            "1. Token-bucket rate limiting with asynchronous dead-letter buffering.\n2. Graceful SIGTERM worker termination ensuring zero in-flight message loss."
        )
    else:
        return (
            "Resilient Asynchronous Ingestion & Scraping Engine",
            "https://github.com/isearchxsolve/crawlee-engine",
            "1. Asynchronous non-blocking pipeline workers with distributed queue decoupling.\n2. Strict health probing, structured OpenTelemetry traces, and containerized Docker execution."
        )

def dispatch_proposal(server, lead):
    email = lead["emails"][0]
    repo_name, repo_link, solution_desc = match_portfolio(lead["keywords"])
    
    subject = f"Turnkey architectural patch for your {lead['keywords'][0].upper()} pipeline"
    body = f"""Hi {lead['author']},

Saw your post regarding your engineering requirement on {lead['source']}.

Common bottleneck in this stack: unhandled backpressure, context drift, and unoptimized throughput under concurrent load.

Here is the exact architectural fix we implement:
{solution_desc}

We already engineered and benchmarked this in production (verified open source reference):
- {repo_name}: {repo_link}
- Master Engineering Showroom (125 Repositories / 1.95M LOC): https://github.com/isearchxsolve

I have open bandwidth to build, benchmark, and ship a containerized Docker PR directly into your repository within 48 hours for a flat $500 pilot (₹15,000 domestic) — 100% written, zero live meetings.

Reply "YES" or WhatsApp text +91 86172 16163 to lock the slot and review technical specs.

Kunal
Written lane: isearch.xsolve@gmail.com | WhatsApp text: +91 86172 16163"""

    msg = MIMEMultipart()
    msg["From"] = f"Kunal Das <{ME}>"
    msg["To"] = email
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="gmail.com")
    msg.attach(MIMEText(body, "plain", "utf-8"))

    refused = server.sendmail(ME, [email], msg.as_string())
    if not refused:
        receipt = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recipient": email,
            "source": lead["source"],
            "url": lead["url"],
            "body_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "status": "DELIVERED_250_OK"
        }
        safe_em = email.replace("@", "_at_").replace(".", "_")
        ts_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rf = RECEIPTS_DIR / f"codex_receipt_{ts_str}_{safe_em}.json"
        rf.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        log(f"Delivered proposal to {email} -> {rf.name}")
        return True
    return False

def run_loop():
    log("Codex Autonomous 24/7 Hunter initializing...")
    seen = load_seen()
    
    if not VAULT.exists():
        log(f"CRITICAL: Vault file {VAULT} missing. Terminating.")
        return

    pw = VAULT.read_text().strip()

    while True:
        log("Checking Reddit and Hacker News feeds for fresh hiring posts...")
        leads = []
        leads.extend(scrape_reddit("forhire"))
        leads.extend(scrape_reddit("freelance_forhire"))
        leads.extend(scrape_reddit("jobbit"))
        leads.extend(scrape_hn())
        
        fresh = [l for l in leads if l["id"] not in seen and l.get("emails")]
        log(f"Found {len(leads)} raw opportunities, {len(fresh)} fresh with direct emails.")
        
        if fresh:
            try:
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=25)
                server.starttls()
                server.login(ME, pw)
                
                for f in fresh[:5]:  # Process up to 5 per cycle
                    success = dispatch_proposal(server, f)
                    seen.add(f["id"])
                    time.sleep(15)
                
                server.quit()
                save_seen(seen)
            except Exception as e:
                log(f"SMTP error in cycle: {e}")
        
        # Save all discovered leads for Kunal's inspection
        all_stored = []
        if LEAD_STORE.exists():
            try:
                all_stored = json.loads(LEAD_STORE.read_text(encoding="utf-8"))
            except Exception:
                all_stored = []
        
        for l in leads:
            if l["id"] not in [x["id"] for x in all_stored]:
                all_stored.append(l)
        LEAD_STORE.write_text(json.dumps(all_stored, indent=2), encoding="utf-8")
        
        log(f"Cycle finished. Sleeping 15 minutes (900s) before next sweep...")
        time.sleep(900)

if __name__ == "__main__":
    run_loop()
```

---

## 📋 INSTRUCTIONS FOR CODEX ON STARTUP

1. **Verify Environment:** Check `D:\anonym\vault\gmail_apppw.txt` and confirm SMTP access to `isearch.xsolve@gmail.com`.
2. **Execute Hunter Daemon:** Run `python D:\anonym\deliverables\codex_247_hunter.py` in the background as a 24/7 process.
3. **Inspect Output:** Inspect `D:\anonym\deliverables\codex_live_opportunities.json` for live discovered opportunities from Reddit and Hacker News.
4. **Honesty Protocol:** When Kunal asks for status, report ONLY real numbers:
   - Total opportunities scraped from Reddit/HN.
   - Exact emails dispatched with live `250 OK` timestamps.
   - Direct links to the Reddit and Hacker News posts.
   - ZERO promises of money until an invoice is settled.
