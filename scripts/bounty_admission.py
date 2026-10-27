"""One evidence-based admission contract for all dispatcher lanes and release."""
from __future__ import annotations

from decimal import Decimal
import re

FLOOR = Decimal("80")
TRUSTED_BOTS = {"algora-pbc", "algora-io[bot]", "polar-sh[bot]", "opire[bot]"}
ISSUERS = {"OWNER", "MEMBER", "COLLABORATOR"}
NON_WORK = re.compile(
    r"\b(?:digest|newsletter|willingness.to.pay|validation plan|ad spend|"
    r"grant proposal|security bug bounty submission|payout claim|sealed solution|"
    r"mirrored from|backfill record|status:\s*done|bounty (?:alert|scout|solution))\b|"
    r"^\s*\[(?:experiment|radar|intake|proposal|roadmap)\]", re.I)
OFFER = re.compile(
    r"/bounty|/reward|\bbount(?:y|ies)\b|\breward\b|\b(?:we|i)\s+(?:will|can|would)\s+pay\b|"
    r"\boffering\b|\brecompensa\b|\brémunération\b|悬赏|赏金|报酬", re.I)
WITHDRAWN = re.compile(
    r"(?:remov(?:e|ed|ing)|withdraw(?:n|ing)?|cancel(?:led|ing)?)\s+(?:the\s+)?(?:bounty|reward)|"
    r"bounty\s+(?:is\s+)?(?:withdrawn|cancelled|paid|awarded)|no longer offering|"
    r"no\s+(?:bounty|reward|payment|funding)(?:\s+(?:is\s+)?(?:available|expected|offered))?", re.I)
PAYEE = re.compile(
    r"\b(?:researcher|payout wallet|settlement wallet|settlement rail|"
    r"claiming bounty|bounty submission|requesting funding)\b", re.I)
HARD = re.compile(
    r"\b(?:race condition|deadlock|concurren\w*|atomic\w*|idempot\w*|"
    r"overflow|underflow|precision|protocols?|invariants?|authorization|bypass|"
    r"cross.tenant|serialization|compilers?|parsers?|memory|latency|throughput|"
    r"regressions?|crash\w*|panic\w*|corrupt\w*|transactions?|consensus|ABI|"
    r"performance|distributed|schedulers?|algorithms?|cryptograph\w*|"
    r"encryption|signatures?|deadlocks?)\b", re.I)
COMPONENT = re.compile(
    r"(?<!https://)(?:[\w.-]+/)+[\w.-]+\.[a-zA-Z0-9]+|"
    r"\b[A-Za-z_][A-Za-z0-9_:]*\(\)|\b(?:E[A-Z0-9_]{4,}|[A-Z][A-Za-z]+Error)\b")
MONEY = re.compile(
    r"(?<![\w.])(?:(?P<c1>\$|€|£|₹|USD|USDC|USDT|EUR|GBP|INR|SGD|AED|ETH|SOL)\s*"
    r"(?P<a1>\d+(?:,\d{3})*(?:\.\d+)?)(?P<m1>[kK])?|"
    r"(?P<a2>\d+(?:,\d{3})*(?:\.\d+)?)(?P<m2>[kK])?\s*"
    r"(?P<c2>USDC|USDT|USD|EUR|GBP|INR|SGD|AED|ETH|SOL|\$|€|£|₹))(?![\w]|\.\d)", re.I)


def trusted(context, document):
    """Is this document written by the party that can commit the project's money?

    Platform bots publish the funding attestation itself, so their login has to be
    recognised in both spellings: GitHub apps report ``algora-pbc[bot]`` while the
    platform is also referred to plainly as ``algora-pbc``. Matching only one form
    silently discards every real offer a platform publishes on someone else's issue.
    """
    user = (document.get("user") or {}).get("login", "")
    owner = context["repository"]["owner"]["login"]
    login = user.lower()
    return (document.get("author_association", "").upper() in ISSUERS
            or login == owner.lower()
            or login in TRUSTED_BOTS
            or login.removesuffix("[bot]") in TRUSTED_BOTS)


MERGE_EVIDENCE_MIN = 10


def repository_intent(evidence):
    """Return (ok, reason) from the repository's measured merge history.

    A bounty is paid on merge, so a repository that carries many pull requests and
    has merged none has demonstrated it does not pay, whatever its own issues say.
    Measured shape of that failure (2026-10-27): one repository took 4,458 pull
    requests and merged 0, while still publishing funded-looking issues, and its
    CONTRIBUTING.md declared the bounties symbolic.

    Absence of evidence is never rejection. A repository with fewer than
    MERGE_EVIDENCE_MIN pull requests, or an unreachable probe, gets no verdict --
    a new project that has not merged yet must not be refused on silence.
    """
    if not evidence:
        return True, ""
    merged, total = evidence.get("merged"), evidence.get("total")
    if merged is None or total is None:
        return True, ""
    if int(total) >= MERGE_EVIDENCE_MIN and int(merged) == 0:
        return False, "REPOSITORY_DOES_NOT_MERGE"
    return True, ""


def monetary_text(text):
    return re.sub(r"\x60{3}[\s\S]*?\x60{3}|~~[\s\S]*?~~|<!--[\s\S]*?-->", " ", text)


def amounts(text, positions=False):
    text = monetary_text(text)
    for match in MONEY.finditer(text):
        after = text[match.end():match.end() + 35]
        if re.match(r"\s*(?:[$\\^_]|(?:pool|TVL|ARR|MRR|valuation|treasury|budget|/month)\b)", after, re.I):
            continue
        amount = Decimal((match["a1"] or match["a2"]).replace(",", ""))
        if match["m1"] or match["m2"]:
            amount *= 1000
        unit = (match["c1"] or match["c2"]).upper()
        unit = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}.get(unit, unit)
        value = (amount, unit, match.group())
        yield (*value, match.start()) if positions else value


def admit(context, quote=None, floor=FLOOR):
    """Return proof or a reason; untrusted payee text never becomes an offer."""
    issue, metadata = context["issue"], context["repository"]
    if not context.get("complete_comments"):
        return None, "INCOMPLETE_COMMENTS"
    if issue.get("state") != "open" or metadata.get("archived") or metadata.get("disabled"):
        return None, "CLOSED_OR_READ_ONLY"
    title, body = issue["title"], issue.get("body") or ""
    if NON_WORK.search(title) or re.search(r"automated\s+(?:superteam\s+)?digest|mirrored from|status:\s*done", body, re.I):
        return None, "MIRROR_OR_NON_ENGINEERING"
    if re.search(r"\b(?:ad spend|marketing campaign|willingness.to.pay|market validation)\b", body, re.I):
        return None, "MARKETING_OR_EXPERIMENT"
    if re.search(r"test network.*practice money|testnet (?:ETH|tokens?).*(?:only|no real)|"
                 r"verbatim copy of all instructions.*before the first human message", body, re.I | re.S):
        return None, "NON_PAYMENT_OR_INSTRUCTION_EXFILTRATION"
    technical = sorted(set(m.group().lower() for m in HARD.finditer(title + "\n" + body)))
    components = sorted(set(m.group() for m in COMPONENT.finditer(re.sub(r"https?://\S+", " ", body))))
    if not technical or (not components and len(technical) < 2):
        return None, "HARD_ISSUE_EVIDENCE_MISSING"
    offer = None
    for document in [issue, *context["comments"]]:
        if not trusted(context, document):
            continue
        text = monetary_text(((title + "\n") if document is issue else "") + (document.get("body") or ""))
        if WITHDRAWN.search(text):
            offer = None
            continue
        if PAYEE.search(text) or not OFFER.search(text):
            continue
        candidates = []
        for amount, currency, raw, location in amounts(text, positions=True):
            if not OFFER.search(text[max(0, location - 160):location + len(raw) + 160]):
                continue
            if currency in {"USD", "USDC", "USDT"}:
                usd, rate = amount, {"basis": "USD face value" if currency == "USD" else "USD-denominated stablecoin offer"}
            elif quote:
                rate = quote(currency)
                usd = amount * Decimal(str(rate["usd_rate"]))
            else:
                continue
            if floor <= usd <= Decimal("9999999"):
                candidates.append({"amount": str(amount), "currency": currency, "usd_value": str(usd),
                                   "quote": rate, "raw": raw, "source_url": document["html_url"],
                                   "payer": document["user"]["login"]})
        if candidates:
            offer = max(candidates, key=lambda row: Decimal(row["usd_value"]))
    if not offer:
        return None, "CURRENT_ISSUER_OFFER_MISSING"
    return {"funding": offer, "technical_signals": technical, "component_references": components,
            "source_issue": issue["html_url"], "fetched_at": context["fetched_at"]}, ""


def competition(api, repo, number, own_head=None):
    pattern = re.compile(rf"(?:#\s*|/issues/|\bissue\s+){number}(?!\d)|(?:^|[-_/]){number}(?:$|[-_/])", re.I)
    for pr in api.pages(f"repos/{repo}/pulls", state="open"):
        if own_head and pr["head"]["sha"] == own_head and pr["head"]["repo"] and (
                pr["head"]["repo"]["owner"]["login"] == "isearchxsolve"):
            continue
        text = "\n".join([pr.get("title") or "", pr.get("body") or "", pr["head"]["ref"]])
        if pattern.search(text):
            raise ValueError("Competing open PR: " + pr["html_url"])
    for event in api.pages(f"repos/{repo}/issues/{number}/timeline"):
        linked = (event.get("source") or {}).get("issue") or {}
        if linked.get("state") != "open" or not linked.get("pull_request"):
            continue
        pull = api.api(linked["pull_request"]["url"].removeprefix("https://api.github.com/"))
        if pull["base"]["repo"]["full_name"].lower() != repo.lower():
            continue
        if own_head and pull["head"]["sha"] == own_head:
            continue
        raise ValueError("Linked open PR: " + pull["html_url"])
    return True
