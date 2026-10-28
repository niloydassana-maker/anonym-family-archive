# The fix blueprint: from zero PRs to a funded delivery

Companion to the RCA in [ACTIONS-REPAIR-VERIFICATION-2026-10-27.md](ACTIONS-REPAIR-VERIFICATION-2026-10-27.md)
(section "RCA: why no bounty PR exists (2026-10-29)") and to the machine-readable
`rca_no_pr` block in [ACTIONS-REPAIR-RECEIPTS-2026-10-27.json](ACTIONS-REPAIR-RECEIPTS-2026-10-27.json).

This document **implements nothing**. It specifies twelve repairs, each with: the proven defect, the
evidence, the exact site in HEAD `003b486`, the target semantics, a code sketch, the tests that must
exist before it ships, acceptance criteria, risk, rollback, and dependencies.

`combined_goal` remains **`NOT_YET_ACHIEVED`**. No gate proposed here is relaxed. Three of them get
stricter.

---

## 0. Scope, and the one sentence this whole document exists to serve

The RCA proved that the pipeline has never delivered, and that **not one of the fourteen Cline-step
failures is an engineering failure**. The failures are of five kinds: a baseline gate that loses a race
by construction (Cause A), an artefact contract with no legal way to declare a non-default base
(Cause B), a host `open()` that converts a missing report into an apparent crash (Cause C), a blanket
exception handler that labels machine death as engineer failure (Cause D), and a claim with no expiry
that can pin a task forever (Cause E).

The blueprint therefore has one job per cause: make that cause **impossible to repeat, or impossible to
mislabel**, without letting a single thing through that the current gates refuse.

Two rules bind every fix below, and they are not negotiable:

1. **A refusal that was correct stays correct.** The librepods refusal (Cause B) was the harness being
   right. Nothing here may have the effect of letting that task through on that evidence.
2. **`FAILED_ENGINEER` may only ever shrink.** Every reclassification moves a record *out of* that
   bucket and into a more precise one. No new record enters it that was not, in fact, an engineering
   failure. This keeps the counters comparable across the migration.

---

## 1. Summary table

| ID | Fix | Cause | Ships in wave | Blocks delivery today |
| --- | --- | --- | --- | --- |
| F1 | Baseline gate: ancestry + changed-file disjointness; `PREPARATION_RACE` class | A | 2 | **yes** |
| F2 | `base_branch` contract field, validated against the real branch list | B | 2 | **yes** |
| F3 | `ClineDeliverableMissing` typed failure + write-early intake skeleton | C | 1 | **yes** |
| F4 | Failure taxonomy replacing the blanket `FAILED_ENGINEER` | C, D | 1 | **yes** (diagnosis) |
| F5 | Claim lease with expiry, stale-owner takeover, stale-run sweeper | E | 3 | **yes** |
| F6 | Velocity-aware dispatch ordering and preparation budget | A | 3 | no (multiplier) |
| F7 | Runner headroom hardening, plus the honest statement about preemption | D | 4 | no (reducer) |
| F8 | Cron and heartbeat reliability | -- | 4 | no (throughput) |
| F9 | Class-level "does this request a code change at all?" gate | quality | 5 | no (supply) |
| F10 | `download_patch` / submodule failure | -- | 4 | no (specific repo) |
| F11 | Refusal-set observability (counters by reason, no gate change) | quality | 1 | no (steering) |
| F12 | Failure digest, so the next RCA costs one command not 35 runs | -- | 5 | no (diagnosis) |

Wave 1 is deliberately the two fixes that change nothing about *what* is admitted, only about *what we
are allowed to see*. Everything after it is easier to verify because of it.

---

## F1. The baseline gate must test ancestry and disjointness, not equality

### Defect

`scripts/actions_delivery.py:177-179`:

```python
upstream = api.api(f"repos/{repo}/commits/{prepared['default_branch']}")
if base != upstream["sha"]:
    raise ValueError("Prepared baseline is not the current upstream default")
```

`base` is the baseline the agent prepared against, captured at the *start* of preparation. `upstream` is
read at the *end*. On any repository that merges while the agent works, these two differ by
construction, and the longer the agent works the more certainly they differ.

### Evidence

Run `40719193494`, `Expensify/App#70080`, from the downloaded `preparation.json`:

- `base_sha = abc9784f1045a74710fabb9e6c020d82c840624d`, committed `2026-10-28T15:45:21Z`, and that
  **was** `main` when preparation began at `15:46:05Z`.
- The gate ran at `16:28:18Z`, 42 minutes later.
- **8 commits landed on `main` inside that window**, the last (`e3f2b2e889`) at `16:25:36Z`, about two
  and a half minutes before the gate.
- Measured velocity that day: 100 commits from `09:01:08Z` to `19:20:56Z`, about **9.7 merges/hour**, on
  a repository of `3,373,546` KB.

Any preparation window longer than roughly six minutes loses this comparison on that repository. This is
not a slow-agent problem and cannot be fixed by making preparation faster.

### Target semantics

A prepared baseline is acceptable when **both** hold:

1. **Ancestry.** The prepared base is reachable from the current default-branch HEAD -- that is,
   `GET repos/{repo}/compare/{base}...{default}` returns `status` in `{"ahead", "identical"}`. A `diverged`
   status means the base is not on the server's line of history at all and is refused as before.
2. **Disjointness.** The set of files changed between `base` and the live default HEAD does **not**
   intersect the files the plan will touch. The plan's touched set is exactly what the contract already
   requires: the `regression_plan.component` verified at `:186-187`, plus any source paths the patch
   names. If upstream modified one of those files, the patch was written against stale content and must
   be re-prepared, not merged blind.

When (1) passes and (2) fails, the outcome is **not** an engineer failure and **not** a refusal: it is
`PREPARATION_RACE`, a retryable, non-accusatory class (see F4), because the agent did nothing wrong and
upstream moved the file under it.

This is **stricter** than equality in the dimension that matters. Equality only asked "is the tip the
same". Disjointness asks "did anyone touch the lines I am about to change", which equality never asked
and which is the actual precondition for applying a patch.

### Code sketch

```python
# actions_delivery.py, replacing :177-179

def baseline_relationship(api, repo, prepared, default_branch):
    base = prepared["base_sha"]
    comparison = api.api(f"repos/{repo}/compare/{base}...{default_branch}")
    status = comparison.get("status")
    if status == "diverged":
        # not on the server's history: a false claim, refuse exactly as before
        raise ValueError("Prepared baseline is not the current upstream default")
    live_sha = comparison["commits"][-1]["sha"] if comparison.get("commits") else base
    touched = set(prepared_touched_files(prepared))
    moved = {entry["filename"] for entry in comparison.get("files", [])}
    overlap = touched & moved
    return {"base": base, "live_sha": live_sha, "status": status,
            "ahead_by": comparison.get("ahead_by", 0), "overlap": sorted(overlap)}
```

and at the decision point:

```python
relationship = baseline_relationship(api, repo, prepared, prepared["default_branch"])
write_json(artifacts() / "baseline-relationship.json", relationship)
if relationship["overlap"]:
    raise PreparationRace(relationship)          # retryable, not an accusation
```

`prepared_touched_files()` must be derived from the plan the contract already validated, never guessed
from the diff at gate time.

### Tests (new suite `scripts/test_baseline_relationship.py`)

1. `identical` comparison, no files changed -> admitted, `overlap == []`.
2. `ahead` by 8 commits, files changed do not include the component -> admitted (this is the Expensify
   case, which must now pass).
3. `ahead` by 8 commits, component file among changed -> `PreparationRace`, no dispatch, retryable.
4. `diverged` (librepods-style false base) -> `ValueError`, unchanged refusal, non-retryable.
5. `ahead` with a file list containing a path not in the touched set -> admitted (no false positive from
   unrelated churn).
6. Base equal to live HEAD -> admitted, `ahead_by == 0`.
7. Comparison payload missing `files` -> treated as unknown overlap and refused closed, never as empty.

Test 4 is the regression guard for the rule that the librepods refusal must not be weakened.

### Acceptance criteria

- A replay of run `40719193494`'s preparation artefact through the new gate is **admitted** and records
  `ahead_by = 8`, `overlap = []` in a receipt.
- A replay of run `40729296273`'s artefact is **still refused** with the same reason.
- `baseline-relationship.json` exists in every delivery run's artefacts, so the next disagreement is
  readable without a log dig.

### Risk and rollback

Risk: distinctness depends on `regression_plan.component` being accurate. It already is a contract
requirement (`:186-187` checks the file exists), so the dependency is inherited, not new. Rollback: the
old equality check is preserved as `baseline_strict_equal()` behind an env flag for one release cycle.

### Dependencies

None to ship. F6 (velocity ordering) reduces how often the retry path is taken.

---

## F2. A legal way to declare a non-default base, with the false claim still refused

### Defect

`preparation.json` has one base field and one branch label, and no vocabulary for "the work belongs on a
feature branch". The harness verifies the pair it is given. When Cline does work on `android/rewrite` and
labels it `main`, the harness correctly refuses -- and there is then no path forward, because declaring
the truth is not expressible.

### Evidence

Run `40729296273`, `librepods-org/librepods#878`, from the downloaded artefact:

- `base_sha = 3d4d2703da39e9903e9789484b838bd5a0930207`, `default_branch = "main"`.
- Live branch map: `main` is `89356c08ce` at `2026-10-16T17:26:17Z`; `android/rewrite` is `3d4d2703da` at
  `2026-10-28T10:26:57Z`.
- The issue is labelled `enhancement / help wanted / android`, and the reported regression component is
  `android/privileged`.

Cline prepared on the right branch and mislabelled it. **The refusal was correct.** The defect is that no
correct declaration existed.

### Target semantics

Add a first-class field `base_branch` to the preparation contract, defaulting to `default_branch` when
absent (so every existing artefact stays valid). The gate then:

1. Resolves `base_branch` against `GET repos/{repo}/branches/{branch}`. A branch that does not exist is a
   refusal -- no invention is possible.
2. Requires `base_sha` to equal that branch's HEAD (or to be an ancestor of it, per F1's rule).
3. Records `base_branch` in the delivery record and uses it for the compare in F1.
4. Keeps the existing rule that the pair must be *truthful*. A `base_sha` that belongs to branch X while
   `base_branch` says Y is refused exactly as today, because the branch's own HEAD list is what decides.

There is no world in which a task can now claim `main` while delivering a feature-branch SHA. Only the
reverse becomes possible: declaring `android/rewrite` honestly, which the harness can verify from the
branch list and which is what the work genuinely needs.

### Code sketch

```python
# actions_delivery.py, near the component check

declared = prepared.get("base_branch") or prepared["default_branch"]
branch = api.api(f"repos/{repo}/branches/{declared}")     # 404 -> ValueError, refusal
branch_head = branch["commit"]["sha"]
if not is_ancestor_or_equal(api, repo, prepared["base_sha"], declared):
    raise ValueError(f"Prepared baseline is not on the declared base branch {declared}")
prepared["base_branch"] = declared
```

`is_ancestor_or_equal` reuses F1's compare helper; a `diverged` answer is a refusal.

### Tests (`scripts/test_base_branch.py`)

1. Field absent -> behaves exactly as today (`base_branch == default_branch`).
2. Field present and equal to default -> identical outcome to today.
3. Field names a real non-default branch whose HEAD equals `base_sha` -> admitted, `base_branch` recorded.
4. Field names a real non-default branch whose HEAD differs from `base_sha` and is not an ancestor ->
   refused.
5. Field names a branch that does not exist -> refused, and the branch name never appears in any diff
   or patch path.
6. librepods replay: `base_sha = 3d4d2703da`, `base_branch = main` -> **still refused** (regression guard).
7. librepods replay with `base_branch = android/rewrite` -> admitted, because now it is true.

Test 6 is the one that must never be deleted.

### Acceptance criteria

- Test 6 passes and test 7 passes in the same run. A fix that only achieves 7 is not this fix.
- The delivery record carries `base_branch` for every task from the first shipped run onward.

### Risk and rollback

Risk: a wider base set multiplies the number of branches a patch can be judged against. Mitigation: the
ancestry rule from F1 applies unchanged, so a wrong branch is still caught. Rollback: ignore the field and
fall back to `default_branch`; the field is additive, so rollback loses nothing.

### Dependencies

F1 (shares the compare helper and the ancestry rule).

---

## F3. A missing deliverable is a named failure, and a crash leaves a diagnosable artefact

### Defect

`scripts/kaggle_engine_worker.py:2826`:

```python
with open(report_path, encoding='utf-8') as handle:
    report = json.load(handle)
```

This read is unguarded. It sits immediately after the exit-code check at `:2822-2825`, which means the
code path assumes "exit zero implies a report exists". That assumption is false, and the falsehood
surfaces as a bare `FileNotFoundError` rather than as the statement of fact it is: *the agent finished
without reporting*.

### Evidence

Run `40673403288` and run `40720474625` share one signature. The downloaded artefact directory for
`40673403288` contains `4d8e11eab5464777a09e9e6774e3dea9.context.json` (714,246 bytes) and **no
`preparation.json` at all**. The job log's terminating line is:

```
END CLINE pid=2404 exit=0 elapsed=3331.4s
```

Cline ran 55 minutes and exited **zero** without writing the one file the contract requires. The
`FileNotFoundError` was then stamped `FAILED_ENGINEER` by the blanket handler, which is the subject of
F4. Two facts -- "the agent did not report" and "the host crashed" -- were collapsed into one misleading
word.

### Target semantics

1. **A typed exception.** `ClineDeliverableMissing(path, elapsed_seconds, exit_code)` raised when the
   report is absent, and `ClineDeliverableInvalid(path, parse_error)` when it is present but unparseable
   or missing required keys. Both are distinct from `PreparationBlocked` (a verdict) and from
   `FailedEngineer` (a real engineering failure).
2. **A write-early skeleton.** Before Cline is invoked, the host writes a `preparation.json` skeleton
   with `action: "incomplete"`, the base SHA, the branch, the run identity, and a `started_at`. Cline's
   final write replaces it atomically. Then:
   - a crash leaves a skeleton, so the artefact directory always explains itself;
   - "exited zero without reporting" becomes a distinguishable state (`action == "incomplete"`), not a
     missing file;
   - the diagnostic carries elapsed time and exit code by construction.
3. **A pre-write validator.** `validate_preparation(report)` runs before anything downstream reads the
   report: `action` in `{retry, reject, incomplete}`, `base_sha` a 40-char hex, `plan` present when
   `action == "retry"`, `regression_plan.component` present. Failures are `ClineDeliverableInvalid`.
4. **No behaviour change to a valid report.** A well-formed `action: retry` follows exactly today's path,
   including `PreparationBlocked` at `:2832` for `action: reject`.

### Code sketch

```python
# kaggle_engine_worker.py, replacing :2826-2827

if not os.path.exists(report_path):
    raise ClineDeliverableMissing(report_path, elapsed=elapsed,
                                  exit_code=result.exit_code)
try:
    with open(report_path, encoding='utf-8') as handle:
        report = json.load(handle)
except (OSError, ValueError) as exc:
    raise ClineDeliverableInvalid(report_path, str(exc)) from exc
report = validate_preparation(report, report_path)   # raises ClineDeliverableInvalid
```

and, before the Cline call:

```python
write_json_atomic(report_path, {
    "action": "incomplete", "base_sha": base_sha, "base_branch": base_branch,
    "default_branch": default_branch, "started_at": utcnow(), "run": run_identity(),
})
```

The skeleton is written **before** `cline_worktree_command` is built, so a failure inside Cline's own
startup still leaves it.

### Tests (`scripts/test_cline_deliverable.py`)

1. No file, exit 0 -> `ClineDeliverableMissing`, message names the path and the elapsed time, and the
   resulting status is not `FAILED_ENGINEER`.
2. Skeleton only (`action: incomplete`) -> `ClineDeliverableInvalid` naming `incomplete`, status
   `FAILED_DELIVERABLE_MISSING`.
3. Truncated JSON -> `ClineDeliverableInvalid` with the parse error preserved verbatim.
4. Valid `action: retry` -> proceeds exactly as today (golden-path regression test).
5. Valid `action: reject` -> `PreparationBlocked`, and the status is `REJECTED_PREPARATION`, terminal
   (the existing `scripts/test_preparation_terminal.py` contract is reused, not duplicated).
6. `base_sha` not 40 hex chars -> `ClineDeliverableInvalid`, refused before any git operation.
7. Skeleton is replaced atomically: a reader observing the file never sees a partial document (written to
   a temp path in the same directory, then `os.replace`).

### Acceptance criteria

- The replay of `40673403288`'s conditions -- exit 0, no report -- yields `FAILED_DELIVERABLE_MISSING`
  with a diagnostic that says the elapsed time and the exit code, from the artefact alone.
- After the change, no artefact directory can exist without at least a skeleton `preparation.json`.

### Risk and rollback

Risk: the skeleton could be mistaken for a real report by a consumer that does not call the validator.
Mitigation: a single accessor, `read_preparation()`, is the only reader, and the validator rejects
`incomplete` for every downstream phase. Rollback: delete the skeleton write; the typed exceptions are
independent and can stay.

### Dependencies

None. F4 consumes the new exception types, so F3 and F4 ship together.

---

## F4. A failure taxonomy, so machine death is never recorded as engineer failure

### Defect

`scripts/actions_delivery.py:492-496`:

```python
except Exception as exc:
    write_json(artifacts() / (args.phase + "-failure.json"),
               {"status": "FAILED_" + args.phase.upper(), "diagnostic": str(exc), "at": utcnow()})
    raise
```

`args.phase` is `engineer`, so **every** exception in that block becomes `FAILED_ENGINEER`, regardless of
cause: a killed runner, a missing artefact, a git submodule fault, a disk full. The pipeline has no
concept of "the machine went away", so it accuses the engineer.

### Evidence

Of 14 Cline-step failures: 6 `RUNNER_SHUTDOWN` (`exit_143` plus "The runner has received a shutdown
signal"), 3 `PREPARATION_BLOCKED`, 2 `BASELINE_MISMATCH`, 2 `FILENOTFOUND_PREP`, 1 `JOB_CANCELLED`.
**Zero genuine engineering failures.** Each was stamped `FAILED_ENGINEER` or `FAILED_MISSING_RECEIPT` by
the same blanket handler.

Two further rows show the handler swallowing infrastructure failures: `FAILED_MISSING_RECEIPT` from
`Install the executable actually used by the worker`, and one `FAILED_ENGINEER` plus one
`FAILED_MISSING_RECEIPT` from `Configure runner memory headroom`.

### Target semantics

Replace the single `except Exception` with an ordered classification, keeping
`retry_eligible()`'s existing contract intact -- every `FAILED_*` stays retryable, every `REJECTED_*`
stays terminal -- so no counter moves except out of `FAILED_ENGINEER`.

| class | status | retryable | meaning |
| --- | --- | --- | --- |
| `PreparationBlocked` | `REJECTED_PREPARATION` | no | the contract verified a refusal. Terminal. Unchanged. |
| `ClineDeliverableMissing/Invalid` | `FAILED_DELIVERABLE_MISSING` | yes | the agent finished without reporting |
| `PreparationRace` | `FAILED_PREPARATION_RACE` | yes | upstream moved under a correct preparation |
| `RunnerShutdown` | `FAILED_RUNNER_SHUTDOWN` | yes | `exit_143`, "runner has received a shutdown signal", job cancelled mid-step |
| `InfrastructureFault` | `FAILED_INFRASTRUCTURE` | yes | memory/disk/executable install/toolchain |
| unclassified `Exception` | `FAILED_ENGINEER` | yes | the catch-all, now genuinely rare |

Two mechanics worth stating:

- **`RunnerShutdown` is detectable, not guessed.** The delivery step inspects its own step state and the
  presence of a shutdown signal in the environment's recorded diagnostics; the six measured runs all
  carry `exit_143` with the literal shutdown string. Where the log is unrecoverable (the five
  `BlobNotFound` runs) the step-state signature -- Cline step `in_progress` with `conclusion: null` while
  `upload-artifact` and `post-checkout` are `pending` -- is the classifier's input, and the record says
  `runner_shutdown_inferred: true` so the inference is visible rather than silent.
- **`FAILED_ENGINEER` must remain reachable.** It is not deleted, it is narrowed. A future real
  engineering failure must still land there, or the taxonomy has merely renamed the problem.

### Code sketch

```python
# actions_delivery.py, replacing :492-496

except PreparationBlocked:
    raise                                     # terminal verdict, handled exactly as today
except ClineDeliverableMissing as exc:
    return _fail("FAILED_DELIVERABLE_MISSING", exc, kind="deliverable_missing",
                 retryable=True, elapsed=exc.elapsed_seconds)
except ClineDeliverableInvalid as exc:
    return _fail("FAILED_DELIVERABLE_MISSING", exc, kind="deliverable_invalid", retryable=True)
except PreparationRace as exc:
    return _fail("FAILED_PREPARATION_RACE", exc, kind="preparation_race", retryable=True,
                 overlap=exc.relationship["overlap"], ahead_by=exc.relationship["ahead_by"])
except RunnerShutdown as exc:
    return _fail("FAILED_RUNNER_SHUTDOWN", exc, kind="runner_shutdown", retryable=True,
                 inferred=exc.inferred)
except InfrastructureFault as exc:
    return _fail("FAILED_INFRASTRUCTURE", exc, kind="infrastructure", retryable=True,
                 subsystem=exc.subsystem)
except Exception as exc:                      # the catch-all: now genuinely rare
    return _fail("FAILED_ENGINEER", exc, kind="engineer", retryable=True)
```

`_fail` writes the same `*-failure.json` shape as today plus `kind`, `retryable`, and the cause-specific
fields, so existing readers do not break.

### Tests (`scripts/test_failure_taxonomy.py`)

1. `PreparationBlocked` -> `REJECTED_PREPARATION`, `retry_eligible()` is `False`. (Existing contract.)
2. `ClineDeliverableMissing` -> `FAILED_DELIVERABLE_MISSING`, `retry_eligible()` is `True`.
3. `PreparationRace` -> `FAILED_PREPARATION_RACE`, carries `overlap` and `ahead_by`.
4. `RunnerShutdown(inferred=True)` -> `FAILED_RUNNER_SHUTDOWN`, record shows `inferred: true`.
5. `InfrastructureFault("memory")` -> `FAILED_INFRASTRUCTURE`, `subsystem == "memory"`.
6. Bare `RuntimeError("boom")` -> `FAILED_ENGINEER` (the class still exists and still works).
7. Every produced status satisfies `retry_eligible()` iff it starts with `FAILED`.
8. A table-driven assertion that the set of statuses the pipeline can emit is exactly the documented set,
   so a new status cannot be added without updating the doc and the test together.

### Acceptance criteria

- Replaying the 13 Cline-step failure records through the new classifier yields **`FAILED_ENGINEER: 0`**
  except where an artefact proves otherwise (currently: none).
- `FAILED_ENGINEER` in the durable ledger only ever decreases during migration.
- `scripts/test_preparation_terminal.py` still passes unchanged -- the terminal-refusal contract is not
  touched by this fix.

### Risk and rollback

Risk: misclassification in the other direction, hiding a real engineer failure behind
`FAILED_INFRASTRUCTURE`. Mitigation: `FAILED_INFRASTRUCTURE` requires a *named* subsystem and an
evidence string; a classification that cannot name one falls through to `FAILED_ENGINEER`. Rollback:
collapse the taxonomy back to the single handler; the `_fail` indirection makes that a one-line change.

### Dependencies

F3 (supplies the two deliverable exceptions). F1 supplies `PreparationRace`.

---

## F5. A claim must have a lease, and a dead owner must be evictable

### Defect

Two independent locks, neither of which can expire.

`scripts/actions_github.py:196-200`:

```python
active = old.get("status") in ("CLAIMED", "ENGINEERING", "VERIFIED", "PUBLISHING")
if active:
    prior = self.api.api(f"repos/{self.repo}/actions/runs/{old['owner'].split(':')[0]}")
    if prior["status"] != "completed":
        raise ValueError("A live Actions run already owns this task")
```

`scripts/actions_dispatch.py:638`:

```python
return status.startswith("FAILED") or status in ("DISPATCHED", "DISPATCHING")
```

`CLAIMED` is not `FAILED`, so it is never re-dispatched. And `claim()` refuses while the prior run is not
`completed`. A run that never completes pins the task forever.

`scripts/actions_reconcile.py:53-58` does look at `CLAIMED`, but only acts when
`run["status"] == "completed"` -- so a run stuck `in_progress` is invisible to reconciliation by
construction.

### Evidence

Run `40746023790`, `fyne-io/fyne#1062`: created `2026-10-28T18:32:08Z`, still `in_progress` more than 24
hours later, against its own 300-minute step timeout (`.github/workflows/engine2.yml:119`) and 330-minute
job timeout (`.github/workflows/engine2.yml:69`). Engineer job `in_progress`; Cline step `in_progress`,
`conclusion: null`;
`upload-artifact` and `post-checkout` `pending`. Status in the ledger: `CLAIMED`.

### Target semantics

1. **A lease, not a flag.** The claim record carries `claimed_at` (it already does) and
   `lease_expires_at = claimed_at + lease_seconds`, where `lease_seconds` is derived from the workflow's
   own budget -- `CLINE_TOTAL_BUDGET_SECONDS` (`.github/workflows/engine2.yml:116`, 14400) plus a fixed
   grace, so the lease
   can never be shorter than a legitimate run.
2. **Takeover requires proof of death, not absence of life.** A stale claim is taken over only when at
   least one of these is true:
   - the owning run's API `status` is `completed`; or
   - `now > lease_expires_at`, **and** a liveness probe of the owning run fails twice in a row (the
     existing grace-law pattern: two consecutive misses, never one).
3. **The takeover is recorded, not silent.** `previous_owner`, `previous_status`, and
   `takeover_reason` are written on every takeover, and a receipt is emitted. A takeover is a
   diagnostic event, never a quiet reset.
4. **`retry_eligible` grows exactly one rule.** A claim whose lease has expired *and* whose owner is
   provably dead becomes retryable, expressed as a distinct status `FAILED_RUNNER_SHUTDOWN` (from F4)
   written by the sweeper, not by widening `retry_eligible` to accept `CLAIMED` in general. This keeps
   the property that a *live* run is never double-dispatched, which is the one thing the current code
   gets right.
5. **A stale-run sweeper.** New phase inside `reconcile()`, run before the existing branches: for every
   record in `CLAIMED/ENGINEERING/VERIFIED/PUBLISHING`, probe the owning run; if it has outlived
   `job_timeout + grace` while still `in_progress`, cancel it via the API, wait for the cancellation to
   land, then write `FAILED_RUNNER_SHUTDOWN` with `swept: true`. The existing `:53-58` branch stays and
   handles the completed case as today.

### Code sketch

```python
# actions_github.py, inside reserve(), replacing the :196-200 block

active = old.get("status") in ("CLAIMED", "ENGINEERING", "VERIFIED", "PUBLISHING")
if active:
    prior = self.api.api(f"repos/{self.repo}/actions/runs/{old['owner'].split(':')[0]}")
    if prior["status"] != "completed" and not self._lease_expired_and_dead(old):
        raise ValueError("A live Actions run already owns this task")
```

```python
# actions_github.py, new helper

def _lease_expired_and_dead(self, old, probes=2):
    expires = old.get("lease_expires_at")
    if not expires or utcnow() < expires:
        return False
    for _ in range(probes):
        try:
            run = self.api.api(f"repos/{self.repo}/actions/runs/{old['owner'].split(':')[0]}")
        except GitHubError:
            continue            # a probe error is not proof of death
        if run["status"] == "completed":
            return True         # completed is unambiguous: the owner is done
    return False                # unknown is never treated as dead
```

```python
# actions_reconcile.py, new sweeper phase before the existing :53 branch

elif status in ("CLAIMED", "ENGINEERING", "VERIFIED", "PUBLISHING"):
    run = api.api(f"repos/{store.repo}/actions/runs/{record['owner'].split(':')[0]}")
    if run["status"] == "completed":
        fields = {"status": "FAILED_MISSING_TERMINAL_RECEIPT", ...}      # existing behaviour
    elif stale_beyond_job_timeout(run, record):
        api.api(f"repos/{store.repo}/actions/runs/{run['id']}/cancel", method="POST")
        fields = {"status": "FAILED_RUNNER_SHUTDOWN", "swept": True,
                  "diagnostic": "Run exceeded its own job timeout while in_progress; cancelled and released"}
```

The lease is stamped where the claim is written -- `claim()` already computes `claimed_at` at `:206`, so
`lease_expires_at` is added beside it.

### Tests (`scripts/test_claim_lease.py`)

1. Fresh claim, owner alive -> second claim raises "A live Actions run already owns this task". (Unchanged.)
2. Lease not yet expired, owner run `in_progress` -> refused.
3. Lease expired, owner run `in_progress`, both probes fail -> refused (unknown is not dead).
4. Lease expired, owner run `completed` -> takeover, `previous_owner` and `takeover_reason` recorded.
5. Lease expired, owner run `in_progress` but past `job_timeout + grace` -> sweeper cancels, writes
   `FAILED_RUNNER_SHUTDOWN`, and the next claim succeeds.
6. `retry_eligible({"status": "CLAIMED"})` is **still False** -- the sweeper is what changes the state,
   never the selector.
7. Bounded attempts still apply after a sweep: `attempt` increments and the cap at `:202-203` holds, so a
   flapping run cannot loop forever.
8. A sweep never touches a record whose `owner` is missing or malformed -- it writes
   `FAILED_MISSING_TERMINAL_RECEIPT` with a diagnostic instead of guessing.

### Acceptance criteria

- `fyne-io/fyne#1062` becomes claimable without any hand edit to the ledger: the sweeper cancels run
  `40746023790` and releases the task with a receipt naming the run, the timeout, and the sweep.
- No task is ever re-dispatched while its owner is genuinely alive -- asserted by test 1 and test 6
  together.

### Risk and rollback

Risk: a sweeper that is too eager kills a slow-but-live run. Mitigation: three independent guards -- the
lease is derived from the workflow's own budget (so it is never shorter than a legal run), two probes are
required, and the external `job_timeout + grace` must also be exceeded. Rollback: disable the sweeper
phase with a flag; `claim()` then behaves exactly as today.

### Dependencies

F4 for the `FAILED_RUNNER_SHUTDOWN` status vocabulary.

---

## F6. Dispatch should prefer repositories it can win, and cap its own exposure

### Defect

`scripts/actions_dispatch.py:813-819` dispatches by candidate iteration order with a headroom of
`max(0, 4 - active)` and no notion of how fast the target repository moves. Every fast repository is
therefore dispatched with the same confidence as a slow one, and the slow ones -- which are the winnable
ones -- get no preference.

### Evidence

`Expensify/App`: 9.7 merges/hour, `3,373,546` KB, and the only repository with a live funding programme.
`librepods-org/librepods`: `main` has not moved since `2026-10-16T17:26:17Z`. The first loses the F1 race
in minutes; the second cannot lose it at all.

### Target semantics

1. **Measure, do not guess.** The dispatch cycle computes, per candidate repository, commits on the
   default branch in the last 24 hours (`GET repos/{repo}/commits?since=...&per_page=100`, count or
   `Link` header), cached for the cycle. Store it on the candidate as `velocity_24h`.
2. **Order by expected completion, keeping the existing priorities.** The current sort already keeps
   fresh-band matches ahead of backlog. `velocity_24h` is a *secondary* key inside each band, ascending,
   so a quiet repository is attempted before a torrential one. Freshness still leads, per the existing
   comment at `:606-607`.
3. **A preparation budget derived from velocity.** For a repository above a velocity threshold, the
   delivery run gets a shorter Cline budget so the window in which it can be overtaken is bounded. This
   is a mitigation, not a fix -- F1 is the fix. The honest framing: the budget reduces how often
   `FAILED_PREPARATION_RACE` is written; it does not make the race disappear.
4. **No gate change.** Admission, funding, competition checks and the funding-programme authority are all
   untouched. This is ordering and budget only.

### Code sketch

```python
# actions_dispatch.py, inside the live dispatch loop, before the retry_eligible check

velocity = repository_velocity(api, candidate["context"]["repo"], cache=velocity_cache)
candidate["velocity_24h"] = velocity
```

```python
# ordering, extending the existing four-way split at :608-614

def _velocity_key(row):
    return (row.get("velocity_24h") is None, row.get("velocity_24h") or 0)
# inside each band:
good_priority.sort(key=lambda row: (_velocity_key(row), -timestamp(row)))
```

and the budget at dispatch time:

```python
budget = CLINE_BUDGET_SECONDS
if velocity_24h > FAST_REPO_COMMITS_PER_DAY:
    budget = min(budget, CLINE_BUDGET_FAST_REPO_SECONDS)
```

### Tests (`scripts/test_dispatch_velocity.py`)

1. Ordering: within one band, a repository with 2 commits/day sorts before one with 200.
2. Ordering never reorders across bands: a fresh-band high-velocity candidate still precedes a
   backlog-band quiet one (the existing priority contract is preserved).
3. A repository whose velocity cannot be measured (API error) sorts last within its band, and the cycle
   proceeds -- an unmeasurable velocity never blocks dispatch.
4. Budget selection: above the threshold yields the fast budget; below yields the full budget; absent
   velocity yields the full budget.
5. Headroom arithmetic unchanged: `headroom = max(0, 4 - active)` still caps `dispatched`.
6. Admission is still consulted per candidate and a rejection still removes the candidate from the queue
   (`counts["admission_changed.<reason>"]`), i.e. this fix cannot admit anything.

### Acceptance criteria

- A dispatch cycle receipt shows `velocity_24h` for every candidate it considered, so the ordering is
  auditable after the fact.
- Test 6 proves the fix cannot widen admission.

### Risk and rollback

Risk: the extra API call per candidate consumes rate limit. Mitigation: one call per repository per
cycle, cached, and the cycle's candidate count is already bounded by headroom and `max_dispatches`.
Rollback: ignore the field; ordering falls back to today's.

### Dependencies

F1 (the race has to be classified sanely before its frequency is worth reducing).

---

## F7. Runner headroom, and the truth about preemption

### Defect

The memory/disk headroom step (`.github/workflows/engine2.yml:88-96`, an 8 GB swapfile on top of
`ubuntu-latest`) assumed a
runner shape that is not guaranteed. Two records show it failing outright: `FAILED_MISSING_RECEIPT` from
`Configure runner memory headroom`, and `FAILED_ENGINEER` from the same step. A step that is meant to
*help* is capable of killing the run before Cline starts.

### Evidence

The cross-tab in the RCA: 1 `FAILED_MISSING_RECEIPT` and 1 `FAILED_ENGINEER` both attributed to
`Configure runner memory headroom`; 1 `FAILED_MISSING_RECEIPT` to `Install the executable actually used by
the worker`. Separately, 6 `RUNNER_SHUTDOWN` runs with `exit_143` and the literal "The runner has
received a shutdown signal".

### Target semantics

1. **Headroom is best-effort, and says so.** Swap creation failure is logged and the run continues. It is
   never fatal, because a run without swap may still succeed and a run killed by its preparer cannot.
2. **Preflight assertions replace hopeful setup.** Before Cline starts: free disk above a floor, free
   memory above a floor, the executable present and executable, `git` version sufficient. Each failure is
   `InfrastructureFault(subsystem=...)` (F4), so it is classed as infrastructure rather than engineer.
3. **The honest statement, written into the code and the doc:** a GitHub-hosted runner **can be
   preempted**. It cannot be prevented from inside the job. What can be done is: classify it
   (`FAILED_RUNNER_SHUTDOWN`), retry it under the existing bounded budget (`claim()`'s `attempt` cap),
   shorten the exposure window (F6's budget), and make a retry cheap rather than total (F3's write-early
   skeleton means a retry does not lose the artefact trail).
   Any claim that this blueprint eliminates preemption would be a lie and is explicitly not made.

### Code sketch

```yaml
# engine2.yml, the headroom step

- name: Configure runner memory and disk headroom
  run: |
    set +e
    sudo fallocate -l 8G /swapfile_extra 2>/dev/null || sudo dd if=/dev/zero of=/swapfile_extra bs=1M count=8192 2>/dev/null
    sudo chmod 600 /swapfile_extra 2>/dev/null
    sudo mkswap /swapfile_extra 2>/dev/null
    sudo swapon /swapfile_extra 2>/dev/null
    if [ $? -ne 0 ]; then echo "HEADROOM swap unavailable; continuing best-effort"; fi
    free -m; df -h /
```

```python
# the preflight check, called before Cline

def preflight(subsystem_checks):
    for subsystem, ok, detail in subsystem_checks:
        if not ok:
            raise InfrastructureFault(subsystem, detail)
```

### Tests (`scripts/test_preflight.py`)

1. Every check passing -> no exception.
2. Disk below floor -> `InfrastructureFault("disk")` with the measured figure in the diagnostic.
3. Executable missing -> `InfrastructureFault("executable")`.
4. Swap unavailable but everything else fine -> **no exception** (best-effort contract asserted).
5. A preflight failure produces `FAILED_INFRASTRUCTURE`, never `FAILED_ENGINEER` (ties to F4 test 5).

### Acceptance criteria

- No run can be killed by its own headroom step.
- Every infrastructure abort names a subsystem.
- The blueprint's honest statement about preemption appears in the code comment beside the class.

### Risk and rollback

Risk: without swap, an out-of-memory kill becomes more likely on tight runners. Mitigation: the preflight
memory floor, plus F6's velocity-aware budget already shortens the longest runs. Rollback: restore the
fatal swap step; nothing else depends on it.

### Dependencies

F4 for `InfrastructureFault`.

---

## F8. Cron is erratic; make the trigger observable and self-healing

### Defect

Of the last 16 discovery runs, exactly **1** was `event=schedule` (`40571754781`,
`2026-10-27T19:44:03Z`, head `8439a46`); the other 15 were `workflow_dispatch`. A pipeline that is only
driven by hand is a pipeline that stops when hands stop.

### Evidence

The 16-run census above. Note also `concurrency` at `.github/workflows/engine2.yml:26`, which can
coalesce scheduled runs.

### Target semantics

1. **A heartbeat that measures, not assumes.** Read the newest `schedule`-evented discovery run and its
   age. Pulse only when the age exceeds the expected cadence by a margin, and hold when: a run is queued
   or in progress, a fresh completed run exists, our own cooldown is active, or the `gh` probe itself
   errored. This is the contract already proven interactively (`18:33:10Z` HOLD -> `18:40:02Z` FIRED ->
   HOLD `already_running`); the fix is to **install** it as a scheduled job rather than a demonstration.
2. **A scheduled fallback that does not depend on the schedule.** A `workflow_run`-triggered check, or a
   cron job whose only job is to dispatch discovery if the last scheduled one is older than the cadence.
   The point is that no single trigger mechanism is a single point of failure.
3. **Receipts.** Every pulse writes the reason for firing or holding, so "the pipeline was quiet" is a
   documented state rather than an inference.

### Code sketch

```python
def heartbeat(now=None, cadence=3600, margin=1200, cooldown=1800):
    latest = newest_schedule_run()          # event == "schedule"
    if latest is None:
        return fire("no_scheduled_run_observed")
    if any(running(r) for r in recent_runs()):
        return hold("already_running")
    age = now - latest["created_at"]
    if age < cadence - margin:
        return hold("fresh", age)
    if within_cooldown(age):
        return hold("cooldown", age)
    return fire("stale", age)
```

### Tests (`scripts/test_heartbeat.py`)

1. Fresh completed run within cadence -> HOLD `fresh`.
2. Queued or in_progress run -> HOLD `already_running`.
3. Stale run, no cooldown -> FIRE, with the age recorded.
4. Stale run inside cooldown -> HOLD `cooldown`.
5. Probe error -> HOLD `probe_error`, never FIRE (a blind pulse is worse than a missed one).
6. No scheduled run ever observed -> FIRE with `no_scheduled_run_observed` (a cold start is a real state).
7. Every branch returns a receipt carrying its reason.

### Acceptance criteria

- The heartbeat exists as a scheduled job and has produced at least one HOLD and one FIRE receipt in
  production, each carrying its reason.
- A quiet period is explainable from receipts alone.

### Risk and rollback

Risk: double dispatch if the heartbeat and the schedule fire together. Mitigation: the `already_running`
hold reads live runs, and `concurrency` coalesces. Rollback: disable the heartbeat job; the schedule
continues as today.

### Dependencies

None.

---

## F9. The class-level gate: is this a code change at all?

### Defect

Per-phrase admission markers cannot distinguish "a code change is requested" from "a document or an
external deliverable is requested, phrased like a bug". Two live examples:

- `xpex-systems-ai/GXEON-AI#452` -- an external docs/contest deliverable -- is **admitted**.
- `MarkDude-design/ALLurbaseRnotbelong2us#2` is refused `BY_DESIGN`, which is the right outcome reached by
  the wrong reason.

### Why this is deliberately last, and gated

The house has already declared phrase-level tightening **exhausted** (D7). Building a class-level
classifier on top of nine anecdotes would be inventing a gate from intuition -- exactly the failure mode
the RCA warns against. So this fix is specified but **not shipped** until a hand-labelled sample exists.

### Target semantics

1. **A labelled sample first.** Hand-label at least 60 issues from the existing discovery corpus into
   `needs_code_change` / `not_code_change_external` / `not_code_change_process` / `unclear`, with the
   label justified in one line each. The sample is committed as data, not as code.
2. **A classifier that must beat the null hypothesis.** Measure the current admission markers against that
   sample: if markers already score well, the gate adds nothing and is not built. If they score poorly,
   build the smallest classifier that separates the classes with a stated precision and recall.
3. **A refusal reason that says the true thing.** `NOT_A_CODE_CHANGE` rather than a borrowed `BY_DESIGN`.
4. **Fail-open on `unclear`.** An unclear issue stays admissible. The gate exists to remove confidently
   out-of-scope work, not to shrink supply by timidity.

### Tests (`scripts/test_code_change_class.py`, only once the sample exists)

1. Each labelled class is reproduced at the documented rate.
2. `unclear` admits.
3. A false negative (a real code change refused) is counted and must be zero on the sample.
4. The classifier's decision is recorded per issue with the evidence span it used.

### Acceptance criteria

- Precision and recall written down before shipping, measured on the committed sample.
- `xpex-systems-ai/GXEON-AI#452` is refused as `NOT_A_CODE_CHANGE`; `MarkDude-design#2` keeps its refusal
  but under the correct reason.
- **Zero** false negatives on the sample.

### Risk and rollback

Risk: a bad classifier quietly starves supply. Mitigation: fail-open on `unclear`, and the sample is
re-measured on every change. Rollback: disable the class gate; per-phrase markers resume.

### Dependencies

F11 (the refusal census) supplies the corpus to label.

---

## F10. `download_patch` and the submodule failure

### Defect

The patch download path fails with `fatal: No url found for submodule path during repo in .gitmodules`.
A repository whose `.gitmodules` is malformed blocks delivery at a stage unrelated to the issue.

### Evidence

The recorded failure string above. This is a narrow, well-defined fault, not a systemic one; it is in this
blueprint because a single repository should not be silently un-deliverable.

### Target semantics

1. `download_patch` runs with `GIT_ALLOW_PROTOCOL` unchanged but with submodule recursion disabled for the
   download path (`git -c submodule.recurse=false ...`), because the patch concerns the top-level tree.
2. If `.gitmodules` is present and malformed, record `FAILED_INFRASTRUCTURE` with
   `subsystem="submodule"` and the repository named, so the class is visible instead of buried.
3. A repository known to have a broken `.gitmodules` is not silently retried forever: the bounded attempt
   cap in `claim()` already limits it, and the receipt names the cause each time.

### Tests (`scripts/test_download_patch_submodule.py`)

1. A repository with no submodules -> unchanged behaviour.
2. A repository with a valid `.gitmodules` -> the download succeeds without initialising submodules.
3. A `.gitmodules` entry with no `url` -> `InfrastructureFault("submodule")` with the repository named,
   not a raw `fatal:` reaching the top level.
4. The failure never produces `FAILED_ENGINEER`.

### Acceptance criteria

- The exact reproduced error is classified, with the repository named, in a receipt.

### Risk and rollback

Risk: disabling submodule recursion could break a repository whose patch genuinely spans submodules.
Mitigation: this is scoped to the *download* path only; if a future task needs submodule content, that is a
new requirement with its own test. Rollback: restore recursion.

### Dependencies

F4 for the class.

---

## F11. Refusal observability: a census, not a judgement

### Defect

The ledger records final statuses but not *why* each admission was refused, so the hypothesis "our supply
is mostly noise" was, until the RCA, an inference from reading twelve issues by hand.

### Target semantics

1. Every refused candidate already increments `counts["admission_changed." + reason]`
   (`scripts/actions_dispatch.py:839`). Persist those counters per cycle into a small, append-only census
   file.
2. Report the census by reason and by repository. No gate changes, no thresholds, no decisions.
3. The census is the input to F9's labelling and the evidence for any future claim about supply quality.

### Tests (`scripts/test_refusal_census.py`)

1. A cycle with mixed outcomes writes one row per reason with the correct count.
2. A cycle with zero refusals writes a zero row rather than omitting the key (absence is data).
3. The census is append-only: a later cycle never rewrites an earlier row.

### Acceptance criteria

- The distribution of refusal reasons is answerable from a file, without reading issues.

### Risk and rollback

Trivial; it writes one small file per cycle.

### Dependencies

None.

---

## F12. A failure digest, so this RCA costs one command next time

### Defect

Producing the RCA required five purpose-written scripts (`_rca_fleet_state.py`,
`_rca_failure_steps.py`, `_rca_terminal_signal.py`, `_rca_error_lines.py`, plus the artifact downloads)
and 35 run records. Nothing in the repo summarised this; the evidence existed but was not assembled.

### Target semantics

1. A single `scripts/failure_digest.py` that emits: funnel by final status, per-task cause, the terminal
   cause table, and the list of runs whose log is unrecoverable.
2. It reads only the durable ledger and the Actions API, uses the F4 taxonomy for grouping, and never
   judges -- it tabulates.
3. It runs on demand and at the end of any delivery run that fails, writing to `scratch/` (never
   committed as truth; the committed record is the ledger).

### Tests (`scripts/test_failure_digest.py`)

1. A synthetic ledger with one record per status produces the expected funnel.
2. A record with no run produces `no_run` rather than a crash.
3. An unrecoverable log is reported as `log_unavailable`, never as an empty cause.
4. Grouping uses the F4 taxonomy; an unknown status is reported as `unclassified`, never dropped.

### Acceptance criteria

- The next "why no PR" question is answered by one command whose output matches the manual RCA on the
  current 30 records.

### Dependencies

F4.

---

## Implementation order and dependency graph

```
Wave 1  (diagnosis, changes no admission outcome)
  F3  ClineDeliverableMissing + write-early skeleton
  F4  failure taxonomy            (depends on F3)
  F11 refusal census              (independent)

Wave 2  (the two delivery blockers)
  F1  baseline ancestry + disjointness   -> PREPARATION_RACE
  F2  base_branch field                  (depends on F1's compare helper)

Wave 3  (liveness and velocity)
  F5  claim lease + sweeper        (depends on F4's status vocabulary)
  F6  velocity ordering + budget   (depends on F1)

Wave 4  (infrastructure)
  F7  preflight + best-effort headroom (depends on F4)
  F10 submodule / download_patch       (depends on F4)
  F8  heartbeat install                (independent)

Wave 5  (supply, evidence-gated)
  F9  class-level gate   (depends on F11's census and a 60-issue hand-labelled sample)
  F12 failure digest     (depends on F4; can be pulled earlier if diagnosis is wanted sooner)
```

Rule for the graph: **a fix may not ship in a wave earlier than the fix it depends on for its status
vocabulary**, because a status that does not exist yet cannot be written. F3 before F4, F4 before
F5/F7/F10, F1 before F2/F6.

---

## Test matrix, wired into CI

Every new suite goes into `.github/workflows/actions-contracts.yml` beside the existing fourteen. The
suite names follow the repository's convention (`scripts/test_<subject>.py`).

| suite | cases | fix | gate it protects |
| --- | --- | --- | --- |
| `test_baseline_relationship.py` | 7 | F1 | librepods refusal must not weaken |
| `test_base_branch.py` | 7 | F2 | false base label still refused |
| `test_cline_deliverable.py` | 7 | F3 | exit-0-no-report is diagnosable |
| `test_failure_taxonomy.py` | 8 | F4 | `FAILED_ENGINEER` only for engineer failure |
| `test_claim_lease.py` | 8 | F5 | a live run is never double-dispatched |
| `test_dispatch_velocity.py` | 6 | F6 | ordering cannot widen admission |
| `test_preflight.py` | 5 | F7 | infrastructure never stamped as engineer |
| `test_heartbeat.py` | 7 | F8 | no blind pulse |
| `test_download_patch_submodule.py` | 4 | F10 | narrow fault stays narrow |
| `test_refusal_census.py` | 3 | F11 | absent data is not silent |
| `test_failure_digest.py` | 4 | F12 | unknown status is not dropped |
| `test_code_change_class.py` | 4 | F9 | **not written until the sample exists** |

Total when complete: 11 shipped suites (66 cases) plus F9's 4 held behind its labelling dependency.

Local sweep requirement before every push, unchanged from the existing discipline: all suites with
`-W error`, `TOTAL_BAD=0`, Ruff clean on every touched file, workflow YAML parsed. The three
non-negotiable regression guards, which must appear verbatim in the matrix and in review:

1. `test_baseline_relationship.py::test_diverged_base_refused` -- the librepods refusal survives.
2. `test_base_branch.py::test_false_base_label_refused` -- the same, through the new field.
3. `test_claim_lease.py::test_live_owner_not_taken_over` -- a live run is never double-dispatched.

---

## Migration plan

### The 30 durable records

**Do not rewrite history.** The ledger is evidence, and a record that was written wrong is more valuable
as a wrong record with a correction than as a silent edit.

1. Add `reclassified_from` and `reclassified_reason` fields. No existing field is modified.
2. Reclassify only where the artefact proves the cause, using the RCA's cause table:
   - 2 `BASELINE_MISMATCH` -> `FAILED_PREPARATION_RACE` (Cause A, artefact-verified).
   - 2 `FILENOTFOUND_PREP` -> `FAILED_DELIVERABLE_MISSING` (Cause C, artefact-verified).
   - 6 `RUNNER_SHUTDOWN`-class records -> `FAILED_RUNNER_SHUTDOWN`.
   - 3 `PREPARATION_BLOCKED` -> **left exactly as they are**, annotated as "mislabelled before `de8cc08`;
     cannot recur on that path". They are historical facts about a code state that no longer exists.
3. The 12 `REJECTED_PREPARATION` records are **not touched**. They are correct refusals.
4. `FAILED_ENGINEER` after migration: only records for which no artefact evidence exists either way. The
   count moves down and never up.
5. `combined_goal` stays `NOT_YET_ACHIEVED` through the entire migration.

### The zombie run `40746023790`

Two legal routes, in order of preference:

1. **Let F5 fix it.** The sweeper cancels the run (it is past `job_timeout + grace` by more than a day)
   and releases the task with a receipt. No hand edit. This is the acceptance test for F5 and should be
   the first thing observed after F5 ships.
2. **If F5 is not yet shipped**, cancel the run through the API and let the existing `reconcile()`
   `:53-58` branch write `FAILED_MISSING_TERMINAL_RECEIPT` on its next pass, which is retryable. Still no
   hand edit to the ledger, and the receipt names the cancellation.

What is **not** permitted: editing the `CLAIMED` record to `FAILED_*` by hand, because that would make the
ledger say a failure occurred that no artefact records.

---

## Measurement: how we will know each fix worked

Before-and-after counters, read from the durable ledger and the F12 digest, not from run colour.

| metric | now | expected after waves 1-3 |
| --- | --- | --- |
| `FAILED_ENGINEER` share of failures | 6 of 30 records | ~0, and only ever from genuine craft failure |
| failures attributable to a machine cause | 6 shutdown + 5 inferred, all mislabelled | all correctly labelled, none accusatory |
| tasks blocked by baseline equality | 2 measured, unbounded in principle | 0; `FAILED_PREPARATION_RACE` is retryable |
| tasks permanently pinned | 1 (`fyne-io/fyne#1062`) | 0; lease expiry + sweeper |
| tasks with no diagnosable artefact | 2 (missing `preparation.json`) | 0; skeleton guarantees an artefact |
| refusal reasons answerable without reading issues | no | yes (F11 census) |
| **PRs delivered** | **0** | **unchanged until a real delivery lands** |

The last row is the honest one. Waves 1-4 remove the *obstacles*; they do not themselves produce a PR. A
PR appears when a task clears preparation, produces a patched tree, passes the native test plan, and
publishes -- and `combined_goal` flips to achieved only when that PR exists with green remote checks.

---

## Definition of a real delivery (the gate on this whole document)

None of the following, alone or together, counts as success:

- a green run,
- an admitted issue,
- a funded issue (funding is title-only authority and a payer attestation, never a promise),
- a completed Cline run,
- a returned patch,
- a dispatched job,
- a synthetic test passing.

A delivery is real when **all** of these hold simultaneously and are independently checkable:

1. A PR exists on the target repository, authored by the owned account, whose head SHA matches the
   verified receipt.
2. The PR's remote checks pass, read from the checks API, not from the PR page's colour.
3. The task record reaches `AWAITING_REVIEW` (or later) with the PR number and URL recorded.
4. The patch corresponds to the issue's requested change, evidenced by the component and the plan that
   the contract already validated.
5. Payout, if claimed, is evidenced by a bank or platform receipt -- never by a funding label.

---

## What we will NOT do

Stated plainly, because each of these is a tempting shortcut that would produce the appearance of
progress:

1. **We will not delete the baseline check.** It becomes ancestry plus disjointness, which is stricter in
   the dimension that predicts whether a patch applies. Equality was never the safety property; it was a
   proxy that lost races.
2. **We will not let a false base label through.** F2 adds a vocabulary, not a permission. Test 6 of
   `test_base_branch.py` exists to make that impossible to regress.
3. **We will not widen `retry_eligible` to accept `CLAIMED`.** A live run must never be double-dispatched.
   The sweeper changes state only after proving death.
4. **We will not inflate counters.** `FAILED_ENGINEER` only shrinks. No record is created or deleted to
   improve a number.
5. **We will not retry a `REJECTED_*`.** A verified refusal is terminal; re-admitting it spends a whole run
   to relearn a written verdict.
6. **We will not "fix" preemption and say we did.** A hosted runner can be preempted; we classify, retry
   under the bounded budget, and shorten exposure. That is all.
7. **We will not build F9 on intuition.** It waits for a hand-labelled sample, and `unclear` admits.
8. **We will not rewrite the ledger's history.** Corrections are additive fields, never silent edits.
9. **We will not auto-merge, self-approve, or bypass the publish gate.** The publish gate and its status
   rules (`engine2.yml`) are untouched by every fix above. The only fix that touches the workflow is F7's
   headroom step and F8's trigger, both of which alter *reliability*, not *authority*.
10. **We will not revive banned compute or hands.** No Kaggle, no browser drivers, no local CLI agents, no
    competing daemons. Every fix here is host-side Python and one workflow step.

---

## Honest statement of what this blueprint cannot promise

- It cannot promise a funded payout. Funding is attested, and a ledger of correct attempts is not money.
- It cannot promise the first task through will succeed end to end. It can promise that a failure will be
  *named correctly*, which is the precondition for fixing it in one cycle instead of five.
- It cannot promise supply quality. F9 and F11 make supply *measurable*; they do not make it good.
- It cannot promise preemption never happens. See F7.

What it can promise, and what the RCA supports: **the five proven causes of zero deliveries become
impossible to repeat in the form they took.** That is the whole claim. `combined_goal` stays
`NOT_YET_ACHIEVED` until a real PR with green checks exists.
