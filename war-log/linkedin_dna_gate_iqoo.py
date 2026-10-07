#!/usr/bin/env python3
"""Guided, phone-only LinkedIn connection workflow for DNA-gate companies.

This deliberately leaves profile discovery and the final Send tap to a human.
It never uses a desktop browser. A send is recorded only after a Pending-state
screen is saved as evidence.
"""

from __future__ import annotations

import argparse
import csv
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\anonym")
ADB = ROOT / "platform-tools" / "adb.exe"
SERIAL = "10BE8135QM001KK"
GATE = ROOT / "war-log" / "_wa_dna_gate.csv"
EVIDENCE = ROOT / "war-log" / "evidence" / "LI"
TARGETS = [
    ("gooey.ai", "Gooey.AI", "oioi", "full-stack AI animation platform; 7-agent pipeline"),
    ("sliceit.com", "Slice", "lateststablecode", "stable-channel release snapshot"),
    ("myhubble.money", "myhubble.money", "guardian_app", "Flutter mobile app"),
    ("realimage.com", "RealImage", "film_kit_v3", "generative film pipeline"),
    ("flamebackcapital.com", "Flameback Capital", "solana_ex", "Solana trading experiment in TypeScript"),
]
BLOCK_TERMS = ("warning", "rate limit", "captcha", "unusual activity", "temporarily restricted")
NOTE_ALLOWED = re.compile(r"^[A-Za-z0-9 .,!?'-]+$")


def adb(*args: str, timeout: int = 30, check: bool = True) -> str:
    p = subprocess.run([str(ADB), "-s", SERIAL, *args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=timeout)
    out = (p.stdout or "") + (p.stderr or "")
    if check and p.returncode:
        raise RuntimeError(f"ADB command failed ({p.returncode}): {out.strip()}")
    return out.strip()


def device_ready() -> bool:
    if not ADB.is_file():
        print(f"ADB not found: {ADB}")
        return False
    listing = subprocess.run([str(ADB), "devices", "-l"], capture_output=True,
                             text=True, encoding="utf-8", errors="replace").stdout
    print(listing.rstrip())
    return any(line.split()[:2] == [SERIAL, "device"] for line in listing.splitlines())


def eligible_targets() -> tuple[list[tuple[str, str, str, str]], list[tuple[str, str]]]:
    with GATE.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    eligible, skipped = [], []
    for domain, company, repo, detail in TARGETS:
        matches = [r for r in rows if r.get("domain", "").strip().lower() == domain]
        if not matches:
            skipped.append((company, "domain is absent from the current DNA gate"))
            continue
        reasons = " ".join(r.get("gate_reasons", "") for r in matches).lower()
        if "already_contacted" in reasons:
            skipped.append((company, "current DNA gate flags already_contacted"))
            continue
        eligible.append((domain, company, repo, detail))
    return eligible, skipped


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def capture(company: str, label: str) -> Path:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9]+", "-", company).strip("-").lower()
    local = EVIDENCE / f"{safe}-{label}-{stamp()}.png"
    remote = f"/sdcard/li-{label}.png"
    adb("shell", "screencap", "-p", remote)
    adb("pull", remote, str(local))
    print(f"Screenshot: {local}")
    return local


def dump_ui(company: str) -> str:
    local = EVIDENCE / f"{re.sub(r'[^A-Za-z0-9]+', '-', company).strip('-').lower()}-ui-{stamp()}.xml"
    adb("shell", "uiautomator", "dump", "/sdcard/li-current.xml", timeout=45)
    adb("pull", "/sdcard/li-current.xml", str(local))
    print(f"UI dump: {local}")
    try:
        return local.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def stop_if_restricted(company: str, ui: str) -> bool:
    if any(term in ui.lower() for term in BLOCK_TERMS):
        shot = capture(company, "warning")
        print(f"STOP: LinkedIn warning/restriction detected. Preserve and report {shot}; do not retry.")
        return True
    return False


def ask_yes(prompt: str) -> bool:
    return input(prompt + " [y/N] ").strip().lower() == "y"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="show current gate exclusions; do not open LinkedIn")
    args = parser.parse_args()
    if not device_ready():
        print("STOP: iQOO is offline. Replug it, choose File transfer / MTP, and decline tethering; then rerun.")
        return 2

    eligible, skipped = eligible_targets()
    print("\nCurrent gate exclusions:")
    for company, reason in skipped:
        print(f"  SKIP {company}: {reason}")
    print("\nLinkedIn candidates:")
    for _, company, repo, detail in eligible:
        print(f"  {company}: {repo} ({detail})")
    if args.dry_run:
        return 0
    print("\nManual review is required at every step. Do not use desktop Chrome.")

    for domain, company, repo, detail in eligible:
        print(f"\n=== {company} | {repo} ===")
        slug = input("Company LinkedIn slug (verify via mobile search/company page): ").strip()
        if not slug or not re.fullmatch(r"[A-Za-z0-9_-]+", slug):
            print(f"SKIP {company}: no verified company slug.")
            continue
        url = f"https://www.linkedin.com/company/{slug}/"
        adb("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url)
        time.sleep(5)
        ui = dump_ui(company)
        if stop_if_restricted(company, ui):
            return 3
        capture(company, "company")
        print("Find one Founder, CEO, CTO, VP Engineering, or Head of Engineering from this company page.")
        person = input("Person's displayed name (blank to skip): ").strip()
        role = input("Exact decision-maker role/headline (blank to skip): ").strip()
        if not person or not role:
            print(f"SKIP {company}: no verified decision-maker.")
            continue
        if re.search(r"open to work|seeking opportunities", role, re.I):
            print(f"SKIP {company}: headline identifies a jobseeker.")
            continue
        if not re.search(r"founder|chief executive|\bceo\b|\bcto\b|vp engineering|head of engineering", role, re.I):
            print(f"SKIP {company}: role is not an allowed decision-maker role.")
            continue
        specific = input("One specific real thing read on their profile (blank to skip): ").strip()
        if not specific:
            print(f"SKIP {company}: no specific profile detail verified.")
            continue
        note = f"Saw your work on {specific}. I build {repo} - {detail}. Would value the exchange."
        if len(note) > 300 or not NOTE_ALLOWED.fullmatch(note):
            print("SKIP: proposed note is over 300 characters or contains non-ASCII/unsupported characters.")
            continue
        print(f"\nExact note ({len(note)} chars):\n{note}")
        print("Read the profile and screenshot yourself; then tap Connect manually on the phone.")
        if not ask_yes("Have you tapped Connect and the note dialog is open?"):
            print(f"SKIP {company}: Connect/dialog not confirmed.")
            continue
        ui = dump_ui(company)
        if stop_if_restricted(company, ui):
            return 3
        capture(company, "dialog-before-entry")
        if not ask_yes("Does the phone show the correct note dialog for this exact person?"):
            print(f"SKIP {company}: note dialog/person not confirmed.")
            continue
        # Use Android input text only after interactive approval. No Send tap is automated.
        escaped = shlex.quote(note.replace(" ", "%s"))
        adb("shell", "input", "text", escaped)
        time.sleep(1)
        capture(company, "dialog-review")
        ui = dump_ui(company)
        if stop_if_restricted(company, ui):
            return 3
        print("Inspect dialog-review screenshot and UI dump. Confirm every character, ASCII rendering, and recipient.")
        if not ask_yes("Is the displayed note character-for-character correct? (You must still tap Send yourself)"):
            print(f"SKIP {company}: note text was not verified; do not send.")
            continue
        if not ask_yes("Have you now tapped Send manually on the phone?"):
            print(f"SKIP {company}: no Send tap confirmed.")
            continue
        time.sleep(3)
        ui = dump_ui(company)
        if stop_if_restricted(company, ui):
            return 3
        if "pending" not in ui.lower():
            shot = capture(company, "unverified")
            print(f"UNVERIFIED {company}: UI dump does not show Pending. No send claim. Screenshot: {shot}")
            continue
        receipt = capture(company, "pending")
        print(f"SENT {company} | {person} | {role} | receipt={receipt}")

    print("\nFinished. Only SENT lines with a saved Pending screenshot count as receipts.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nStopped by operator.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        raise SystemExit(1)
