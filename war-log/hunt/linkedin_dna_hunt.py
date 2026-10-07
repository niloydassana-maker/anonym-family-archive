#!/usr/bin/env python3
"""Strict, evidence-first company-to-repo gate for LinkedIn connection notes.

Reads only the local hunt database and repo catalog. It does not browse, send,
or automate LinkedIn. Repo similarity is a discovery hint, never proof of need.
Every note-ready lead needs a fresh, first-party explicit need, a strong direct
repo match, and a separately verified decision-maker/profile detail.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
DB = HERE / "leads.db"
CATALOG = HERE / "repo-verticals.json"
OUT = HERE / "linkedin-dna-hunt.csv"
REVIEW = HERE / "linkedin-dna-human-review.csv"
CONTACTED = HERE / "linkedin-dna-outreach.csv"
MAX_AGE_DAYS = 30

STOP = set("""about above after again against all also any because been before being
below between both but can cannot could does doing down during each every few first
from further have having here hers herself him himself itself just last more most
much must neither nor now only other others our ours ourselves out over own same she
should some such than that the their theirs them themselves then there these they
this those through under until very was were what when where which while who whom
why will with your yours yourself using used use one two like get got make made may
might company team looking seeking need needs help with build building developer
engineer agency prototype mvp app software solution vendor tool we our i am are""".split())
CODE_NOISE = set("""class classes complete framework function functions import return
string strings object objects method methods member members package packages interface
interfaces instance variable variables callback callbacks parameter parameters argument
arguments boolean integer float arrays null true false self this get set list dict
value values type types build built service platform system systems product products
project projects company business developer engineering team application applications""".split())
JOBSEEKER = re.compile(r"\b(open to work|seeking opportunities|looking for (a )?(job|role|position)|actively seeking (employment|a role|a position))\b", re.I)
DECISION = re.compile(r"\b(founder|co-founder|chief executive|\bceo\b|\bcto\b|vp engineering|head of engineering)\b", re.I)
EXPLICIT = re.compile(
    r"\b(?:i|we|our team|our company)\s+(?:are |am |need |want |seek(?:ing)? |looking for |struggling with |cannot find |can't find )"
    r"[^.!?\n]{0,180}\b(?:developer|engineer|agency|prototype|mvp|app|software|automation|dataset|"
    r"training data|voice assistant|integration|consultant|vendor|tool|platform|pipeline)\b",
    re.I,
)


def tokens(text: str) -> set[str]:
    return {x for x in re.findall(r"[a-z][a-z0-9+#.-]{2,}", (text or "").lower())
            if x not in STOP and x not in CODE_NOISE}


def norm_domain(value: str) -> str:
    value = (value or "").strip().lower()
    if "://" not in value:
        value = "//" + value
    host = (urlsplit(value).hostname or "").lower().strip(".")
    return host[4:] if host.startswith("www.") else host


def same_company_source(domain: str, source: str) -> bool:
    host = norm_domain(source)
    domain = norm_domain(domain)
    return bool(host and domain and (host == domain or host.endswith("." + domain)))


def valid_person_profile(url: str) -> bool:
    parsed = urlsplit(url or "")
    return parsed.hostname in {"linkedin.com", "www.linkedin.com"} and parsed.path.startswith("/in/")


def date_age(value: str) -> int | None:
    if not value:
        return None
    try:
        stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=dt.timezone.utc)
        return max(0, (dt.datetime.now(dt.timezone.utc) - stamp.astimezone(dt.timezone.utc)).days)
    except (ValueError, TypeError):
        return None


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    # Ignore infrastructure, snapshots, and packaging stubs as commercial assets.
    catalog = {k: v for k, v in catalog.items()
               if k not in {"anonym-family-archive", "war-pipe", "for-zipping"}
               and not k.startswith(("state-", "sale-", "_"))}
    repo_df = Counter(t for repo in catalog.values() for t in set(repo.get("tokens", [])))
    outreach = load_csv(CONTACTED)
    contacted = {norm_domain(r.get("domain", "")) for r in outreach
                 if (r.get("verdict", "").upper() in {"SENT", "PENDING", "ACCEPTED"})}
    human_rows = load_csv(REVIEW)
    humans = {norm_domain(r.get("domain", "")): r for r in human_rows if r.get("domain")}

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    leads = con.execute("""SELECT org,domain,linkedin,source_url,snippet,buyer_intent,
        buyer_intent_evidence,last_seen FROM leads
        WHERE domain IS NOT NULL AND domain<>''""").fetchall()
    con.close()

    # Collapse duplicate contacts/rows to one company, preserving the freshest evidence row.
    by_company: dict[str, sqlite3.Row] = {}
    for lead in leads:
        dom = norm_domain(lead["domain"])
        if not dom:
            continue
        old = by_company.get(dom)
        if old is None or (lead["last_seen"] or "") > (old["last_seen"] or ""):
            by_company[dom] = lead

    output = []
    for domain, lead in by_company.items():
        evidence = (lead["buyer_intent_evidence"] or "").strip()
        source = lead["source_url"] or ""
        age = date_age(lead["last_seen"] or "")
        reasons = []
        if domain in contacted:
            reasons.append("already contacted on LinkedIn")
        if not evidence:
            reasons.append("no captured explicit-need evidence")
        elif not EXPLICIT.search(evidence):
            reasons.append("captured text does not pass explicit-need check")
        if not same_company_source(domain, source):
            reasons.append("need evidence is not from the company's own domain")
        if age is None or age > MAX_AGE_DAYS:
            reasons.append("source evidence missing or older than 30 days")

        evidence_tokens = tokens(evidence)
        best_repo, best_hits, best_rare = "", set(), set()
        for name, repo in catalog.items():
            hits = evidence_tokens.intersection(repo.get("tokens", []))
            rare = {t for t in hits if repo_df[t] <= 4}
            if (len(rare), len(hits)) > (len(best_rare), len(best_hits)):
                best_repo, best_hits, best_rare = name, hits, rare
        if not best_repo or len(best_hits) < 2 or not best_rare:
            reasons.append("no strong direct repo match (requires 2 need-evidence tokens, 1 catalog-rare)")

        person = humans.get(domain, {})
        name = (person.get("person_name") or "").strip()
        profile = (person.get("profile_url") or "").strip()
        headline = (person.get("headline") or "").strip()
        detail = (person.get("profile_detail") or "").strip()
        if not name or not profile or not headline or not detail:
            reasons.append("decision-maker profile and specific profile detail not verified")
        elif not valid_person_profile(profile):
            reasons.append("profile URL is not an individual LinkedIn profile")
        elif not DECISION.search(headline):
            reasons.append("profile is not a Founder/CEO/CTO/VP Engineering/Head of Engineering")
        if headline and JOBSEEKER.search(headline):
            reasons.append("jobseeker headline; never contact")

        note = ""
        if not reasons:
            desc = (catalog[best_repo].get("problem") or catalog[best_repo].get("desc") or "").strip()
            desc = re.sub(r"\s+", " ", desc).rstrip(". ")
            note = f"Saw your work on {detail}. I build {best_repo} - {desc}. Would value the exchange."
            if len(note) > 300 or not note.isascii():
                reasons.append("personalized note exceeds 300 ASCII characters")
                note = ""

        output.append({
            "company": lead["org"] or domain, "domain": domain,
            "company_linkedin": lead["linkedin"] or "", "source_url": source,
            "evidence_age_days": age if age is not None else "",
            "explicit_need_evidence": evidence, "best_repo": best_repo,
            "repo_evidence_tokens": ";".join(sorted(best_hits)),
            "rare_repo_evidence_tokens": ";".join(sorted(best_rare)),
            "person_name": name, "profile_url": profile, "headline": headline,
            "profile_detail": detail, "note_draft": note,
            "status": "NOTE_READY_REVIEW" if not reasons else "HOLD",
            "hold_reasons": "; ".join(reasons),
        })

    output.sort(key=lambda r: (r["status"] != "NOTE_READY_REVIEW", r["company"].lower()))
    fields = list(output[0].keys()) if output else [
        "company", "domain", "company_linkedin", "source_url", "evidence_age_days",
        "explicit_need_evidence", "best_repo", "repo_evidence_tokens",
        "rare_repo_evidence_tokens", "person_name", "profile_url", "headline",
        "profile_detail", "note_draft", "status", "hold_reasons",
    ]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)

    review_fields = ["domain", "person_name", "profile_url", "headline", "profile_detail", "reviewed_on"]
    if not REVIEW.exists():
        with REVIEW.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=review_fields).writeheader()
    if not CONTACTED.exists():
        with CONTACTED.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=["domain", "person_name", "profile_url", "verdict", "receipt", "ts_local"]).writeheader()
    counts = Counter(r["status"] for r in output)
    print(f"companies={len(output)} note_ready_review={counts['NOTE_READY_REVIEW']} held={counts['HOLD']}")
    print(f"report={OUT}")
    print(f"manual_profile_evidence={REVIEW}")
    print("A NOTE_READY_REVIEW row is still a draft for human review; this script never sends.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
