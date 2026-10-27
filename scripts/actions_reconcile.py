"""Observe actual Actions/PR status and queue bounded repairs of owned work."""
import argparse
from datetime import datetime, timezone
import json

from actions_github import GitHub, StateStore, utcnow


def classify_checks(api, repo, head):
    checks = []
    # check-runs is an envelope, unlike the legacy statuses array.
    page = 1
    while True:
        result = api.api(f"repos/{repo}/commits/{head}/check-runs?per_page=100&page={page}")
        rows = result["check_runs"]
        checks.extend(rows)
        if len(rows) < 100:
            break
        page += 1
    statuses = list(api.pages(f"repos/{repo}/commits/{head}/statuses"))
    latest = {}
    for row in checks:
        key = (row["name"], (row.get("app") or {}).get("id"))
        if key not in latest or row["id"] > latest[key]["id"]:
            latest[key] = row
    failures = [r for r in latest.values() if r["status"] == "completed"
                and r.get("conclusion") in ("failure", "timed_out", "cancelled", "startup_failure")]
    latest_status = {}
    for row in statuses:  # newest first
        latest_status.setdefault(row["context"], row)
    failures += [r for r in latest_status.values() if r["state"] in ("error", "failure")]
    pending = any(r["status"] != "completed" or r.get("conclusion") == "action_required"
                  for r in latest.values()) or any(
        r["state"] == "pending" for r in latest_status.values())
    return {"head_sha": head, "checks": list(latest.values()), "statuses": list(latest_status.values()),
            "failures": failures, "state": "FAILED" if failures else "PENDING" if pending else
            "PASSED" if latest or latest_status else "NO_REMOTE_CHECKS"}


def reconcile(repair=False, api=None, store=None):
    api, store = api or GitHub(), store or StateStore()
    receipts = []
    for record in store.records():
        status = record["status"]
        fields = {}
        if status in ("DISPATCHING", "DISPATCHED"):
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(record["dispatched_at"])).total_seconds()
            if age > 1800:
                runs = api.api(f"repos/{store.repo}/actions/runs?per_page=100")["workflow_runs"]
                matching = [r for r in runs if record["task_id"] in r.get("display_title", "")]
                if not matching:
                    fields = {"status": "FAILED_DISPATCH", "diagnostic": "Dispatch acknowledgement timeout: no Actions run observed"}
        elif status in ("CLAIMED", "ENGINEERING", "VERIFIED", "PUBLISHING"):
            run = api.api(f"repos/{store.repo}/actions/runs/{record['owner'].split(':')[0]}")
            if run["status"] == "completed":
                fields = {"status": "FAILED_MISSING_TERMINAL_RECEIPT", "diagnostic":
                          f"Actions run completed ({run['conclusion']}) without terminal callback; artifacts retained",
                          "run_url": run["html_url"]}
        # Reconcile a server-acknowledged PR after a transport/callback failure.
        if (status.startswith("FAILED") or status == "PUBLISHING") and record.get("proposed_head"):
            matches = [p for p in api.pages(f"repos/{record['repo']}/pulls", state="open")
                       if p["head"]["sha"] == record["proposed_head"]
                       and p["head"]["repo"] and p["head"]["repo"]["owner"]["login"] == "isearchxsolve"]
            if len(matches) == 1:
                fields = {"status": "PUBLISHED_PENDING_CHECKS", "head_sha": record["proposed_head"],
                          "pr_number": matches[0]["number"], "pr_url": matches[0]["html_url"],
                          "branch": matches[0]["head"]["ref"], "publication_recovered": True}
        if status in ("PUBLISHED_PENDING_CHECKS", "AWAITING_REVIEW", "FAILED_REMOTE_CHECKS"):
            pr = api.api(f"repos/{record['repo']}/pulls/{record['pr_number']}")
            if pr["head"]["sha"] != record["head_sha"]:
                fields = {"status": "BLOCKED_HEAD_CHANGED", "diagnostic": "Owned PR head differs from verified receipt"}
            elif pr.get("merged"):
                fields = {"status": "DELIVERED", "merged_at": pr["merged_at"], "pr_url": pr["html_url"]}
            elif pr["state"] == "closed":
                fields = {"status": "CLOSED_UNMERGED", "pr_url": pr["html_url"]}
            else:
                proof = classify_checks(api, record["repo"], record["head_sha"])
                fields = {"status": "FAILED_REMOTE_CHECKS" if proof["failures"] else
                          "PUBLISHED_PENDING_CHECKS" if proof["state"] == "PENDING" else "AWAITING_REVIEW",
                          "remote_verification": proof}
                if proof["failures"]:
                    fields["failures"] = [*record.get("failures", []), proof]
        if not fields:
            continue
        identity = record["task_id"]
        def update(old):
            if not old or old.get("updated_at") != record.get("updated_at"):
                raise ValueError("Concurrent state change; reconciliation deferred")
            return {**old, **fields, "observed_at": utcnow()}
        state = store.mutate(identity, update)
        receipt = {"task_id": identity, "previous": status, "status": state["status"], "at": utcnow()}
        if repair and state["status"] == "FAILED_REMOTE_CHECKS" and int(state.get("attempt", 0)) < 3:
            from actions_dispatch import dispatch
            from bounty_admission import admit, competition
            from bounty_fx import quote
            context = api.issue_context(state["repo"], state["issue_number"])
            proof, reason = admit(context, quote=quote)
            if proof:
                competition(api, state["repo"], state["issue_number"], own_head=state["head_sha"])
                dispatch(api, store, context, proof, state.get("lanes", []), remote_repair=True)
                receipt["repair"] = "DISPATCHED"
            else:
                receipt["repair_blocked"] = reason
        receipts.append(receipt)
        print(json.dumps(receipt), flush=True)
    return receipts


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair", action="store_true")
    reconcile(parser.parse_args().repair)
