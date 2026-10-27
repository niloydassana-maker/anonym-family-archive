# GitHub Actions migration: three-layer bounty pipeline audit

Audit date: 27 October 2026. Evidence capture: 13:39–14:04 UTC (19:09–19:34 IST). The closing API check still reported the same deployed SHA, 27 runs and latest run 40511749430.

**Verdict: the migration is operational at the event/job layer, but it has not earned an end-to-end pass under the influx + quality + live receipts + hard issues law.** The captured evidence establishes zero qualifying hard-issue deliveries. It establishes real dispatches, green jobs without engineering, and a retracted lockfile-only PR. Those are different outcomes.

This audit reviews discovery, qualification, dispatch, ownership, Cline/model transport, provisioning, repository changes, verification, publication, recovery and reconciliation. It includes all identified regressions in those paths, plus inherited defects and improvements. Production code and deployments were not changed during this audit.

Companion: [repair path](ACTIONS-MIGRATION-REPAIR-PATH-2026-10-27.md).
Machine-readable evidence: [audit receipts](ACTIONS-THREE-LAYER-E2E-RECEIPTS-2026-10-27.json).

## 1. Scope, versions and evidence limits

| Reference | Purpose |
| --- | --- |
| Recovered monolith <code>a376f67</code> | Original Cline engineering contract and historical comparison; not assumed defect-free |
| Repaired Kaggle worker <code>2ce3a85</code> | Pre-migration contract: Cline-first intake, dynamic native plan, recovery, lease and publication guards |
| Initial Actions migration <code>06b3f14</code> | Determines which losses were introduced at migration |
| Subsequent Actions changes <code>28faa87</code>, <code>747a827</code>, <code>e532f4d</code> | Dependency fallbacks, fork/push publication and token mapping |
| Deployed/current remote master <code>5920df2d897b853c7bff3db2f2f944767b2d37ed</code> | Main audited Actions version; local workflow bytes matched remote workflow bytes |
| Local startup and silo hunters | Untracked at capture; copied and SHA-256 hashed separately |

The run inventory contains all 27 runs returned by the repository Actions API, from 08:55:00 to 13:24:24 UTC on 27 October. Jobs and artifact inventories were obtained for all 27. Logs were available for 26; run 40487271448 did not return a usable log. The audit does not invent that run's internal outcome.

All network evidence was read-only: GitHub runs/jobs/logs/artifacts, issue bodies/comments, PR metadata/files, Git trees, searches, and npm registry metadata. No audit task, issue comment, PR or dispatch was submitted.

Raw evidence, baseline source versions, current local source copies, CSV snapshots and hashes are retained under <code>scratch/actions-e2e-audit-20261027/</code>. The SHA-256 manifest establishes captured-byte integrity, not the truth of an upstream claim.

Visual receipt limitation: the browser automation inventory returned no browser or app surfaces. No screenshot is claimed. The linked live API/run/PR receipts are available, but screen verification remains unperformed.

An uncommitted BOM-normalization edit appeared in local <code>tokenharbor_router.py</code> during the audit. Remote master remained <code>5920df2</code>. It is recorded as a pending local repair, not as a deployed or verified fix.

## 2. Live outcome receipts

| Observed metric | Actual result | Interpretation |
| --- | ---: | --- |
| Actions runs | 27 | 26 repository_dispatch; 1 workflow_dispatch |
| GitHub conclusions | 10 success; 10 failure; 7 cancelled | Job status alone does not establish delivery |
| Green runs with no changes and no PR | 9 of 10 | Confirmed false success at delivery level |
| Logs entering missing-Cline fallback | 17 | Launcher did not execute the intended Cline binary |
| Latest green runs with proxy BOM crash | 2 | Current deployed model path failed before engineering |
| PR directly linked by a run's actual output | 1 | paraloom-wallet #136; lockfile only; closed unmerged |
| Published artifacts | 0 across all 27 runs | No uploaded patch/checkpoint/native receipt bundle |
| Local ledger entries DISPATCHED_TO_ACTIONS | 14 | All 14 lacked PR URL, receipt URL and receipt digest |
| Startup CSV candidates | 13 | Discovery snapshot, not 13 qualified deliveries |
| Silo CSV candidates | 8 | Discovery snapshot, not 8 additional unique tasks |
| Combined startup+silo population | 15 unique issues; 6 overlaps | Summing lane counts overstates unique influx |
| Evidenced complete hard-issue delivery | 0 | No captured case meets the full conjunction |

### Receipt A: latest green job did no engineering

[Run 40511749430](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40511749430), target [airdropia/earn-ops #21](https://github.com/airdropia/earn-ops/issues/21), at deployed SHA <code>5920df2</code>:

- TokenHarbor failed with <code>JSONDecodeError: Unexpected UTF-8 BOM</code>.
- The launcher printed <code>Running local engineering repair fallback turn...</code>.
- It then printed completion without executing a fallback file.
- Collector: <code>No changes detected in worktree.</code>
- Publisher: <code>No verified files staged; skipping PR creation.</code>
- GitHub conclusion: success.

[Run 40508328803](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40508328803), target [xaviercallens/HiveMind #247](https://github.com/xaviercallens/HiveMind/issues/247), shows the same deployed failure chain.

### Receipt B: a real PR was not a real issue resolution

[Run 40502275358](https://github.com/isearchxsolve/anonym-family-archive/actions/runs/40502275358) at older SHA <code>e532f4d</code> created [paraloom-wallet PR #136](https://github.com/paraloom-labs/paraloom-wallet/pull/136).

- Cline again took the missing-binary fallback.
- Provisioning created <code>package-lock.json</code>.
- Collector selected that one file.
- Seven existing Vitest files / 107 tests passed, with a Vite deprecation warning.
- PR #136 added 12,725 lines in the lockfile and changed no product source or regression tests.
- It was closed unmerged at 12:19:06 UTC. The closing comment explicitly retracts the unverified automated lockfile commit.

The issue alleged a Rust defect at <code>src/wallet/privacy.rs</code>. The actual run's checked-out base was <code>1e79eec8fbe99cd7e1381f6971c855bdce883d41</code>. Its complete Git tree contained zero Rust files and no such path. This was also a task-to-codebase qualification failure.

Two other same-day PRs, [#131](https://github.com/paraloom-labs/paraloom-wallet/pull/131) and [#132](https://github.com/paraloom-labs/paraloom-wallet/pull/132), also contain only the same 12,725-line lockfile addition and are closed unmerged. Their publication is confirmed by the PR API; this audit does not attribute their creation to a particular successful Actions run.

Current <code>5920df2</code> excludes lockfiles from the collector. That specific earlier publication route has been addressed in source. The latest two runs still fail to execute Cline, so the complete delivery path remains unverified.

### Receipt C: wrong executable package

Live npm registry metadata:

| Installed/compared package | Version observed | Exposed executable |
| --- | --- | --- |
| <code>@cline/cli</code> | 0.0.13 | <code>clite</code> |
| <code>cline@3.0.74</code> | 3.0.74 | <code>cline</code> |

The workflow installs the first package; <code>run-cline.sh</code> checks for the second executable name. The live logs confirm that the check fails. Installing a package is therefore not a Cline readiness receipt.

## 3. Actual deployed topology and lane audit

~~~mermaid
flowchart LR
  N[Normal hunter: run_hunter_dispatcher.py] --> D[repository_dispatch]
  S[Startup hunter: startup_hunter_parallel.py] --> D
  F[Silo hunter: agentic_silo_hunter.py] --> D
  D --> A[engine2.yml: per-target concurrency]
  A --> P[Static npm provisioning]
  P --> C[run-cline.sh and text proxy]
  C --> G[Collector and masked native checks]
  G --> R[Fork, force push, PR]
  R --> J[Unconditional job summary]
  J -. missing durable completion callback .-> L[Local SQLite ledger]
  K[Legacy autonomous_icu_pipeline.py] -. still targets .-> Q[Old Kaggle relay queue]
~~~

One Actions workflow was listed: Engine 2. It can run different targets concurrently on hosted runners; it is not a deployed five-engine Kaggle fleet or the local four-worker script. Per-target concurrency serializes a target but is not a durable task outcome or retry ledger.

| Lane | Search queries | Current implementation and gaps |
| --- | ---: | --- |
| Normal | 15 | Platform/paid-term search; nominal $80 floor; dollar amount can remain absent; genuine payer verification is not invoked; hardness score is unused |
| Startup | 21 | Financial/auth/concurrency keyword ranking; no verified startup/funding-stage identity; severity-to-dollar fallback; CSV plus optional dispatch |
| Silo/founder | 17 | Agent/MCP/memory keyword ranking; no verified founder or silo ownership; severity-to-dollar fallback; CSV plus optional dispatch; source calls this “Layer 4” despite the current three-lane model |

The startup and silo scripts were untracked locally. Their names, hashes and snapshots are included in the evidence set. A fresh checkout of the audited remote commit cannot reproduce these two local dispatcher layers.

No normal/startup/silo hunter process was present in the captured local process inventory. A legacy <code>autonomous_icu_pipeline.py --once</code> preview and a local proxy were present. No bounty/hunter/silo scheduled task was found by the named-task inspection. This does not prove that no other external scheduler exists; continuous operation of all three lanes is not evidenced.

### Global horizon: live query measurements

All three queries are global across repositories, but every hunter requests only the first 25 newest results. None of these three hunters uses the repaired date-partition horizon or follows search pagination.

| Lane probe | GitHub total_count | Returned | Receipt implication |
| --- | ---: | ---: | --- |
| Normal: Algora commenter + bounty | 30 | 25 | Remaining older matches not visited by this request |
| Startup: bounty + wallet/solana/token | 1,763 | 25 | Only about 1.42% of this query's reported horizon retrieved |
| Silo: polar.sh + agent + bounty | 17 | 16 | Small raw pool; search index/count mismatch retained honestly |

These are raw API matches, not payable code tasks. GitHub returned <code>incomplete_results=false</code> for these probes. Repeating a newest-first first page does not traverse the rest of the horizon.

The nominal per-cycle retrieval ceilings are 375 normal, 525 startup and 425 silo rows before overlap. These are code limits, not observed qualified influx.

### Candidate quality: concrete counterexamples

| Captured candidate | Hunter claim | Live issue reality |
| --- | --- | --- |
| airdropia/earn-ops #20 | Startup score 175; silo score 230; $100 | Automated digest, with disabled payment pools; not an original funded engineering issue |
| airdropia/earn-ops #21 | Actually dispatched by normal lane | Superteam listings digest; no direct code repair contract for earn-ops |
| paraloom-wallet #135 | $300; financial risk | Researcher payout submission; amount inferred from “High”; reported Rust path absent from actual checkout |
| dsh-bounty #1840 | $150; “Zero Competition” | Completed intake pointing to another repository's existing PR #1068 |
| dsh-bounty #71 | $150 | Marketing materials, channels and reach statistics; not the required hard engineering work |
| dsect-net/quantum #288 | $150 | Mirrored tracker entry explicitly marked done / priority medium |
| relayhop/sn-monetization-runtime #1333 | $2,026 | Radar mirror of a weekly stock contest; no captured $2,026 issuer-funded code repair |
| WholeTroutMedia/open-source-bounties #1 | $500 | Another solver's sealed solution vault, not the original client issue |
| limitlessprojects/Go-Hybrid #2049 | $300 | Technically demanding proposal with applicant settlement instructions; no captured issuer-attested $300 offer |
| SlopDotCash/slopdotcash #1411 | Silo score 250; $500 | Broad remaining-work/MVP tracker; a discrete funded repair and amount were not established |

Potentially real programs also exist in the snapshot: Memanto's maintainer-posted $100 security challenge, Kendraio's historical $500 integration offer, and the $200 SST/Pulumi deployment challenge. Their existence is not a claim that funding is current, competition is zero, or delivery has occurred. For example, the deployment challenge explicitly requires real AWS deployment evidence and credentials. Old issues should be revalidated, not automatically discarded for age.

## 4. Findings and repair mapping

Evidence types: **LIVE** = observed in actual remote output/API; **SOURCE** = definite implementation behavior; **CONDITIONAL** = source risk whose exploit/runtime impact was not exercised.

| ID | Priority | Finding, impact and evidence | Repair |
| --- | --- | --- | --- |
| F01 | P0 | Wrong CLI package/executable. Workflow line 73 installs clite while launcher line 41 checks cline. Seventeen logs take the fallback. LIVE + SOURCE. | R1 |
| F02 | P0 | Deployed router cannot parse the BOM-prefixed secret. Latest two green jobs crash before model readiness. Local normalization is pending, not deployed proof. LIVE. | R1 |
| F03 | P0 | Failures and no-op are converted into success: failed Cline command is echoed away; missing executable/fallback file still completes; no-change collector exits successfully; native failures are swallowed. Job green is unsafe as a delivery signal. LIVE + SOURCE. | R1, R3 |
| F04 | P0 | PR and summary assertions are unconditional. Test success, production-vulnerability resolution, boundary checks and single-commit proof are printed without corresponding measured receipts. Startup/silo previews also assert completed work and passing tests before execution. SOURCE + historical published PR. | R3, R5 |
| F05 | P0 | Funding is manufactured or unproven. All hunters contain severity-to-dollar fallbacks. Normal also permits absent amount because its floor comparison only runs when an amount exists; parsed bounds are ignored. Payer authority and current original funding are not consistently established. LIVE + SOURCE. | R5 |
| F06 | P0 | Target component is not verified. Issue #135's Rust source did not exist in the actual base tree; root TypeScript tests passed while no product fix existed. A repository having “languages” is insufficient. Codebase API/parse errors can also fall through as eligible. LIVE + SOURCE. | R2, R5 |
| F07 | P0 | Untrusted event title/repository values are interpolated directly into shell source in “Resolve task inputs.” A title can contain shell syntax. Checkout also persists a PAT by default before untrusted dependency scripts run, and publication places it in a remote URL. The sibling harness/control files share the writable runner filesystem with target commands. No exploit was attempted; these injection/credential/control-integrity paths are source-confirmed. SOURCE / CONDITIONAL. | R0, R4 |
| F08 | P1 | Migrated proxy flattens message history, ignores tool-role results and tools/tool_calls, and fabricates a text-only finish_reason=stop response. Repaired Kaggle chat_completion preserved the native protocol. Structured tool execution is regressed; a live tool round trip is missing. SOURCE; impact requires the configured CLI protocol. | R1 |
| F09 | P1 | Cline-first preparation is lost. Project npm install/ci runs before Cline and may fall back to ignored lifecycle scripts or ignored failure. Package manager pins, workspace protocols and build approvals are not owned by Cline here. SOURCE; installation failures seen live. | R2 |
| F10 | P1 | Verification contract is lost. No untouched baseline, mandatory successful test receipt, build/lint/format gate, test-immutability check, or issue-specific red-to-green regression proof. if/elif checks only one of Node/Rust/Go; Python/Scala and other stacks can execute no tests and pass. SOURCE. | R3 |
| F11 | P1 | Repair feedback loop is lost. One ignored Cline turn replaces bounded engineering/test/repair turns and lifecycle supervision. A later failing native gate does not return diagnostics to Cline. SOURCE. | R2, R3 |
| F12 | P1 | Full-horizon traversal regressed to first-page scans. Search failures are often returned as an empty object, making API failure indistinguishable from zero supply. Comment funding hydration reads only five earliest comments, missing later offers or withdrawals. LIVE + SOURCE. | R6 |
| F13 | P1 | Hard issues are optional scoring, not admission evidence. Normal computes hardness and never uses it. Startup/silo accept candidates without technical signals; zero competition, freshness and supposed amount earn high scores. Their fixed language lists also exclude ecosystems such as Scala and Dart instead of letting Cline provision them. Digest scores prove the scoring distortion. SOURCE + CSV. | R5, R6 |
| F14 | P1 | Claim/dedup/result chain is incomplete. Normal marks DISPATCHED_TO_ACTIONS and delivered_at on event acceptance, without a run URL or terminal reconciliation. Startup/silo do not record successful dispatch into that ledger. Their run IDs omit repository/lane uniqueness; payload lane/proof is absent. Fourteen ledger rows remain un-reconciled. LIVE + SOURCE. | R4, R6 |
| F15 | P1 | Publication lost release checks. Actions does not recheck competition/current funding immediately before push/PR, does not enforce a verified base/tree/head receipt, does not prove a single commit relative to the intended base, and force-pushes. Fork parent/account is assumed. SOURCE; repeated attempts visible in run history. | R4 |
| F16 | P1 | Completed edits are ephemeral. No patch/untracked-file recovery artifact is uploaded on success, failure, cancellation or timeout. All 27 artifact lists are empty. Repaired Kaggle preserve_cline_edits and recovery journals are not wired into Actions. LIVE + SOURCE. | R4 |
| F17 | P1 | NUL safety is partial. Collector reads NUL status correctly, but decodes with replacement, strips filename bytes and writes a newline list; workflow reconstructs NUL using tr. Embedded newlines and non-UTF-8 names no longer preserve identity. Blocked changes are silently omitted rather than failing the source boundary. SOURCE; unusual-path cases not exercised against live tasks. | R3 |
| F18 | P1 | Context contract regressed. Fetch omits comments/timeline, fetch failure substitutes an empty object, and the prompt does not name the saved issue_context.json. There is no explicit 20k truncation, but complete funding, prior-failure and issue context is not assured. SOURCE. | R2 |
| F19 | P1 | Migration leaves multiple execution paths. Legacy dispatcher still targets the Kaggle relay; the new local four-worker script runs native preparation before Cline and hard-codes base main. It calls a missing build_scenario_test_matrix helper and supplies unsupported body= to commit_and_open_pr. This latent route is untracked and was not observed executing. SOURCE. | R0, R2 |
| F20 | P2 | Continuous operation, provenance and remote monitoring are missing. No per-lane receipt lineage, Actions completion callback, demonstrated three-lane scheduler, CI/review follow-up or tested recovery controller. force_recovery input is declared but unused. Summary target variables are not provided to its step. SOURCE + process/ledger snapshot. | R4, R6, R7 |

The source-boundary and credential findings are included because this workflow executes arbitrary third-party code and publishes with a repository PAT. They are material release concerns, not claims that a credential theft occurred.

## 5. Migration regression crosswalk

The comparison baseline is the repaired worker, not an indiscriminate return to the recovered monolith. The monolith already had defects such as a 300-second Cline turn and legacy proposal fallback.

| Contract | Repaired pre-migration worker | Actions at 5920df2 | Classification |
| --- | --- | --- | --- |
| Cline receives task first after claim | run_cline_claim_intake | Static project installation first | Regressed |
| Full issue/prior-failure file context | Complete JSON artifact | Partial fetch, unwired file, no prior failures | Regressed |
| Cline chooses pinned tools/package/test plan | Cited native plan and supervisor | npm manifest heuristic | Regressed |
| Compiler/test execution permitted | Permitted | Prompt contains no prohibition | Preserved in wording; runtime unusable |
| Native tool conversation | Intact chat_completion payload/SSE | Flattened text proxy | Regressed |
| Cline executable/read-only tool probe | Binary/configuration plus real tool result | Wrong binary name; no probe | Regressed |
| Universal Cline runway | 3,600 seconds | 60-minute step / 3,600-second timeout | Preserved nominally; no successful invocation |
| Parent/native verification budget | Bounded native commands | 75-minute total job; no independent native plan budgets | Reduced control |
| Node 22 checksum | Verified Node bootstrap | Verified Node 22.23.4 seen live | Preserved |
| New test directories | All untracked files, NUL status | All untracked files, NUL status | Original directory-crash repair preserved |
| Path identity through staging | Structured path arrays | NUL input becomes newline list | Regressed |
| No lockfile masquerading as fix | Genuine edited-file set and release gates | Earlier lockfile-only PR; latest collector excludes it | Historical regression; partial source repair |
| Untouched upstream baseline | Required before product edits | Absent | Regressed |
| No tests means no release | Successful native receipt required | Conditional block can run no tests and pass | Regressed |
| All relevant ecosystems | Cline-managed native plan | Single Node/Rust/Go conditional | Regressed |
| Builds/linters/zero warnings | Planned verification and warning gate | Not enforced | Regressed |
| Existing master tests protected | Explicit invariant and source checks | No machine-enforced invariant | Regressed |
| Multi-turn compiler/test feedback | Engineering repair loop | One ignored turn | Regressed |
| Edit backup before reset/failure | ZIP + digest + journals | No Actions artifact persistence | Regressed |
| Lease ownership before publication | Guarded at commit/push/PR | Concurrency group only | Regressed |
| Competition immediately before release | Rechecked | Search-time check only | Regressed |
| Verified base/head/single commit | Machine proof | Summary declaration | Regressed |
| PR transport recovery/idempotence | Resume verified publication | Force push / create once | Regressed |
| Actual command-derived PR receipts | Command/exit/duration evidence | Constant success prose | Regressed |
| Remote CI failure returns to Cline | monitor_delivery_checks | No monitor | Regressed |
| Terminal result reconciliation | Durable fleet result handling | Event acceptance remains terminal local state | Regressed |
| Global historical partitions | discovery_horizon persisted windows | New hunters never call it | Regressed |
| Dynamic ecosystem admission | Cline-managed tools without a language whitelist | Startup/silo fixed language lists; codebase lookup errors can pass | Regressed |
| Comment funding pagination/authority | Full issue hydration path | Five comments / weak actor matching | Regressed |
| Payer versus payee separation | Genuine ICU verification | Separate weak amount heuristics | Regressed |
| Independent parallel targets | Fixed fleet/shards | Per-target Actions concurrency | Migration improvement, not delivery proof |
| Durable lane source/version | Tracked common dispatcher/worker | Two local layers untracked | New reproducibility gap |
| Genuine hard issue admission | Earlier imperfect heuristic | Unused/optional scores | Inherited weakness, worsened by duplicated gates |

### Changes after the initial migration

- <code>06b3f14</code> already installed the clite package, masked native failures and accepted lockfiles. These are migration-introduced defects.
- <code>28faa87</code> added ignored-install-script/failure fallbacks. This made provisioning appear green while bypassing required dependency behavior.
- <code>747a827</code> enabled fork/force-push publication and constant founder-facing verification prose without restoring the pre-PR contract.
- <code>e532f4d</code> fixed token mapping. It did not fix Cline readiness or test gating. Run #40502275358 published the lockfile-only PR at this version.
- <code>5920df2</code> excluded lockfiles and wired a proxy start. It preserved the wrong executable package and introduced a live proxy-start failure on the actual BOM-prefixed secret. Both latest jobs still ended green without engineering.

## 6. Existing tests and coverage gap

These exact existing suites were run unmodified with Python warnings treated as errors:

| Command | Result |
| --- | --- |
| python -W error scripts/test_partition_regressions.py | 6 tests passed |
| python -W error scripts/test_icu_pipeline_suite.py | All 16 integrity groups passed |
| python -W error scripts/test_cline_delivery_ownership.py | 12 tests passed |

Before/after SHA-256 checks confirm those test files were unchanged. The fixtures are isolated tests, not live deliveries.

Their green result does not validate the migrated worker: the partition and ownership suites exercise the Kaggle implementation; the ICU suite exercises monolith helpers and mocked delivery. Source search found no corresponding tests of engine2.yml, run-cline.sh, collect-changes.py, report-result.sh or the three new hunter paths. The Actions workflow also does not run these harness suites. A second implementation can therefore bypass the tested contract while the old suites remain green.

## 7. Required standard for an earned pass

The law is a conjunction:

**qualified unique influx AND genuine hard engineering AND correct verified changes AND live delivery receipts.**

Each accepted task needs an original current issuer offer, payable amount/currency, correct repository/component, no active competing PR, and a concrete engineering problem. A severity label, a sponsor request, a donation goal, a digest's monetary figure or another solver's claim cannot satisfy that offer.

Difficulty must have a technical basis: relevant component, failure mechanism, state/protocol/concurrency/performance complexity and a reproduction/verification plan. Keywords and a score alone do not establish it.

An earned delivery links one task/attempt to the Actions run, harness SHA, full context digest, issuer proof, upstream base SHA, failing reproduction, passing final native build/test/lint commands, exact changed tree/head SHA, PR URL, remote checks and terminal ledger record. Existing tests must remain intact. Any unknown state remains unknown.

Per-lane metrics must report raw retrieval, hydrated original issues, qualified unique funded hard issues, claims, verified engineering, PRs and accepted/paid outcomes separately. Lane overlap is counted once. No numerical high-influx target or reliable qualified pre-migration rate was captured, so this audit does not manufacture one or relabel 15 questionable candidates as “high influx.”

The companion repair path maps every finding to an implementation stage and a proof obligation. Production completion must be judged against the repaired path's live receipts, not the count of green Actions badges.

## 8. Evidence index

Raw local evidence directory: <code>D:\anonym\scratch\actions-e2e-audit-20261027</code>.

Key files:

- <code>runs.json</code>, <code>outcomes.json</code>, <code>all-run-artifacts.json</code>: full run inventory and derived outcome accounting.
- <code>run-ID.log</code> and <code>run-ID-jobs.json</code>: actual job output and step conclusions.
- <code>pr-131/132/136.json</code>, corresponding files/comments JSON: source diff and closure evidence.
- <code>wallet-tree-at-run-base.json</code>: actual checked-out tree proving the missing Rust component.
- <code>npm-cline-cli.json</code>, <code>npm-cline-3.0.74.json</code>: live binary metadata.
- <code>live-query-metrics.json</code> and per-lane raw query JSON: current API horizon measurements.
- <code>startup_bounty_candidates.csv</code>, <code>agentic_silo_candidates.csv</code>, <code>candidate-wire-audit.json</code>: lane outputs and live source audit.
- <code>ledger-actions.json</code>: read-only SQLite status/receipt snapshot.
- <code>version-comparison.json</code>, <code>versions/</code>, <code>source-snapshot.json</code>: historical and local source provenance.
- <code>legacy-test-results.json</code>: exact commands, exits, output hashes and unchanged-test proof.
- <code>sha256-manifest.json</code>: captured evidence integrity.

Stable source references:

- [Deployed Actions workflow](https://github.com/isearchxsolve/anonym-family-archive/blob/5920df2d897b853c7bff3db2f2f944767b2d37ed/.github/workflows/engine2.yml)
- [Deployed Cline launcher](https://github.com/isearchxsolve/anonym-family-archive/blob/5920df2d897b853c7bff3db2f2f944767b2d37ed/scripts/run-cline.sh)
- [Deployed collector](https://github.com/isearchxsolve/anonym-family-archive/blob/5920df2d897b853c7bff3db2f2f944767b2d37ed/scripts/collect-changes.py)
- [Deployed result reporter](https://github.com/isearchxsolve/anonym-family-archive/blob/5920df2d897b853c7bff3db2f2f944767b2d37ed/scripts/report-result.sh)
- [Repaired pre-migration worker](https://github.com/isearchxsolve/anonym-family-archive/blob/2ce3a85/scripts/kaggle_engine_worker.py)

Audit completion means this report and its evidence were prepared. It does not mean the pipeline passed or that the listed repairs have been deployed.
