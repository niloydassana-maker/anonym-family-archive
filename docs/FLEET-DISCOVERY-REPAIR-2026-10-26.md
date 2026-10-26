# Fleet discovery and bootstrap repair, 26 October 2026

This report extends the [24-hour engineering work log](ENGINEERING-WORKLOG-24H-2026-10-26.md)
and the [fleet-idle RCA](RCA-FLEET-IDLE-2026-10-26.md). Times are Asia/Kolkata
unless explicitly marked UTC. Operational evidence is preserved locally under
`scratch/discovery-repair-r9-20261026/`; private credentials and database backups
are excluded from this commit.

## Findings

The earlier influx was not equivalent to a stream of executable paid engineering
work. The morning log recorded 61 first-sweep dispatches followed by two empty
sweeps; 19 of those records were NEXAITECHAU mirrors and 15 requested banking data.
Those categories must remain excluded. Conversely, real paid work was being lost
before the funding check could inspect authoritative comments.

Two independent dispatcher faults reduced supply:

1. The primary-key index in the delivery database contained 16 ghost entries.
   The preceding RCA preserved the database, rebuilt the index, and verified all
   196 real table rows remained unchanged. A quick SQLite check had missed this;
   full `PRAGMA integrity_check` detected it.
2. Commit `a510fc9` reduced each query from 1,000 results to 30 and rejected
   unpriced title/body search results. GitHub search results omit comments, where
   platform funding can be recorded. Recovered Cline monolith checkpoint
   `a376f67e47e58ad860139ee74f54437d5f692c25` used a 1,000-result search horizon.

The live counterexample is [magnus919/SlopSearX#271](https://github.com/magnus919/SlopSearX/issues/271).
It ranked 17th in the captured 30-result `polar.sh` sample, so increasing search
depth alone would not recover it. The old title/body filter rejected it, while an
authoritative comment supplied the parsed **$500** funding. The repaired
dispatcher enqueued it at 22:27:01 (event 195). Engine 1 claimed it and later
reclaimed it as attempt 2 after cancellation reconciliation.

## Repairs

### Discovery and state integrity

- Run a read-only full SQLite integrity check before trusting delivery lookups.
  An invalid database stops the dispatcher with a nonzero exit. The check never
  silently recreates or repairs records.
- Restore the default 1,000-result horizon, with `--search-limit 1..1000` available
  explicitly. The GitHub CLI performs pagination. Preserve grouped search text
  as one argument while retaining support for the legacy `--label bounty` query.
- Fetch issue and authoritative funding comments before applying payment and
  consulting-floor checks. Keep territory, authority, competition, and funding
  requirements intact.
- Exclude bot/discussion mirrors, archive records, program budgets, and banking
  collection requests before model or build work. Genuine source-code daily
  reviews remain eligible.
- Triage each issue once per sweep. Cache author corridor results only in
  `--anytime` mode; business-hours scheduling still evaluates current time.
- Reject unknown CLI flags. The former `--all-lanes` flag now fails clearly
  instead of appearing to enable a mode that did not exist.
- Treat an unavailable competing-PR query as a failed lookup, without permanently
  blacklisting the issue. A real open competing PR still blocks implementation.

### Native verification and provider startup

- Discover one unambiguous immediate-child Rust product workspace when no root
  ecosystem exists. Exclude example, test, benchmark, vendored, and symlink
  manifests; ambiguous roots do not invent a verification plan.
- Read a literal semantic-version `PINNED_RUST` from `tools/env.sh` when standard
  Rust toolchain files are absent. Never source the script or inherit its host
  paths. Install the declared toolchain and clippy, then invoke cargo with its
  explicit version selector and manifest path.
- Retry transient provider startup failures at most four times, with 30/60/60
  second waits. Report STARTING while retrying. Authentication and configuration
  failures remain closed, and ONLINE still requires a real tool round trip.
- Add a checksum-verified Go 1.26.9 bootstrap, including both `go` and `gofmt`.
  The archive hash was checked against the live official
  [Go release manifest](https://go.dev/dl/?mode=json&include=all). The worker probes
  both executables before advertising readiness.
- Install declared Python project dependencies and declared dev/test extras, or
  applicable requirements files, before pytest. Retain the repository's test
  command and coverage thresholds unchanged.

The prior collector, complete-payload transport, Node 22.23.4 bootstrap, and
universal 3,600-second Cline turn remain protected by the existing regressions.
No existing test suite was edited.

## Live verification and remaining task blockers

Go-Hybrid #186 exposed three distinct environment problems in order:

| Attempt | Observed result | Response |
| --- | --- | --- |
| 1 | No root native verification target discovered | Recognize the actual `compiler/Cargo.toml` workspace. |
| 2 | HYB build rejected rustc 1.99.1 against its 1.99.0 pin | Honor the repository pin without overriding its guard. |
| 3 | `cargo +1.99.0 test --manifest-path compiler/Cargo.toml --workspace` compiled, then failed because `gofmt` was missing | Add Go/gofmt bootstrap; preserve the failure and attempt count. |

The exact final test was
`tests::generate_one_ignores_stale_generated_hy_go_siblings_on_package_rename`.
Its message was `running gofmt (gofmt): No such file or directory (os error 2)`.
This is an environment prerequisite failure observed on untouched upstream,
not proof of a source-code defect. No fourth attempt was granted automatically.
The two earlier scoped controller authorizations required matching task/release,
manifest, fresh timestamps, and a cap no greater than three; they do not permit
bypassing test, ownership, security, or publication gates.

SlopSearX attempt 2 subsequently reached pytest, which exited 4 because the
configured `--cov` options were unavailable. Its `pyproject.toml` declares
`pytest-cov>=6.0` in the dev extra. The Python bootstrap repair installs that
declared extra; it does not remove the options or lower the 80% coverage floor.
This task has not yet earned a successful post-repair test receipt or PR.

At 22:50, authenticated Kaggle status checks found Engines 1, 2, and 5 in
`CANCEL_ACKNOWLEDGED`, while their old claims remained. The cause of cancellation
was not established. Events 221-223 recorded these terminal runtime facts;
attempt counters and cooldowns were retained. New versions 26/28/23 respectively
restarted them, and events 235/237/241 show attempt-2 claims for core#988,
SlopSearX#271, and core#992. All five latest kernels reported RUNNING at
22:56:26. Later heartbeats confirmed native verification for both core tasks.

The two `INVALID_TASK_JSON chars=20000` warnings are preserved historical records,
events 15 and 18, written at 17:27:18 and 17:27:47. Their digest prefixes match
the user's pasted logs: `f1a26372b3344e7d` and `086e95d2021f6fe9`. They are
diagnosed and never executed. Event 195 contains a valid **20,805-character**
SlopSearX payload, proving that current transport can exceed the former cutoff.
These corrupt historical records were not deleted or reconstructed.

### Bootstrap addendum rollout

After the final local gates passed, only idle Engines 1, 3, and 4 were updated:
versions **27, 29, and 34** respectively, completed at 23:04:29. The deployment
receipt records exactly the tested source hashes below. Engines 2 version 28 and
5 version 23 retain the earlier R9 build while their core-task compilations run;
they were not interrupted for this addendum. Thus all five carry the discovery
repairs, while the Go/Python bootstrap additions have a staged rollout.
Engine 1's actual startup log confirms both `go version go1.26.9 linux/amd64`
and `gofmt` validation, followed by a successful Cline round trip and ONLINE
registration (event 262). This log is saved as
`bootstrap-addendum/engine-1-startup-logs.json`.

Dispatcher PID 12176 remains active with `--live --anytime --search-limit 1000`
and dedicated stdout/stderr files. The sweep continues processing live search
results. Its live database passed the full integrity check after the repairs.

## Local gates and receipt index

Final local verification ran with Python warnings treated as errors:

| Suite | Result |
| --- | --- |
| `test_discovery_repairs.py` | 16 tests passed |
| `test_partition_regressions.py` | 6 tests passed |
| `test_icu_pipeline_suite.py` | All 16 integrity groups passed |
| `test_fleet_recovery_live_receipts.py` | 13 tests passed against preserved live receipts |
| `test_dispatch_transport_live_receipts.py` | 5 tests passed against preserved live fixtures |
| `py_compile` of the four changed Python files | Exit 0, empty stderr |

Receipt: `bootstrap-addendum/verification.json`, captured 23:01:08. Original
master and existing regression suites are unchanged. Unit fixtures exercise
failure branches; they are not presented as live network or successful task
receipts. Live logs and ledger events are stored separately.

Final tested file SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `scripts/autonomous_icu_pipeline.py` | `d6aab40d1b0f8c9f7b6f3c781c8a281bf17ad8b9e1bd48e5193752b2d0b90da8` |
| `scripts/kaggle_engine_worker.py` | `7fd889d6d3f7ec697cf767bee26dde7ccb9e4fa4e4f2aec1939b14afece15152` |
| `scripts/fleet_recovery_policy.py` | `ffe3ac034674be43ec590b3e3aadee27264ec66587b20f5338e51a4bcae62059` |
| `scripts/test_discovery_repairs.py` | `b3f5edd252df748a4101ab294992b939f5f1d9bbb469d126fb5070fc0f44ee10` |

Additional receipts: `recovered-comment-funded-task.json`,
`recovered-task-authentic-payload.json`, `queue-integrity-receipt.json`,
`cancelled-executions-reconciled.json`, `pinned-rust-revalidation.json`,
`gohybrid-attempt3-authentic-worker-logs.json`, `fleet-status.json`, and
`bootstrap-addendum/official-go-release.json`.

The deployment CLI emitted an outdated-client advisory (Kaggle 2.2.4 versus
2.2.5); deployment success is recorded independently. Passing local tests does
not imply every fleet task passed, nor that new PRs were published. No new
verified bounty PR is claimed in this discovery-repair report.
