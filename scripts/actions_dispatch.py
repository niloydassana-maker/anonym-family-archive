"""Three global discovery lanes, one admission contract and durable Actions queue."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
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
        if fresh or len(rows) < 100:
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
    if NON_WORK.search(context["title"]) and re.search(
            r"original|source|upstream|mirrored|digest|intake", text, re.I):
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


def discover(lanes, max_dispatches=2, live=False, queries_per_lane=2, state_dir=None):
    folder = Path(state_dir or os.environ.get("BOUNTY_STATE_DIR", Path(__file__).resolve().parents[1] / "scratch/actions-discovery"))
    folder.mkdir(parents=True, exist_ok=True)
    api, store = GitHub(), StateStore()
    horizon = Horizon(folder / "horizon.sqlite3")
    con = sqlite3.connect(folder / "discovery.sqlite3", timeout=30)
    con.execute("CREATE TABLE IF NOT EXISTS cursors(lane TEXT PRIMARY KEY, position INTEGER)")
    con.execute("CREATE TABLE IF NOT EXISTS candidates(task_id TEXT PRIMARY KEY, payload TEXT, updated_at TEXT)")
    counts = Counter()
    candidates = {}
    seen = set()
    try:
        for lane in lanes:
            start_row = con.execute("SELECT position FROM cursors WHERE lane=?", (lane,)).fetchone()
            start = start_row[0] if start_row else 0
            for offset in range(min(queries_per_lane, len(QUERIES[lane]))):
                expression = QUERIES[lane][(start + offset) % len(QUERIES[lane])]
                window = horizon.window(expression)
                rows, total = query_window(api, expression, window)
                horizon.complete(expression, window, 1000 if total >= 1000 else len(rows), 1000)
                recent, _ = query_window(api, expression, fresh=30)
                counts[lane + ".raw"] += len(rows) + len(recent)
                print(json.dumps({"phase": "SEARCH", "lane": lane, "query": expression,
                                  "partition": horizon.qualifier(window), "total_count": total,
                                  "returned": len(rows), "fresh": len(recent)}), flush=True)
                for item in [*recent, *rows]:
                    marker = (item["repository_url"], item["number"])
                    if marker in seen:
                        identity = task_id(item["repository_url"].split("/repos/")[-1], item["number"])
                        if identity in candidates:
                            candidates[identity]["lanes"].add(lane)
                        continue
                    seen.add(marker)
                    try:
                        for context in context_candidates(api, item):
                            identity = task_id(context["repo"], context["issue_number"])
                            proof, reason = admit(context, quote=quote)
                            if not proof:
                                counts[lane + "." + reason] += 1
                                continue
                            competition(api, context["repo"], context["issue_number"])
                            candidates.setdefault(identity, {"context": context, "proof": proof, "lanes": set()})["lanes"].add(lane)
                            counts[lane + ".qualified"] += 1
                    except (GitHubError, OSError, ValueError, KeyError) as exc:
                        counts[lane + ".unknown_or_competing"] += 1
                        print(json.dumps({"phase": "ADMISSION_DIAGNOSTIC", "source": marker, "error": str(exc)}), flush=True)
            con.execute("INSERT OR REPLACE INTO cursors VALUES(?,?)",
                        (lane, (start + queries_per_lane) % len(QUERIES[lane])))
            con.commit()
        for identity, candidate in candidates.items():
            serializable = {**candidate, "lanes": sorted(candidate["lanes"])}
            con.execute("INSERT OR REPLACE INTO candidates VALUES(?,?,?)",
                        (identity, json.dumps(serializable), utcnow()))
        con.commit()
        dispatched = []
        if live:
            runs = api.api(f"repos/{store.repo}/actions/runs?per_page=100")["workflow_runs"]
            active = sum(r["status"] != "completed" and r.get("path", "").endswith("engine2.yml") for r in runs)
            headroom = max(0, 4 - active)
            for identity, candidate in candidates.items():
                if len(dispatched) >= min(max_dispatches, headroom):
                    break
                try:
                    dispatched.append(dispatch(api, store, candidate["context"], candidate["proof"], candidate["lanes"]))
                except (ValueError, GitHubError) as exc:
                    counts["dispatch_deferred"] += 1
                    print(json.dumps({"phase": "DISPATCH_DIAGNOSTIC", "task_id": identity, "error": str(exc)}), flush=True)
        summary = {"at": utcnow(), "mode": "LIVE" if live else "READ_ONLY", "counts": dict(counts),
                   "qualified_unique": len(candidates), "dispatched": dispatched}
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
