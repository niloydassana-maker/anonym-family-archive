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
from bounty_admission import admit, competition, NON_WORK, repository_intent
from bounty_fx import quote
from discovery_horizon import Horizon

QUERY_CONFIG = json.loads(Path(__file__).with_name("bounty_queries.json").read_text(encoding="utf-8"))
PRIORITY_PROGRAM_QUERIES = tuple(QUERY_CONFIG.pop("priority_programs", ()))
QUERIES = QUERY_CONFIG
SEARCH_QUALIFIERS = (
    "is:issue", "is:open", "is:public", "archived:false",
    "-label:type/experiment", "-label:video-demo", "no:assignee", "-linked:pr",
)
QUERY_POLICY_VERSION = "unassigned-no-closing-pr-no-video-demo-contextual-branches-v4"
QUERY_EXCLUDED_ASSIGNED = "query_excluded_assigned"
QUERY_EXCLUDED_EXPERIMENT = "query_excluded_experiment"
QUERY_EXCLUDED_VIDEO_DEMO = "query_excluded_video_demo"
SEARCH_QUALIFIER_ATOM = re.compile(r"^-?[A-Za-z][A-Za-z0-9_-]*:")


def _search_atoms(expression):
    """Tokenize GitHub search text without splitting quoted phrases or groups."""
    atoms = []
    start = None
    quoted = False
    escaped = False
    depth = 0
    for index, char in enumerate(expression):
        if start is None and not char.isspace():
            start = index
        if char == '"' and not escaped:
            quoted = not quoted
        elif not quoted:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char.isspace() and depth == 0 and start is not None:
                atoms.append(expression[start:index])
                start = None
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    if start is not None:
        atoms.append(expression[start:])
    return atoms


def _is_search_qualifier(atom):
    return bool(SEARCH_QUALIFIER_ATOM.match(atom))


def split_search_or_branches(expression):
    """Expand top-level OR alternatives while preserving shared query context.

    Lane expressions use a common text/qualifier prefix before the first alternative and
    may put common search qualifiers (such as is:issue and is:open) after the last one.
    Distribute that prefix and suffix into every branch. Without this step, splitting
    `label:bounty auth OR permission` silently turns the second query into an unscoped
    search for permission across GitHub.

    GitHub's REST issue-search endpoint changed semantics when a whole expression was
    wrapped in parentheses, so each expanded branch is searched independently instead.
    """
    expression = str(expression or "").strip()
    branches = []
    start = 0
    quoted = False
    escaped = False
    depth = 0
    index = 0
    while index < len(expression):
        char = expression[index]
        if char == '"' and not escaped:
            quoted = not quoted
        elif not quoted:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth < 0:
                    raise ValueError("Unbalanced parentheses in GitHub search expression")
            elif (depth == 0 and expression[index:index + 2].upper() == "OR"
                  and (index == 0 or expression[index - 1].isspace())
                  and (index + 2 == len(expression) or expression[index + 2].isspace())):
                branches.append(expression[start:index].strip())
                start = index + 2
                index += 1
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
        index += 1
    if quoted or depth:
        raise ValueError("Unbalanced quote or parentheses in GitHub search expression")
    branches.append(expression[start:].strip())
    if any(not branch for branch in branches):
        raise ValueError("Empty branch in GitHub OR search expression")
    if len(branches) == 1:
        return branches

    first_atoms = _search_atoms(branches[0])
    last_atoms = _search_atoms(branches[-1])
    if not first_atoms or not last_atoms:
        raise ValueError("Missing alternative in GitHub OR search expression")
    if _is_search_qualifier(first_atoms[-1]):
        raise ValueError("Place shared query context before the first OR alternative")

    shared_prefix = first_atoms[:-1]
    suffix_start = len(last_atoms)
    while suffix_start and _is_search_qualifier(last_atoms[suffix_start - 1]):
        suffix_start -= 1
    last_alternative = last_atoms[:suffix_start]
    if not last_alternative:
        raise ValueError("Missing final alternative in GitHub OR search expression")
    shared_suffix = last_atoms[suffix_start:]

    expanded = [" ".join([*shared_prefix, first_atoms[-1], *shared_suffix])]
    for branch in branches[1:-1]:
        atoms = _search_atoms(branch)
        if not atoms:
            raise ValueError("Empty branch in GitHub OR search expression")
        expanded.append(" ".join([*shared_prefix, *atoms, *shared_suffix]))
    expanded.append(" ".join([*shared_prefix, *last_alternative, *shared_suffix]))
    return expanded


def build_issue_search_query(expression, window=None, fresh=0):
    """Compile one GitHub search branch with shared server-side eligibility filters.

    Disjunctions are expanded by ``build_issue_search_queries`` so every branch gets
    these filters before GitHub returns results. GitHub can enforce issue state,
    visibility, archive, assignee and closing-PR relations at search time; predicates
    without GitHub search qualifiers remain in the existing evidence-based admission
    contract.
    """
    expression = str(expression or "").strip()
    if len(split_search_or_branches(expression)) != 1:
        raise ValueError("Compile OR expressions with build_issue_search_queries")
    atoms = _search_atoms(expression)
    for qualifier in SEARCH_QUALIFIERS:
        if qualifier not in atoms:
            atoms.append(qualifier)
    query = " ".join(atoms)
    if window:
        query += " created:" + Horizon.qualifier(window)
    if fresh:
        query += " updated:>=" + datetime.fromtimestamp(
            time.time() - 7 * 86400, timezone.utc).strftime("%Y-%m-%d")
    return query


def build_issue_search_queries(expression, window=None, fresh=0):
    """Compile one or more queries, applying shared filters to every OR branch."""
    return [build_issue_search_query(branch, window=window, fresh=fresh)
            for branch in split_search_or_branches(expression)]


def has_assignees(item):
    """Read assignment evidence carried by GitHub search results/cache rows."""
    assignees = item.get("assignees")
    if isinstance(assignees, list):
        return bool(assignees)
    return assignees not in (None, "")


def has_label(item, label_name):
    """Read a label name from GitHub search's REST issue representation."""
    labels = item.get("labels")
    if not isinstance(labels, list):
        return False
    return any(
        (label.get("name") if isinstance(label, dict) else label) == label_name
        for label in labels
    )


def query_exclusion_status(item):
    """Return a durable queue status for exclusions enforced by GitHub search."""
    if has_assignees(item):
        return QUERY_EXCLUDED_ASSIGNED
    if has_label(item, "type/experiment"):
        return QUERY_EXCLUDED_EXPERIMENT
    if has_label(item, "video-demo"):
        return QUERY_EXCLUDED_VIDEO_DEMO
    return ""


def refreshed_query_exclusion(context):
    """Reapply server-query exclusions to the live issue before dispatch.

    A search row can become assigned or receive a disqualifying label while it waits in
    the durable queue. Its stale search snapshot must not be enough to start delivery.
    """
    issue = context.get("issue") if isinstance(context, dict) else None
    return query_exclusion_status(issue if isinstance(issue, dict) else {})


def retire_query_excluded_pending(con):
    """Retire cached rows that the current server-side query now excludes.

    The Actions cache can outlive a query-policy deployment. Replaying an old assigned
    issue or an explicitly non-engineering video deliverable would bypass the new GitHub
    query qualifiers, so migrate that cached search evidence when the policy changes.
    """
    retired = Counter()
    for identity, payload in con.execute("SELECT task_id,payload FROM pending").fetchall():
        try:
            item = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            continue
        status = query_exclusion_status(item) if isinstance(item, dict) else ""
        if status:
            retired[status] += con.execute(
                "UPDATE pending SET status=? WHERE task_id=?",
                (status, identity)).rowcount
    return dict(retired)


def _query_compiled_window(api, q, fresh=0):
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
            return [], total, True  # Split before spending hydration work on a capped window.
        rows = result["items"]
        items.extend(rows)
        if fresh or not rows or page * 100 >= total:
            return items, total, False
        page += 1


def query_expression_window(api, expression, window=None, fresh=0):
    """Search all OR branches, deduplicate their union, and report saturation."""
    queries = build_issue_search_queries(expression, window=window, fresh=fresh)
    if len(queries) == 1:
        rows, total, saturated = _query_compiled_window(api, queries[0], fresh=fresh)
        return rows, total, saturated, [total]
    merged = {}
    branch_totals = []
    for query in queries:
        rows, total, saturated = _query_compiled_window(api, query, fresh=fresh)
        branch_totals.append(total)
        if saturated:
            return [], sum(branch_totals), True, branch_totals
        for item in rows:
            repository = item.get("repository_url", "")
            number = item.get("number")
            identity = (repository.lower(), number) if repository and number is not None else json.dumps(
                item, sort_keys=True, separators=(",", ":"))
            merged.setdefault(identity, item)
    return list(merged.values()), sum(branch_totals), False, branch_totals


def query_window(api, expression, window=None, fresh=0):
    """Backward-compatible two-value wrapper around branch-aware search."""
    rows, total, _saturated, _branch_totals = query_expression_window(
        api, expression, window=window, fresh=fresh)
    return rows, total


def merge_evidence(api, repo, cache):
    """Measure how many pull requests this repository has merged, once per cycle.

    A bounty is paid on merge, so merge history is the only durable evidence that a
    repository pays outside work. Every issue in the same repository reuses the
    verdict, so the cost tracks the number of repositories that reach candidate
    status rather than the size of the queue.

    This uses GraphQL deliberately. `search/issues` is capped at 30 requests per
    minute for the whole account, and discovery already spends that allowance on its
    own lane queries: the first live run of this gate died at 16:08:56 with
    "API rate limit exceeded" after five lane searches consumed the minute.
    GraphQL draws on the 5,000-point core allowance instead.

    A failed probe records that fact and yields no verdict. It is never a rejection:
    a throttled query says nothing about the repository.
    """
    if repo in cache:
        return cache[repo]
    owner, name = repo.split("/", 1)
    query = ("query($owner:String!,$name:String!){repository(owner:$owner,name:$name){"
             "merged:pullRequests(states:MERGED){totalCount} all:pullRequests{totalCount}}}")
    try:
        result = api.api("graphql", "POST",
                         {"query": query, "variables": {"owner": owner, "name": name}})
        node = (result or {})["data"]["repository"]
        cache[repo] = {"merged": int(node["merged"]["totalCount"]),
                       "total": int(node["all"]["totalCount"])}
    except (GitHubError, OSError, ValueError, KeyError, TypeError) as exc:
        cache[repo] = {"unavailable": str(exc)[:160]}
    return cache[repo]


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


HYDRATION_BATCH = 120
HYDRATION_PER_REPO = 4


def pending_window(rows, limit=HYDRATION_BATCH, per_repo=HYDRATION_PER_REPO, priority_ids=()):
    """Hydrate current-cycle search hits first, then breadth-first backlog rows.

    GitHub search returns a repository as a unit: one project can publish hundreds
    of matching issues and consume the whole per-cycle hydration budget while every
    unrelated origin waits forever. Selection therefore takes at most ``per_repo``
    backlog sources from each repository first, then fills the rest of the batch from
    leftovers. Fresh query hits already passed the global query contract and lead the
    bounded window, even when a single repository contributes several of them.
    ``rows`` are queue tuples whose first three fields are
    ``(task_id, payload, lanes)``, in durable queue order. Extra trailing fields are
    ignored here and read by the caller.
    """
    chosen, counted, rest, seen = [], Counter(), [], set()
    priority = set(priority_ids)
    for row in rows:
        if row[0] in priority and row[0] not in seen and len(chosen) < limit:
            repository = json.loads(row[1]).get("repository_url", "").split("/repos/")[-1]
            chosen.append(row)
            counted[repository] += 1
            seen.add(row[0])
    for row in rows:
        if row[0] in seen:
            continue
        repository = json.loads(row[1]).get("repository_url", "").split("/repos/")[-1]
        if len(chosen) < limit and counted[repository] < per_repo:
            counted[repository] += 1
            chosen.append(row)
            seen.add(row[0])
        else:
            rest.append(row)
    for row in rest:
        if len(chosen) >= limit:
            break
        if row[0] not in seen:
            chosen.append(row)
            seen.add(row[0])
    return chosen


INTENT_PRECHECK_MAX = 150
INTENT_REFRESH_S = 7 * 86400
REPO_INTENT_RETIRED = "rejected_repository_intent"
QUEUE_WINDOW = 2000


def repository_of(payload):
    url = (json.loads(payload).get("repository_url") or "") if payload else ""
    return url.split("/repos/")[-1] if "/repos/" in url else ""


def queue_window(con, limit=QUEUE_WINDOW, priority_ids=()):
    """Prioritize current-cycle matches, then read both edges of the backlog.

    ``ORDER BY checked,rowid`` alone made a new candidate unreachable: with 3,131 rows
    waiting and a bounded hydration batch, a candidate discovered this cycle sat behind
    roughly twenty-seven cycles of work at the current batch size, and the six-hour
    re-queue then pushed refreshed rows
    behind the same block. A bounded priority list now keeps fresh query hits in the
    hydration window even when later queries add thousands of rows in the same cycle;
    the remaining capacity still drains both the backlog and newest queue edge.
    """
    rows, seen = [], set()
    select = ("SELECT task_id,payload,lanes,signature,rowid FROM pending "
              "WHERE status='pending' AND task_id=?")
    current_hits = []
    for identity in priority_ids:
        row = con.execute(select, (identity,)).fetchone()
        if row and row[0] not in seen:
            seen.add(row[0])
            current_hits.append(row)
    current_hits.sort(key=lambda row: row[3] or "", reverse=True)
    rows.extend(current_hits[:limit])
    remaining = max(0, limit - len(rows))
    if remaining:
        half = max(1, remaining // 2)
        for query in (
            "SELECT task_id,payload,lanes,signature,rowid FROM pending WHERE status='pending' "
            "ORDER BY checked,rowid LIMIT ?",
            "SELECT task_id,payload,lanes,signature,rowid FROM pending WHERE status='pending' "
            "ORDER BY rowid DESC LIMIT ?",
        ):
            for row in con.execute(query, (half,)):
                if len(rows) >= limit:
                    break
                if row[0] in seen:
                    continue
                seen.add(row[0])
                rows.append(row)
    return rows


def precheck_repository_intent(api, con, rows, cache, limit=INTENT_PRECHECK_MAX):
    """Classify the repositories behind the queue before paying to hydrate them.

    Hydration is the expensive step: it fetches the issue and every comment. On the
    2026-10-27 backlog 885 of 3,311 queued rows sat in repositories that merge nothing,
    and each was re-hydrated on every cycle only to be rejected afterwards. The verdict is
    therefore taken once per repository, remembered in ``repo_intent``, and the rows of a
    rejected repository are retired permanently instead of being re-queued six hours later.

    Only unprobed repositories, or verdicts older than a week, cost a probe, and at most
    ``limit`` repositories are probed per cycle, largest queue share first, so a farm with
    hundreds of rows is classified before an origin that contributed one.
    """
    counts = Counter(repository_of(row[1]) for row in rows)
    counts.pop("", None)
    known = {r[0]: (r[1], r[2]) for r in con.execute(
        "SELECT repository,verdict,probed_at FROM repo_intent")}
    verdicts = {repo: verdict for repo, (verdict, _) in known.items()}
    stale = time.time() - INTENT_REFRESH_S
    due = [repo for repo, _ in counts.most_common(limit)
           if repo not in known or (known[repo][1] or 0) < stale]
    probed = 0
    for repo in due:
        evidence = merge_evidence(api, repo, cache)
        ok, reason = repository_intent(evidence)
        verdicts[repo] = "OK" if ok else reason
        con.execute("INSERT OR REPLACE INTO repo_intent VALUES(?,?,?,?,?,?)",
                    (repo, verdicts[repo], evidence.get("merged"), evidence.get("total"),
                     json.dumps(evidence)[:400], time.time()))
        probed += 1
    con.commit()
    retired = 0
    for row in rows:
        if verdicts.get(repository_of(row[1])) != "REPOSITORY_DOES_NOT_MERGE":
            continue
        retired += con.execute(
            "UPDATE pending SET status=? WHERE task_id=? AND status='pending'",
            (REPO_INTENT_RETIRED, row[0])).rowcount
    con.commit()
    return verdicts, probed, retired


def preferred_order(rows, verdicts, priority_ids=()):
    """Fresh query hits first, then known-good repositories, with retired farms removed.

    A fresh issue should be hydrated in the cycle that discovered it. Otherwise a large
    backlog of previously checked, known-good repositories can fill the bounded hydration
    window for many cycles and starve current results. Within the fresh band, measured-good
    repositories lead; the historical backlog then keeps the existing good-before-unknown
    order.
    """
    priority_ids = set(priority_ids)
    good, rest = [], []
    for row in rows:
        if verdicts.get(repository_of(row[1])) == "OK":
            good.append(row)
        elif verdicts.get(repository_of(row[1])) != "REPOSITORY_DOES_NOT_MERGE":
            rest.append(row)
    good.sort(key=lambda row: row[3] or "", reverse=True)
    # Keep current-cycle query matches ahead of the historical backlog after repository
    # precheck. Freshness leads; measured-good repositories lead only within that fresh band.
    good_priority = sorted((row for row in good if row[0] in priority_ids),
                           key=lambda row: row[3] or "", reverse=True)
    rest_priority = sorted((row for row in rest if row[0] in priority_ids),
                           key=lambda row: row[3] or "", reverse=True)
    good_rest = [row for row in good if row[0] not in priority_ids]
    rest_other = [row for row in rest if row[0] not in priority_ids]
    return good_priority + rest_priority + good_rest + rest_other


def retry_eligible(state):
    """Only a recorded failure may be dispatched again.

    A verified refusal (``REJECTED_*``) is a terminal engineering outcome: it means the
    engineering phase ran, the contract verified the answer, and the answer was "this is not
    a warranted change". Re-admitting the same issue on the next cycle spends a whole delivery
    run to relearn a verdict already written down.

    Measured 2026-10-27: ``Expensify/App#105153`` was refused as by-design at 17:57 and
    re-dispatched at 18:44 (runs 40555464157 -> 40562829637) purely because the refusal had
    been recorded as ``FAILED_ENGINEER``, which is retryable by design. The same mechanism
    re-queued ``xpex-systems-ai/GXEON-AI#452``.

    ``FAILED_*`` stays retryable: a real fault is worth another attempt, bounded elsewhere.
    """
    if not state:
        return True
    return str(state.get("status", "")).startswith("FAILED")


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
    con.execute("CREATE TABLE IF NOT EXISTS repo_intent(repository TEXT PRIMARY KEY, verdict TEXT, "
                "merged INTEGER, total INTEGER, evidence TEXT, probed_at REAL)")
    policy_material = "\n".join(Path(__file__).with_name(name).read_text(encoding="utf-8-sig")
                                for name in ("bounty_admission.py", "actions_github.py"))
    policy_material += "\nquery-policy=" + QUERY_POLICY_VERSION
    policy_material += "\nquery-qualifiers=" + " ".join(SEARCH_QUALIFIERS)
    policy = hashlib.sha256(policy_material.encode()).hexdigest()
    old_policy = con.execute("SELECT value FROM metadata WHERE name='admission_policy'").fetchone()
    if not old_policy or old_policy[0] != policy:
        # A changed search/admission policy must revisit the cache without letting old
        # search hits bypass a newly pushed-down query filter.
        con.execute("UPDATE pending SET status='pending',checked=0")
        con.execute("DELETE FROM candidates")
        con.execute("INSERT OR REPLACE INTO metadata VALUES('admission_policy',?)", (policy,))
        query_excluded_retired = retire_query_excluded_pending(con)
        con.commit()
        print(json.dumps({"phase": "SEARCH_POLICY_MIGRATION",
                          "version": QUERY_POLICY_VERSION,
                          "qualifiers": list(SEARCH_QUALIFIERS),
                          "query_excluded_cache_rows_retired": query_excluded_retired}), flush=True)
    counts = Counter()
    candidates = {}
    intent_cache = {}
    priority_ids = []
    verdicts = {r[0]: r[1] for r in con.execute("SELECT repository,verdict FROM repo_intent")}

    def search_and_queue(lane, expression):
        window = horizon.window(expression)
        rows, total, saturated, branch_totals = query_expression_window(api, expression, window)
        recent, fresh_total, _fresh_saturated, fresh_branch_totals = query_expression_window(
            api, expression, fresh=30)
        counts[lane + ".raw"] += len(rows) + len(recent)
        queries = build_issue_search_queries(expression, window=window)
        fresh_queries = build_issue_search_queries(expression, fresh=30)
        print(json.dumps({"phase": "SEARCH", "lane": lane, "expression": expression,
                          "query": queries[0] if len(queries) == 1 else queries,
                          "queries": queries,
                          "fresh_query": fresh_queries[0] if len(fresh_queries) == 1 else fresh_queries,
                          "fresh_queries": fresh_queries,
                          "partition": horizon.qualifier(window), "total_count": total,
                          "branch_total_counts": branch_totals,
                          "fresh_total_count": fresh_total,
                          "fresh_branch_total_counts": fresh_branch_totals,
                          "returned": len(rows), "fresh": len(recent),
                          "saturated": saturated}), flush=True)
        # Persist the raw horizon before hydration; bounded work never drops the unprocessed
        # remainder of a search partition.
        for item in [*recent, *rows]:
            repository = item["repository_url"].split("/repos/")[-1]
            identity = task_id(repository, item["number"])
            old = con.execute("SELECT lanes,signature,checked,status FROM pending WHERE task_id=?",
                              (identity,)).fetchone()
            lanes_seen = set(json.loads(old[0])) if old else set()
            lanes_seen.add(lane)
            signature = item.get("updated_at", "")
            was_query_excluded = bool(old and str(old[3]).startswith("query_excluded_"))
            pending = (was_query_excluded or not old or old[1] != signature
                       or time.time() - old[2] > 21600)
            status = "pending" if pending else old[3]
            excluded_status = query_exclusion_status(item)
            if excluded_status:
                status = excluded_status
            elif verdicts.get(repository) == "REPOSITORY_DOES_NOT_MERGE":
                status = REPO_INTENT_RETIRED
            con.execute("INSERT OR REPLACE INTO pending VALUES(?,?,?,?,?,?)",
                        (identity, json.dumps(item), json.dumps(sorted(lanes_seen)), signature,
                         old[2] if old else 0, status))
        # Give every lane's current-cycle results the same bounded hydration priority.
        # Previously only the dedicated program fast lane populated this list, leaving
        # fresh normal/startup/founder hits behind the accumulated historical backlog.
        for item in recent:
            repository = item["repository_url"].split("/repos/")[-1]
            identity = task_id(repository, item["number"])
            if identity not in priority_ids:
                priority_ids.append(identity)
        con.commit()
        horizon.complete(expression, window, len(rows), 1000, saturated=saturated)

    try:
        # A small, quality-oriented paid-program query runs every cycle. It is additive:
        # the normal, startup, founder, and rotating program lanes below continue to scan
        # their full configured horizons.
        for expression in PRIORITY_PROGRAM_QUERIES:
            search_and_queue("programs", expression)
        for lane in lanes:
            start_row = con.execute("SELECT position FROM cursors WHERE lane=?", (lane,)).fetchone()
            start = start_row[0] if start_row else 0
            for offset in range(min(queries_per_lane, len(QUERIES[lane]))):
                expression = QUERIES[lane][(start + offset) % len(QUERIES[lane])]
                search_and_queue(lane, expression)
            con.execute("INSERT OR REPLACE INTO cursors VALUES(?,?)",
                        (lane, (start + queries_per_lane) % len(QUERIES[lane])))
            con.commit()
        queued = queue_window(con, priority_ids=priority_ids)
        priority_set = set(priority_ids)
        verdicts, probed_intent, retired = precheck_repository_intent(
            api, con, queued, intent_cache)
        queued = preferred_order(queued, verdicts, priority_ids)
        print(json.dumps({"phase": "REPOSITORY_PRECHECK", "queued": len(queued),
                          "distinct_repositories": len({repository_of(row[1]) for row in queued}),
                          "probed": probed_intent, "retired": retired,
                          "known_good": sum(1 for row in queued
                                            if verdicts.get(repository_of(row[1])) == "OK")}),
              flush=True)
        pending_rows = pending_window(queued, priority_ids=priority_ids)
        print(json.dumps({"phase": "HYDRATION_WINDOW", "queued": len(queued),
                          "selected": len(pending_rows),
                          "current_cycle_hits_queued": sum(row[0] in priority_set for row in queued),
                          "current_cycle_hits_selected": sum(row[0] in priority_set for row in pending_rows),
                          "distinct_repositories": len({json.loads(row[1]).get("repository_url", "")
                                                        for row in pending_rows})}), flush=True)
        # Read the queue row positionally: ``queue_window`` yields
        # (task_id,payload,lanes,signature,rowid) so a freshly discovered source can be
        # recognised at the newest edge, while a window built elsewhere may carry fewer
        # columns. The first three are the durable contract.
        for row in pending_rows:
            source_id, payload, lane_json = row[0], row[1], row[2]
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
                    merge_ok, merge_reason = repository_intent(
                        merge_evidence(api, context["repo"], intent_cache))
                    if not merge_ok:
                        counts[merge_reason] += 1
                        print(json.dumps({"phase": "REPOSITORY_INTENT", "repo": context["repo"],
                                          "issue_number": context["issue_number"], "reason": merge_reason,
                                          "evidence": intent_cache.get(context["repo"])}), flush=True)
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
                    if not retry_eligible(state):
                        counts["terminal_refusal" if str(state.get("status", "")).startswith("REJECTED_")
                               else "already_owned"] += 1
                        continue
                    current = api.issue_context(candidate["context"]["repo"], candidate["context"]["issue_number"])
                    query_exclusion = refreshed_query_exclusion(current)
                    if query_exclusion:
                        con.execute("UPDATE pending SET checked=?,status=? WHERE task_id=?",
                                    (time.time(), query_exclusion, identity))
                        con.execute("DELETE FROM candidates WHERE task_id=?", (identity,))
                        con.commit()
                        counts["CURRENT_" + query_exclusion.upper()] += 1
                        continue
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
