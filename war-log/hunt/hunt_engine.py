#!/usr/bin/env python3
"""hunt_engine.py - WORLDWIDE HUNT ENGINE (Baba order 2026-09-28).

Mission: index the public web like a search engine and extract >=1,000,000 leads whose DNA is
perfect for the house assets (repo/code corpus, Kilo-Bridge/app-builder, voice clinic, docs).
Kernel-first: plain HTTP bytes over sockets, not app/browser automation. Robots-aware, polite,
honest UA. Defense-only: public pages only, no auth walls, no private data, no personal scraping
of non-business contacts. See war-log/roadmap/HUNT-ENGINE-1M-2026-09-28.md for the law.

DB: war-log/hunt/leads.db (SQLite)
Tables: leads, frontier, seen, runs, hosts

CLI:
  python hunt_engine.py add <url> [<url> ...]     seed the frontier
  python hunt_engine.py crawl --budget 200        fetch up to N pages (polite)
  python hunt_engine.py stats                     counts
  python hunt_engine.py export --bucket hot --limit 100 [--out f.csv]
  python hunt_engine.py clock                     who is in business hours right now
"""
import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse as up
import urllib.robotparser as rp
from datetime import datetime, timezone, timedelta

try:
    import requests
except Exception as exc:  # pragma: no cover
    print("hunt: requests missing:", exc)
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "leads.db")
LOG = os.path.join(HERE, "hunt.log")
UA = "KiloHuntBot/1.0 (+contact: isearch.xsolve@gmail.com; public business pages only)"
POLITE_SECONDS = 1.5
TIMEOUT = 20
MAX_BYTES = 800_000

# WhatsApp extraction lives in its own tested module (Baba order 2026-10-01: "the hunt should
# extract WhatsApp numbers"). Tiered by provenance: declared wa.me link > chat widget > tel:
# anchor > contextual digits > bare mention (never queued). See _test_wa_extract.py, 29/29.
sys.path.insert(0, HERE)
import wa_extract  # noqa: E402


# ---------------------------------------------------------------- DNA / scoring
DNA = {
    "ai_ml": r"\b(ai|a\.i\.|artificial intelligence|machine learning|ml|deep learning|"
             r"neural|llm|large language model|genai|gen-ai|generative|agent|agentic|rag|"
             r"embedding|vector database|inference|fine-?tun|foundation model|transformer|"
             r"gpu|cuda|pytorch|tensorflow|copilot|autonomous)\b",
    "corpus_need": r"\b(training data|dataset|datasets|data acquisition|data labeling|"
                   r"annotation|crawl|crawler|crawling|web scale|corpus|scrape|scraping|"
                   r"data collection|synthetic data|eval set|benchmark)\b",
    "hiring": r"\b(we are hiring|join our team|open roles|open positions|careers?|"
              r"apply now|now hiring|hiring engineers?)\b",
    "funding": r"\b(seed round|series [abc]|raised \$|raised \u20b9|backed by|valuation|"
               r"investors?|venture|vc-backed|yc [ws]\d{2})\b",
    "codebase": r"\b(open ?source|github|sdk|api docs|developer|framework|repository|repo)\b",
    "voice": r"\b(voice ai|voice agent|receptionist|call center|ivr|speech|tts|stt|asr|"
             r"transcri|telephony|sip|clinic|appointment|helpline)\b",
}
DNA_RE = {k: re.compile(v, re.I) for k, v in DNA.items()}

# ---------------------------------------------------------------- CONTACT QUALITY (2026-10-07)
# Provenance-gated emails + buyer intent classifier (war-log/hunt/contact_quality.py)
sys.path.insert(0, HERE)
import contact_quality as cq  # noqa: E402

# ---------------------------------------------------------------- OUR ASSET DNA
# Two-sided DNA: our asset fingerprint <-> the lead's need fingerprint (Baba 2026-09-28).
# match_score = sum of weights of the lead signals that our asset satisfies.
# Ground truth: roadman/ASSET-DNA-2026-09-28.md. D-drive = African diamond, never undersold.
# ask = rarity price spoken to a matched buyer; floor = comparable / risk-adjusted, INTERNAL ONLY.
ASSETS = {
    "corpus":   {"label": "Code corpus lots (60 T1, 9.4M LOC) - licensing only, ownership never sold",
                 "signals": {"corpus_need": 6, "ai_ml": 4, "funding": 3, "codebase": 1},
                 "ask": "$12k non-exclusive lot / $60k exclusive; portfolio premium",
                 "floor": "$12k non-excl (internal only)", "kind": "buyer"},
    "agent":    {"label": "ASES v3.1 (215 tests/61% cov) + NEON ARCHITECT v4.7 autonomous coding agents (crown jewels)",
                 "signals": {"ai_ml": 5, "codebase": 4, "hiring": 2, "funding": 2},
                 "ask": "$100k-200k non-excl / $250k-450k exclusive (ASES); $75k-120k / $200k-350k (NEON); integration $30k-60k",
                 "floor": "$75k non-excl (internal only)", "kind": "buyer"},
    "infra":    {"label": "omniroute-monetizer session-replay/orchestration (77k LOC) + SafeScreen ONNX moderation + war-pipe infra",
                 "signals": {"ai_ml": 4, "corpus_need": 2, "codebase": 3, "hiring": 1},
                 "ask": "$60k-150k non-excl / $150k-300k exclusive (omniroute); war-pipe $25k-50k / $150k-300k",
                 "floor": "$25k non-excl (internal only)", "kind": "buyer"},
    "builder":  {"label": "Self-healing app builder (emergentsh / idea-terminal / OMEGA)",
                 "signals": {"ai_ml": 4, "codebase": 3, "hiring": 3, "funding": 2},
                 "ask": "$20k-60k non-excl / $100k-250k exclusive",
                 "floor": "$20k non-excl (internal only)", "kind": "buyer"},
    "testauto": {"label": "OpenPath NL->Playwright test automation",
                 "signals": {"codebase": 4, "hiring": 3, "ai_ml": 2},
                 "ask": "$20k-50k non-excl / $80k-200k exclusive (post critical fixes)",
                 "floor": "$20k post-fix (internal only)", "kind": "buyer"},
    "voice":    {"label": "Voice-agent receptionist / clinic (Rs 15k-50k)",
                 "signals": {"voice": 5, "ai_ml": 1},
                 "ask": "Rs 15k-50k per build", "floor": "Rs 15k (internal only)", "kind": "buyer"},
    "film":     {"label": "GODSHAND / oioi AI film pipeline (free-tier, blueprint-first)",
                 "signals": {"voice": 3, "ai_ml": 4},
                 "ask": "$25k-40k non-excl code / $150k-400k exclusive (license cleared)",
                 "floor": "$25k non-excl (internal only)", "kind": "buyer"},
    "archive":  {"label": "timeofmylife digital life-archive provenance platform",
                 "signals": {"corpus_need": 3, "ai_ml": 3, "codebase": 2},
                 "ask": "$40k-80k exclusive (after security fixes)",
                 "floor": "$40k excl (internal only)", "kind": "buyer"},
    "bridge":   {"label": "Kilo-Bridge kit / app-builder (Rs 999-24,999)",
                 "signals": {"ai_ml": 3, "codebase": 3, "hiring": 2},
                 "ask": "Rs 999-24,999", "floor": "Rs 999 (internal only)", "kind": "buyer"},
    "docs":     {"label": "Documents / architecture / roadmap / proposals",
                 "signals": {"ai_ml": 3, "hiring": 2, "funding": 2},
                 "ask": "Rs 8k-15k", "floor": "Rs 8k (internal only)", "kind": "buyer"},
    "trading":  {"label": "Fail-closed trading engine (crypto-trader / solana) - engineering IP only",
                 "signals": {"ai_ml": 3, "codebase": 3},
                 "ask": "$75k-150k exclusive", "floor": "$75k excl (internal only)", "kind": "buyer"},
}

BAD_EMAIL = re.compile(r"(noreply|no-reply|donotreply|example\.|test@|sentry|wixpress|"
                       r"^(you|your|name|user|email|someone)@|@(domain|email|example|yourdomain)\."
                       r"|@\d|\.png|\.jpg|\.jpeg|\.gif|\.webp|\.svg|\.css|\.js$)", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# Indian mobiles and explicit international numbers. Bare 10-digit Indian
# mobiles count so a contact page with no email still yields a WhatsApp target.
PHONE_RE = re.compile(
    r"(?<!\d)(\+91[\s-]*[6-9](?:[\s-]?\d){9}|\+[1-9](?:[\s-]?\d){7,14}|(?<![+\d])[6-9]\d{9})(?!\d)"
)
ORG_EMAIL_HINT = re.compile(r"^(info|hello|contact|hi|sales|team|founders?|founder|"
                            r"biz|business|partners?|bd|support|admin|careers?|jobs|press)@", re.I)
PERSONAL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
                    "protonmail.com", "proton.me", "aol.com", "gmx.com", "mail.com", "zoho.com"}
SKIP_HOSTS = re.compile(r"(facebook|twitter|x\.com|instagram|youtube|tiktok|pinterest|"
                        r"doubleclick|google-analytics|googletagmanager|gravatar|"
                        r"wp\.com|wixstatic|cloudflare|gstatic)\.", re.I)
DROP_FILE = re.compile(r"\.(png|jpe?g|gif|webp|svg|css|js|ico|woff2?|ttf|eot|mp4|mp3|"
                       r"zip|gz|tgz|pdf|xml|rss|json)$", re.I)
GOOD_PATH = re.compile(r"(about|contact|team|company|careers?|jobs|imprint|impressum|"
                       r"privacy|pricing|docs|developers?|api|blog|product|platform)", re.I)

# global clock: city -> utc offset hours (approx, DST-agnostic)
CLOCK = {
    "US-East": -4, "US-Central": -5, "US-Mountain": -6, "US-Pacific": -7,
    "Brazil": -3, "UK": 1, "EU-Central": 2, "EU-East": 3, "UAE": 4,
    "India": 5.5, "Singapore": 8, "China": 8, "Japan": 9, "Australia-East": 10,
    "Korea": 9, "Israel": 3, "Canada-East": -4, "Mexico": -6,
}


def now_utc():
    return datetime.now(timezone.utc)


def log(msg):
    line = f"{now_utc().isoformat()} {msg}"
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------- db
SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  org TEXT, domain TEXT, email TEXT UNIQUE, email_kind TEXT,
  linkedin TEXT, twitter TEXT, github TEXT, channels TEXT,
  dna TEXT, score INTEGER DEFAULT 0, bucket TEXT,
  asset TEXT, match_score INTEGER DEFAULT 0,
  source_url TEXT, snippet TEXT, first_seen TEXT, last_seen TEXT, status TEXT DEFAULT 'new'
);
CREATE TABLE IF NOT EXISTS frontier (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT UNIQUE, host TEXT, depth INTEGER DEFAULT 0,
  priority INTEGER DEFAULT 0, status TEXT DEFAULT 'queued',
  http_status INTEGER, note TEXT, added_at TEXT, fetched_at TEXT
);
CREATE TABLE IF NOT EXISTS seen (url TEXT PRIMARY KEY, at TEXT);
CREATE TABLE IF NOT EXISTS hosts (
  host TEXT PRIMARY KEY, last_hit REAL DEFAULT 0, robots TEXT, robots_at REAL DEFAULT 0,
  fetched INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started TEXT, ended TEXT, fetched INTEGER, found INTEGER, note TEXT
);
CREATE INDEX IF NOT EXISTS ix_leads_score ON leads(score DESC);
CREATE INDEX IF NOT EXISTS ix_leads_bucket ON leads(bucket);
CREATE INDEX IF NOT EXISTS ix_frontier_status ON frontier(status);
CREATE TABLE IF NOT EXISTS wa_targets (
  phone TEXT PRIMARY KEY,
  org TEXT, domain TEXT, source_url TEXT, snippet TEXT, first_seen TEXT,
  country TEXT, kind TEXT, confidence INTEGER DEFAULT 0, evidence TEXT,
  score INTEGER DEFAULT 0, dna TEXT, asset TEXT,
  verified TEXT, verified_at TEXT, receipt TEXT, status TEXT DEFAULT 'new'
);
"""


def db():
    conn = sqlite3.connect(DB, timeout=30)
    conn.executescript(SCHEMA)
    migrate(conn)
    conn.commit()
    return conn


def migrate(conn):
    """Add columns that older leads.db copies lack (CREATE TABLE IF NOT EXISTS never ALTERs)."""
    have = {r[1] for r in conn.execute("PRAGMA table_info(leads)")}
    for col, ddl in (("asset", "TEXT"), ("match_score", "INTEGER DEFAULT 0"), ("phone", "TEXT"),
                     ("email_provenance", "TEXT"), ("email_send_gate", "TEXT"),
                     ("buyer_intent", "TEXT"), ("buyer_intent_evidence", "TEXT")):
        if col not in have:
            conn.execute(f"ALTER TABLE leads ADD COLUMN {col} {ddl}")
    have_wa = {r[1] for r in conn.execute("PRAGMA table_info(wa_targets)")}
    for col, ddl in (("country", "TEXT"), ("kind", "TEXT"), ("confidence", "INTEGER DEFAULT 0"),
                     ("evidence", "TEXT"), ("score", "INTEGER DEFAULT 0"), ("dna", "TEXT"),
                     ("asset", "TEXT"), ("verified", "TEXT"), ("verified_at", "TEXT"),
                     ("receipt", "TEXT"), ("status", "TEXT DEFAULT 'new'")):
        if col not in have_wa:
            conn.execute(f"ALTER TABLE wa_targets ADD COLUMN {col} {ddl}")



def norm_url(base, href):
    try:
        u = up.urljoin(base, href.strip())
        p = up.urlsplit(u)
        if p.scheme not in ("http", "https"):
            return None
        host = p.netloc.lower().split(":")[0]
        if not host or SKIP_HOSTS.search(host):
            return None
        frag = up.urlunsplit((p.scheme, p.netloc.lower(), p.path or "/", p.query, ""))
        return frag
    except Exception:
        return None


def host_of(url):
    return up.urlsplit(url).netloc.lower().split(":")[0]


def add_urls(conn, urls, depth=0, priority=0):
    added = 0
    for u in urls:
        u = u.strip()
        if not u:
            continue
        if not u.startswith("http"):
            u = "https://" + u
        p = up.urlsplit(u)
        host = p.netloc.lower().split(":")[0]
        if not host:
            continue
        # Baba's cash order 2026-09-30: Indian wounds first - India is the lane where money
        # can land today (UPI, 50% advance, written-only). Indian hosts get front-of-queue.
        if host.endswith((".in", ".co.in", ".nom.in")):
            priority = max(priority, 6)
        try:
            conn.execute(
                "INSERT OR IGNORE INTO frontier(url,host,depth,priority,added_at) VALUES(?,?,?,?,?)",
                (u, host, depth, priority, now_utc().isoformat()))
            added += conn.total_changes and 0 or 0
        except sqlite3.Error:
            pass
    conn.commit()
    return added


# ---------------------------------------------------------------- fetch / robots
def robots_ok(conn, url):
    host = host_of(url)
    row = conn.execute("SELECT robots, robots_at FROM hosts WHERE host=?", (host,)).fetchone()
    txt, at = (row if row else (None, 0))
    if txt is None or (time.time() - (at or 0)) > 86400:
        try:
            r = requests.get(f"https://{host}/robots.txt", headers={"User-Agent": UA},
                             timeout=TIMEOUT)
            txt = r.text[:20000] if r.status_code == 200 else ""
        except Exception:
            txt = ""
        conn.execute("INSERT INTO hosts(host,robots,robots_at) VALUES(?,?,?) "
                     "ON CONFLICT(host) DO UPDATE SET robots=excluded.robots,"
                     "robots_at=excluded.robots_at", (host, txt, time.time()))
        conn.commit()
    if not txt:
        return True
    r = rp.RobotFileParser()
    r.parse(txt.splitlines())
    try:
        return r.can_fetch(UA, url)
    except Exception:
        return True


def polite(conn, url):
    host = host_of(url)
    row = conn.execute("SELECT last_hit FROM hosts WHERE host=?", (host,)).fetchone()
    last = row[0] if row else 0
    wait = POLITE_SECONDS - (time.time() - (last or 0))
    if wait > 0:
        time.sleep(min(wait, 5))
    conn.execute("INSERT INTO hosts(host,last_hit) VALUES(?,?) "
                 "ON CONFLICT(host) DO UPDATE SET last_hit=excluded.last_hit",
                 (host, time.time()))
    conn.commit()


def fetch(url):
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en"},
                         timeout=TIMEOUT, allow_redirects=True, stream=True)
        ctype = r.headers.get("Content-Type", "")
        if "html" not in ctype and "text" not in ctype and "json" not in ctype:
            r.close()
            return r.status_code, "", ctype
        chunks, total = [], 0
        for chunk in r.iter_content(65536):
            chunks.append(chunk)
            total += len(chunk)
            if total >= MAX_BYTES:
                break
        r.close()
        return r.status_code, b"".join(chunks).decode("utf-8", "replace"), ctype
    except requests.RequestException as exc:
        return 0, "", str(exc)[:120]


# ---------------------------------------------------------------- extract
def extract(html, url):
    """Return dict with emails, links, org, socials, dna, snippet, buyer_intent."""
    out = {"emails": [], "phones": [], "wa": [], "links": [], "org": "", "linkedin": "", "twitter": "",
           "github": "", "dna": [], "snippet": "", "buyer_intent": "NO_EXPLICIT_NEED", "buyer_intent_evidence": ""}
    if not html:
        return out
    # WhatsApp numbers, tiered by provenance. out["phones"] stays the queueable subset only,
    # so nothing that is a bare prose mention can ever reach a send queue.
    wa = wa_extract.extract_whatsapp(html, host_of(url))
    out["wa"] = wa
    out["phones"] = [r["phone"] for r in wa_extract.queueable(wa)]

    # CONTACT QUALITY: provenance-gated emails + buyer intent (2026-10-07)
    cq_emails = cq.extract_public_emails(html, url)
    out["emails"] = [e["email"] for e in cq_emails]
    out["email_provenance"] = {e["email"]: e["provenance"] for e in cq_emails}
    out["email_kind_cq"] = {e["email"]: e["kind"] for e in cq_emails}
    out["email_send_gate"] = {e["email"]: e["send_gate"] for e in cq_emails}

    host = host_of(url)
    title = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if m:
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
    og = re.search(r'property=["\']og:site_name["\'][^>]*content=["\']([^"\']+)', html, re.I)
    out["org"] = (og.group(1).strip() if og else title)[:160]

    li = re.search(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(company|in)/([A-Za-z0-9\-_%]+)", html, re.I)
    if li:
        out["linkedin"] = f"https://www.linkedin.com/{li.group(1)}/{li.group(2)}"
    tw = re.search(r"https?://(?:www\.)?(?:twitter|x)\.com/([A-Za-z0-9_]{2,20})", html, re.I)
    if tw and tw.group(1).lower() not in ("intent", "share", "home"):
        out["twitter"] = f"https://x.com/{tw.group(1)}"
    gh = re.search(r"https?://(?:www\.)?github\.com/([A-Za-z0-9\-_.]+)", html, re.I)
    if gh and gh.group(1).lower() not in ("features", "pricing", "about", "login", "join"):
        out["github"] = f"https://github.com/{gh.group(1)}"

    for k, rx in DNA_RE.items():
        if rx.search(html):
            out["dna"].append(k)

    # links for the frontier (same host, good paths)
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            u = norm_url(url, a["href"])
            if u:
                out["links"].append(u)
        if not out["org"]:
            h1 = soup.find(["h1", "h2"])
            if h1:
                out["org"] = h1.get_text(" ", strip=True)[:160]
        text = soup.get_text(" ", strip=True)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", html)
    for rx in DNA_RE.values():
        m = rx.search(text)
        if m:
            s = max(0, m.start() - 60)
            out["snippet"] = re.sub(r"\s+", " ", text[s:m.start() + 120]).strip()[:220]
            break

    # BUYER INTENT CLASSIFIER (2026-10-07)
    intent, evidence = cq.buyer_intent(text)
    out["buyer_intent"] = intent
    out["buyer_intent_evidence"] = evidence

    return out


def score_dna(dna):
    s = 0
    if "ai_ml" in dna:
        s += 3
    if "corpus_need" in dna:
        s += 5
    if "voice" in dna:
        s += 3
    if "hiring" in dna:
        s += 2
    if "funding" in dna:
        s += 4
    if "codebase" in dna:
        s += 1
    return s


def bucket_for(score):
    if score >= 10:
        return "hot"
    if score >= 6:
        return "warm"
    if score >= 3:
        return "cool"
    return "raw"


def email_kind(email, domain):
    return "role" if ORG_EMAIL_HINT.search(email) else ("personal" if domain in PERSONAL_DOMAINS else "direct")


def match_assets(dna):
    """Return (best_asset, match_score, all_matches) for a lead's DNA signals."""
    dset = set(dna)
    best, best_score, allm = "", 0, []
    for key, a in ASSETS.items():
        s = sum(w for sig, w in a["signals"].items() if sig in dset)
        if s > 0:
            allm.append(f"{key}:{s}")
        if s > best_score:
            best, best_score = key, s
    return best, best_score, ";".join(allm)


def store_lead(conn, url, ex):
    domain = host_of(url)
    ts = now_utc().isoformat()
    n = 0
    # page-level score, computed once so a page with NO email but a published WhatsApp
    # number still carries its DNA score (that lead used to be scored only per-email)
    _asset_best, _ms_best, _ = match_assets(ex["dna"])
    s_best = score_dna(ex["dna"]) + _ms_best
    for e in ex["emails"]:
        d = e.split("@")[-1]
        # Use contact_quality provenance/kind/gate if available, fallback to old logic
        kind = ex.get("email_kind_cq", {}).get(e) or email_kind(e, d)
        provenance = ex.get("email_provenance", {}).get(e, "")
        send_gate = ex.get("email_send_gate", {}).get(e, "")
        asset, ms, _allm = match_assets(ex["dna"])
        s = score_dna(ex["dna"]) + ms + (2 if kind == "direct" else 1)
        phone = ex.get("phones", [""])[0] if ex.get("phones") else ""
        ch = "email,linkedin" + (",whatsapp" if phone else "")
        b = bucket_for(s)
        try:
            conn.execute(
                "INSERT INTO leads(org,domain,email,email_kind,email_provenance,email_send_gate,"
                "buyer_intent,buyer_intent_evidence,linkedin,twitter,github,channels,dna,"
                "score,bucket,asset,match_score,source_url,snippet,first_seen,last_seen,phone) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ex["org"], d, e, kind, provenance, send_gate,
                 ex.get("buyer_intent", "NO_EXPLICIT_NEED"),
                 ex.get("buyer_intent_evidence", ""),
                 ex["linkedin"], ex["twitter"], ex["github"],
                 ch, ",".join(ex["dna"]), s, b, asset, ms, url, ex["snippet"], ts, ts, phone))
            n += 1
        except sqlite3.IntegrityError:
            conn.execute(
                "UPDATE leads SET last_seen=?, phone=COALESCE(NULLIF(phone,''), ?), "
                "email_kind=?, email_provenance=?, email_send_gate=?, "
                "buyer_intent=?, buyer_intent_evidence=? WHERE email=?",
                (ts, phone, kind, provenance, send_gate,
                 ex.get("buyer_intent", "NO_EXPLICIT_NEED"),
                 ex.get("buyer_intent_evidence", ""), e))
    # LinkedIn hunt lane: preserve an explicit company need even when the page
    # publishes no email or phone. Previously these pages vanished before the
    # DNA matcher could see them. The email remains NULL; company/person review
    # is a separate gate and no contact action is triggered here.
    if ex.get("buyer_intent") == "EXPLICIT_NEED" and ex.get("buyer_intent_evidence"):
        asset, ms, _allm = match_assets(ex.get("dna", []))
        existing = conn.execute(
            "SELECT id FROM leads WHERE lower(domain)=lower(?) AND source_url=? "
            "AND (email IS NULL OR email='') LIMIT 1", (domain, url)).fetchone()
        if existing:
            conn.execute(
                "UPDATE leads SET org=?,linkedin=?,twitter=?,github=?,channels=?,dna=?,"
                "score=?,bucket=?,asset=?,match_score=?,snippet=?,last_seen=?,"
                "buyer_intent='EXPLICIT_NEED',buyer_intent_evidence=? WHERE id=?",
                (ex.get("org") or "", ex.get("linkedin") or "", ex.get("twitter") or "",
                 ex.get("github") or "", "linkedin" if ex.get("linkedin") else "company-site",
                 ",".join(ex.get("dna", [])), score_dna(ex.get("dna", [])) + ms,
                 bucket_for(score_dna(ex.get("dna", [])) + ms), asset, ms,
                 ex.get("snippet") or "", ts, ex["buyer_intent_evidence"], existing[0]))
        else:
            conn.execute(
                "INSERT INTO leads(org,domain,email,linkedin,twitter,github,channels,dna,"
                "score,bucket,asset,match_score,source_url,snippet,first_seen,last_seen,"
                "buyer_intent,buyer_intent_evidence) VALUES(?,?,NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ex.get("org") or "", domain, ex.get("linkedin") or "", ex.get("twitter") or "",
                 ex.get("github") or "", "linkedin" if ex.get("linkedin") else "company-site",
                 ",".join(ex.get("dna", [])), score_dna(ex.get("dna", [])) + ms,
                 bucket_for(score_dna(ex.get("dna", [])) + ms), asset, ms, url,
                 ex.get("snippet") or "", ts, ts, "EXPLICIT_NEED", ex["buyer_intent_evidence"]))
            n += 1

    for w in ex.get("wa") or []:
        if w["confidence"] < 4:
            continue                      # a bare prose mention is not a target, it is a guess
        try:
            conn.execute(
                "INSERT OR IGNORE INTO wa_targets(phone,org,domain,source_url,snippet,first_seen,"
                "country,kind,confidence,evidence,score,dna,asset) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (w["phone"], ex.get("org") or "", domain, url, (ex.get("snippet") or "")[:220], ts,
                 w["country"], w["kind"], w["confidence"], w["evidence"], s_best,
                 ",".join(ex["dna"]), _asset_best))
            n += 1
        except sqlite3.OperationalError:
            pass
    conn.commit()
    return n


# ---------------------------------------------------------------- crawl
def crawl(conn, budget):
    run = conn.execute("INSERT INTO runs(started,fetched,found) VALUES(?,0,0)",
                       (now_utc().isoformat(),))
    conn.commit()
    run_id = run.lastrowid
    fetched = found = 0
    while fetched < budget:
        row = conn.execute("SELECT id,url,depth,priority FROM frontier WHERE status='queued' "
                           "ORDER BY priority DESC, id ASC LIMIT 1").fetchone()
        if not row:
            break
        fid, url, depth, prio = row
        if url in {r[0] for r in conn.execute("SELECT url FROM seen")}:
            conn.execute("UPDATE frontier SET status='seen' WHERE id=?", (fid,))
            conn.commit()
            continue
        if not robots_ok(conn, url):
            conn.execute("UPDATE frontier SET status='robots' WHERE id=?", (fid,))
            conn.commit()
            continue
        polite(conn, url)
        status, html, ctype = fetch(url)
        ex = extract(html, url) if status and html else {
            "emails": [], "phones": [], "wa": [], "links": [], "org": "",
            "linkedin": "", "twitter": "", "github": "", "dna": [], "snippet": ""}
        # THE OLD BUG: this stored only when an email existed, so every page that published
        # a WhatsApp number and no email was discarded - exactly the SME pages we need.
        if (ex["emails"] or ex["phones"] or
                (ex.get("buyer_intent") == "EXPLICIT_NEED" and ex.get("buyer_intent_evidence"))):
            n = store_lead(conn, url, ex)
        else:
            n = 0
        found += n
        conn.execute("UPDATE frontier SET status='done',http_status=?,fetched_at=? WHERE id=?",
                     (status, now_utc().isoformat(), fid))
        conn.execute("INSERT OR IGNORE INTO seen(url,at) VALUES(?,?)",
                     (url, now_utc().isoformat()))
        # enqueue child links (same host, good paths preferred, depth<=2)
        if depth < 2:
            same = [u for u in ex["links"] if host_of(u) == host_of(url)]
            good = [u for u in same if GOOD_PATH.search(u)][:8]
            rest = [u for u in same if u not in good][:4]
            add_urls(conn, good + rest, depth + 1, max(prio - 1, 0))
        fetched += 1
        conn.execute("UPDATE hosts SET fetched=fetched+1 WHERE host=?", (host_of(url),))
        conn.commit()
        if fetched % 25 == 0:
            log(f"crawl {fetched}/{budget} fetched, {found} leads")
    conn.execute("UPDATE runs SET ended=?,fetched=?,found=? WHERE id=?",
                 (now_utc().isoformat(), fetched, found, run_id))
    conn.commit()
    log(f"crawl end: fetched={fetched} leads={found}")
    return fetched, found


# ---------------------------------------------------------------- cli
def cmd_stats(conn):
    def one(q):
        return conn.execute(q).fetchone()[0]
    print("leads total :", one("SELECT COUNT(*) FROM leads"))
    for b in ("hot", "warm", "cool", "raw"):
        print(f"  bucket {b:<5}:", one(f"SELECT COUNT(*) FROM leads WHERE bucket='{b}'"))
    print("frontier    :", dict(conn.execute(
        "SELECT status,COUNT(*) FROM frontier GROUP BY status").fetchall()))
    print("hosts fetched:", one("SELECT COUNT(*) FROM hosts WHERE fetched>0"))


def cmd_refresh_company_sites(conn, limit):
    """Requeue a small, DNA-ranked set of official homepages for need evidence.

    This is intentionally bounded and does not fetch anything. Run crawl with a
    separate budget after reviewing the queued count.
    """
    rows = conn.execute(
        "SELECT lower(domain),MAX(COALESCE(match_score,0)),MAX(COALESCE(score,0)) "
        "FROM leads WHERE domain IS NOT NULL AND domain<>'' "
        "GROUP BY lower(domain) ORDER BY 2 DESC,3 DESC LIMIT ?", (limit,)).fetchall()
    queued = 0
    for raw_domain, match_score, _score in rows:
        host = host_of("https://" + (raw_domain or ""))
        if not host or not re.fullmatch(r"[a-z0-9.-]+", host) or ".." in host:
            continue
        url = "https://" + host + "/"
        priority = min(10, max(1, int(match_score or 0) + 3))
        exists = conn.execute("SELECT id FROM frontier WHERE url=?", (url,)).fetchone()
        if exists:
            conn.execute("DELETE FROM seen WHERE url=?", (url,))
            conn.execute("UPDATE frontier SET status='queued',depth=0,priority=?,note='DNA need-evidence refresh' WHERE id=?",
                         (priority, exists[0]))
        else:
            add_urls(conn, [url], depth=0, priority=priority)
        queued += 1
    conn.commit()
    print("company homepages requeued:", queued)
    print("crawl separately with: py hunt_engine.py crawl --budget N")


def cmd_export(conn, bucket, limit, out):
    rows = conn.execute(
        "SELECT org,email,email_kind,email_provenance,email_send_gate,domain,asset,match_score,"
        "buyer_intent,buyer_intent_evidence,dna,score,bucket,linkedin,twitter,github,source_url,snippet "
        "FROM leads WHERE bucket=? ORDER BY score DESC LIMIT ?",
        (bucket, limit)).fetchall()
    cols = ["org", "email", "email_kind", "email_provenance", "email_send_gate", "domain",
            "asset", "asset_ask", "match_score", "buyer_intent", "buyer_intent_evidence",
            "dna", "score", "bucket", "linkedin", "twitter", "github", "source_url", "snippet"]
    out = out or os.path.join(HERE, f"export-{bucket}.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            ask = ASSETS.get(r[6], {}).get("ask", "")
            w.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6], ask] + list(r[7:]))
    print(f"wrote {out} rows={len(rows)}")


def cmd_wa_queue(conn, min_conf=5, out=None, verified_only=False):
    """Export the WhatsApp send queue: provenance-gated, deduped, evidence per row.

    Baba's order 2026-10-01 made WhatsApp the extraction target; this is the gate that keeps
    it honest. A row is only as good as its source_url (openable evidence) and its verified
    column (the phone lane must confirm CHAT_READY per number before anything is sent - the
    2026-09-30 probe found 0/5 scraped numbers on WhatsApp, so an unverified number never sends).
    """
    out = out or os.path.join(HERE, "wa-sendable.csv" if verified_only else "wa-queue.csv")
    # The documentary gate, stated in SQL and not just in prose: rows whose source stopped proving
    # them (re-extraction found the number no longer on the owner's page, or the site is gone) must
    # never ride into a queue on their old confidence number.
    where = ("t.confidence>=? AND t.status NOT IN ('dead','stale-source','absent-on-page') "
             "AND t.kind IS NOT NULL AND t.kind!=''")
    # SECOND gate, added 2026-10-01 after 3 of 10 phone cycles were burned on 403 pages: if a row's
    # source page is tracked in wa_seed it must have ANSWERED HTTP 200 when last probed (s.alive=1),
    # unless the phone itself already proved the number (verified='yes' is live evidence, stronger
    # than any page probe). Rows born from a crawl today (no wa_seed row) are fresh by construction.
    where += " AND (t.verified='yes' OR s.alive=1 OR s.url IS NULL)"
    base = ("confidence>=? AND status NOT IN ('dead','stale-source','absent-on-page') "
            "AND kind IS NOT NULL AND kind!=''")
    # SECOND gate, added 2026-10-01 after 3 of 10 phone cycles were burned on 403 pages: if a row's
    # source page is tracked in wa_seed it must have ANSWERED HTTP 200 when last probed (s.alive=1),
    # unless the phone itself already proved the number (verified='yes' is live evidence, stronger
    # than any page probe). Rows born from a crawl today (no wa_seed row) are fresh by construction.
    alive_gate = " AND (verified='yes' OR s.alive=1 OR s.url IS NULL)"
    args = [min_conf]
    if verified_only:
        base += " AND verified='yes'"
    has_seed = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='wa_seed'").fetchone()
    if not has_seed:
        # no seed table yet = no page-probe data at all; the gate cannot demand s.alive, and says so
        # rather than silently passing every unprobed row as if it had been checked.
        print("NOTE: table wa_seed does not exist yet - the alive-probe gate is INACTIVE for this "
              "export. Treat every unverified row as unproven (run _wa_seed_in.py then "
              "_wa_alive_probe.py).")
        sql = ("SELECT phone, org, domain, source_url, kind, confidence, country, score, dna, asset, "
               "snippet, verified, verified_at FROM wa_targets WHERE " + base + " "
               "ORDER BY country='IN' DESC, confidence DESC, score DESC")
    else:
        sel = ["t." + c for c in ("phone", "org", "domain", "source_url", "kind", "confidence",
                                  "country", "score", "dna", "asset", "snippet", "verified",
                                  "verified_at")]
        sql = ("SELECT " + ", ".join(sel) + " FROM wa_targets t "
               "LEFT JOIN wa_seed s ON s.url = t.source_url WHERE "
               + base.replace("confidence", "t.confidence").replace("status", "t.status")
                   .replace("kind", "t.kind").replace("verified", "t.verified") + alive_gate + " "
               "ORDER BY t.country='IN' DESC, t.confidence DESC, t.score DESC")
    rows = conn.execute(sql, args).fetchall()
    cols = ["phone", "org", "domain", "source_url", "kind", "confidence", "country", "score",
            "dna", "asset", "snippet", "verified", "verified_at"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow(r)
    in_n = sum(1 for r in rows if r[6] == "IN")
    dec = sum(1 for r in rows if r[4] == "declared")
    ver = sum(1 for r in rows if (r[11] or "") == "yes")
    print(f"wrote {out} rows={len(rows)}  India={in_n}  declared-tier={dec}  phone-verified={ver}")
    if ver == 0:
        print("GATE: phone-verified=0 means NOTHING here may be sent yet - each number must be "
              "confirmed CHAT_READY on the phone lane first (invite-ban law).")
    else:
        print(f"GATE: {ver} row(s) carry verified=yes and an evidence receipt - those, and only "
              f"those, are ready for a drafted message under Baba's eye.")


def cmd_assets():
    print(f"{'key':<9} {'asks (rarity price)':<52} signals")
    for k, a in ASSETS.items():
        print(f"{k:<9} {a['ask']:<52} {','.join(a['signals'])}")
    print(f"\nlegend: {len(ASSETS)} stones. floor values are INTERNAL ONLY (ASSET-DNA doc).")


def cmd_clock(_conn):
    h = now_utc().hour + now_utc().minute / 60
    print(f"UTC now {now_utc().isoformat(timespec='minutes')}  (IST {(h + 5.5) % 24:.1f})")
    print("region        local   business-hours")
    for region, off in sorted(CLOCK.items(), key=lambda kv: kv[1]):
        loc = (h + off) % 24
        ok = 9 <= loc <= 18
        print(f"  {region:<14} {loc:5.1f}   {'SEND NOW' if ok else '-'}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("add"); p.add_argument("urls", nargs="+")
    p = sub.add_parser("add-file"); p.add_argument("path")
    p = sub.add_parser("crawl"); p.add_argument("--budget", type=int, default=100)
    p = sub.add_parser("refresh-company-sites")
    p.add_argument("--limit", type=int, default=50,
                   help="maximum distinct official homepages to requeue (default: 50)")
    sub.add_parser("stats")
    p = sub.add_parser("export")
    p.add_argument("--bucket", default="hot")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--out")
    sub.add_parser("clock")
    p = sub.add_parser("wa-queue")
    p.add_argument("--min-conf", type=int, default=5)
    p.add_argument("--verified-only", action="store_true")
    p.add_argument("--out")
    sub.add_parser("assets")
    a = ap.parse_args()
    conn = db()
    if a.cmd == "add":
        add_urls(conn, a.urls, priority=5)
        print("frontier queued:", conn.execute(
            "SELECT COUNT(*) FROM frontier WHERE status='queued'").fetchone()[0])
    elif a.cmd == "add-file":
        with open(a.path, encoding="utf-8") as fh:
            urls = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
        add_urls(conn, urls, priority=5)
        print("frontier queued:", conn.execute(
            "SELECT COUNT(*) FROM frontier WHERE status='queued'").fetchone()[0])
    elif a.cmd == "crawl":
        crawl(conn, a.budget)
    elif a.cmd == "refresh-company-sites":
        cmd_refresh_company_sites(conn, max(1, min(a.limit, 500)))
    elif a.cmd == "stats":
        cmd_stats(conn)
    elif a.cmd == "export":
        cmd_export(conn, a.bucket, a.limit, a.out)
    elif a.cmd == "clock":
        cmd_clock(conn)
    elif a.cmd == "assets":
        cmd_assets()
    elif a.cmd == "wa-queue":
        cmd_wa_queue(conn, a.min_conf, a.out, a.verified_only)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
