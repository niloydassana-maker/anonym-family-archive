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
                             validate_plan_contract, write_json)
from bounty_admission import admit, competition
from bounty_fx import quote


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
    # Only the loopback gateway child retains provider secrets. Target commands
    # do not inherit the key pool or the private harness's read token.
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
    task, state = document["context"], document["state"]
    repo, number = task["repo"], task["issue_number"]
    lease = SimpleNamespace(run_id=state["owner"], attempt=state["attempt"], lost=threading.Event(),
                            phase="CLINE_INTAKE", command_pid=0)
    prepared = worker.run_cline_claim_intake(task, lease)
    root, base = prepared["worktree"], prepared["base_sha"]
    try:
        upstream = api.api(f"repos/{repo}/commits/{prepared['default_branch']}")
        if base != upstream["sha"]:
            raise ValueError("Prepared baseline is not the current upstream default")
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
        if task.get("owned_pr"):
            body += "\nRepair this same owned PR: " + task["owned_pr"] + "\n" + json.dumps(task["prior_failures"])
        arch = prepared["architecture"]
        arch["full_delivery_context"] = prepared["context_path"]
        cases = worker.model_scenarios(task["title"], body, arch)
        ok, run, diagnostic = worker.run_engineering_iteration_loop(
            root, repo, number, task["title"], body, arch, plan, cases, base, max_iterations=3)
        if not ok:
            raise RuntimeError(diagnostic)
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
        require_commands(final_commands, results)
        if manifest(root, status_paths(root)) != before:
            raise ValueError("Native verification changed the proposed source tree")
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
    store.owned_update(identity, run_owner, status="PUBLISHING", proposed_head=head)
    subprocess.run(["gh", "auth", "setup-git"], check=True, timeout=30)
    lease = [f"--force-with-lease=refs/heads/{branch}:{prior_head}"] if state.get("pr_number") else []
    git(root, "push", *lease, f"https://github.com/{account}/{name}.git", head + ":refs/heads/" + branch)
    # Recover a server-acknowledged PR after an earlier client timeout.
    existing = [p for p in api.pages(f"repos/{repo}/pulls", state="open")
                if p["head"]["sha"] == head and p["head"]["repo"]
                and p["head"]["repo"]["owner"]["login"] == account]
    if len(existing) > 1:
        raise ValueError("Multiple matching PRs need reconciliation")
    if existing:
        pr = existing[0]
    else:
        competition(api, repo, number)
        rows = receipt["verification"]
        body = (f"Resolves #{number}: {context['title']}.\n\n"
                f"Verified base: {receipt['base_sha']}\nVerified head: {head}\n\n"
                "Regression: the companion test fails on the upstream source and passes with this change.\n\n"
                "Native verification:\n" + "\n".join(
                    f"- {json.dumps(r['argv'])}: exit {r['exit_code']}, {r['duration_s']:.2f}s" for r in rows)
                + "\n\nExecution receipt: " + receipt["run_url"])
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
    elif job_status != "success" or result.get("status") != "VERIFIED":
        result["status"] = "FAILED_" + str(result.get("status", job_status)).removeprefix("FAILED_")
    else:
        result["status"] = "FAILED_PUBLICATION_MISSING"
    if result["status"].startswith("FAILED"):
        result["failures"] = [*previous.get("failures", []),
                              {"run_url": previous.get("run_url"), **result}]
    store.owned_update(identity, owner(), **result, finished_at=utcnow())
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
    except Exception as exc:
        # No success fallthrough. Existing workspace/checkpoints remain intact.
        write_json(artifacts() / (args.phase + "-failure.json"),
                   {"status": "FAILED_" + args.phase.upper(), "diagnostic": str(exc), "at": utcnow()})
        raise


if __name__ == "__main__":
    main()
