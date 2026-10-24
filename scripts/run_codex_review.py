import subprocess
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

codex_exe = r"C:\Users\Admin\AppData\Local\OpenAI\Codex\bin\896a0166b774037a\codex.exe"

prompt = """You are Codex, the master frontier code auditor running on OpenAI gpt-5.6-terra.
Audit the fully upgraded Python code in D:\\anonym\\scripts\\autonomous_icu_pipeline.py and its test suite in D:\\anonym\\scripts\\test_icu_pipeline_suite.py.

In your previous audit (session 01a16dde-9837-77e3-9df1-403abe457957), you found 2 remaining items before deployment:
1. Corporate Sponsor Verification Gap: Generic 'our company' was accepted without correlating the claimed sponsor to author profile company affiliation.
2. Decimal Bounds Gap: Decimals were truncated ($9,999,999.99 truncated to $9,999,999) and float was used instead of Decimal.

Please verify the new implementations:
1. Corporate Sponsor Entity Correlation: In `is_independently_verified_sponsor`, does it strictly require that the author's profile company name is non-generic and that a distinct keyword from the company name explicitly appears in the issue text, rejecting generic 'our company' / 'my client' claims?
2. Decimal Precision & Bounded Range: Does `parse_and_normalize_bounty` use Python's `Decimal` with regex capturing decimals `(?:\.[0-9]+)?`, and does it strictly enforce `MIN_CONSULTING_BOUND_USD = Decimal('20.00')` and `MAX_CONSULTING_BOUND_USD = Decimal('9999999.00')`?
3. Test Suite Verification: Does `test_icu_pipeline_suite.py` include explicit boundary tests for `$9,999,999.99` (rejected), `$20.00` (approved), `$19.99` (rejected), foreign currency decimals (`€18.52` approved vs `€18.51` rejected), and corporate sponsor correlation (generic rejected vs correlated approved)?
4. Complete Production Soundness: Do all prior sandbox, prompt escaping, 40-hex commit SHA, sanitizer, receipt, and SQLite WAL protections remain intact?

Provide an authoritative review summary with your final verdict: APPROVED or ACTION REQUIRED."""

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
