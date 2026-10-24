import subprocess
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

codex_exe = r"C:\Users\Admin\AppData\Local\OpenAI\Codex\bin\896a0166b774037a\codex.exe"

prompt = """You are Codex, the master frontier code auditor running on OpenAI gpt-5.6-terra.
Audit the Python code in D:\\anonym\\scripts\\autonomous_icu_pipeline.py thoroughly.

The purpose of this automation is to target REAL 'ICU patients' (enterprise operators, founders, and maintainers in acute technical distress who have explicitly offered payment/consulting fees in writing), analyze their architecture, and route private consulting engagements.

Evaluate the codebase on:
1. Architectural soundness and honesty (Zero-Manufacture compliance - are all false test claims eliminated?).
2. Follow-the-Sun daytime timezone classifier (word-boundary regex correctness and active business hours).
3. Strictness of client payment verification (does it strictly identify real paying ICU patients and reject student programs/aggregators?).
4. Private commercial routing (confirm no public bank account / UPI dumping).
5. Potential edge cases or bugs.

Provide a comprehensive, authoritative review summary with your verdict: APPROVED or ACTION REQUIRED."""

cmd = [
    codex_exe,
    "exec",
    "--skip-git-repo-check",
    "--ephemeral",
    "-C", r"D:\anonym",
    prompt
]

print("Executing Frontier Audit via OpenAI Codex (gpt-5.6-terra)...")
proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace")

print("Exit code:", proc.returncode)
print("\n" + "="*50)
print("CODEX FRONTIER MODEL (GPT-5.6-TERRA) REVIEW REPORT")
print("="*50)
if proc.stdout:
    print(proc.stdout)
if proc.stderr:
    lines = proc.stderr.splitlines()
    for l in lines:
        if any(k in l.lower() for k in ["model:", "tokens used", "session id"]):
            print(f"[{l.strip()}]")
