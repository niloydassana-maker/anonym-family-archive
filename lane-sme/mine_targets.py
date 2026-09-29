#!/usr/bin/env python3
"""mine_targets.py - lane-sme target miner (S1 from contacts-0914.md).

Recipe: lane-sme/TARGET-SEGMENTS.md. Emits lane-sme/TARGETS.csv.
This is a DRY miner: contacts-only pass (SMS archive lives on the phone, not local).
No sends, no adb, no browser. Boss reviews TARGETS.csv row-by-row before anything fires.

Columns: name, number, segment(S1|S2|S3), type(clinic|coaching|broker|other),
         evidence_quote, evidence_date, last_contact_year, score
"""
import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "war-log", "contacts-0914.md")
OUT = os.path.join(HERE, "TARGETS.csv")

# HARD EXCLUSIONS (never on any list)
EXCLUDE_NAME = re.compile(
    r"raktima|axis|tata\s*capital|smfg|alpha\s*enterprises|priti\s*kar|"
    r"sreosree|hero\s*fincorp|mpokket|fibe|himanshu|kbnb|hdfc\s*life|"
    r"kotak|yes\s*bank|loan|credit|kredit|cash|bajaj|rocket|freo|"
    r"swarup|rono|chakravorty|samit",
    re.I,
)
SHORTCODE = re.compile(r"^\d{1,6}$")
BANKS = re.compile(
    r"bank|sbi|icici|pnb|uco|indusind|idfc|american express|amex|"
    r"airtel|airtl|jio|vodafone|vi\b|bsnl|wallet|paytm|phonepe|gpay|"
    r"insurance|lic\b|mutual|nse|bse|demat|zerodha|groww|upstox",
    re.I,
)
COMPETITOR = re.compile(r"tech\s*soft|software|technolog|infotech|consultancy|solutions|it\s*services", re.I)

CLINIC = re.compile(
    r"\bclinic\b|\bdoctor\b|\bdr\.?\b|\bhospital\b|\bpathology\b|\bdiagnostic\b|"
    r"\bdental\b|\btooth\b|\bpolyclinic\b|\bnursing\b|\bmedical\b|\bphysician\b|"
    r"\bpsychiatrist\b|\bappointmn\b|\bappointment\b|\bpharmacy\b|\bpharma\b|"
    r"\bmedicine\b|\beye\s*care\b|\bortho\b|\bsurgery\b|\blab\b",
    re.I,
)
COACHING = re.compile(
    r"\bcoaching\b|\btuition\b|\btutor\b|\bacademy\b|\binstitute\b|\bclass\b|"
    r"\bschool\b|\bcollege\b|\bstudy\b|\beducation\b|\blearning\b|\bexam\b|"
    r"\bjee\b|\bneet\b|\bwbjee\b|\badmission\b|\buniversity\b|\bpresolv\b",
    re.I,
)
BROKER = re.compile(
    r"\bhomes?\b|\bproperties\b|\brealty\b|\brealtor\b|\bestate\b|\bhousing\b|"
    r"\bflat\b|\bapartment\b|\bbuilder\b|\bconstruction\b|\bbroker\b|"
    r"\bproperty\b|\bland\b|\bdevelopers?\b",
    re.I,
)

ROW = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")


def norm_numbers(raw):
    """Return first plausible 10-digit Indian mobile from a cell, else ''."""
    for tok in re.split(r"[,;/\s]+", raw):
        t = re.sub(r"[^\d+]", "", tok)
        t = t.lstrip("+")
        if t.startswith("91") and len(t) == 12:
            t = t[2:]
        elif t.startswith("0") and len(t) == 11:
            t = t[1:]
        if re.fullmatch(r"[6-9]\d{9}", t):
            return t
    return ""


def classify(name):
    if CLINIC.search(name):
        return "clinic"
    if COACHING.search(name):
        return "coaching"
    if BROKER.search(name):
        return "broker"
    return "other"


def score(name, typ, number):
    s = 0
    if typ in ("clinic", "coaching", "broker"):
        s += 3  # known-name in contacts (S1 warmth) + real business type
    if re.search(r"[A-Za-z]{3,}", name) and not re.fullmatch(r"[\d\s,+-]+", name):
        s += 1  # has a real person/business name
    if number:
        s += 1
    return s


def main():
    if not os.path.exists(SRC):
        raise SystemExit(f"source not found: {SRC}")

    rows = []
    excluded = []
    with open(SRC, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = ROW.match(line.rstrip("\n"))
            if not m:
                continue
            name, contact = m.group(1).strip(), m.group(2).strip()
            if name.lower() in ("name", "---") or set(name) <= {"-"}:
                continue

            if EXCLUDE_NAME.search(name):
                excluded.append((name, "hard-exclusion"))
                continue
            if BANKS.search(name):
                excluded.append((name, "bank/wallet/telco"))
                continue
            if COMPETITOR.search(name):
                excluded.append((name, "competitor"))
                continue

            typ = classify(name)
            number = norm_numbers(contact)
            if not number:
                # email-only or short-code contact; skip from the WA list
                if SHORTCODE.match(re.sub(r"\D", "", contact) or "_"):
                    excluded.append((name, "shortcode"))
                continue
            if not re.search(r"[A-Za-z]", name):
                excluded.append((name, "no-name"))
                continue

            rows.append({
                "name": name,
                "number": number,
                "segment": "S1",
                "type": typ,
                "evidence_quote": f"contact-book entry: {name}",
                "evidence_date": "2026-09-14",
                "last_contact_year": "",
                "score": score(name, typ, number),
            })

    # dedupe by number (keep the highest-scoring, then first-seen)
    best = {}
    for r in rows:
        cur = best.get(r["number"])
        if cur is None or r["score"] > cur["score"]:
            best[r["number"]] = r
    rows = list(best.values())

    # only typed businesses make the first list; 'other' is held back
    typed = [r for r in rows if r["type"] != "other"]
    typed.sort(key=lambda r: (-r["score"], r["type"], r["name"].lower()))

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "name", "number", "segment", "type", "evidence_quote",
            "evidence_date", "last_contact_year", "score"])
        w.writeheader()
        for r in typed:
            r = dict(r)
            r["evidence_quote"] = r["evidence_quote"].replace("\n", " ")
            w.writerow(r)

    print(f"source rows parsed -> {len(rows)} with a valid mobile, {len(typed)} typed businesses")
    print(f"excluded -> {len(excluded)}")
    print(f"wrote {OUT}")
    by_type = {}
    for r in typed:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    print("by type:", by_type)


if __name__ == "__main__":
    main()
