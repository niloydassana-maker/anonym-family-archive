# Dispatcher repair and Cline ownership — 27 October 2026

## Contract

The production sequence is **claim → Cline**. Cline receives the complete issue,
repository identity, and previous failure context. Cline owns package-manager
selection, versions, installation, configuration, and the native verification plan.
The worker independently executes that plan and retains publication, competition,
claim-ownership, and receipt checks.

No issue-specific Bun, pnpm, Scala, JVM, or SDK installers were introduced. The
experimental language-specific resolver was removed in favour of Cline ownership.

## Dispatcher findings and repairs

- The CLI treated a combined quoted query as a different literal search. The live
  grouped query "will pay" "fix" returned zero; the repaired command boundary
  returned five sampled results. GitHub's REST API reported 3,399 open matches for
  the corresponding global query. Counts describe search matches, not funded jobs.
- Implicit comment-count and no-assignee restrictions, and the pre-2025 creation
  cutoff excluded legitimate discovery. Those defaults were removed.
- Date partitions persist across full scans and split searches at GitHub's
  1,000-result ceiling. Fresh discovery continues separately. This is incremental
  coverage; a complete crawl of GitHub has not been claimed.
- Funding in authoritative comments must be inspected even when an old body
  already contains an amount. A later withdrawal is not a current offer.
- Contributor payout requests containing platform URLs do not authenticate a
  platform actor. Known platform identities and repository-authority comments are
  handled separately.
- Severity names cannot manufacture dollar amounts. Volatile currencies without a
  quote remain discovery records, not automatically priced deliveries.
- Algora's standard demo-video instructions were being classified as a marketing
  task. Task-type predicates now inspect the actual issue request rather than
  platform payment/verification boilerplate.
- SDK/language keywords do not establish that an otherwise funded task is invalid.
  Runtime feasibility belongs to the Cline owner.
- Competition lookups now inspect up to 1,000 open PRs and block when that horizon
  is exhausted. The earlier 100-PR window missed older competing PRs.
- Search logs distinguish raw matches, retained candidates, filtering, and errors.
  A singleton prevents overlapping live dispatcher instances.

## Cline-first execution

The claim-intake function is the first task executor after a fleet claim. It gives
Cline a full context file, avoiding command-line argument limits and issue-context
truncation. Cline prepares the isolated upstream-based checkout and returns its own
native plan with repository source citations.

Production execution uses the Cline plan directly. It does not run the legacy
package-manager or test-plan detector over the prepared checkout. The worker then
executes the untouched baseline. Any failure returns to Cline with the complete
failure artifact. Model assertions do not substitute for native command receipts.

Implementation uses the existing verified engineering loop. Publication failures
can return to Cline without resetting completed edits. A frozen single commit can
be resumed after a transport failure. Remote check failures route back into the
engineering repair path; pending checks are recorded as pending.

Artifacts are retained under /kaggle/working/fleet-artifacts on Kaggle. A failed
preparation or collector retains recoverable edits and diagnostics.

## Honest live audit

The earlier queue admissions exposed invalid interpretations: a severity range,
a shared pool, hypothetical discussion amounts, historical payout requests, and
competition outside the first 100 PRs. Withdrawal records were acknowledged by
the fleet relay. Those records are **not** counted as qualified influx.

The subsequent source audit found:

| Source issue | Public offer | Observed competition check |
| --- | ---: | --- |
| [Omi #2316](https://github.com/BasedHardware/omi/issues/2316) | $1,000 | No matching open PR found |
| [Omi #2315](https://github.com/BasedHardware/omi/issues/2315) | $300 | No matching open PR found |
| [CaravanaCloud #3](https://github.com/CaravanaCloud/rinha-de-backend-2024-q1-impl/issues/3) | $50 | No matching open PR found |

These are public source observations. They are not payment, successful
implementation, or accepted-PR receipts. Funding and competition must be refreshed
at delivery time. Cline must report real external-input or hardware blockers.

## Verification and evidence

The unchanged existing tests plus new companion regressions passed:

- 78 unit/regression tests across eight suites.
- All 16 ICU integrity groups.
- Python compilation and Ruff with no findings on the changed source/test files.
- The tested source hashes were recorded and the same snapshot was staged.

The isolated tests explicitly distinguish fixtures and mocked Cline from live
fleet execution.

Local evidence directory: scratch/dispatcher-horizon-repair-20261027/

Key artifacts include verification-current.json, query-quoting-live.json,
live-search.json, issue-source audits, acknowledged withdrawals, and individual
test logs. Deployment and fresh claim/execution receipts are recorded separately.
Deployment acceptance alone is not proof that a worker completed a new task.


## Live rollout receipts (2026-10-27)

All five Kaggle push requests were accepted: Engine 1 v28, Engine 2 v29,
Engine 3 v30, Engine 4 v35, Engine 5 v24. The CLI emitted an outdated-version
notice (2.2.4 versus 2.2.5); this is disclosed separately from the clean local checks.

Engine 2 claimed filecoin-project/devgrants#2094 and logged
`CLINE_FIRST_AFTER_CLAIM` at 05:47:29 UTC, followed immediately by Cline with
a 3600-second deadline. Cline read the complete context and repository. A plan
command failure subsequently reached Cline's repair path. This demonstrates the
handoff and repair routing, not a verified implementation or payment.

A fresh funding and competition check admitted CaravanaCloud/
rinha-de-backend-2024-q1-impl#3 ($50 platform-attested bounty). The public queue
returned the full payload for task
`BT-1793080291-CaravanaCloud_rinha-de-backend-2024-q1-impl-3`.
The two Omi candidates did not pass the fresh open/fetch check and were not queued.
The withdrawn Kyo #392 offer received an acknowledged SKIPPED withdrawal.

Evidence: fleet-deployment.json, engine-2-live-cline-first.json,
qualified-influx-live.json, qualified-queue-echo.json, kyo-withdrawal.json.
These are in the local evidence directory listed above. A successful native run,
verified PR, and sustained qualified throughput remain unproven at this checkpoint.
