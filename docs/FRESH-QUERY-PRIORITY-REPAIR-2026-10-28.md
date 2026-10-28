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

The post-deploy discovery run [40608596686](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40608596686)
completed successfully on `9016ef500b5534d4a15ce46744fd11647358310a`. Its hydration record was
`queued=1985`, `selected=60`, `current_cycle_hits_queued=6`, and
`current_cycle_hits_selected=6`. This is a direct receipt that all six new-cycle hits in the
queue reached the bounded inspection window.

The run still produced `qualified_fresh=0`, `qualified_unique=0`, and `dispatched=[]`, with
`pending_hydration=7136`. The 60 inspected candidates were rejected by the unchanged gates:
28 lacked hard issue evidence, 25 lacked a current issuer-backed offer, one was closed or
read-only, three were mirror/non-engineering, and one had a competition/unknown result. The
repair fixed backlog starvation; it did **not** produce a qualified task or a verified PR.

The live search receipt also shows why the next iteration must improve source/query yield rather
than alter admission: this cycle's scheduled queries returned many broad historical matches
(`label:bounty "$200"` total 91 and `label:bounty "$500"` total 49), while the currently updated
subset was small. The sampled issues did not carry enough current payer and engineering evidence
to pass. We have not yet demonstrated a live query that returns a candidate meeting every gate.

## Follow-up: repair one measured false-negative

Live GitHub reads on 2026-10-28 found `microg/GmsCore#2994`, an open, unassigned RCS bounty
issue titled `[BOUNTY] RCS Support [14999$]`. Its maintainer comment
[#issuecomment-4643350506](https://github.com/microg/GmsCore/issues/2994#issuecomment-4643350506)
describes RCS as an entirely new feature "(not a bug fix)". The prior `BY_DESIGN` expression
matched the shorter substring `not a bug`, incorrectly treating the task description as a
maintainer verdict that the reported behaviour was intentional.

The expression now excludes both `not a bug-fix` and `not a bug fix` while retaining the bare
`not a bug` verdict. A regression case uses the exact live maintainer sentence. Verification
against the live issue and comment now returns `live_declared_by_design: null`; the existing
bare-verdict test still returns `BY_DESIGN`.

This issue is **not** eligible for dispatch: live GitHub data shows open draft PR
[#3924](https://github.com/microg/GmsCore/pull/3924), which explicitly says it is related to
`#2994`. The competition gate keeps the issue out. This precision repair produces no dispatch
for the measured issue and is not counted as influx.

The live BountyHub search `commenter:bountyhub-bot is:issue is:open updated:>=2026-10-21`
returned four issues: `react/react#37620` and three `microg/GmsCore` issues. Inspecting the React
result found a `$100` BountyHub comment but also 12 open PR search matches for the same issue,
including existing fixes. It is likewise preempted. BountyHub's documentation says its comments
mark bounty creation/reward events, creators may choose pay-in-advance or pay-on-solution, and
retraction is available when there is no open claim
([creator docs](https://www.bountyhub.dev/en/docs/create-bounty),
[platform description](https://www.bountyhub.dev/en)). These samples do not justify a global
`bountyhub-bot` payer exception: a safe source integration also needs to verify current bounty
status and reward amount, not just trust a historical comment.

### Verification receipts

- `python -W error scripts/test_by_design_gate.py` — 30 tests passed.
- `python -W error scripts/test_admission_trust.py` — 7 tests passed.
- `python -W error scripts/test_engineering_evidence.py` — 14 tests passed.
- `python -W error scripts/test_markup_and_funding_gate.py` — 10 tests passed.
- `python -W error scripts/test_icu_pipeline_suite.py` — all 16 sections passed, 100% green.
- Live GitHub reevaluation of issue `#2994` and maintainer comment `4643350506` returned no
  by-design verdict; live PR `#3924` remains open and related.

This follow-up repairs one confirmed precision bug. It does not claim a qualified task or a
verified PR; discovery still needs a live candidate to pass the complete unchanged quality and
competition gates.
