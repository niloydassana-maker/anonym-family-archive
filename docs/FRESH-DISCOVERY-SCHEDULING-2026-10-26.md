# Fresh-first discovery scheduling

The dispatcher formerly fetched and triaged up to 1,000 results for its first
query before reaching the next query. A large low-yield backlog could therefore
delay fresh candidates from later searches. The preceding
[funding audit](FUNDING-FILTER-AUDIT-2026-10-26.md) did not justify weakening
payment or competition checks.

## Resulting behavior

The daemon now visits the newest **30 raw search results for each of its 23
queries** before revisiting those queries at the full **1,000-result horizon**.
The existing per-cycle issue deduplication spans both passes, so an issue is
triaged once even when it appears in several searches or both passes. GitHub
still sorts each request by creation time descending; existing hardness ranking
is retained within the returned candidate window.

Funding, authority, territory, the live $50 floor, comment limits, competing-PR
checks, payload integrity, and all worker verification gates remain unchanged.
No bounty task implementation or Kaggle worker was restarted for this change.

CLI defaults are `--search-limit 1000 --fresh-limit 30`. A smaller total horizon
caps the fresh window and does not trigger an identical second pass.
`--fresh-limit 0` explicitly restores the former single-pass order. Direct
callers of `run_pipeline_cycle` retain their existing single-pass API default;
the daemon passes its fresh-window setting explicitly.

Logs identify each pass with `DISCOVERY_PASS_START` and
`DISCOVERY_PASS_COMPLETE`. An empty or failed search does not stop the following
query, and full backlog scans remain scheduled after the fresh pass.

This improves ordering rather than promising a fixed refresh interval. The
daemon still waits until its complete cycle finishes before its 180-second
sleep. Issues arriving during backlog processing are considered in the next
cycle; this change does not introduce a concurrent scanner or persistent cursor.

## Verification

All six suites passed with Python warnings treated as errors:

| Suite | Result |
| --- | --- |
| `test_fresh_discovery_schedule.py` | 5 tests |
| `test_discovery_repairs.py` | 16 tests |
| `test_partition_regressions.py` | 6 tests |
| `test_icu_pipeline_suite.py` | All 16 integrity groups |
| `test_fleet_recovery_live_receipts.py` | 13 tests |
| `test_dispatch_transport_live_receipts.py` | 5 tests |

Existing suites were not edited. The added tests exercise actual cycle ordering,
deduplication across passes, unchanged eligibility and floor rejection, a failed
first query, CLI wiring, disabled mode, empty query sets, and limit boundaries.
Compilation exited 0 with empty stderr. Test fixtures are isolated unit inputs,
not live task receipts.

Final tested source SHA-256:

- Dispatcher: `b77aa3d76d076a90ec764338a417d1e6ecad3af3af8fb23ae354776a890f57ce`
- New tests: `4df0f9c7e928bc0d5a008835cc800b3d64f04b31c3c48c4323f2a8d603d519fc`

## Live rollout

At **23:31:36 IST on 26 October 2026**, the known dispatcher process 12176 was
replaced by process **16676**, running:

```text
python -u scripts/autonomous_icu_pipeline.py --live --anytime --search-limit 1000 --fresh-limit 30
```

Before the restart, a consistent delivery-database backup preserved all 203 rows
and the full SQLite integrity check returned `ok`. The new process independently
reported `DELIVERY_DB_OK integrity=ok rows=203`, followed by:

```text
[DISCOVERY_PASS_START] phase=fresh limit=30 queries=23
[Search Query] algora.io
Found 4 candidates.
```

Fresh fleet heartbeats after the restart continued to report `phase=CLINE` for
core #988 and #992, establishing that their engineering runs were not interrupted.
That is progress evidence, not a completed implementation or verified new PR.

Receipts are local under `scratch/fresh-discovery-20261026/`:
`verification.json`, `before-restart.json`,
`delivery-db-before-restart.sqlite3`, `dispatcher-restart.json`, and separate
dispatcher stdout/stderr logs. The database backup and operational artifacts
remain outside Git.
