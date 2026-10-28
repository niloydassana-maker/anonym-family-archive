"""Actions adapter for the repaired Cline lifecycle; publication is a separate job."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
from types import SimpleNamespace

from actions_github import GitHub, GitHubError, StateStore, issue_number, repository, task_id, utcnow
from actions_release import (git, manifest, product_paths, protect_baseline_tests,
                             regression_proof, require_commands, safe_path, status_paths,
                             validate_plan_contract, write_json, restore_checkpoint)
from bounty_admission import admit, competition
from bounty_fx import quote


class PreparationRace(RuntimeError):
    """The prepared baseline is still on the server's line of history, but upstream
    modified a file the plan will touch. Retryable: not an accusation, not a refusal."""
    def __init__(self, base, live_sha, overlap):
        self.base = base
        self.live_sha = live_sha
        self.overlap = overlap
        super().__init__(
            f"preparation race: base={base[:12]} live={live_sha[:12]} "
            f"overlap={sorted(overlap)}")


class ClineDeliverableMissing(RuntimeError):
    """Cline completed but produced no verification receipt at all."""
    def __init__(self, path, elapsed=None, exit_code=None):
        self.path = path
        self.elapsed = elapsed
        self.exit_code = exit_code
        msg = f"Cline delivered no report at {path}"
        if elapsed is not None:
            msg += f" after {elapsed:.1f}s"
        if exit_code is not None:
            msg += f" (exit {exit_code})"
        super().__init__(msg)


class ClineDeliverableInvalid(RuntimeError):
    """Cline produced a receipt but it is malformed or refuses to validate."""
    def __init__(self, path, reason):
        self.path = path
        self.reason = reason
        super().__init__(f"Cline deliverable invalid at {path}: {reason}")


class RunnerShutdown(RuntimeError):
    """The Actions runner shut down mid-delivery (exit_143, shutdown signal)."""
    def __init__(self, message=None, inferred=False):
        self.message = message
        self.inferred = inferred
        super().__init__(message or "Runner shutdown detected")


class InfrastructureFault(RuntimeError):
    """Infrastructure failure: disk, network, executable install, toolchain."""
    def __init__(self, subsystem, detail=""):
        self.subsystem = subsystem
        self.detail = detail
        super().__init__(f"Infrastructure fault in {subsystem}: {detail}")


def write_json_atomic(path, document):
    """Write JSON to a temp path in the same directory, then os.replace so a reader
    never observes a partial document."""
    tmp = path.with_name(path.name + ".tmp")
    write_json(tmp, document)
    os.replace(tmp, path)


def prepared_touched_files(prepared):
    """Derive the set of files the prepared plan will touch, from the contract-validated
    regression plan plus any source paths the plan names."""
    touched = set()
    plan = prepared.get("plan")
    if plan is not None:
        component = plan.component if hasattr(plan, "component") else None
        if component:
            touched.add(component)
        for attr in ("source_paths", "files", "touched"):
            paths = getattr(plan, attr, None) or prepared.get(attr, [])
            for p in paths:
                if isinstance(p, str):
                    touched.add(p)
    rp = prepared.get("regression_plan") or {}
    if isinstance(rp, dict):
        comp = rp.get("component")
        if comp:
            touched.add(comp)
    return touched


def artifacts():
    root = Path(os.environ.get("FLEET_ARTIFACT_DIR", "fleet-artifacts")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def owner():
    return os.environ["GITHUB_RUN_ID"] + ":" + os.environ.get("GITHUB_RUN_ATTEMPT", "1")


def output(**values):
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
            for key, value in values.items():
                if not re.fullmatch(r"[A-Za-z0-9_./:-]+", str(value)):
                    raise ValueError("Unsafe Actions output value")
                handle.write(f"{key}={value}\n")


def summary(result):
    """Echo a terminal outcome into the job summary.

    A refusal recorded only in an uploaded artifact reads, on the run page, exactly like a
    pipeline that quietly did nothing. Measured need: the 2026-10-27 delivery run ended with
    no PR and no visible reason until the step log was opened.
    """
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    status = str(result.get("status") or "")
    if not status:
        return
    detail = str(result.get("declared_reason") or result.get("reason") or result.get("error") or "")
    lines = ["### " + status, "",
             "- task: `" + str(result.get("task_id") or "unknown") + "`"]
    if result.get("repo"):
        lines.append("- issue: `" + str(result["repo"]) + "#" + str(result.get("issue_number", "")) + "`")
    if detail:
        lines.append("- reason: " + " ".join(detail.split())[:600])
    if result.get("pr_url"):
        lines.append("- pull request: " + str(result["pr_url"]))
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def reject_preparation(blocked, task, repo, number):
    """Record a verified preparation refusal as terminal and stop the chain here.

    The refusal is not a fault: Cline inspected the repository and returned
    ``action=blocked`` with its actual diagnosis, and the contract verified that answer
    before this host saw it. Retrying would buy the same verdict again, so the run ends with
    the verdict written down, its evidence attached, and the publish job unarmed.
    """
    report = getattr(blocked, "report", None) or {}
    result = {"status": "REJECTED_PREPARATION", "at": utcnow(),
              "task_id": task.get("task_id"), "repo": repo, "issue_number": number,
              "reason": str(blocked), "declared_reason": report.get("reason", ""),
              "evidence": {"action": report.get("action"), "worktree": report.get("worktree", ""),
                           "base_sha": report.get("base_sha", ""),
                           "default_branch": report.get("default_branch", ""),
                           "sources": report.get("sources", []),
                           "run_url": task.get("run_url", ""),
                           "admission": (task.get("admission") or {}).get("funding")}}
    write_json(artifacts() / "engineering-result.json", result)
    output(verdict="rejected_preparation")
    summary(result)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def claim(event_file):
    event = read_json(event_file)
    payload = event.get("client_payload") or event.get("inputs") or {}
    mode = payload.get("mode", "deliver")
    if mode == "canary":
        output(mode="canary", task_id="canary")
        write_json(artifacts() / "claim.json", {"mode": "canary", "owner": owner()})
        return
    if mode != "deliver":
        raise ValueError("Unknown task mode")
    repo = repository(payload.get("repo") or payload.get("target_repo"))
    number = issue_number(payload.get("issue_number"))
    identity = task_id(repo, number)
    api, store = GitHub(), StateStore()
    old, _ = store.read(identity)
    context = api.issue_context(repo, number)
    proof, reason = admit(context, quote=quote)
    if not proof:
        raise ValueError("Admission blocked: " + reason)
    competition(api, repo, number, own_head=(old or {}).get("head_sha"))
    recovery = (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
                and str(payload.get("force_recovery", "")).lower() == "true")
    state = store.claim(repo, number, owner(),
                        f"https://github.com/{store.repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
                        os.environ["GITHUB_SHA"], recovery)
    context.update(task_id=identity, admission=proof, prior_failures=state.get("failures", []),
                   owned_pr=state.get("pr_url"), owned_head=state.get("head_sha"),
                   owned_pr_number=state.get("pr_number"))
    write_json(artifacts() / "claim.json", {"mode": "deliver", "context": context, "state": state})
    output(mode="deliver", task_id=identity)


def runtime():
    os.environ.setdefault("FLEET_SANDBOX_DIR", str(Path(tempfile.gettempdir()) / "bounty-workspaces"))
    os.environ.setdefault("FLEET_ARTIFACT_DIR", str(artifacts()))
    os.environ.setdefault("CLINE_DATA_DIR", str(Path(tempfile.gettempdir()) / "bounty-cline"))
    os.environ["ACTIONS_PUBLISHER_MANAGED"] = "1"
    import kaggle_engine_worker as worker
    ok, diagnostic = worker.configure_cline_for_engine()
    if not ok:
        raise RuntimeError(diagnostic)
    # Remove credentials from ordinary child environments. This is not a
    # hostile-code sandbox; write credentials live in the separate publisher job.
    for name in list(os.environ):
        if re.search(r"TOKEN|SECRET|PASSWORD|API_KEY|GH_PAT", name, re.I):
            os.environ.pop(name, None)
    status = worker.cline_proxy_router_status()
    if status["states"].get("READY", 0) < 1:
        raise RuntimeError("Gateway has no ready provider key")
    ok, diagnostic = worker.verify_cline_provider_wire()
    if not ok:
        raise RuntimeError(diagnostic)
    write_json(artifacts() / "model-wire.json", {"at": utcnow(), "diagnostic": diagnostic,
                                               "gateway": worker.cline_proxy_router_status()})
    return worker


def engineer():
    document = read_json(artifacts() / "claim.json")
    api = GitHub()  # retain read token only in the host transport object
    worker = runtime()
    if document["mode"] == "canary":
        write_json(artifacts() / "engineering-result.json", {"status": "CANARY_PASSED", "at": utcnow(),
                                               "harness_sha": os.environ["GITHUB_SHA"]})
        return
    cline_budget = int(os.environ.get("CLINE_TOTAL_BUDGET_SECONDS", "14400"))
    worker.set_cline_execution_budget(cline_budget)
    print(json.dumps({"phase": "CLINE_BUDGET", "total_seconds": cline_budget}), flush=True)
    task, state = document["context"], document["state"]
    repo, number = task["repo"], task["issue_number"]
    lease = SimpleNamespace(run_id=state["owner"], attempt=state["attempt"], lost=threading.Event(),
                            phase="CLINE_INTAKE", command_pid=0)
    try:
        prepared = worker.run_cline_claim_intake(task, lease)
    except worker.PreparationBlocked as blocked:
        # Terminal for this dispatch: the refusal reason was already verified, so the chain
        # stops here instead of being reported as a broken engineering phase.
        reject_preparation(blocked, task, repo, number)
        return
    root, base = prepared["worktree"], prepared["base_sha"]
    default_branch = prepared.get("base_branch") or prepared["default_branch"]
    try:
        comparison = api.api(f"repos/{repo}/compare/{base}...{default_branch}")
        status = comparison.get("status")
        if status == "diverged":
            raise ValueError("Prepared baseline is not the current upstream default")
        live_sha = comparison["commits"][-1]["sha"] if comparison.get("commits") else base
        touched = prepared_touched_files(prepared)
        moved = {entry["filename"] for entry in comparison.get("files", [])}
        overlap = touched & moved
        write_json_atomic(artifacts() / "baseline-relationship.json", {
            "base": base, "live_sha": live_sha, "status": status,
            "ahead_by": comparison.get("ahead_by", 0), "overlap": sorted(overlap),
        })
        if overlap:
            raise PreparationRace(base, live_sha, sorted(overlap))
        if git(root, "remote", "get-url", "upstream").stdout.decode().strip().removesuffix(".git") != (
                "https://github.com/" + repo):
            raise ValueError("Unexpected upstream remote")
        plan = prepared["plan"]
        validate_plan_contract(plan)
        component = prepared.get("regression_plan", {}).get("component")
        if not component or not safe_path(root, component).is_file():
            raise ValueError("Cline must identify the actual existing defect component")
        baseline_ok, diagnostic, baseline = worker.verify_baseline(root, plan)
        if not baseline_ok:
            repaired, plan, repair_error = worker.cline_supervise_delivery_phase(
                root, repo, number, "baseline", diagnostic, plan)
            if not repaired:
                raise RuntimeError("BLOCKED_BASELINE: " + repair_error)
            validate_plan_contract(plan)
            baseline_ok, diagnostic, baseline = worker.verify_baseline(root, plan)
        if not baseline_ok:
            raise RuntimeError("BLOCKED_BASELINE: " + diagnostic)
        if status_paths(root):
            raise ValueError("Provisioning mutated the untouched source baseline")
        if state.get("previous_owner") and not task.get("owned_pr"):
            prior_run = state["previous_owner"].split(":")[0]
            if not prior_run.isdecimal():
                raise ValueError("Invalid previous run identity")
            recovery_dir = artifacts() / "previous-run"
            environment = dict(os.environ)
            if api.token:
                environment["GH_TOKEN"] = api.token
            downloaded = subprocess.run(["gh", "run", "download", prior_run,
                "--repo", os.environ["GITHUB_REPOSITORY"], "--name", "task-engineering-" + prior_run,
                "--dir", str(recovery_dir)], env=environment, capture_output=True, timeout=180)
            if downloaded.returncode:
                write_json(artifacts() / "recovery.json", {"status": "NO_PRIOR_ARTIFACT_AVAILABLE", "run": prior_run})
            else:
                checkpoints = []
                import zipfile
                for archive in recovery_dir.glob("cline-recovery/*.zip"):
                    with zipfile.ZipFile(archive) as saved:
                        if "checkpoint.json" in saved.namelist():
                            info = json.loads(saved.read("checkpoint.json"))
                            checkpoints.append((info["at"], archive))
                if checkpoints:
                    archive = max(checkpoints)[1]
                    try:
                        recovery = restore_checkpoint(root, base, archive)
                    except ValueError as exc:
                        recovery = {"status": "REQUIRES_CLINE_RECONCILIATION", "archive": str(archive),
                                    "diagnostic": str(exc)}
                    write_json(artifacts() / "recovery.json", recovery)
    except PreparationRace:
        raise
        # Resume the real owned patch after checking the untouched current base.
        # Source is fetched as Git objects; no credentials are given to Cline.
        if task.get("owned_pr_number"):
            git(root, "fetch", "upstream", f"refs/pull/{int(task['owned_pr_number'])}/head")
            prior_head = git(root, "rev-parse", "FETCH_HEAD").stdout.decode().strip()
            if prior_head != task["owned_head"]:
                raise ValueError("Owned PR changed since claim; reconcile before repair")
            ancestor = git(root, "merge-base", base, prior_head).stdout.decode().strip()
            patch = git(root, "diff", "--binary", ancestor, prior_head).stdout
            patch_file = artifacts() / "owned-pr.patch"
            patch_file.write_bytes(patch)
            git(root, "apply", "--3way", str(patch_file))
        regression_file = artifacts() / "regression.json"
        body = task["body"] + (
            "\n\nDelivery contract: write " + str(regression_file) + " as JSON with "
            "test_files (new companion test paths), argv (the exact native regression command), "
            "expected_failure (a specific defect assertion, minimum 12 characters). "
            "The host runs these tests with actual upstream product source restored, then with your fix. "
            "Do not modify any existing master test or verification configuration. "
            "Do not commit, push, create a fork or publish. Preserve complete issue context at "
            + prepared["context_path"] + "."
        )
        if (artifacts() / "recovery.json").exists():
            body += "\nRead retained previous-run edits and recovery evidence at " + str(artifacts() / "recovery.json")
        if task.get("owned_pr"):
            body += "\nRepair this same owned PR: " + task["owned_pr"] + "\n" + json.dumps(task["prior_failures"])
        arch = prepared["architecture"]
        arch["full_delivery_context"] = prepared["context_path"]
        cases = worker.model_scenarios(task["title"], body, arch)
        feedback = json.dumps(task.get("prior_failures", []))

        # F3: write-early intake skeleton before Cline starts, so a failure inside
        # Cline's own startup still leaves a document that distinguishes "Cline never
        # wrote a report" from "Cline crashed while writing one".
        report_path = artifacts() / "preparation.json"
        write_json_atomic(report_path, {
            "action": "incomplete",
            "base_sha": base,
            "base_branch": prepared.get("base_branch", default_branch),
            "default_branch": default_branch,
            "started_at": utcnow(),
            "run": state.get("owner", ""),
        })

        for release_turn in range(1, 4):
            ok, run, diagnostic = worker.run_engineering_iteration_loop(
                root, repo, number, task["title"], body, arch, plan, cases, base,
                max_iterations=1, initial_feedback=feedback)
            if not ok:
                feedback = diagnostic
                worker.preserve_cline_edits(root)
                if worker.cline_turn_timeout_seconds() <= 0:
                    raise RuntimeError("CLINE_TOTAL_BUDGET_EXHAUSTED after preserving the current worktree")
                continue
            # F3: Cline reported success but produced no verification receipt at all.
            # This is not an engineering failure: Cline ran and exited, but the
            # artefact contract was not satisfied.
            if not report_path.exists():
                raise ClineDeliverableMissing(report_path, elapsed=None, exit_code=0)
            try:
                if git(root, "rev-parse", "HEAD").stdout.decode().strip() != base:
                    raise ValueError("Cline changed Git HEAD before release verification")
                paths = status_paths(root)
                protect_baseline_tests(root, base, paths)
                if not product_paths(paths):
                    raise ValueError("No issue-linked product change; no-op/docs/lockfile-only release blocked")
                regression = regression_proof(
                    root, base, read_json(regression_file),
                    lambda argv: worker.run_command_safe(argv, cwd=root, timeout=3600))
                before = manifest(root, status_paths(root))
                final_commands = plan.builds + worker.verification_test_commands(plan) + plan.linters + plan.format_checks
                final = [worker.run_command_safe(argv, cwd=root, timeout=3600) for argv in final_commands]
                results = [asdict(row) for row in final]
                evidence_file = artifacts() / f"release-verification-{release_turn}.json"
                write_json(evidence_file, results)
                require_commands(final_commands, results)
                if manifest(root, status_paths(root)) != before:
                    raise ValueError("Native verification changed the proposed source tree")
                break
            except (ValueError, RuntimeError, OSError) as exc:
                feedback = ("Independent release verification failed: " + str(exc) +
                            "\nRead complete native receipts at " + str(artifacts()) +
                            ". Repair the actual failure, preserving completed edits and master tests.")
                worker.preserve_cline_edits(root)
        else:
            raise RuntimeError("Bounded Cline delivery repair exhausted: " + feedback)
        git(root, "diff", "--check")
        git(root, "config", "user.name", "isearchxsolve")
        git(root, "config", "user.email", "isearch.xsolve@gmail.com")
        git(root, "add", "--", *paths)
        git(root, "-c", "commit.gpgsign=false", "commit", "-m", f"fix: #{number} - {task['title']}")
        head = git(root, "rev-parse", "HEAD").stdout.decode().strip()
        if git(root, "rev-list", "--count", base + ".." + head).stdout.strip() != b"1":
            raise ValueError("Expected exactly one verified task commit")
        git(root, "bundle", "create", str(artifacts() / "release.bundle"), "HEAD", "^" + base)
        receipt = {"schema": 1, "status": "VERIFIED", "task_id": task["task_id"],
                   "repo": repo, "issue_number": number, "owner": state["owner"],
                   "harness_sha": os.environ["GITHUB_SHA"], "base_sha": base, "head_sha": head,
                   "tree_sha": git(root, "rev-parse", "HEAD^{tree}").stdout.decode().strip(),
                   "default_branch": prepared["default_branch"], "files": before,
                   "plan": asdict(plan), "sources": prepared["sources"], "regression": regression,
                   "baseline": [asdict(r) for r in baseline], "verification": results,
                   "admission": task["admission"], "run_url": state["run_url"], "at": utcnow()}
        write_json(artifacts() / "release.json", receipt)
        write_json(artifacts() / "engineering-result.json", {"status": "VERIFIED", "head_sha": head,
                                               "task_id": task["task_id"], "at": utcnow()})
        # The publish job is gated on this verdict alone: a refusal must never arm it.
        output(verdict="verified")
    finally:
        if Path(root, ".git").exists():
            worker.preserve_cline_edits(root)


def validate_bundle(receipt, bundle, root):
    """Runs no target code and requires the actual committed object/diff proof."""
    if receipt.get("status") != "VERIFIED" or receipt.get("harness_sha") != os.environ["GITHUB_SHA"]:
        raise ValueError("Release/harness provenance mismatch")
    repo, number = repository(receipt["repo"]), issue_number(receipt["issue_number"])
    if task_id(repo, number) != receipt["task_id"]:
        raise ValueError("Release task identity mismatch")
    subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "clone", "--no-checkout",
                    "https://github.com/" + repo + ".git", str(root)], check=True, timeout=180)
    git(root, "fetch", str(bundle), "HEAD")
    head, base = receipt["head_sha"], receipt["base_sha"]
    if git(root, "rev-parse", "FETCH_HEAD").stdout.decode().strip() != head:
        raise ValueError("Bundle HEAD mismatch")
    if git(root, "rev-list", "--count", base + ".." + head).stdout.strip() != b"1":
        raise ValueError("Release is not one task commit")
    if git(root, "show", "-s", "--format=%P", head).stdout.decode().split() != [base]:
        raise ValueError("Release must have exactly the verified upstream parent")
    if git(root, "rev-parse", head + "^{tree}").stdout.decode().strip() != receipt["tree_sha"]:
        raise ValueError("Release tree mismatch")
    paths = [os.fsdecode(p) for p in git(root, "diff", "--name-only", "-z", base, head).stdout.split(b"\0") if p]
    if set(paths) != set(receipt["files"]) or not product_paths(paths):
        raise ValueError("Changed-file release proof mismatch")
    protect_baseline_tests(root, base, paths, head_sha=head)
    for name in paths:
        safe_path(root, name)
        blob = git(root, "show", head + ":" + name, check=False)
        proof = receipt["files"][name]
        if proof.get("deleted"):
            if blob.returncode == 0:
                raise ValueError("Deletion proof mismatch")
        elif blob.returncode or hashlib.sha256(blob.stdout).hexdigest() != proof["sha256"]:
            raise ValueError("File content proof mismatch")
        mode = git(root, "ls-tree", head, "--", name).stdout.split(b" ", 1)[0]
        if mode in (b"120000", b"160000"):
            raise ValueError("Symlink/submodule release requires separate review")
    for source in receipt["sources"]:
        if hashlib.sha256(git(root, "show", base + ":" + source["path"]).stdout).hexdigest() != source["sha256"]:
            raise ValueError("Native-plan source citation mismatch")
    plan = SimpleNamespace(**receipt["plan"])
    validate_plan_contract(plan)
    require_commands(plan.baseline_tests, receipt["baseline"])
    commands = plan.builds + plan.baseline_tests + plan.targeted_tests + plan.final_tests + plan.linters + plan.format_checks
    require_commands(commands, receipt["verification"])
    if receipt["regression"]["red_exit"] == 0 or receipt["regression"]["green_exit"] != 0:
        raise ValueError("Red-to-green regression proof missing")
    git(root, "diff", "--check", base, head)
    return repo, number, head


def publish():
    receipt = read_json(artifacts() / "release.json")
    api, store = GitHub(), StateStore()
    identity, run_owner = receipt["task_id"], owner()
    state, _ = store.read(identity)
    if not state or state.get("owner") != run_owner or receipt["owner"] != run_owner:
        raise ValueError("Publication lease ownership lost")
    root = Path(tempfile.mkdtemp()) / "objects"
    repo, number, head = validate_bundle(receipt, artifacts() / "release.bundle", root)
    context = api.issue_context(repo, number)
    proof, reason = admit(context, quote=quote)
    if not proof:
        raise ValueError("Release funding/issue state blocked: " + reason)
    competition(api, repo, number, own_head=state.get("head_sha") or head)
    current_base = api.api(f"repos/{repo}/commits/{receipt.get('base_branch') or receipt['default_branch']}")["sha"]
    if current_base != receipt["base_sha"]:
        raise ValueError("Upstream base changed after native verification; rebase and reverify before publication")
    account = api.api("user")["login"]
    name = repo.split("/")[1]
    try:
        fork = api.api(f"repos/{account}/{name}")
    except GitHubError as exc:
        if "404" not in str(exc):
            raise
        fork = api.api(f"repos/{repo}/forks", "POST", {"default_branch_only": True})
    if (fork.get("parent") or {}).get("full_name", "").lower() != repo.lower():
        fork = api.api(f"repos/{account}/{name}")
        if (fork.get("parent") or {}).get("full_name", "").lower() != repo.lower():
            raise ValueError("Fork parent mismatch")
    branch = state.get("branch") or f"fix/bounty-{number}-{identity[:6]}-{state['attempt']}"
    prior_head = state.get("head_sha")
    store.owned_update(identity, run_owner, status="PUBLISHING", proposed_head=head,
                       proposed_branch=branch, verified_run=receipt["run_url"])
    subprocess.run(["gh", "auth", "setup-git"], check=True, timeout=30)
    lease = [f"--force-with-lease=refs/heads/{branch}:{prior_head}"] if state.get("pr_number") else []
    git(root, "push", *lease, f"https://github.com/{account}/{name}.git", head + ":refs/heads/" + branch)
    # Recover a server-acknowledged PR after an earlier client timeout.
    existing = [p for p in api.pages(f"repos/{repo}/pulls", state="open")
                if p["head"]["sha"] == head and p["head"]["repo"]
                and p["head"]["repo"]["owner"]["login"] == account]
    if len(existing) > 1:
        raise ValueError("Multiple matching PRs need reconciliation")
    rows = receipt["verification"]
    body = (f"Resolves #{number}: {context['title']}.\n\n"
            f"Verified base: {receipt['base_sha']}\nVerified head: {head}\n\n"
            "Regression: the companion test fails on the upstream source and passes with this change.\n\n"
            "Native verification:\n" + "\n".join(
                f"- {json.dumps(r['argv'])}: exit {r['exit_code']}, {r['duration_s']:.2f}s" for r in rows)
            + "\n\nExecution receipt: " + receipt["run_url"])
    if existing:
        pr = api.api(f"repos/{repo}/pulls/{existing[0]['number']}", "PATCH", {"body": body})
    else:
        competition(api, repo, number)
        pr = api.api(f"repos/{repo}/pulls", "POST",
                     {"head": account + ":" + branch, "base": context["repository"]["default_branch"],
                      "title": f"fix: #{number} - {context['title']}", "body": body})
    store.owned_update(identity, run_owner, status="PUBLISHED_PENDING_CHECKS", pr_url=pr["html_url"],
                       pr_number=pr["number"], head_sha=head, branch=branch,
                       release_digest=hashlib.sha256((artifacts() / "release.json").read_bytes()).hexdigest())
    write_json(artifacts() / "publication.json", {"status": "PUBLISHED_PENDING_CHECKS", "pr_url": pr["html_url"],
                                               "head_sha": head, "at": utcnow()})


def finish(job_status):
    store = StateStore()
    path = artifacts() / "claim.json"
    if not path.exists():
        return
    claim_doc = read_json(path)
    if claim_doc["mode"] == "canary":
        result = read_json(artifacts() / "engineering-result.json") if (artifacts() / "engineering-result.json").exists() else {}
        print(json.dumps({"mode": "canary", "job_status": job_status, "result": result}))
        return
    identity = claim_doc["context"]["task_id"]
    previous, _ = store.read(identity)
    if not previous or previous.get("owner") != owner():
        raise ValueError("Result owner mismatch")
    publication = artifacts() / "publication.json"
    result_file = artifacts() / "engineering-result.json"
    result = read_json(result_file) if result_file.exists() else {"status": "FAILED_MISSING_RECEIPT"}
    for phase in ("engineer", "publish"):
        failure = artifacts() / (phase + "-failure.json")
        if failure.exists():
            result = read_json(failure)
    if publication.exists():
        result = read_json(publication)
    elif str(result.get("status", "")).startswith("REJECTED_"):
        # A verified refusal is a terminal outcome, not a fault. The engineering phase ran,
        # the contract verified the answer, and the verdict is the deliverable. Prefixing it
        # with FAILED_ (as every non-published run did until now) erases the reason and
        # reports a correct decision as a broken pipeline: measured 2026-10-27, when a
        # by-design refusal on Expensify/App#105153 surfaced as FAILED_ENGINEER.
        pass
    elif job_status != "success" or result.get("status") != "VERIFIED":
        result["status"] = "FAILED_" + str(result.get("status", job_status)).removeprefix("FAILED_")
    else:
        result["status"] = "FAILED_PUBLICATION_MISSING"
    if result["status"].startswith("FAILED"):
        result["failures"] = [*previous.get("failures", []),
                              {"run_url": previous.get("run_url"), **result}]
    store.owned_update(identity, owner(), **result, finished_at=utcnow())
    summary(result)
    print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["claim", "engineer", "publish", "finish"])
    parser.add_argument("--event-file", default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--job-status", default="failure")
    args = parser.parse_args()
    try:
        if args.phase == "claim":
            claim(args.event_file)
        elif args.phase == "engineer":
            engineer()
        elif args.phase == "publish":
            publish()
        else:
            finish(args.job_status)
    except PreparationRace as exc:
        # F4: preparation race is retryable, never an engineer failure.
        write_json(artifacts() / (args.phase + "-failure.json"),
                   {"status": "FAILED_PREPARATION_RACE",
                    "diagnostic": str(exc),
                    "base": exc.base, "live_sha": exc.live_sha, "overlap": exc.overlap,
                    "at": utcnow()})
        raise
    except ClineDeliverableMissing as exc:
        # F4: Cline produced no receipt at all — machine/infrastructure issue,
        # never an engineer failure.
        write_json(artifacts() / (args.phase + "-failure.json"),
                   {"status": "FAILED_DELIVERABLE_MISSING",
                    "diagnostic": str(exc),
                    "path": exc.path, "elapsed": exc.elapsed, "exit_code": exc.exit_code,
                    "at": utcnow()})
        raise
    except ClineDeliverableInvalid as exc:
        # F4: Cline produced a malformed receipt — deliverable contract violation,
        # not an engineer coding failure.
        write_json(artifacts() / (args.phase + "-failure.json"),
                   {"status": "FAILED_DELIVERABLE_INVALID",
                    "diagnostic": str(exc),
                    "path": exc.path, "reason": exc.reason,
                    "at": utcnow()})
        raise
    except RunnerShutdown as exc:
        # F4: Runner shutdown mid-delivery — infrastructure fault, not engineer failure.
        write_json(artifacts() / (args.phase + "-failure.json"),
                   {"status": "FAILED_RUNNER_SHUTDOWN",
                    "diagnostic": str(exc),
                    "inferred": exc.inferred,
                    "message": exc.message,
                    "at": utcnow()})
        raise
    except InfrastructureFault as exc:
        # F4: Infrastructure fault — disk, network, executable install, toolchain.
        write_json(artifacts() / (args.phase + "-failure.json"),
                   {"status": "FAILED_INFRASTRUCTURE",
                    "diagnostic": str(exc),
                    "subsystem": exc.subsystem,
                    "detail": exc.detail,
                    "at": utcnow()})
        raise
    except Exception as exc:
        # Genuine engineering failure: everything that is not an infrastructure,
        # delivery-contract, or preparation-race fault.
        write_json(artifacts() / (args.phase + "-failure.json"),
                   {"status": "FAILED_" + args.phase.upper(), "diagnostic": str(exc), "at": utcnow()})
        raise


if __name__ == "__main__":
    main()
