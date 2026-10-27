# Repair path: restore the delivery contract on GitHub Actions

Prepared alongside the [full migration audit](ACTIONS-THREE-LAYER-E2E-AUDIT-2026-10-27.md).

**Status: implementation path and acceptance backlog prepared; production repairs have not been executed by this audit.** The pending local BOM edit is not a completed migration repair.

The target is GitHub Actions with three dispatcher lanes: normal, startup, and silo/founder. Kaggle is retired as compute. The recovered monolith is a behavioral reference; the repaired worker at <code>2ce3a85</code> supplies stronger lifecycle controls. Do not restore its obsolete Kaggle bootstrapping or its old defects.

The success condition is simultaneous qualified influx, hard issues, engineering quality and live delivery proof. Increasing dispatches while accepting digests, inferred prices or no-op green jobs does not satisfy it.

## R0 — Establish one controlled execution path

Findings: F07, F19; prerequisite for every later stage.

Files: <code>.github/workflows/engine2.yml</code>, <code>scripts/run-cline.sh</code>, new Actions entrypoint/common lifecycle module, dispatcher entrypoints.

1. Pin the audited source and retain the current run/PR/evidence inventory before changing deployment.
2. Make publication depend on an explicit machine-validated release receipt. A no-op, absent model, failed test or unknown outcome must never enter the publisher.
3. Keep the three hunters as discovery adapters. Give them one common admission/dispatch client and one task schema. Retire their independent publication/execution routes.
4. Extract the repaired worker lifecycle into a platform-neutral module, or adapt it through a thin Actions entrypoint. Reuse its context, Cline intake, tool gateway, command receipts, repair supervision, recovery and release checks. Do not invoke the Kaggle worker main/bootstrap.
5. Retire or explicitly mark legacy Kaggle-relay and local four-worker launchers as unsupported deployment routes. The local four-worker script currently has incompatible helper calls and pre-Cline installation.
6. Treat event values as data: pass them through step environment variables or a JSON file and validate repository/issue identifiers. Remove direct GitHub expression interpolation from shell source.
7. Run third-party install/build/test code without persisted publication credentials. Use read-scoped access for discovery/intake and a separate guarded publisher credential. Set checkout credential persistence deliberately; avoid PATs embedded in Git remote URLs.
8. Keep the publisher and its validator in a fresh, trusted harness context. Target commands must not replace the harness scripts or supply self-asserted release proof through writable sibling control files. The trusted validator computes and checks source/test/HEAD receipts independently.

Required proof:

- A task cannot reach push/PR when its release receipt is absent, invalid or mismatched to HEAD.
- Shell metacharacters and multiline titles remain inert task data in isolated contract tests.
- Exactly one supported execution entrypoint is referenced by the deployed workflow.
- No third-party build step can read the publisher PAT from its environment or stored checkout configuration.

Rollback: retain previous artifacts and disable the new publisher if the contract tests fail. Compute remains on Actions.

## R1 — Restore an actual Cline and native tool round trip

Findings: F01, F02, F03, F08.

Files: <code>engine2.yml</code>, <code>run-cline.sh</code>, <code>tokenharbor_router.py</code>, the shared gateway.

1. Install a pinned package that exposes the intended executable. Registry evidence confirms <code>cline@3.0.74</code> exposes <code>cline</code>; <code>@cline/cli@0.0.13</code> exposes <code>clite</code>. Validate the selected version's actual help/configuration before adopting flags.
2. Require successful executable/version/configuration checks. Remove success echoes and absent-runner fallthrough.
3. Normalize UTF-8 BOMs at secret/file parsing boundaries, then validate the complete key-document shape without logging credentials. Exercise both plain and BOM-prefixed representations.
4. Restore the repaired gateway's intact messages/tools/tool_calls/tool-result forwarding and real response fields. Do not flatten the history into a generated-text prompt.
5. Health must prove usable key capacity and a healthy gateway, rather than merely any HTTP response. A failed readiness deadline exits nonzero.
6. Retain the verified Node 22 bootstrap and universal 3,600-second Cline turn. Make parent job and subsequent native verification budgets large enough to preserve that actual runway.
7. Preserve process exit codes, stdout/stderr and timeout reasons. No alternate model-generated proposal is substituted when Cline fails or produces no changes.

Required proof:

- On an Actions runner, the exact deployed CLI executes a read-only command in a real checkout and returns its actual output.
- Gateway receipts show forwarded tool definitions, returned tool calls and tool results on the same conversation.
- A real provider response is received through the configured gateway. Record model/provider/version and protocol receipt; expose no keys.
- Missing binary, malformed key JSON, unavailable gateway and timeout all produce failed/blocked jobs with diagnostics, never success.

Do not claim the model path repaired solely because the BOM unit test or HTTP health endpoint passes.

## R2 — Restore Cline-first task and environment ownership

Findings: F06, F09, F11, F18, F19.

Files: Actions entrypoint, shared Cline intake/supervisor, <code>engine2.yml</code>, <code>run-cline.sh</code>.

1. Acquire the task lease and give Cline the full issue/context artifact before project installation or host test-plan detection.
2. Fetch complete issue body, all relevant comments, funding/withdrawal and linked-PR context. Include prior attempt diagnostics and exact source URLs/digests. Never replace failed context retrieval with an empty object.
3. Cline establishes whether the original issue requests a payable, specific engineering change in this repository. It inspects the actual referenced component. It blocks an irrelevant/missing component, mirrored completion claim, marketing request, research proposal or payee submission with evidence.
4. Cline reads repository instructions, manifests, lockfiles, CI and setup documentation, and owns package manager/version selection, installations, repository-authorized lifecycle scripts, native dependencies, configuration and native test planning.
5. Use the repaired worker's cited preparation artifact. Validate command argv arrays and source digests; permit unfamiliar ecosystems. Installation and plan diagnostics return to Cline.
6. Preserve the source baseline during environment preparation. A genuine upstream product defect or missing external credential/hardware is an honest blocker, not a silently ignored failure.
7. Return native compilation/test/lint diagnostics to bounded Cline repair turns. Keep the full diagnostic file and completed edits; do not regenerate from a shortened generic failure.

Required proof:

- The first task-execution receipt after claim is Cline intake.
- Workspace-protocol, pinned pnpm/bun, Python and non-Node/JVM examples are routed through Cline's native plan in isolated tests.
- No fixed npm install or static ecosystem selector can terminate a project before Cline sees its issue.
- A live eligible hard issue has actual component/path evidence and a repository-derived native plan.

Minimal runtime installation required to launch Cline is distinct from project provisioning.

## R3 — Restore source integrity and genuine native verification

Findings: F03, F04, F10, F11, F17.

Files: shared engine/release validator, collector, <code>engine2.yml</code>, result/PR renderer.

1. Remove every native-verification failure suppression. A primary suite failing cannot be replaced by a smaller passing suite.
2. Run the unchanged upstream baseline before product edits. After engineering, run all required build, native test, lint and format commands selected from repository evidence; require zero warnings under the applicable repository gates.
3. Require issue-specific red-to-green proof and applicable negative/boundary/race cases. Demonstrate the defect on the actual base, then the fix at the proposed head.
4. Protect existing master tests and CI/integrity checks from weakening. Tests that merely assert the new implementation's own assumptions are insufficient proof.
5. Restore mandatory successful native test receipts. No tests discovered/executed, unsupported ecosystem, absent Cline, no product change or empty plan means no release.
6. Preserve path identity from Git status through staging using a binary NUL file or structured argv handling. Do not convert through newline lists, strip legitimate filename bytes or decode with replacement.
7. Validate worktree boundaries, symlinks, renames, deletions and all unexpected changes. Unsafe paths fail the run rather than disappearing from the commit.
8. Validate the exact final tree after tests. Freeze file/tree digests; stage only that same verified content. A file list captured before verification is not proof of the subsequently staged bytes.
9. A lockfile, Markdown/config extension or number of changed lines is not proof of an issue resolution. Require meaningful issue-linked behavior and verified regression coverage.
10. Generate PR/summary claims only from measured command and diff receipts. Remove constant “100%”, “production vulnerability resolved”, “single commit verified” and pre-execution true fields.

Required proof:

- A failing test, missing suite, compiler error, linter warning and changed-after-verification tree each block publication.
- The original new-directory collector regression remains fixed; spaces, Unicode, embedded newline, rename and deletion cases preserve exact identity.
- A hybrid repository executes all relevant suites. Python/Scala/other stacks are handled through their native plans.
- The lockfile-only failure in run 40502275358 cannot recur as an issue-resolution PR.
- Live final receipts name the command, cwd, exit, duration, base SHA, head/tree SHA and full log digest.

## R4 — Restore durable ownership, recovery, release and reconciliation

Findings: F07, F14, F15, F16, F20.

Files: common task/lease backend adapter, Actions entrypoint/workflow, dispatcher client, publisher/reconciler.

1. Use a canonical unique task identity keyed by original repository+issue and a unique attempt/run ID. Carry lane memberships separately.
2. Reuse the existing durable lease/recovery contract through an Actions backend adapter. The storage/controller must survive runner termination; an accepted event and a concurrency group alone are insufficient.
3. Atomically reserve before dispatch. Record the accepted event and reconcile it with the real Actions run ID. Update the same task through claimed, preparing, engineering, verifying, publication and terminal states.
4. Immediately before commit/push/PR, verify current lease ownership, current issuer funding/issue state and all relevant open competing PRs.
5. Prove the dynamic upstream default branch/base SHA, clean isolation, intended fork parent/owner, exact verified tree and one task commit. Do not hard-code main.
6. Replace unconditional force push with an idempotent publication flow. Recover an already-created matching PR after transport timeout; never overwrite unrelated or newer work.
7. Upload recovery evidence on failure/timeout/cancellation where Actions permits cleanup: binary tracked patch, untracked files, native logs, source/verification digests and context/plan journals. Persist checkpoints before long turns so abrupt runner loss has a recovery point.
8. Keep terminal outcomes honest: NO_CHANGE, BLOCKED_BASELINE, MODEL_FAILED, TEST_FAILED, PUBLICATION_FAILED, CHECKS_PENDING and DELIVERED must remain distinct.
9. Restore remote CI/review monitoring. Actual failures return to Cline with the verified checkout and exact diagnostics. Record pending/unknown checks without claiming success.
10. Write the result to the canonical ledger. Populate actual run/PR/receipt URLs and digests. A dispatch timestamp is not delivered_at.

Required proof:

- Concurrent normal/startup/silo attempts for one issue yield one owned execution.
- Retry after an acknowledged dispatch or PR-creation timeout does not create a duplicate.
- Lease loss and a newly competing PR block publication.
- A killed test/Cline turn has a recoverable artifact and an honest terminal state.
- A completed run updates the same ledger record, and a remote failing check triggers the recorded Cline repair path.

## R5 — Restore common funding, scope and hard-issue admission

Findings: F04, F05, F06, F13.

Files: one shared qualification module called by all three hunters, lane adapters, Cline intake.

1. Remove all critical/high/medium-to-dollar mappings. Parse actual monetary offers with currency precision and a real current FX source when needed.
2. Distinguish issuer/payer offers from researcher payout requests, applicant settlement instructions, donation milestones, budget metrics, grant applications and years in titles.
3. Verify the original current offer and authority/platform attestation from complete source context. Missing amount, ambiguous authority, withdrawal and unavailable proof remain ineligible/unknown.
4. Resolve aggregators to original tasks; do not execute the mirror. Reject completed intake/solution records, digests, marketing and prior submissions as work offers.
5. Verify the target repository/component exists and the issue's requested change actually belongs there.
6. Apply one monetary floor and one admission policy before a candidate leaves the search service. Price alone does not establish difficulty or engineering value.
7. Require structured hard-issue evidence: component, failure mechanism/constraint, reproduction or performance/protocol target, complexity basis and a verifiable acceptance plan. Optional keyword scores rank only candidates already meeting the contract.
8. Startup/founder lane membership needs evidence of the intended organization/product/owner characteristics. Unproven membership defaults to the general lane; it must not exclude an otherwise valid global engineering opportunity.
9. Replace pre-execution founder reports with plans and unknown states. Completed-work assertions appear only after measured execution.

Required proof:

- Every counterexample in audit section 3 is rejected or correctly resolved to its original eligible task.
- Genuine maintainer and platform-attested offers remain discoverable, including comment-only offers.
- No invented price, donor target, researcher payout wallet or irrelevant source path qualifies.
- A high score cannot admit a digest or a zero-hardness task.

## R6 — Restore global horizon, distinct lane influx and continuous operation

Findings: F12, F13, F14, F20.

Files: common search/hydration service, <code>discovery_horizon.py</code>, all hunter entrypoints, operational scheduler/reconciler.

1. Restore persisted disjoint time partitions and pagination. Split search windows at GitHub's result ceiling and retain cursors across restarts.
2. Preserve a fresh-created/updated lane while historical windows progress, so backlog work cannot stall new issues.
3. Keep repository coverage global. Do not substitute a few preferred accounts or a language whitelist for horizon traversal.
4. Push supported predicates into GitHub queries: issue state/type, visibility, archive state and justified label exclusions. Keep arbitrary funding/authority/source predicates in the common search service before it returns eligible records; GitHub does not execute local custom Python functions.
5. Hydrate all required comments and source evidence. API errors, incomplete results, unavailable codebase metadata and empty supply must have distinct counters and retry behavior.
6. Merge lane memberships by canonical original issue. Share atomic dedup/dispatch state and persist successful dispatch from every lane.
7. Track per-lane raw, hydrated, original, qualified funded hard, unique accepted, claimed, verified and delivered counts. Report overlap, rejection/unknown reasons, cursor depth and API error/rate-limit status.
8. Deploy an observable scheduler for all lanes and completion reconciliation. Verify its heartbeat and restart recovery. Do not infer a daemon from a script's existence.

Required proof:

- The live startup query reporting 1,763 results progresses beyond its first 25.
- Restart resumes the persisted next window; newly updated qualifying issues are still visited.
- Three lane memberships for one original issue create one task.
- Every accepted task has a run correlation and every completed run has a terminal result.
- Sustained rolling-window measurements establish both qualified influx and delivery quality. Raw matches and repeated old CSV rows are excluded.

## R7 — Close every regression with tests and live canaries

Findings: all, including the coverage blind spot.

Do not edit or weaken the existing suites to pass the migration. Keep the unmodified partition, ICU and ownership suites, then add tests that exercise the actual Actions entrypoint and every shared adapter referenced by the deployed workflow.

Required contract coverage:

- Executable identity, secret parsing, readiness, intact native tool round trip and nonzero failure propagation.
- Cline-first task context, pinned/dynamic provisioning, missing component, no-op and baseline failures.
- Real multi-ecosystem commands, mandatory test success, warnings, source integrity and immutable master tests.
- Exact path staging, preserved edits, cancellation/retry, duplicate dispatch and current lease.
- Funding/authority/negation, original issue resolution, hard admission and complete search horizon.
- Publication eligibility, exact verified commit, remote checks and terminal ledger reconciliation.

After isolated tests pass, deploy the pinned revision and perform:

1. A read-only live Cline tool canary on the Actions runner.
2. A real uncontested, issuer-funded hard engineering task selected through the common search service.
3. Full red-to-green/native verification, exact source PR review and remote-check reconciliation.
4. The same evidence chain for each dispatcher lane, without fabricating a task to satisfy a lane quota.
5. A sustained influx observation with distinct, current, funded hard issues and no repetition/false-positive inflation.

The audit has no trustworthy numerical pre-migration qualified-influx baseline. Establish and publish the real measured rate before using the word “high.” If a lane yields zero, retain that result and diagnose coverage/classification/source supply; do not lower the engineering or funding standards to manufacture volume.

Each live canary bundle must contain:

| Receipt | Required fields |
| --- | --- |
| Discovery/admission | Original URL, lane membership, current payer/funding proof, amount/currency, component and hardness evidence |
| Task/run | Canonical task ID, attempt ID, Actions URL, harness SHA, context digest and lease events |
| Engineering | Upstream base SHA, failing reproduction, Cline plan/tool receipts and actual source/test diff |
| Verification | Native command argv/cwd/exit/duration, full logs, immutable test proof and final tree/head digest |
| Publication | Current competition/funding/ownership checks, fork parent, one-commit proof and matching PR head |
| Completion | Remote check state, authoritative result/receipt URLs and reconciled terminal ledger record |

Only after these receipts exist can the repaired migration be called complete.

## Delivery order and closure map

| Stage | Depends on | Enables |
| --- | --- | --- |
| R0 | Audit snapshot | Safe single execution/publication boundary |
| R1 | R0 | Real Cline/model tools |
| R2 | R1 | Cline-owned issue/environment lifecycle |
| R3 | R2 | Earned source and native verification |
| R4 | R0–R3 | Durable verified publication and recovery |
| R5 | R0 | Correct common admission, prepared alongside worker repairs |
| R6 | R5 | Sustained global qualified influx and lane accounting |
| R7 | R1–R6 | Unmodified tests plus live proof of the complete conjunction |

R5/R6 discovery work can proceed alongside R1–R4 worker restoration. Publication remains dependent on the full release contract. This provides parallel progress without exchanging quality for volume.
