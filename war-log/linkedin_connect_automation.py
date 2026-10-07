#!/usr/bin/env python3
"""Draft concise LinkedIn connection notes from manually selected contacts.

This is intentionally a local draft tool. LinkedIn's User Agreement disallows
unauthorized automation for profile access, contact adding, and message sending.
It does not connect to LinkedIn, scrape profiles, click controls, or send invites.

Input CSV columns: name, profile_url, observed_context
Output CSV columns: name, profile_url, note, characters, status
"""
import argparse
import csv
import re
import sys
from pathlib import Path

MAX_NOTE_CHARS = 200
REQUIRED = ("name", "profile_url", "observed_context")


def ascii_field(value, field, row_number):
    value = (value or "").strip()
    if not value:
        raise ValueError(f"row {row_number}: {field} is required")
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"row {row_number}: {field} must be ASCII") from exc
    return value


def make_note(name, context):
    first = re.split(r"\s+", name, maxsplit=1)[0]
    context = re.sub(r"\s+", " ", context).strip().rstrip(".!?;,")
    note = (
        f"Hi {first}, I noticed {context}. I built a Rs 499 job-search "
        "automation setup. May I share the short demo?"
    )
    if len(note) > MAX_NOTE_CHARS:
        raise ValueError(
            f"note for {first} is {len(note)} characters; shorten observed_context "
            f"until it is at most {MAX_NOTE_CHARS}"
        )
    return note


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contacts", type=Path, help="CSV of manually selected contacts")
    parser.add_argument("--out", type=Path, help="draft CSV (default: <contacts>-drafts.csv)")
    args = parser.parse_args(argv)
    output = args.out or args.contacts.with_name(args.contacts.stem + "-drafts.csv")

    with args.contacts.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fields = set(reader.fieldnames or [])
        missing = [field for field in REQUIRED if field not in fields]
        if missing:
            raise ValueError("input is missing required columns: " + ", ".join(missing))

        rows = []
        seen = set()
        for row_number, row in enumerate(reader, start=2):
            name = ascii_field(row.get("name"), "name", row_number)
            profile = ascii_field(row.get("profile_url"), "profile_url", row_number)
            context = ascii_field(row.get("observed_context"), "observed_context", row_number)
            if not profile.startswith("https://www.linkedin.com/in/"):
                raise ValueError(f"row {row_number}: profile_url must be a LinkedIn /in/ URL")
            if profile.lower() in seen:
                raise ValueError(f"row {row_number}: duplicate profile_url")
            seen.add(profile.lower())
            note = make_note(name, context)
            rows.append({
                "name": name,
                "profile_url": profile,
                "note": note,
                "characters": len(note),
                "status": "DRAFT_ONLY - review manually; no invitation sent",
            })

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=("name", "profile_url", "note", "characters", "status"),
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Drafted {len(rows)} note(s): {output}")
    print("No LinkedIn page was accessed and no invitation was sent.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
