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

## Follow-up: stale post-merge task and refreshed query exclusions — 2026-10-28

The live delivery receipt for [Expensify/App#101616](https://github.com/Expensify/App/issues/101616)
showed that it remained open during its payment window after its fix had already shipped. The
issue timeline links merged [PR #103877](https://github.com/Expensify/App/pull/103877), whose
`Fixed Issues` section names the issue; the PR was merged on 2026-10-26. Cline correctly
recognized that the requested behavior was already fixed, but only after the delivery run had
started. This was stale discovery/admission state, not an engineering defect in the task.

`competition()` now follows closed PR references from the issue timeline and blocks only when
the linked PR is merged and explicitly identifies this issue as fixed (in a `Fixed Issues`
section or a direct fixes/closes/resolves reference). A merged PR that mentions the issue only
as related remains non-blocking. Immediately before dispatch, the dispatcher also reapplies the
same server-query exclusions to the freshly fetched issue context. A candidate that became
assigned or acquired an excluded label while waiting in the durable queue is retired before
delivery.

### Verification receipts

- `python -W error scripts/test_actions_migration.py` — 38 passed; one newline-path test skipped
  because Windows does not permit newline characters in filenames.
- `python -W error scripts/test_icu_pipeline_suite.py` — all 16 sections passed, 100% green.
- `python -W error scripts/test_discovery_repairs.py` — 16 passed.
- `python -W error scripts/test_queue_ordering.py` — 22 passed.
- Ruff on the three changed Python files and Python byte-compilation — clean.
- Live GitHub `competition()` check for `Expensify/App#101616` returned
  `Issue already resolved by merged PR: https://github.com/Expensify/App/pull/103877`.

This closes the measured stale-resolution path and the stale-assignee/label path at dispatch.
It does not claim a new qualified task, dispatch, or verified PR; the preceding discovery
receipt still had zero qualified candidates. The next live discovery run must report its own
qualified, dispatched, and verified-PR counts before influx or delivery quality can be called
successful.

### Post-repair live cycle

Discovery run [40613382410](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40613382410)
completed successfully on repair commit `4e1dfa49a5a48a4422d925207d20b47d6e9d2736`. Its final
receipt recorded overlapping raw hits of programs 26, normal 864, startup 538, and founder 36;
admission recorded 37 `HARD_ISSUE_EVIDENCE_MISSING`, 50 `CURRENT_ISSUER_OFFER_MISSING`, five
`REPORTED_BEHAVIOUR_DECLARED_BY_DESIGN`, and eight `CLOSED_OR_READ_ONLY`. The cycle ended with
`qualified_fresh=0`, `qualified_unique=0`, `dispatched=[]`, and `pending_hydration=9465`.
Therefore Cline did not start for a new claim and no PR was produced in this cycle. The broad
search volume is real, but the receipt does not support claiming qualified influx or delivery.

The live refreshed issue check independently confirmed `Expensify/App#101616` is still open,
assigned to `wildan-m`, `inimaga`, and `FitseTLT`, with labels `External`, `Daily`, `Overdue`,
and `Bug`. `refreshed_query_exclusion()` returned `query_excluded_assigned`; the live competition
check independently returned merged PR #103877 as the fix. Both paths now have regression tests
and a live receipt. This demonstrates the stale task is blocked before another Cline run, while
the broader zero-qualified outcome remains unresolved.

## Follow-up: global bounty discovery and expired offer repair — 2026-10-28

The every-cycle priority query was still hard-coded to `repo:Expensify/App` and `$250`, despite
the rotating lanes already searching globally. That made the fast lane narrow and introduced an
amount-specific bias. It is now the global query `bounty in:title`; it contains no repository or
account qualifier. The common query compiler still adds `is:issue is:open is:public archived:false
no:assignee -linked:pr`, while the persistent horizon partitions creation dates from 2008 to the
present and splits any partition that reaches GitHub's 1,000-result ceiling. A separate last-seven-
days query brings fresh updates to the front of each bounded hydration window.

### Live breadth and yield

The exact compiled global priority query returned `total_count=347` from GitHub. Those are search
matches, not 347 payable tasks. The first 30 fresh hydrated matches from this query had 13
mirror/non-engineering refusals, 13 missing hard engineering evidence, three missing current
issuer-backed offers, and one false positive that the prior gate admitted. After the repair below,
that last row is refused too, leaving zero qualified rows in this measured 30-issue sample.

As a separate breadth probe, 11 global source/engineering queries (Algora, Polar, Opire, BountyHub,
IssueHunt, and technical bounty terms) returned 108 overlapping hits in total. The direct current
dispatcher admission gate was applied to four issues that an older predicate probe had accepted;
all four were refused with concrete reasons:

| Live issue | Current dispatcher result |
| --- | --- |
| `pursekeeper/api#31` | `CURRENT_ISSUER_OFFER_MISSING` |
| `angeloasante/Diaspora_AI_Visa_data#20` | `HARD_ISSUE_EVIDENCE_MISSING` |
| `UnsafeLabs/Bounty-Hunters#825` | `NON_PAYMENT_OR_INSTRUCTION_EXFILTRATION` |
| `paraloom-labs/paraloom-core#856` | `CURRENT_ISSUER_OFFER_MISSING` |

For example, `paraloom-labs/paraloom-core#856` contains “Reward tier: up to $150 USDC” in a
report authored by a user with no repository authority. The comment that mentions a payout wallet
is a claimant's comment, not an issuer commitment. The payer gate correctly refuses to infer a
funded offer from it.

### Expired issuer offer false positive

The one admitted row was
[`perria080925-bot/agente-bountie#1`](https://github.com/perria080925-bot/agente-bountie/issues/1),
an owner-authored `$500 USDC` bounty listing. Its body explicitly says `Deadline: 2026-10-07`, and
the owner’s later comment repeats that the deadline had passed while describing the code submission
as complete. The issue remained open and was recently updated, so GitHub's ordinary state and
recency qualifiers did not remove it. Before repair, `admit()` returned a funding proof for it.

`bounty_admission.py` now recognizes explicit ISO deadlines only in the issue or a funding-authority
comment. A deadline before the current UTC date returns `EXPIRED_OFFER`; a later trusted comment may
extend it, while an untrusted comment cannot extend or expire it. Same-day and future deadlines stay
eligible. A fresh live read of the exact issue and all comments now returns `offer_expired=true`,
`admitted=false`, `reason=EXPIRED_OFFER`.

GitHub's native issue search can apply its documented qualifiers and custom issue-field filters, but
free-text deadlines are not a universal issue field across arbitrary repositories. Therefore this
semantic check still requires the issue body and authoritative comments to be hydrated; representing
it as a standard query qualifier would be fictitious. The universal query itself is global and uses
all available server-side qualifiers before returning results.

### Verification receipts

- `python -W error scripts/test_program_offers.py` — 20 passed, including past/today/future dates,
  trusted extension, untrusted override, and the expired-offer rejection.
- `python -W error scripts/test_admission_trust.py` — 7 passed.
- `python -W error scripts/test_queue_ordering.py` — 23 passed.
- `python -W error scripts/test_discovery_repairs.py` — 16 passed.
- `python -W error scripts/test_engineering_evidence.py` — 14 passed.
- `python -W error scripts/test_markup_and_funding_gate.py` — 10 passed.
- `python -W error scripts/test_by_design_gate.py` — 30 passed.
- `python -W error scripts/test_actions_migration.py` — 39 passed; one Windows-incompatible
  newline-path case skipped.
- `python -W error scripts/test_icu_pipeline_suite.py` — all 16 sections passed, 100% green.
- `python -W error scripts/test_global_influx_queries.py` — passed against live GitHub, 11 broad
  queries and 108 overlapping results.
- `python -W error scripts/test_predicate_pushdown_live.py` — exited 0 with four candidates under its
  older gate; direct current admission checks refused all four as listed above.
- Ruff, Python byte-compilation, and `git diff --check` — passed. Git emitted only Windows
  LF-to-CRLF conversion notices before line-ending normalization.

This repair broadens the fast lane and closes one measured expired-offer false positive. It has not
yet produced a qualified dispatch or verified PR. The 347 search matches and 108 overlapping broad
query hits are raw discovery receipts, not proof of eligible influx; the next post-deploy Actions
receipt must show qualified work and a real verified PR before the goal is called achieved.
