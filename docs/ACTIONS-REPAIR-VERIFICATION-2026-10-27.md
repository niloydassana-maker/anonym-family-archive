# Actions migration: repair verification and remaining acceptance

This is a repair supplement to [the full migration audit](ACTIONS-THREE-LAYER-E2E-AUDIT-2026-10-27.md) and [repair path](ACTIONS-MIGRATION-REPAIR-PATH-2026-10-27.md). It distinguishes tested infrastructure from actual qualified work and completed delivery. It does **not** declare the influx + quality + hard issues + live receipts objective achieved.

## Deployed repairs

| Area | Result and evidence boundary |
|---|---|
| Correct agent executable | Install `cline@3.0.74`, not the package exposing `clite`. The live canaries executed Cline successfully. |
| Provider and native tools | Reuse the worker's OpenAI-compatible gateway, preserving messages, tool definitions and tool results. BOM-normalized credential loading. Live model/tool round trips succeeded. |
| Cline first after claim | The Actions adapter calls Cline intake before project preparation. Cline reads manifests, lockfiles, setup docs and CI and owns installations, configuration and the native plan. There is no host-selected npm/pnpm installation before intake. |
| Native verification | Independent host execution of the untouched baseline, builds, full native test plan, linters and formatting checks. Failed commands, warning receipts, explicit zero-test output, no-op and lockfile-only changes block publication. No synthesized success prose. |
| Real regression | New companion tests run against restored upstream product bytes and then the actual fix. A specific defect assertion must fail on the base and pass on the fix. Existing master tests and verification scripts remain protected. |
| Repair and retention | Three bounded delivery turns retain edits and return actual errors to Cline. Universal Cline turn timeout is 3,600 seconds. ZIP checkpoints retain tracked patches and new companion files. Retry can restore the previous run artifact; a stale checkpoint is retained for explicit Cline reconciliation. |
| Artifact survival | Claim, engineering and publication artifacts upload with `always()` and 14-day retention. The engineering step has a 300-minute limit within a 330-minute job, leaving time for artifact upload. This is not unlimited retention or a guarantee after abrupt runner loss. |
| Full context | Task events carry validated identity, not truncated issue JSON. The worker fetches full issue text and comment pages. A >50k-character context is covered by the contract suite. |
| Stale comment counters | REST issue counters were observed to exceed the accessible comment connection. The adapter independently checks GraphQL visible count and terminal comment ID before accepting completeness. It does not invent missing comment bodies. |
| Three lanes, one standard | Normal, startup and founder entrypoints use one dispatcher and admission contract. No severity-to-dollar conversion. Funding requires issuer evidence and an actual amount; foreign currency uses an observed quote. Hard technical scope, original source and current competition are checked. |
| Global horizon | Global queries have no repository-owner or language restriction. Persistent creation-time partitions address the search ceiling, and pagination is not limited to page one. Fresh searches run alongside historical partitions. |
| Durable backlog | Search results persist before advancing their horizon. Each cycle hydrates a bounded batch, retaining the remainder. Qualified candidates not dispatched remain queued. Admission-code changes invalidate cached rejections so a repaired gate does not preserve stale zero results. |
| Claims and delivery state | Canonical original-issue identity, control-branch compare-and-swap, run ownership and bounded retries replace uncorrelated local `DISPATCHED` rows. Live claim contention still needs a genuine task receipt. |
| Publication | A separate job validates Git objects, source hashes, exact upstream parent, one task commit, baseline and final receipts. Funding, current upstream and competition are checked again. Initial pushes are not forced. Updating an owned PR requires the exact previous head through `--force-with-lease`. |
| Remote follow-through | Reconcile the actual PR head and current checks/statuses. Pending checks and maintainer approval do not regenerate code. Actual failures can return the same owned PR to bounded Cline repair. Missing checks are recorded explicitly. A merge, not merely a dispatch, is `DELIVERED`. |
| Inputs and credentials | Workflow inputs are parsed from event JSON, not interpolated into shell commands. The engineering job receives no publisher PAT. Removing variables from ordinary child environments is **not** a hostile-code sandbox; Cline retains the requested provisioning freedom. |
| Archive checkout | Live deployment exposed an existing gitlink without `.gitmodules`. Its actual repository URL is now registered, and harness checkouts are restricted to scripts, workflows and that metadata. |
| Legacy launchers | The old live pipeline entrypoint and three hunter scripts route to Actions. The four-worker launcher dispatches cloud work. The former Kaggle worker is reused as a library; Kaggle is not launched. |
| Collector | Enumerate every untracked file with NUL-safe Git status. Preserve rename sources, Unicode and newline names; do not treat a directory as a file. Path collection is explicitly not verification. |

## Live receipts

- [Final delivery/gateway canary on `5bc9023`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40530525138): **success**. Earlier successful canaries: [40528748332](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40528748332), [40525139616](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40525139616).
- The retained gateway receipt records `deepseek-v4.1-flash:free`, HTTP 200, two completed model requests, eight forwarded tool definitions and one forwarded tool result. These are actual provider/tool observations, not an issue-delivery receipt.
- [Linux contract run on `5bc9023`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40530523348): **success**, including the new 31-case suite and unchanged partition, delivery-ownership and ICU suites. [Final Linux contracts on `5c4811c`](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40531287767) also passed: 32 new cases, including cache invalidation and pending maintainer approval, plus all unchanged suites.
- [First live three-lane discovery](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40528756264): **success as a discovery execution**, 2026-10-27 15:15:28 UTC. Returned rows before deduplication: normal 611, startup 598, founder 33. Durable store: 605 unique source issues, 60 checked, **545 pending**. Qualified/dispatched: **0/0**.
- [Second live discovery](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40529552133): **success as a discovery execution**, 15:19:33 UTC. It restored the previous cache, processed another 60 sources, and retained **525 pending** after adding new search results. Qualified/dispatched: **0/0**. This demonstrates resumption, not qualified influx.
- A separate global `label:bounty` search observed **4,336** open results; the saturated partition was split rather than represented as a complete result set. This count is raw supply, not eligible work.
- Actual issuer offers were recovered for SpaceApp issues #60 ($400), #62 ($750) and #63 ($600). Current open PRs #325, #328 and #324 respectively prevented competing work. They are not counted as dispatches.
- Live counter verification for `auscaster/frantic-board#540`: REST reported 60, REST returned 50, GraphQL visible count was 50 and its terminal ID matched the last REST comment. The resulting completeness decision is backed by both live API observations.

The first two deployment failures remain visible: [40524660843](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40524660843), [40524970510](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40524970510). Both exposed the archive gitlink issue; neither is presented as successful verification.

Latest code is `5c4811cf2b1b5b5aef34d6c7a1ab255392551e1c`. At handoff, [discovery run 40531780003](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40531780003) was running this revision, including comment-counter confirmation and policy-cache invalidation. Its outcome must be read live, not inferred from the two older zero-result runs.

## Local verification and reproducibility

Run from `D:\anonym`:

```powershell
python -W error scripts/test_actions_migration.py
python -W error scripts/test_partition_regressions.py
python -W error scripts/test_cline_delivery_ownership.py
python -W error scripts/test_icu_pipeline_suite.py
```

The current Actions migration suite has 32 cases. Windows skips the newline-filename filesystem case; Linux exercises it. The unchanged suites have 6 cases, 12 cases and 16 test groups respectively. Local `py_compile`, Ruff checks of the new adapters and actionlint validation passed. Existing master tests were not edited. Unit fixtures are explicitly labelled and are not counted as live receipts.

Raw evidence is local under `scratch/actions-repair-20261027/`; verification logs and command/SHA records are under its `verification*` directories. Earlier audit evidence is under `scratch/actions-e2e-audit-20261027/`. The accompanying repair receipt JSON contains a SHA-256 manifest of the repair evidence files. Credentials are not copied into the documents.

## Repair commit history

- `70a3256`: shared Cline-first Actions delivery, release guards, three-lane discovery and contract suite.
- `c265cb2`: restricted harness checkout; this alone did not resolve Git credential cleanup against the archive gitlink.
- `c7e2d79`: registered the actual existing gitlink; live checkout and canary then passed.
- `72ebc3f`: durable discovery backlog, exact checkpoint recovery, complete release feedback and publication reconciliation.
- `5bc9023`: independent visible-comment count confirmation after live REST/GraphQL comparison.
- `b78c061`: invalidate cached admission decisions when the policy is repaired.
- `5c4811c`: treat maintainer approval as pending rather than regenerating verified code.

The earlier audit commit is `13f18c2`; the comparison checkpoints are recorded in that audit. These are recovered code/log observations, not a claim that every minute of the previous 24 hours was continuously observed.

## Remaining acceptance: do not erase this boundary

The repaired infrastructure has live canary and test receipts. **Sustained qualified influx and a real hard-issue delivery through the new publication path have not yet been demonstrated.** There is no new verified bounty PR from these repair runs.

The next owner must continue the global backlog and fresh searches, audit remaining false negatives with original evidence, dispatch genuine funded uncontested hard issues, and observe Cline intake, untouched baseline, native verification, real red-to-green regression, publication and remote follow-through. Count discovered, qualified, claimed, blocked, published and merged work separately. Do not lower gates or invent prices to produce a nonzero number.

The original audit and this supplement are API/disk evidence. No authenticated browser screen receipt or direct control of the OpenCode session is claimed. DeepSeek receives the handoff prompt in the adjacent document; the user must submit it in the selected session.

## Supplement 2: four repairs, measured before and after

Seven consecutive discovery cycles had reported `qualified = 0` and `dispatched = 0`, and the
`candidates` table held 0 rows in every artifact. The four repairs below were derived from that
backlog rather than from a hunch, and each one is measured against live API data, both before and
after. `combined_goal` stays `NOT_YET_ACHIEVED`.

### 1. Instruction exfiltration was measured, then the rule was widened (not guessed)

The backlog contained repositories that pay a contributor to hand over the private preamble its
agent runtime loaded. Coverage of the previous two-phrase rule, and of the replacement, over the
same stored bodies:

| repository | before | after |
| --- | --- | --- |
| `ClankerNation/OpenAgents` | 14 / 201 | **201 / 201** |
| `UnsafeLabs/Bounty-Hunters` | 0 / 182 | **171 / 182** |

The 11 remaining `UnsafeLabs` documents read as ordinary acceptance criteria in the sampled text and
were left unmatched rather than forced. False positives were measured, not assumed: **0 / 40** known
funded issues across `Expensify/App`, `drizzle-team/drizzle-orm`, `limitlessprojects/Go-Hybrid` and
`oll4com/spaceapp`. A bare "system prompt" is deliberately not matched - an issue about editing or
forwarding a prompt is an ordinary bug report. `EXFILTRATION` is applied to the title **and** the
body; scanning the title alone missed the demand whenever the title was innocent.

### 2. A documented paying programme was invisible because its attestation comes from a bot

`Expensify/App` has merged 40,729 of 49,272 pull requests and pays on a `[$N]` issue title, attested
by `melvin-bot[bot]` publishing a `https://www.upwork.com/jobs/~...` comment. `trusted()` refuses
that login on purpose (app identity, no repository association) and the title carries no
`bounty`/`reward` word, so every Expensify issue was rejected. `FUNDING_PROGRAMS` now records the
convention for that one repository, and the entry is only honoured once the repository's own
automation has published a payout artifact **on that very issue**.

Measured through the production path (`GitHub().issue_context()` then `admit()`):

- `Expensify/App#103403` - ADMITTED, USD 250, payer `melvin-bot[bot]`, `competition()` **clear**.
- `Expensify/App#94622` - ADMITTED, USD 250, payer `melvin-bot[bot]`.
- `Expensify/App#100290` - still `HARD_ISSUE_EVIDENCE_MISSING`.

Two corrections were found by testing this path and both are now enforced in code:

- **Funding authority is title-only for a programme.** An untrusted reporter could otherwise write
  "a bounty of $5000" in the body of a `[$250]` issue and be admitted at 5000. A programme amount
  must sit inside the title; a body amount is never funding authority.
- **The payer was mislabelled.** The verdict named the issue reporter as payer, stamping funding
  authority on a party who pays nothing. For a title-borne programme amount the payer is now the
  attesting login.

### 3. The queue could not reach a fresh candidate

`ORDER BY checked,rowid` reads oldest-first. With 3,131 rows at `checked=0` and
`HYDRATION_BATCH = 60`, a candidate found this cycle sat behind roughly 52 cycles of work, and the
six-hour re-queue pushed refreshed rows behind the same block. `queue_window()` now reads half the
window from the backlog edge and half from the newest edge; `INSERT OR REPLACE` gives a re-queued row
a fresh rowid, so a refresh is reachable immediately. A regression fixture reproduces the old
behaviour and asserts the fresh row is absent from it and present in the new window.

### 4. Farm repositories consumed 38.1% of the queue to reach one rejection

Of 3,311 queued rows, **885 (26.7%)** sat in repositories already rejected on merge history and
**1,261 (38.1%)** in 14 farm/trap repositories. Each was re-hydrated every cycle only to be rejected
afterwards. `repo_intent` now stores the verdict once per repository (7-day refresh, 150-repository
probe budget, largest share first), known farms are force-retired at insert time, and
`preferred_order()` puts repositories with measured merge history ahead of unknown ones while an
unprobed repository stays in the queue - absence of evidence is still never rejection.

### 5. The new supply lane, and whether it can actually be seen

The `programs` lane adds 7 expressions, each verified live to return results from a repository whose
merge history is real. Reachability was then measured through the production window rules, because
`query_window` refuses to hydrate a window whose total reaches 1000:

| expression | total | first-cycle behaviour |
| --- | --- | --- |
| `repo:Expensify/App label:External` | 432 | yields now |
| `repo:eclipse-mosquitto/mosquitto label:"Status: Available"` | 192 | yields now |
| `repo:stakwork/sphinx-tribes label:bounties` | 66 | yields now |
| `repo:stakwork/sphinx-tribes-frontend label:bounties` | 41 | yields now |
| `repo:keepassxreboot/keepassxc label:"bounty :moneybag:"` | 3 | yields now |
| `label:bounties archived:false` | 127 | yields now |
| `label:"Status: Available" archived:false` | 3,389 | deferred to horizon subdivision |

`#105153` (USD 175) is on the first page the Expensify window reads; the 432-item window paginates
fully, so `#103403` is reachable in the same cycle. `--lane` defaults to `all` and the cursor is
written with `INSERT OR REPLACE`, so the lane rotates through all 7 expressions.

### 6. What the yield actually is, and which gate binds

29 issues sampled across the verified paying programmes, through the production gate:

| verdict | count |
| --- | --- |
| `QUALIFIED` | 1 |
| `HARD_ISSUE_EVIDENCE_MISSING` | 26 |
| `CURRENT_ISSUER_OFFER_MISSING` | 2 |

The hard-evidence test is the binding constraint, at roughly 3.4% qualify rate. It was **deliberately
not loosened**: it is the "genuinely hard" requirement itself, and the remaining rejections were
re-checked against live source - `oll4com/spaceapp` fails on competing pull requests (54/40/34/31),
`mergeos-bounties` `[50 MRG]` parses to zero USD, `limitlessprojects/Go-Hybrid` "Bounty" carries no
USD, and `keepassxreboot/keepassxc#99` sits below the USD 80 floor.

### 7. Verification

- New deterministic suites: `scripts/test_program_offers.py` (15 cases) and
  `scripts/test_queue_ordering.py` (17 cases), wired into `actions-contracts.yml`; all 9 gated
  suites pass under `python -W error`, Ruff reports 0, the workflow parses.
- A real regression was caught by the existing gate and fixed: `discover()` unpacked three fields
  from a queue row that now carries five, which raised
  `ValueError: too many values to unpack` in `test_hydration_budget_keeps_every_unprocessed_search_result`.
  The read is now positional over the first three durable fields.
- Four suites outside the CI gate fail for reasons unrelated to these changes and are recorded
  rather than "fixed": `test_dispatch_transport_live_receipts.py` and
  `test_fleet_recovery_live_receipts.py` require fixture snapshots through environment variables,
  `test_deepseek_inbound_suite.py` requires a dedicated inbound TokenHarbor key pool, and
  `test_fleet_retry_policy.py` targets `kaggle_engine_worker`, whose Kaggle lane is retired.
- The diff touches only the exfiltration rule, the programme table, `admit()` eligibility and payer,
  the queue window, the repository pre-check, the query lane and the CI test list. `FLOOR`,
  `TRUSTED_BOTS`, the hard-evidence test and `competition()` are unchanged.

### 8. Boundary

A funded hard issue now passes the **full admission path** with competition clear, which had never
happened before these repairs. That is not a delivery. No qualified issue has yet been dispatched by
a scheduled discovery cycle, no pull request has been opened from this lane, nothing has merged, and
no payout exists. Qualified influx is not yet sustained across cycles. `combined_goal` therefore
remains `NOT_YET_ACHIEVED`, and discovery remains a lottery whose outcome is never revenue until a
payout is observed.

## Supplement 3: the first real dispatch, the two refusals it produced, and the stall behind them

Supplement 2 measured admission in isolation. This supplement measures the whole chain for the first
time, and every claim below is read from a run, an artifact or a source file - none is inferred from
a count.

### 1. The chain ran end to end, and then it stopped at engineering

| stage | receipt | outcome |
| --- | --- | --- |
| discovery | run `40554931565`, 17:57:43Z, sha `ff60885` | `qualified: 1`, `qualified_fresh: 1`, `qualified_unique: 1`, `dispatched: ["818bf873582db6114e20b66a7cdc8ee8"]`, `programs.raw: 659`, `pending_hydration: 3447` |
| dispatch | same run | `repository_dispatch` genuinely fired |
| claim | delivery run `40555464157`, 17:57:43Z | job `claim` = success |
| engineering | same run | job `engineer` = **failure**, no pull request |
| publish | same run | skipped (0s) |
| reconcile | same run | success |

The dispatched original, named from the artifact rather than from the log: **`Expensify/App#105153`**,
`"[$175] Web/iOS-Spend-Refresh-needed error not reappear when network requests fail"`, USD 175, payer
`melvin-bot[bot]`, signal `regression`. This is the first funded hard issue this lane has ever carried
past admission into engineering, so the repair of the `candidates` table (always 0 rows before
Supplement 2) is confirmed by real traffic and not only by a test.

### 2. The engineering failure was a correct answer punished as a fault

Cline ran 244.4s, exited 0, and submitted a **verified** report:

```json
{"action": "blocked",
 "reason": "Not a concrete, warranted code change: documented by the repository's own maintainer analysis as expected/by-design"}
```

The host then raised `RuntimeError('Cline preparation blocked: ...')` from
`run_cline_claim_intake`, which the workflow recorded as `FAILED_ENGINEER`. So a decision the contract
accepted was reported as a broken pipeline, and - measured below - the same issue stayed eligible for
the next cycle.

The attribution was read live from `gh api repos/Expensify/App/issues/105153/comments` (7 comments),
not from memory of the run log:

- declaring comment `6447058391`, `created_at 2026-10-27T16:09:17Z`,
  `https://github.com/Expensify/App/issues/105153#issuecomment-6447058391`;
- author login `MelvinBot`, account type `User`, `author_association: CONTRIBUTOR`;
- the sentence: `**Root Cause:** This works as designed. It is not a bug.`

A body-less stranger (`camesenin`, association `NONE`) merely corroborated it, so the stranger is not
the authority and is not treated as one.

### 3. Repair: the declared-by-design gate

`scripts/bounty_admission.py` now settles this at admission, before any run is spent.

- **Authority is the repository's own voice.** Bare `trusted()` refuses the issuing account here
  (`MelvinBot` is a `User` with `CONTRIBUTOR`, not a bot association), so authority is
  `trusted()` **or** a per-programme `automation_logins` entry that cites a read attestation. The
  `expensify/app` entry is scoped to that repository and cites comment `6447058391`.
- **Markers are declarative only.** Every bug report carries `Expected Behaviour`, and it states the
  *opposite* of this verdict, so that heading is never a marker. A later authoritative statement that
  it *is* a bug clears the verdict, and beats a stale label; labels are consulted only when no
  authoritative comment settles the question.
- **Measured, both directions.** Live, through the production gate:
  `#105153` -> `admitted=false`, reason `REPORTED_BEHAVIOUR_DECLARED_BY_DESIGN`, quote exactly
  `**Root Cause:** This works as designed. It is not a bug. ...`; controls `#94622` (83 comments) and
  `#103403` (96 comments) both still `admitted=true` at `250 USD`. The gate does not empty the backlog.

### 4. Repair: a verified refusal is terminal, not a failure

`scripts/kaggle_engine_worker.py` raises `PreparationBlocked(RuntimeError)` carrying the report;
`scripts/actions_delivery.py` catches it and writes `REJECTED_PREPARATION` with the declared reason and
the evidence block, and `finish()` preserves a `REJECTED_*` status instead of prefixing `FAILED_`. The
`engineer` job now publishes `outputs.verdict`, and `engine2.yml` arms `publish` only when
`needs.engineer.outputs.verdict == 'verified'` - a refusal can no longer reach the publication step at
all. The refusal is also excluded from `failures`, because it is not one.

### 5. Repair: a refusal is not re-dispatched (measured loop, then closed)

The fired cycle at 18:44:55Z re-dispatched **the same original** that had already been refused at
17:57:

```json
{"counts": {"normal.raw": 73, "startup.raw": 1588, "founder.raw": 25, "programs.raw": 107,
            "HARD_ISSUE_EVIDENCE_MISSING": 42, "CURRENT_ISSUER_OFFER_MISSING": 14,
            "unknown_or_competing": 3, "MIRROR_OR_NON_ENGINEERING": 1},
 "qualified_fresh": 0, "qualified_unique": 1,
 "dispatched": ["818bf873582db6114e20b66a7cdc8ee8"], "pending_hydration": 3137}
```

`qualified_fresh: 0` with a non-empty `dispatched` is the loop in one line. The durable record that let
it through is the control store's `FAILED_ENGINEER` - failures are retryable by design - and not a
carried candidate row, because CI runs with an ephemeral `BOUNTY_STATE_DIR=/tmp/bounty-discovery`.
The first draft of this paragraph said "the candidate table carried the refused original forward"; that
was an inferred mechanism and it was wrong. Correction recorded in Supplement 4, item 1. `scripts/actions_dispatch.py` now exposes
`retry_eligible(state)` - only a recorded `FAILED_*` may be re-dispatched, and a `REJECTED_*` is
counted separately as `terminal_refusal` instead of hiding inside `already_owned`.

Note the honest timing: this loop was measured *before* the gate was pushed, which is why it is
evidence that the repairs are needed rather than evidence that they failed.

### 6. A second refusal, a different class, and it is NOT covered by the gate above

Run `40559211885` (18:21:27Z) failed on **`xpex-systems-ai/GXEON-AI#452`**, also with
`action=blocked`, and the log states why: the issue is an external contest/documentation deliverable
("GXEON PAID-WORK #002 - TokenGems/Jupiter docs review"), i.e. *"a docs/contest research deliverable,
not a repo code change"*, and Cline noted an existing competing PR `#453`.

That is not a maintainer declaring "works as designed", so the by-design gate does **not** catch it.
The terminal-outcome repair converts its symptom (`FAILED_ENGINEER` -> `REJECTED_PREPARATION`, publish
disarmed, no `failures` entry) and `retry_eligible` stops it from being re-dispatched, but its
*admission* is still wrong: a task that asks for no change to the repository was admitted as a funded
hard issue. This is recorded as an **open, measured gap**, not repaired here, because a
"asks for a code change at all" rule needs its own measurement across the paying programmes before it
can be tightened without over-rejecting - the same discipline that kept `HARD_ISSUE_EVIDENCE_MISSING`
closed in Supplement 2.

### 7. The scheduler is genuinely stalled, and the cron is not missing

`.github/workflows/bounty-discovery.yml` does define `schedule: - cron: '*/15 * * * *'`. The default
branch is `master`, the file first reached it in `70a3256` (14:48Z), and workflow `398368410` is
`active` - not `disabled_inactivity`. At 18:33Z all nine runs visible for it were
`workflow_dispatch` (15:13Z through 17:54Z, one failure at 16:07Z). **Zero scheduled runs on an
active workflow with a valid cron on the default branch.** It is a measured scheduler stall, not a
configuration error, and it cannot be repaired from this repository.

### 8. Repair: a heartbeat that fires only when GitHub is genuinely silent

`scripts/discovery_heartbeat.py` decides from live state, and holds in every case where firing would
duplicate or race:

| condition | decision |
| --- | --- |
| any run `queued`/`in_progress` | `already_running` -> HOLD |
| last completed run younger than `--max-age-minutes` (45 = three missed `*/15` slots) | `fresh` -> HOLD |
| fired within `--cooldown-minutes` (20) | `cooldown` -> HOLD |
| `gh` probe errors | fail closed -> HOLD |
| older than the window, nothing running | `stale` -> **FIRED** |

Receipts are appended to `scratch/discovery-heartbeat.jsonl`; the cold run also refuses to stack a
second instance (mtime-based stale-lock takeover, deliberately not `os.kill(pid, 0)`, which routes to
`TerminateProcess` on Windows).

Proven live, not simulated:

```
18:33:10Z  dry_run  decision=fresh            newest run 39 min old   VERDICT: HOLD fresh
18:40:02Z  live     decision=stale            newest run 46 min old   VERDICT: FIRED bounty-discovery.yml
                    dispatch -> run 40562102584 (created 18:40:08Z, completed success 18:45:03Z, 4m55s)
18:40:18Z  live     decision=already_running  newest run in_progress   VERDICT: HOLD already_running
```

The third line is the anti-duplication proof: ten seconds after firing, the same decision function
refused to fire again. The limitation is stated plainly - GitHub exposes no API that creates a
`schedule` event, so a heartbeat-triggered run is a `workflow_dispatch`. It restores cadence; it does
not impersonate the scheduler.

### 9. Repair: a stale test that encoded a contract the code no longer has

`scripts/test_fresh_discovery_schedule.py` asserted that the `--live` CLI reaches `run_pipeline_cycle`,
which has not been true since the consolidation in `autonomous_icu_pipeline.main()` (L3915-3920
delegates to `actions_dispatch.main`). It failed at HEAD for that reason alone - it was never in the CI
gate, so nothing caught it. It now pins the real contract: validation of the explicit fresh setting, the
exact delegated argv for `--once` and `--daemon`, `run_pipeline_cycle` proven *not* called, and the
legacy non-live path still honouring the setting. 7 cases in 0.43s, offline, versus 263-542s of live
network work before.

### 10. Verification at this revision

- **13 gated suites, all green locally** under `python -W error`:
  `test_actions_migration` 32, `test_partition_regressions` 6, `test_cline_delivery_ownership` 12,
  `test_icu_pipeline_suite` (own summary format, exit 0), `test_discovery_breadth` 8,
  `test_admission_trust` 7, `test_repository_intent` 11, `test_program_offers` 15,
  `test_queue_ordering` 17, `test_by_design_gate` 19, `test_preparation_terminal` 13,
  `test_discovery_heartbeat` 19, `test_fresh_discovery_schedule` 7.
- CI gate widened from 9 to 13 suites; `discovery_heartbeat.py` added to the compile step.
- Ruff: **0 findings** across every touched file (three findings were raised and fixed: two unused
  imports, and a test that built a body it never fed to the gate - that one was made real instead of
  silenced).
- Both workflows parse, and the folded publish condition resolves exactly to
  `needs.claim.outputs.mode == 'deliver' && needs.engineer.result == 'success' && needs.engineer.outputs.verdict == 'verified'`.

### 11. Known limitations, stated rather than discovered later

- An authoritative comment reading "current behaviour is by design, but we should improve it" rejects an
  otherwise valid issue unless it matches a withdrawal marker. The gate reads declarative markers only.
- A `REJECTED_PREPARATION` issue is never retried. That is deliberate and consistent with `DELIVERED`,
  `CLOSED_UNMERGED` and `PUBLISHED_PENDING_CHECKS`, which are equally non-retryable; re-admitting a
  written verdict is the waste this repair exists to remove. Resetting the record is a manual act.
- The heartbeat is not yet installed as a scheduled task on the laptop. Until it is, its cadence is
  whatever a session exercises - the receipts above are a proof of correctness, not of standing
  coverage.

### 12. Boundary

The chain now reaches engineering, and engineering now refuses on evidence instead of failing. There is
still **no pull request, no merge and no payout**, and `combined_goal` remains `NOT_YET_ACHIEVED`. What
changed is that the pipeline no longer spends delivery runs to relearn verdicts it already holds, and it
no longer reports a correct refusal as a fault.

---

## Supplement 4: the first two refusals the live pipeline made on its own, audited against source

Cycle: **`40564874763`**, `workflow_dispatch` on `de8cc08e662ff989177f599bf74053e9872910b8`, started
18:58:27Z, completed **success** 19:00:44Z, 1 job (`discover`). This run was **dispatched manually to
observe the gate at cycle level**; it was not fired by the heartbeat, whose own receipts are in
Supplement 3 section 8.

Summary line as emitted:

```
{"at": "2026-10-27T19:00:39.762164+00:00", "mode": "LIVE",
 "counts": {"normal.raw": 598, "startup.raw": 806, "founder.raw": 32, "programs.raw": 33,
            "CURRENT_ISSUER_OFFER_MISSING": 17, "REPORTED_BEHAVIOUR_DECLARED_BY_DESIGN": 2,
            "HARD_ISSUE_EVIDENCE_MISSING": 38, "unknown_or_competing": 1, "CLOSED_OR_READ_ONLY": 2},
 "qualified_fresh": 0, "qualified_unique": 0, "dispatched": [], "pending_hydration": 3873}
```

Two admission refusals carried the new reason, on issues no human had inspected:

```
{"phase":"ADMISSION","repo":"limitlessprojects/Go-Hybrid","issue_number":940,
 "reason":"REPORTED_BEHAVIOUR_DECLARED_BY_DESIGN","reported_comments":3,"visible_comments":3}
{"phase":"ADMISSION","repo":"Ensrick/vermintide-2-tweaker","issue_number":760,
 "reason":"REPORTED_BEHAVIOUR_DECLARED_BY_DESIGN","reported_comments":13,"visible_comments":13}
```

A gate that refuses for a reason is making a claim about a human's words. Both were therefore read
back from the API and pushed through the production function (`scratch/_audit_by_design_two.py`,
`declared_by_design()` in `scripts/bounty_admission.py`), not judged by eye.

### 1. What the audit found, before any change

| issue | title | keyed sentence | authority | audit verdict |
|---|---|---|---|---|
| `limitlessprojects/Go-Hybrid#940` | *Triage Board (auto-updated daily - pin me)* | "**CI freshness:** 23/27 heads fully green. The 4 red-`quick` heads ... are a **stale-merge-ref artifact** ..." | `limitlessprojects`, OWNER, 2026-10-20 | **right refusal, wrong reason** - the issue is a status board, not a bug report, so nothing on it is a verdict about one behaviour. Its honest refusal reason is the hard-evidence gate it fails next, not a declaration of intent. |
| `Ensrick/vermintide-2-tweaker#760` | *[CWV] Outrider uses Kruber body animations on Saltzpyre* | "Closed/wontfix #627 records the rejected custom launcher model history." | `Ensrick`, OWNER | **wrong** - a pointer to another issue's label and history is not a statement about the behaviour reported here. |

Two defects, both structural rather than one-off typos:

- **D1, a pointer read as a verdict.** A bare `wontfix` in prose is overwhelmingly the name of a label or
  a cross-reference (`Closed/wontfix #627`), and the prose regex accepted it as a declaration.
- **D2, a board read as a bug report.** Nothing restricted declarations to issues that are actually
  reports, so a status bullet on an aggregate board could decide an issue's fate.
- **D3, found while reading the receipts: the quote could hide its own trigger.** The stored excerpt was
  taken from the start of the line, 240 characters, so on #940 it showed the CI-status bullet and cut off
  before the words that fired the gate. A receipt that does not show the trigger is not a receipt.

Why this matters more than the run it saves: a false by-design refusal **silently deletes qualified
influx**, which is the first thing this pipeline exists to produce. The `HARD_ISSUE_EVIDENCE_MISSING`
gate is measured as the binding one (38 refusals this cycle alone, 26/29 in the earlier sample); the
by-design gate must not become a second, quieter filter that removes real work.

### 2. Correction to Supplement 3 section 5 (recorded, not quietly rewritten)

Supplement 3 said the re-dispatch loop happened because "the candidate table carried the refused original
forward". That was an inferred mechanism and it was **wrong**: CI runs with
`BOUNTY_STATE_DIR=/tmp/bounty-discovery`, so no candidate row survives between runs. The durable record
that actually let the same identity through is the control store's `FAILED_ENGINEER`, which is retryable
by design. The repair (`retry_eligible()`) is unchanged and still correct; only its stated justification
is now exact. The paragraph in section 5 carries the correction inline.

Second measured instance of the loop, for the record: delivery run **`40562829637`** (re-dispatched at
18:44Z) completed **failure** at 18:57:40Z - claim success, engineer failure, publish skipped, reconcile
success - one full run spent relearning the same `blocked` verdict.

### 3. The repairs

- `scripts/bounty_admission.py`
  - **Prose regex:** bare `\bwontfix\b` removed from `BY_DESIGN`. A real `wontfix` label is still read,
    through `BY_DESIGN_LABELS`, which is where a label belongs. `won't fix` prose remains a marker
    because it is a declarative sentence ("We won't fix this").
  - **`cross_reference(body, match)`** and a `finditer` scan: a marker occurrence preceded by
    `closed/`/`labelled`/`tagged`/`per`/`see` or followed by `#123` is a pointer, not a verdict, and is
    skipped so a later genuine declaration in the same comment can still be read.
  - **`AGGREGATE_DOCUMENT`** (`triage board`, `auto-updated`, `pin me`): if the issue itself is a board,
    `declared_by_design()` returns `None` immediately - the question does not apply, and the honest
    reason comes from the gates that follow.
  - **`marker_sentence()`** now centres a long line on the marker instead of truncating from the start,
    so the stored quote always contains the words that fired the gate.
- `scripts/test_by_design_gate.py`: new class `PrecisionOnUnseenTrafficTests`, 5 cases - a pointer is not
  a verdict, a declarative `won't fix` still counts, a board title is excused, a board body is excused,
  and the quote always shows the marker. Suite 19 -> **24**.

### 4. Before and after, on the same live issues

| issue | before | after | note |
|---|---|---|---|
| `Expensify/App#105153` | `BY_DESIGN` | **`BY_DESIGN`** | true positive preserved; sentence "*This works as designed. It is not a bug.*", `MelvinBot`, `CONTRIBUTOR` |
| `limitlessprojects/Go-Hybrid#940` | `BY_DESIGN` | **`None`** | no longer decided by a status board |
| `Ensrick/vermintide-2-tweaker#760` | `BY_DESIGN` | **`None`** | no longer decided by a pointer to another issue |

The controls from Supplement 3 section 4 (`#94622`, `#103403` at `250 USD`) are unaffected: they never
matched a marker, and nothing here adds one.

### 5. Verification at this revision

- 13 gated suites under `python -W error`, **`TOTAL_BAD=0`**: 32, 6, 12, ICU (own format, exit 0), 8, 7,
  11, 15, 17, **24**, 13, 19, 7.
- Ruff: **0 findings** on `bounty_admission.py`, `test_by_design_gate.py` and the two adjacent files.

### 6. Boundary, unchanged

`dispatched: []` this cycle, so this supplement adds **no PR, no merge, no payout**. What it adds is a
gate that refuses on a sentence that actually exists and quotes it, and two measured false attributions
that will no longer remove real work from the queue. `combined_goal` remains **`NOT_YET_ACHIEVED`**.
