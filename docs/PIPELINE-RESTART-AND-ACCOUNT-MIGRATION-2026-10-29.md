# Pipeline restart and account migration — 2026-10-29

This document records why the autonomous bounty pipeline stopped, what was repaired, and how
the pipeline now runs under a different GitHub account. It is written to be read cold, without
the conversation that produced it.

---

## 1. Why the pipeline was dead

The pipeline was not broken by code. GitHub refused to start any job on
`isearchxsolve/anonym-family-archive`:

```
The job was not started because recent account payments have failed or your spending limit
needs to be increased. Please check the 'Billing & plans' section in your settings
```

Evidence:

| run | workflow | result | duration |
| --- | --- | --- | --- |
| 40842026273 | Actions migration contracts | failure (never started) | 3s |
| 40842046464 | Bounty discovery and reconciliation | failure (never started) | 3s |

Every run after commit `ff531dc` failed this way, including scheduled discovery runs. The job
logs do not exist at all (`log not found`), which is the signature of a job that never
executed rather than one that ran and failed. `ff531dc` itself had succeeded, so the outage
began shortly before 08:25Z on 2026-10-29.

**A 3-second failure is unambiguous**: a real test failure takes tens of seconds because the
compile and suite steps run first.

---

## 2. What was wrong with the code (independent of billing)

An audit of the F1–F12 blueprint implementation found that 8 of the 12 fixes had no acceptance
suite, so the earlier claim of "zero implementation gaps" was never checkable. The misleading
"verification" was `scripts/audit_complete.py`, which substring-matches against
`D:/anonym/scripts/*` — a **different path** from the repository it sits in — and asserts
things like `'validate_preparation(' in d2`, which the function's own definition satisfies.

Three latent runtime defects were found by writing the missing suites:

1. **`actions_dispatch.velocity_sort_key`** — the live sort compared `None` to `int`. The first
   repository whose velocity probe failed would raise `TypeError` and abort the whole dispatch
   cycle.
2. **`actions_delivery.preflight`** — `check_disk_space` and friends returned `(ok, detail)`
   while `preflight` unpacked `(subsystem, ok, detail)`, so **every delivery run reaching
   preflight raised `ValueError`**, which the host records as an *engineering* failure.
3. **`failure_digest.refusal_reasons`** — referenced an undefined name (`k`), raising
   `NameError` on any receipt carrying a refusal, so the digest could never have produced its
   refusal table.

### Behaviour gaps closed

| fix | before | now |
| --- | --- | --- |
| F5 lease | fixed 1800s + 300s grace, shorter than a legal 14400s run | derived from `CLINE_TOTAL_BUDGET_SECONDS`, floor preserved |
| F5 sweeper | absent entirely | `sweep_stale_runs()` proves death, cancels, releases with `FAILED_RUNNER_SHUTDOWN` |
| F5 takeover | `previous_owner`/`previous_status` only | plus `takeover_reason`, `takeover_at` |
| F6 budget | ordering only | `preparation_budget_seconds()` + payload → `PREPARATION_BUDGET_SECONDS` |
| F7 headroom | step aborted the run on `swapon` failure | `set +e`, best-effort, says so |
| F7 preflight | raised `ValueError` on every run | returns `(subsystem, ok, detail)`; classified as `InfrastructureFault` |
| F10 patch download | no `download_patch` at all | `download_patch()` with `submodule.recurse=false`; malformed `.gitmodules` → `InfrastructureFault("submodule")` |
| F3 boundary | typed errors escaped `supervise()` unhandled | classified by name, journal preserved |
| F12 digest | `NameError` on refusals | fixed |

### Suites added

`test_claim_lease.py`, `test_dispatch_velocity.py`, `test_preflight.py`,
`test_download_patch_submodule.py`, `test_heartbeat.py`, `test_code_change_class.py`,
`test_refusal_census.py`, `test_failure_digest.py` — plus `test_f9_class_gate.py` wired into
CI for the first time.

`test_f9_class_gate.py` had been excluded because it hardcoded the absolute Windows path
`D:/anonym/scripts/...`; it now resolves relative to its own file, which is what made it
portable enough to gate.

The contract workflow now runs **27 suites** and compiles 13 modules.

---

## 3. The migration

| item | old | new |
| --- | --- | --- |
| account | `isearchxsolve` (billing blocked) | `niloydassana-maker` (billing works) |
| repository | `isearchxsolve/anonym-family-archive` | `niloydassana-maker/anonym-family-archive` (private) |
| branches | `master`, `bounty-control` | both mirrored; `bounty-control` carries the claim ledger |
| default branch | `master` | `master` (GitHub initially set `bounty-control`, corrected) |

`bounty-control` is the durable claim/state ledger. It must always be mirrored: without it the
new pipeline starts with no claim history and the sweeper has nothing to reconcile against.

### Identity made configurable

The fork/PR identity was hardcoded in six adapters. It is now read from the environment:

| variable | default | meaning |
| --- | --- | --- |
| `BOUNTY_ACCOUNT` | `niloydassana-maker` | account that owns forks, commit authorship and `--head` on PRs |
| `BOUNTY_REPOSITORY` | `$BOUNTY_ACCOUNT/anonym-family-archive` | the pipeline's own repo |
| `GITHUB_REPOSITORY` | set by Actions | takes precedence when present |

Sites now reading it: `actions_github.py` (`StateStore`), `actions_reconcile.py` and
`bounty_admission.py` (own-PR ownership), `actions_delivery.py` (commit author),
`kaggle_engine_worker.py` (fork URL, commit author, `--head`), `discovery_heartbeat.py`
(discovery target).

`scripts/deploy_kaggle_engines.py` still lists the legacy account for Kaggle engine tokens.
That is Kaggle credential plumbing, not PR identity, and was left alone deliberately.

### Secrets

| secret | status |
| --- | --- |
| `GH_PAT` | set — classic PAT, scopes include `repo`, `workflow` |
| `TOKENHARBOR_KEYS_JSON` | set — 17-key JSON list from the local vault |

Both were set from files with stdin redirection (`gh secret set NAME < file`), so no value
passed through a shell argument or appeared in process listings.

---

## 4. Verification receipts

| check | result |
| --- | --- |
| local contract suites | 27/27 pass under `-W error` |
| local compile step | 13 modules compile with `-W error` |
| workflow YAML parse | `engine2.yml`, `actions-contracts.yml` OK |
| remote contracts on new account | **run 40844664417 — success (12s)** |
| billing on new account | jobs start and complete (the 3s "never started" signature is gone) |
| discovery restart | run 40845215968 dispatched via `workflow_dispatch` |

---

## 5. Operational runbook

**Push** (the global git config pins the old username, so it must be overridden):

```bash
git -c 'credential.https://github.com.username=niloydassana-maker' push mirror master
```

**Dispatch discovery manually:**

```bash
gh workflow run bounty-discovery.yml --repo niloydassana-maker/anonym-family-archive --ref master
```

**Check health:**

```bash
gh run list  --repo niloydassana-maker/anonym-family-archive --limit 5
gh run view  <RUN_ID> --repo niloydassana-maker/anonym-family-archive
```

**Read the claim ledger:** branch `bounty-control`, directory `fleet-state/`, one JSON file
per task.

---

## 6. Known issues and open items

1. **Vaulted credentials exposed in a chat transcript on 2026-10-29.** The Tokenharbor key list
   and two GitHub tokens were printed and/or screenshotted during the migration. Rotate the
   Tokenharbor keys and re-create both PATs; re-set the two secrets afterwards. This is the only
   item here with a security consequence.
2. **The fine-grained PAT is insufficient for git writes.** It reports `admin` on the repo via
   the API but returns `403 Write access to repository not granted` on push, because
   fine-grained tokens need *Contents: read and write*. It should not be used as `GH_PAT`.
3. **`origin` still points at the legacy repo.** `mirror` is canonical. Pushing to `origin`
   fails with a credential prompt because global git config pins the old username. Run
   `git remote rename origin legacy && git remote rename mirror origin` when convenient.
4. **The legacy repository is now stale** and its Actions remain blocked. Keep it as a
   read-only archive.
5. **`chmod 600` is a no-op on this NTFS volume** — the vault files report `-rw-r--r--`.
   Access is controlled by the Windows user profile, not POSIX modes.
6. **`scripts/audit_complete.py` and `scripts/audit_f2.py` remain on disk.** They produced the
   false "zero gaps" conclusion. They are scratch probes, not gates, and are not in CI; delete
   them or they will mislead the next audit.
7. **No verified PR has been produced by the new pipeline yet.** Everything above proves the
   pipeline *runs*; it does not prove it *delivers*. The first real end-to-end proof remains a
   PR with a head SHA matching its receipt and green remote checks.
