"""GitHub transport and durable per-original-issue state; never logs credentials."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import subprocess
import time
from urllib.parse import urlencode


class GitHubError(RuntimeError):
    pass


def repository(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ValueError("Invalid GitHub repository")
    return value


def issue_number(value):
    if isinstance(value, bool) or not re.fullmatch(r"[1-9][0-9]*", str(value)):
        raise ValueError("Invalid issue number")
    return int(value)


def task_id(repo, number):
    return hashlib.sha256(f"{repository(repo).lower()}#{issue_number(number)}".encode()).hexdigest()[:32]


def utcnow():
    return datetime.now(timezone.utc).isoformat()


class GitHub:
    def __init__(self, token=None):
        self.token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    def api(self, endpoint, method="GET", data=None):
        command = ["gh", "api", endpoint, "--method", method]
        encoded = None
        if data is not None:
            command += ["--input", "-"]
            encoded = json.dumps(data).encode()
        environment = dict(os.environ)
        if self.token:
            environment["GH_TOKEN"] = self.token
        result = subprocess.run(command, input=encoded, capture_output=True, timeout=90, env=environment)
        if result.returncode:
            # gh itself masks authentication; do not include body/environment.
            raise GitHubError(result.stderr.decode("utf-8", errors="replace")[-1500:])
        return json.loads(result.stdout) if result.stdout.strip() else None

    def pages(self, endpoint, **params):
        """Require complete pagination; a failed page never means empty supply."""
        page = 1
        while True:
            sep = "&" if "?" in endpoint else "?"
            rows = self.api(endpoint + sep + urlencode({**params, "per_page": 100, "page": page}))
            if not isinstance(rows, list):
                raise GitHubError("Expected paginated GitHub array")
            yield from rows
            if len(rows) < 100:
                return
            page += 1

    def issue_context(self, repo, number):
        repo, number = repository(repo), issue_number(number)
        metadata = self.api(f"repos/{repo}")
        issue = self.api(f"repos/{repo}/issues/{number}")
        if issue.get("pull_request"):
            raise ValueError("Task is a pull request, not an issue")
        comments = list(self.pages(f"repos/{repo}/issues/{number}/comments"))
        return {"repo": repo, "issue_number": number, "title": issue["title"],
                "body": issue.get("body") or "", "issue": issue,
                "repository": metadata, "comments": comments,
                "author_comments": [c.get("body") or "" for c in comments],
                "fetched_at": utcnow(), "complete_comments": len(comments) == issue["comments"]}


class StateStore:
    """Contents API SHA compare-and-swap on a dedicated control branch."""
    def __init__(self, api=None, repo=None):
        self.api = api or GitHub()
        self.repo = repository(repo or os.environ.get("GITHUB_REPOSITORY", "isearchxsolve/anonym-family-archive"))
        self.branch = "bounty-control"

    def ensure(self):
        try:
            self.api.api(f"repos/{self.repo}/git/ref/heads/{self.branch}")
        except GitHubError as exc:
            if "404" not in str(exc):
                raise
            info = self.api.api(f"repos/{self.repo}")
            head = self.api.api(f"repos/{self.repo}/git/ref/heads/{info['default_branch']}")
            try:
                self.api.api(f"repos/{self.repo}/git/refs", "POST",
                             {"ref": "refs/heads/" + self.branch, "sha": head["object"]["sha"]})
            except GitHubError as race:
                if "422" not in str(race):
                    raise

    def read(self, identity):
        if not re.fullmatch(r"[a-f0-9]{32}", identity):
            raise ValueError("Invalid canonical task identity")
        try:
            obj = self.api.api(f"repos/{self.repo}/contents/fleet-state/{identity}.json?ref={self.branch}")
        except GitHubError as exc:
            if "404" in str(exc):
                return None, None
            raise
        return json.loads(base64.b64decode(obj["content"])), obj["sha"]

    def write(self, identity, document, expected_sha):
        body = {"message": f"fleet: {identity} {document['status']}",
                "branch": self.branch,
                "content": base64.b64encode(json.dumps(document, indent=2).encode()).decode()}
        if expected_sha:
            body["sha"] = expected_sha
        return self.api.api(f"repos/{self.repo}/contents/fleet-state/{identity}.json", "PUT", body)

    def mutate(self, identity, change):
        self.ensure()
        for attempt in range(5):
            previous, sha = self.read(identity)
            document = change(previous)
            document["updated_at"] = utcnow()
            try:
                self.write(identity, document, sha)
                return document
            except GitHubError as exc:
                if not any(code in str(exc) for code in ("409", "422")) or attempt == 4:
                    raise
                time.sleep(min(attempt + 1, 4))
        raise GitHubError("State compare-and-swap exhausted")

    def claim(self, repo, number, owner, run_url, harness_sha, recovery=False):
        identity = task_id(repo, number)
        def reserve(old):
            old = old or {"task_id": identity, "repo": repo, "issue_number": number, "attempt": 0}
            if old.get("status") == "DELIVERED":
                raise ValueError("Task already delivered")
            if old.get("status") in ("PUBLISHED_PENDING_CHECKS", "AWAITING_REVIEW"):
                raise ValueError("Owned PR is pending; reconcile it before another engineering run")
            if old.get("owner") == owner and old.get("status") == "CLAIMED":
                return old
            active = old.get("status") in ("CLAIMED", "ENGINEERING", "VERIFIED", "PUBLISHING")
            if active:
                prior = self.api.api(f"repos/{self.repo}/actions/runs/{old['owner'].split(':')[0]}")
                if prior["status"] != "completed":
                    raise ValueError("A live Actions run already owns this task")
            attempt = int(old.get("attempt", 0)) + 1
            if attempt > (4 if recovery else 3):
                raise ValueError("Bounded recovery attempts exhausted")
            return {**old, "status": "CLAIMED", "attempt": attempt, "owner": owner,
                    "run_url": run_url, "harness_sha": harness_sha, "claimed_at": utcnow()}
        return self.mutate(identity, reserve)

    def owned_update(self, identity, owner, **fields):
        def update(old):
            if not old or old.get("owner") != owner:
                raise ValueError("Task ownership lost")
            return {**old, **fields}
        return self.mutate(identity, update)

    def records(self):
        try:
            entries = self.api.api(f"repos/{self.repo}/contents/fleet-state?ref={self.branch}")
        except GitHubError as exc:
            if "404" in str(exc):
                return
            raise
        for entry in entries:
            if re.fullmatch(r"[a-f0-9]{32}\.json", entry.get("name", "")):
                record, _ = self.read(entry["name"][:-5])
                yield record
