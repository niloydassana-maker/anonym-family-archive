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
