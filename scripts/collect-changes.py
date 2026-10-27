#!/usr/bin/env python3
"""
NUL-Safe Git Status Collector (Engine 2 / R7 Integrity Standard)
Extracts changed worktree paths from `git status --porcelain=v1 -z` without trusting unverified buffers.
Handles spaces, special characters, and non-ASCII file paths cleanly.
"""
import subprocess
import sys
import os
import json
from pathlib import Path

FORBIDDEN_PREFIXES = (
    ".git/",
    ".github/workflows/",
    "node_modules/",
    ".venv/",
    "venv/",
    "target/",
    "build/",
    "dist/",
)

def collect_nul_safe_changes():
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all", "-z"],
            capture_output=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running git status: {e}", file=sys.stderr)
        sys.exit(1)

    raw_output = proc.stdout
    if not raw_output:
        print("No changes detected in worktree.")
        Path("../harness/verified_files.txt").write_text("", encoding="utf-8")
        return []

    entries = raw_output.split(b"\x00")
    paths = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry:
            continue
        if len(entry) < 4 or entry[2:3] != b" ":
            print(f"Warning: malformed entry {entry!r}", file=sys.stderr)
            continue
        
        rel_path = entry[3:].decode("utf-8", errors="replace")
        paths.append(rel_path)
        
        # In porcelain -z, renames and copies (R or C) are followed by a second NUL-separated path (original source)
        status_code = entry[:2]
        if b"R" in status_code or b"C" in status_code:
            if i < len(entries):
                original_source = entries[i].decode("utf-8", errors="replace")
                i += 1
                paths.append(original_source)

    # Filter out forbidden paths / safety invariants
    verified_paths = []
    blocked_paths = []
    for p in sorted(set(paths)):
        normalized = p.replace("\\", "/").strip()
        if any(normalized.startswith(fp) for fp in FORBIDDEN_PREFIXES):
            blocked_paths.append(normalized)
        else:
            verified_paths.append(normalized)

    if blocked_paths:
        print(f"Security Warning: Blocked dangerous/sensitive paths: {blocked_paths}", file=sys.stderr)

    # Write verified paths for the commit step
    out_file = Path("../harness/verified_files.txt")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(verified_paths) + ("\n" if verified_paths else ""), encoding="utf-8")

    summary = {
        "total_changed": len(paths),
        "verified_count": len(verified_paths),
        "verified_files": verified_paths,
        "blocked_files": blocked_paths,
    }
    print(json.dumps(summary, indent=2))
    return verified_paths

if __name__ == "__main__":
    collect_nul_safe_changes()
