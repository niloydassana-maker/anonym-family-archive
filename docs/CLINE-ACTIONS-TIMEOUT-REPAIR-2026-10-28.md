# Actions Cline timeout root cause and repair — 2026-10-28

## Failure receipts

Two claimed Expensify deliveries ended during the Cline engineering step after approximately
one hour:

- [`40592395695`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40592395695),
  issue `Expensify/App#103214`: engineer job `22:08:27–23:08:06 UTC`; Cline step began
  `22:09:03 UTC`.
- [`40591329401`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40591329401),
  issue `Expensify/App#102333`: engineer job `22:00:31–23:00:34 UTC`; Cline step began
  `22:01:10 UTC`.

Both runs failed and their retained-artifact listing contained only the claim artifact, not an
engineering artifact. GitHub returned `log not found` for the failed engineer job logs, so an
exact Cline exit diagnostic could not be recovered. The timing matches the source-level cause:
`cline_turn_timeout_seconds()` returned exactly `3600` for every ecosystem and
`run_cline_engineering_turn()` used that value for Cline. The Actions engineer step itself had a
300-minute limit and its job had a 330-minute limit. The worker's one-hour subprocess limit was
the earlier effective deadline.

## Repair

- Actions now sets `CLINE_TOTAL_BUDGET_SECONDS=14400` (four hours) for a claimed delivery. The
  same monotonic deadline covers claim intake and all Cline repair turns; a new turn cannot reset
  the clock. This leaves up to one hour within the existing five-hour step for independent
  builds, regression tests, linters, final checks, and publication preparation.
- When Actions does not set a delivery budget, Cline keeps the standalone 60-minute timeout.
  This preserves the Kaggle worker's existing default.
- If the shared budget expires, the worker stops launching Cline turns after preserving the
  current worktree and writes `CLINE_TOTAL_BUDGET_EXHAUSTED`. It fails closed; the existing
  native-verification and publication gates are unchanged. Recovery recognizes this marker and
  the new `14400`-second timeout as the same repaired infrastructure class as the existing 900-,
  2400-, and 3600-second timeout receipts.

## Local verification

- `python -W error -m py_compile scripts/kaggle_engine_worker.py scripts/actions_delivery.py
  scripts/fleet_recovery_policy.py scripts/test_partition_regressions.py` — passed.
- `python -W error scripts/test_partition_regressions.py` — 9 passed.
- `python -W error scripts/test_actions_migration.py` — 34 tests, 33 passed and one
  Windows-only newline-path test skipped.
- `python -W error scripts/test_cline_delivery_ownership.py` — 12 passed.
- `python -W error scripts/test_icu_pipeline_suite.py` — all 16 sections passed, 100% green.

These local checks verify the shared-budget behavior and workflow wiring. They do not prove a
new Actions task has completed a four-hour run. The first post-deployment delivery is still the
required live receipt for the extended Cline runway; only a verified pull request counts as a
completed bounty delivery.
