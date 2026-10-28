# Fresh-query hydration priority repair — 2026-10-28

## Live baseline and root cause

Discovery run [40607559211](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40607559211)
completed successfully on `c1805df7b885b9b6cfb7b6f5de30d8ae6a927902`.

The run returned raw results in every code lane: programs 212, normal 175, startup 486, and
founder 0. These are overlapping search hits, not unique or qualified bounty tasks. Admission
correctly rejected the sampled issues: 27 lacked actionable engineering evidence, 20 lacked a
current issuer-backed offer, six were closed/read-only, two were declared by design, and one was
non-engineering. Final output was `qualified_fresh=0`, `qualified_unique=0`, `dispatched=[]`.

The same run logged `REPOSITORY_PRECHECK` with 1,910 queued rows, 622 repositories, 18 new
probes, 90 farm rows retired, and 1,528 known-good rows. The bounded hydration window selected
60 rows across 36 repositories. Inspection of the scheduler showed that only the dedicated
priority-program queries populated the current-cycle priority list. Fresh results from the
normal, startup, founder, and rotating program lanes could therefore sit behind a large
historical backlog. The ordering also placed old known-good rows ahead of fresh hits from
unprobed repositories. This is a throughput/starvation defect; the run does not prove a
qualified candidate was hidden in that queue.

## Repair

- Every fresh result from every lane now enters the current-cycle hydration priority list.
- Priority rows are ordered by issue update time across lanes. Fresh measured-good repositories
  lead within the fresh band; fresh unprobed repositories still precede the historical backlog.
- Retired non-paying farms remain excluded, and all offer, engineering evidence, competition,
  and release gates remain unchanged.
- `HYDRATION_WINDOW` now records the number of current-cycle hits in the queue and the number
  actually selected, so a live run can prove whether fresh results reached the bounded worker.

## Local verification

- `python -W error scripts/test_queue_ordering.py` — 22 passed, including fresh-hit priority
  across repositories and lanes.
- `python -W error scripts/test_dispatcher_horizon.py` — 16 passed.
- `python -W error scripts/test_actions_migration.py` — 34 passed, one Windows-only newline-path
  case skipped because Windows disallows that filename.
- `python -W error scripts/test_icu_pipeline_suite.py` — all 16 sections passed, 100% green.
- `python -W error -m py_compile scripts/actions_dispatch.py scripts/test_queue_ordering.py` —
  passed.
- `git diff --check` — passed (Git printed only its informational LF-to-CRLF conversion notices).

## Live verification status

The baseline run above confirms raw search supply and zero qualified admissions. A post-deploy
discovery run is still required to verify that fresh current-cycle hits are selected from the
backlog, then whether any meet the unchanged quality gates. No qualified influx or verified PR
is claimed by this repair record yet.
