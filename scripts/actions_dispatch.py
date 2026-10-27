"""Three global discovery lanes, one admission contract and durable Actions queue."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from urllib.parse import urlencode
import uuid

from actions_github import GitHub, GitHubError, StateStore, task_id, utcnow
from bounty_admission import admit, competition, NON_WORK
from bounty_fx import quote
from discovery_horizon import Horizon

QUERIES = json.loads(Path(__file__).with_name("bounty_queries.json").read_text(encoding="utf-8"))


def query_window(api, expression, window=None, fresh=0):
    q = expression + " is:issue is:open is:public archived:false -label:type/experiment"
    if window:
        q += " created:" + Horizon.qualifier(window)
    if fresh:
        q += " updated:>=" + datetime.fromtimestamp(time.time() - 7 * 86400, timezone.utc).strftime("%Y-%m-%d")
    items = []
    page = 1
    total = None
    while True:
        result = api.api("search/issues?" + urlencode(
            {"q": q, "per_page": min(fresh, 100) if fresh else 100,
             "page": page, "sort": "updated" if fresh else "created", "order": "desc"}))
        if result.get("incomplete_results") or not isinstance(result.get("items"), list):
            raise GitHubError("Search horizon incomplete; cursor retained")
        total = result["total_count"]
        if not fresh and total >= 1000:
            return [], total  # Split before spending hydration work on a capped window.
        rows = result["items"]
        items.extend(rows)
        if fresh or not rows or page * 100 >= total:
            return items, total
        page += 1


def context_candidates(api, item, visited=None):
    repo = item["repository_url"].split("/repos/")[-1]
    number = item["number"]
    visited = set(visited or ())
    identity = task_id(repo, number)
    if identity in visited or len(visited) >= 3:
        return
    visited.add(identity)
    context = api.issue_context(repo, number)
    text = context["title"] + "\n" + context["body"]
    if ((NON_WORK.search(context["title"]) and re.search(
            r"original|source|upstream|mirrored|digest|intake", text, re.I))
            or re.search(r"mirrored from|(?:original|source|upstream)\s+issue\s*:|"
                         r"source\s*:\s*https://github\.com/[^\s]+/issues/", text, re.I)):
        for original_repo, original_number in dict.fromkeys(re.findall(
                r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)", text)):
            yield from context_candidates(api, {"repository_url": "https://api.github.com/repos/" + original_repo,
                                                "number": int(original_number)}, visited)
        return
    yield context


def dispatch(api, store, context, proof, lanes, remote_repair=False):
    repo, number = context["repo"], context["issue_number"]
    identity, dispatch_id = task_id(repo, number), uuid.uuid4().hex
    def reserve(old):
        if old:
            status = old.get("status", "")
            retryable = status.startswith("FAILED") and int(old.get("attempt", 0)) < 3 and (re.search(
                r"timeout|timed out|429|502|503|provider|gateway|network|connection|tokenharbor|publication",
                json.dumps(old.get("failures") or old.get("diagnostic") or ""), re.I)
                or (remote_repair and status == "FAILED_REMOTE_CHECKS"))
            if not retryable:
                raise ValueError("Existing durable task state: " + status)
        return {**(old or {}), "task_id": identity, "repo": repo, "issue_number": number,
                "status": "DISPATCHING", "dispatch_id": dispatch_id, "admission": proof,
                "lanes": sorted(set(lanes)), "dispatched_at": utcnow(), "attempt": (old or {}).get("attempt", 0)}
    store.mutate(identity, reserve)
    payload = {"event_type": "bounty_task_dispatch", "client_payload": {
        "repo": repo, "issue_number": number, "task_id": identity, "lanes": sorted(set(lanes)), "mode": "deliver"}}
    api.api(f"repos/{store.repo}/dispatches", "POST", payload)
    def acknowledge(old):
        if old and old.get("dispatch_id") == dispatch_id and old["status"] == "DISPATCHING":
            return {**old, "status": "DISPATCHED"}
        if not old:
            raise ValueError("Dispatch state disappeared")
        return old  # A runner can claim before the POST acknowledgement arrives.
    store.mutate(identity, acknowledge)
    return identity


HYDRATION_BATCH = 60
HYDRATION_PER_REPO = 4


def pending_window(rows, limit=HYDRATION_BATCH, per_repo=HYDRATION_PER_REPO):
    """Breadth-first hydration window over queued search results.

    GitHub search returns a repository as a unit: one project can publish hundreds
    of matching issues and consume the whole per-cycle hydration budget while every
    unrelated origin waits forever. Selection therefore takes at most ``per_repo``
    sources from each repository first, then fills the rest of the batch from the
    leftovers, so breadth is gained without ever shrinking the per-cycle budget and
    a queue that genuinely holds a single origin still receives the full batch.
    ``rows`` are ``(task_id, payload, lanes)`` tuples in durable queue order.
    """
    chosen, counted, rest = [], Counter(), []
    for row in rows:
        repository = json.loads(row[1]).get("repository_url", "").split("/repos/")[-1]
        if len(chosen) < limit and counted[repository] < per_repo:
            counted[repository] += 1
            chosen.append(row)
        else:
            rest.append(row)
    for row in rest:
        if len(chosen) >= limit:
            break
        chosen.append(row)
    return chosen


def discover(lanes, max_dispatches=2, live=False, queries_per_lane=2, state_dir=None):
    folder = Path(state_dir or os.environ.get("BOUNTY_STATE_DIR", Path(__file__).resolve().parents[1] / "scratch/actions-discovery"))
    folder.mkdir(parents=True, exist_ok=True)
    api, store = GitHub(), StateStore()
    horizon = Horizon(folder / "horizon.sqlite3")
    con = sqlite3.connect(folder / "discovery.sqlite3", timeout=30)
    con.execute("CREATE TABLE IF NOT EXISTS cursors(lane TEXT PRIMARY KEY, position INTEGER)")
    con.execute("CREATE TABLE IF NOT EXISTS candidates(task_id TEXT PRIMARY KEY, payload TEXT, updated_at TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS pending(task_id TEXT PRIMARY KEY, payload TEXT, lanes TEXT, "
                "signature TEXT, checked REAL DEFAULT 0, status TEXT DEFAULT 'pending')")
    con.execute("CREATE TABLE IF NOT EXISTS metadata(name TEXT PRIMARY KEY,value TEXT)")
    policy = hashlib.sha256("\n".join(Path(__file__).with_name(name).read_text(encoding="utf-8-sig")
                                     for name in ("bounty_admission.py", "actions_github.py")).encode()).hexdigest()
    old_policy = con.execute("SELECT value FROM metadata WHERE name='admission_policy'").fetchone()
    if not old_policy or old_policy[0] != policy:
        # A repaired gate must revisit old rejections instead of preserving a
        # stale zero-result verdict in the restored Actions cache.
        con.execute("UPDATE pending SET status='pending',checked=0")
        con.execute("DELETE FROM candidates")
        con.execute("INSERT OR REPLACE INTO metadata VALUES('admission_policy',?)", (policy,))
        con.commit()
    counts = Counter()
    candidates = {}
    try:
        for lane in lanes:
            start_row = con.execute("SELECT position FROM cursors WHERE lane=?", (lane,)).fetchone()
            start = start_row[0] if start_row else 0
            for offset in range(min(queries_per_lane, len(QUERIES[lane]))):
                expression = QUERIES[lane][(start + offset) % len(QUERIES[lane])]
                window = horizon.window(expression)
                rows, total = query_window(api, expression, window)
                recent, _ = query_window(api, expression, fresh=30)
                counts[lane + ".raw"] += len(rows) + len(recent)
                print(json.dumps({"phase": "SEARCH", "lane": lane, "query": expression,
                                  "partition": horizon.qualifier(window), "total_count": total,
                                  "returned": len(rows), "fresh": len(recent)}), flush=True)
                # Persist the raw horizon before hydration; bounded work never
                # drops the unprocessed remainder of a search partition.
                for item in [*recent, *rows]:
                    identity = task_id(item["repository_url"].split("/repos/")[-1], item["number"])
                    old = con.execute("SELECT lanes,signature,checked,status FROM pending WHERE task_id=?", (identity,)).fetchone()
                    lanes_seen = set(json.loads(old[0])) if old else set()
                    lanes_seen.add(lane)
                    signature = item.get("updated_at", "")
                    pending = not old or old[1] != signature or time.time() - old[2] > 21600
                    con.execute("INSERT OR REPLACE INTO pending VALUES(?,?,?,?,?,?)",
                                (identity, json.dumps(item), json.dumps(sorted(lanes_seen)), signature,
                                 old[2] if old else 0, "pending" if pending else old[3]))
                con.commit()
                horizon.complete(expression, window, 1000 if total >= 1000 else len(rows), 1000)
            con.execute("INSERT OR REPLACE INTO cursors VALUES(?,?)",
                        (lane, (start + queries_per_lane) % len(QUERIES[lane])))
            con.commit()
        queued = con.execute("SELECT task_id,payload,lanes FROM pending WHERE status='pending' "
                             "ORDER BY checked,rowid LIMIT 2000").fetchall()
        pending_rows = pending_window(queued)
        if len(pending_rows) < len(queued):
            print(json.dumps({"phase": "HYDRATION_WINDOW", "queued": len(queued),
                              "selected": len(pending_rows),
                              "distinct_repositories": len({json.loads(row[1]).get("repository_url", "")
                                                            for row in pending_rows})}), flush=True)
        for source_id, payload, lane_json in pending_rows:
            item, source_lanes = json.loads(payload), json.loads(lane_json)
            try:
                for context in context_candidates(api, item):
                    identity = task_id(context["repo"], context["issue_number"])
                    proof, reason = admit(context, quote=quote)
                    if not proof:
                        counts[reason] += 1
                        print(json.dumps({"phase": "ADMISSION", "repo": context["repo"], "issue_number": context["issue_number"],
                                          "reason": reason, "reported_comments": context["issue"].get("comments"),
                                          "visible_comments": len(context["comments"])}), flush=True)
                        continue
                    competition(api, context["repo"], context["issue_number"])
                    candidates.setdefault(identity, {"context": context, "proof": proof, "lanes": set()})["lanes"].update(source_lanes)
                    counts["qualified"] += 1
                con.execute("UPDATE pending SET checked=?,status='checked' WHERE task_id=?", (time.time(), source_id))
            except (GitHubError, OSError, ValueError, KeyError) as exc:
                counts["unknown_or_competing"] += 1
                print(json.dumps({"phase": "ADMISSION_DIAGNOSTIC", "source": source_id, "error": str(exc)}), flush=True)
                # Transport failures stay pending; competition may change next refresh.
                if isinstance(exc, ValueError):
                    con.execute("UPDATE pending SET checked=?,status='checked' WHERE task_id=?", (time.time(), source_id))
            con.commit()
        for identity, candidate in candidates.items():
            serializable = {**candidate, "lanes": sorted(candidate["lanes"])}
            con.execute("INSERT OR REPLACE INTO candidates VALUES(?,?,?)",
                        (identity, json.dumps(serializable), utcnow()))
        con.commit()
        fresh_count = len(candidates)
        for identity, payload in con.execute("SELECT task_id,payload FROM candidates ORDER BY updated_at LIMIT 100"):
            if identity not in candidates:
                saved = json.loads(payload)
                saved["lanes"] = set(saved["lanes"])
                candidates[identity] = saved
        dispatched = []
        if live:
            runs = api.api(f"repos/{store.repo}/actions/runs?per_page=100")["workflow_runs"]
            active = sum(r["status"] != "completed" and r.get("path", "").endswith("engine2.yml") for r in runs)
            headroom = max(0, 4 - active)
            for identity, candidate in candidates.items():
                if len(dispatched) >= min(max_dispatches, headroom):
                    break
                try:
                    state, _ = store.read(identity)
                    if state and not state["status"].startswith("FAILED"):
                        counts["already_owned"] += 1
                        continue
                    current = api.issue_context(candidate["context"]["repo"], candidate["context"]["issue_number"])
                    proof, reason = admit(current, quote=quote)
                    if not proof:
                        con.execute("DELETE FROM candidates WHERE task_id=?", (identity,))
                        con.commit()
                        counts["admission_changed." + reason] += 1
                        continue
                    competition(api, current["repo"], current["issue_number"], own_head=(state or {}).get("head_sha"))
                    dispatched.append(dispatch(api, store, current, proof, candidate["lanes"]))
                except (ValueError, GitHubError) as exc:
                    counts["dispatch_deferred"] += 1
                    print(json.dumps({"phase": "DISPATCH_DIAGNOSTIC", "task_id": identity, "error": str(exc)}), flush=True)
        summary = {"at": utcnow(), "mode": "LIVE" if live else "READ_ONLY", "counts": dict(counts),
                   "qualified_fresh": fresh_count, "qualified_unique": len(candidates), "dispatched": dispatched,
                   "pending_hydration": con.execute("SELECT count(*) FROM pending WHERE status='pending'").fetchone()[0]}
        with (folder / "receipts.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(summary) + "\n")
        print(json.dumps(summary), flush=True)
        return summary
    finally:
        con.close()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=["all", *QUERIES], default="all")
    parser.add_argument("--live", "--dispatch", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=180)
    parser.add_argument("--max-dispatches", "--max", type=int, default=2)
    parser.add_argument("--queries-per-lane", type=int, default=2)
    parser.add_argument("--state-dir")
    args = parser.parse_args(argv)
    while True:
        discover(list(QUERIES) if args.lane == "all" else [args.lane], args.max_dispatches,
                 args.live, args.queries_per_lane, args.state_dir)
        if not args.daemon or args.once:
            return
        time.sleep(max(30, args.interval))


if __name__ == "__main__":
    main()
