"""Shared, pure recovery rules for the laptop dispatcher and cloud workers."""
from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass

MAX_EXECUTION_ATTEMPTS = 3
RECOVERY_RELEASE = '2026-10-26-bounded-recovery-r1'
CLAIM_LEASE_SECONDS = 30 * 60
CLAIM_HEARTBEAT_SECONDS = 60
FLEET_LEASE_CHANNEL = 'BOUNTY_FLEET_LEASE'
RETRY_DELAYS_SECONDS = (5 * 60, 15 * 60)

_PERMANENT_FAILURE = re.compile(
    r"security violation|assessment safety gate|unsafe relative path|"
    r"FAILED_NO_TEST_VERIFICATION|no native test commands|"
    r"competing (?:pull request|pr)|open (?:pull request|pr) already|"
    r"PR exists|receipt failed|HTTP\s*404|repository not found|"
    r"not a software|non-software|speculative|roadmap|bot/discussion mirror",
    re.IGNORECASE,
)
_TRANSIENT_FAILURE = re.compile(
    r"timed?\s*out|timeout|network|connection (?:reset|refused|aborted)|"
    r"temporary failure|temporarily unavailable|name resolution|"
    r"HTTP(?:\s+Error)?\s*(?:401|408|429|500|502|503|504)\b|rate.?limit|"
    r"key exhaustion|no ready .*key|model is unavailable|"
    r"model unavailable|claim lease lost|ledger .*unavailable",
    re.IGNORECASE,
)


def is_retryable_failure(reason: str) -> bool:
    """Unknown and deterministic failures remain closed."""
    return bool(_TRANSIENT_FAILURE.search(reason or "")) and not bool(
        _PERMANENT_FAILURE.search(reason or "")
    )


def is_nonsoftware_data_task(task: dict) -> bool:
    # These paid collection tasks require authentic account data, not code.
    return bool(re.search(
        r"\bbanking\s+transcripts?\s*,\s*\$\d+(?:\.\d+)?\s+each\b",
        str(task.get("title") or ""), re.IGNORECASE,
    ))


def task_reference(task: dict) -> str:
    return f"{task.get('repo', '')}#{task.get('issue_number', '')}"


def event_reference(text: str) -> str:
    matches = re.findall(r"\sfor\s+([^/\s]+/[^#\s]+)#(\d+)\b", text)
    if matches:
        return f"{matches[-1][0]}#{matches[-1][1]}"
    # Historical claims omitted the repository; their real task IDs encode it.
    match = re.search(r"\bBT-\d+-([^_\s]+)_(\S+)-(\d+)(?:\s|$)", text)
    return f"{match[1]}/{match[2]}#{match[3]}" if match else ""


def event_number(text: str, field: str, default: float = 0) -> float:
    match = re.search(r"\b" + re.escape(field) + r"=(\d+(?:\.\d+)?)\b", text)
    return float(match[1]) if match else default


def event_run(text: str) -> str:
    match = re.search(r"\brun=([a-zA-Z0-9_-]+)\b", text)
    return match[1] if match else ""


def _timestamp(row: dict) -> float:
    value = float(row.get("at", 0))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Fleet receipt has no valid timestamp; recovery blocked")
    return value


def matching_events(task: dict, rows: list[dict]) -> list[dict]:
    ref = task_reference(task)
    task_id = str(task.get("task_id") or "")
    selected = []
    for row in rows:
        text = str(row.get("text") or "")
        if event_reference(text) == ref or (
            task_id and re.search(r"\b" + re.escape(task_id) + r"(?:\s|$)", text)
        ):
            _timestamp(row)
            selected.append(row)
    return sorted(selected, key=_timestamp)


def current_claim(task: dict, rows: list[dict]) -> tuple[dict | None, float]:
    events = matching_events(task, rows)
    claims = [r for r in events if str(r.get("text", "")).startswith("CLAIMED ")]
    if not claims:
        return None, 0
    claim = claims[-1]
    run = event_run(claim["text"])
    lease = event_number(claim["text"], "lease_until", _timestamp(claim) + CLAIM_LEASE_SECONDS)
    # Only the latest claimant's heartbeats may extend ownership.
    if run:
        for row in events:
            if row["text"].startswith("HEARTBEAT ") and event_run(row["text"]) == run:
                lease = max(lease, event_number(row["text"], "lease_until"))
    return claim, lease


@dataclass(frozen=True)
class RecoveryDecision:
    allowed: bool
    reason: str
    attempt: int
    retry_at: float = 0


def recovery_decision(
    task: dict, claim_rows: list[dict], result_rows: list[dict], now: float | None = None,
) -> RecoveryDecision:
    now = time.time() if now is None else now
    if not task.get("task_id") or not task.get("repo") or not task.get("issue_number"):
        return RecoveryDecision(False, "invalid task", 0)
    if is_nonsoftware_data_task(task):
        return RecoveryDecision(False, "non-software data collection", 0)
    claims = matching_events(task, claim_rows)
    results = matching_events(task, result_rows)
    results = [r for r in results if re.match(r"^(?:SUCCESS|FAILED|SKIPPED)\b", r["text"])]
    initial_claims = [r for r in claims if r["text"].startswith("CLAIMED ")]
    failures = [r for r in results if r["text"].startswith("FAILED ")]
    explicit = [int(event_number(r["text"], "attempt")) for r in claims + results]
    # Heartbeats and repeated reads never consume attempts.
    identities = {event_run(r["text"]) or (r["at"], r["text"]) for r in initial_claims}
    used = max(len(identities), len(failures), max(explicit, default=0))
    next_attempt = used + 1
    if any(r["text"].startswith("SUCCESS ") or re.search(r"PR exists", r["text"], re.I) for r in results):
        return RecoveryDecision(False, "already delivered or PR exists", used)
    if any(r["text"].startswith("SKIPPED ") for r in results):
        return RecoveryDecision(False, "excluded task", used)
    if any(not is_retryable_failure(r["text"]) for r in failures):
        return RecoveryDecision(False, "permanent or unclassified failure", used)
    claim, lease_until = current_claim(task, claims)
    last_result_at = _timestamp(results[-1]) if results else 0
    unfinished = claim is not None and _timestamp(claim) > last_result_at
    if unfinished and lease_until > now:
        return RecoveryDecision(False, "active claim lease", used, lease_until)
    if used >= MAX_EXECUTION_ATTEMPTS:
        return RecoveryDecision(False, "attempt limit reached", used)
    if unfinished:
        return RecoveryDecision(True, "expired claim lease", next_attempt)
    if failures:
        retry_at = _timestamp(failures[-1]) + RETRY_DELAYS_SECONDS[min(max(used - 1, 0), 1)]
        return RecoveryDecision(now >= retry_at, "temporary failure cooldown" if now < retry_at else "temporary failure retry", next_attempt, retry_at)
    return RecoveryDecision(True, "new task", 1)
