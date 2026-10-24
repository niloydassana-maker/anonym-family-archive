#!/usr/bin/env python3
"""Build a human-review queue of fresh public portal opportunities.

This tool is deliberately unable to log in, bid, post, DM, email, or handle
credentials.  It collects only public posts, preserves source receipts, rejects
seller/stale/territory-mismatched items, and writes portal-native draft replies
for a human to review and submit.

Examples:
  python portal_opportunity_desk.py --days 7 --limit 20
  python portal_opportunity_desk.py --sources n8n make --days 14
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import html
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlencode

from hunt_leads import CLOSED, EXCLUDED, Page, SELLER, TECH, Web

OWNER_LINKEDIN = "https://www.linkedin.com/in/kunal-das-technologist/"
ASSET_CATALOG = "https://github.com/isearchxsolve/repo-catalog"
SOURCES = {
    "n8n": ("https://community.n8n.io", "/c/jobs/13.json"),
    "make": ("https://community.make.com", "/c/hire-a-pro/hire-help/74.json"),
}
PORTAL_MARKET = re.compile(r"\b(?:project|contract|freelance|consult|agency|fixed[ -]price|budget|paid|invoice|client)\b", re.I)
BUYER = re.compile(r"\b(?:hiring|looking for|need(?:ed)?|seeking|want|request|help with|build|implement|repair|fix|troubleshoot)\b", re.I)
EMPLOYMENT = re.compile(r"\b(?:full[ -]?time|salary|employment|employee|benefits|resume|cv|recruiter)\b", re.I)
FRESHER = re.compile(r"\b(?:student|fresher|intern(?:ship)?)\b", re.I)
SELLER_OFFER = re.compile(r"\[\s*(?:for hire|available|free build)\s*\]|\b(?:i(?:'m| am|’m) offering|i will automate|offering one)\b", re.I)
LOW_USD_BUDGET = re.compile(r"\b(?:budget|fixed(?:[ -]price| fee)?|price|pay)\s*[:=-]?\s*(?:USD\s*)?\$?\s*(\d{1,3})(?!\d)", re.I)
KEYWORDS = {
    "automation": re.compile(r"\bn8n\b|\bmake(?:\.com)?\b|\bzapier\b|automation|workflow", re.I),
    "ai_agents": re.compile(r"\b(?:ai agent|llm|rag|langgraph|langchain|mcp|copilot)\b", re.I),
    "backend": re.compile(r"\b(?:python|fastapi|api|webhook|postgres(?:ql)?|redis|backend|integration)\b", re.I),
    "reliability": re.compile(r"\b(?:bug|error|fail(?:ing|ure)?|reliab|retry|queue|duplicate|incident|repair|fix|troubleshoot)\b", re.I),
}
COMPLEXITY_SIGNALS = {
    "workflow_orchestration": re.compile(r"\b(?:n8n|make(?:\.com)?|zapier|workflow|scenario)\b", re.I),
    "api_or_webhook": re.compile(r"\b(?:api|webhook|oauth|sdk|integration)\b", re.I),
    "data_state": re.compile(r"\b(?:airtable|postgres(?:ql)?|redis|database|crm|sheets?|duplicate|idempot)\b", re.I),
    "agent_or_rag": re.compile(r"\b(?:ai agent|llm|rag|knowledge base|prompt|human handoff)\b", re.I),
    "messaging_or_voice": re.compile(r"\b(?:whatsapp|telegram|slack|email|sms|voice|video)\b", re.I),
    "reliability_or_operations": re.compile(r"\b(?:error|retry|queue|monitor|alert|test|stress|production|reliab|debug|troubleshoot)\b", re.I),
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_date(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def plain(value: str) -> str:
    return Page(value or "").text


def match_tags(title: str, body: str) -> list[str]:
    text = title + "\n" + body
    return [name for name, pattern in KEYWORDS.items() if pattern.search(text)]


def complexity(text: str) -> list[str]:
    return [name for name, pattern in COMPLEXITY_SIGNALS.items() if pattern.search(text)]


def classify(title: str, body: str) -> str:
    text = title + "\n" + body
    if EMPLOYMENT.search(text) and not PORTAL_MARKET.search(text):
        return "employment_application"
    if PORTAL_MARKET.search(text):
        return "paid_project_or_agency"
    return "buyer_request_needs_scope_confirmation"


def reject_reasons(title: str, body: str, created: datetime | None, days: int, reply_count: int | None,
                   max_replies: int, min_complexity: int) -> list[str]:
    text = title + "\n" + body
    reasons: list[str] = []
    if created is None:
        reasons.append("publication_date_unknown")
    elif utcnow() - created > timedelta(days=days):
        reasons.append("older_than_age_limit")
    if SELLER.search(title) or SELLER.search(body[:500]):
        reasons.append("seller_or_job_seeker_post")
    if SELLER_OFFER.search(title) or SELLER_OFFER.search(body[:500]):
        reasons.append("seller_or_free_offer_not_buyer_demand")
    if EXCLUDED.search(text):
        reasons.append("excluded_territory")
    if FRESHER.search(text):
        reasons.append("fresher_or_internship")
    amounts = [int(match.group(1)) for match in LOW_USD_BUDGET.finditer(text)]
    if amounts and max(amounts) < 150:
        reasons.append("stated_usd_budget_below_minimum")
    if CLOSED.search(text):
        reasons.append("post_reports_closed_or_filled")
    if reply_count is None:
        reasons.append("reply_count_unknown")
    elif reply_count > max_replies:
        reasons.append("already_has_more_than_maximum_replies")
    if len(complexity(text)) < min_complexity:
        reasons.append("problem_not_multi_system_or_complex_enough")
    if not BUYER.search(text):
        reasons.append("buyer_need_unconfirmed")
    if not match_tags(title, body):
        reasons.append("automation_ai_or_backend_fit_unconfirmed")
    return reasons


def score(kind: str, tags: list[str], body: str) -> tuple[int, list[str]]:
    value = 0
    reasons: list[str] = []
    if kind == "paid_project_or_agency":
        value += 45; reasons.append("explicit_project_or_agency_language")
    elif kind == "buyer_request_needs_scope_confirmation":
        value += 25; reasons.append("buyer_request_without_stated_commercial_terms")
    else:
        value += 15; reasons.append("employment_route_not_direct_project")
    value += min(30, 10 * len(tags))
    if "reliability" in tags:
        value += 10; reasons.append("repair_or_reliability_need")
    if re.search(r"(?:\$|USD|SGD|GBP|EUR|₹|INR)\s*\d", body, re.I):
        value += 15; reasons.append("budget_mentioned")
    return min(value, 100), reasons


def draft_reply(item: dict[str, Any]) -> str:
    tags = item["matching_tags"]
    focus = {
        "automation": "workflow state, idempotency, retries, and operational visibility",
        "ai_agents": "bounded agent behavior, structured outputs, and human approval gates",
        "backend": "API contracts, durable data state, and production deployment",
        "reliability": "the failure mode before adding new features",
    }
    focus_text = ", ".join(focus[tag] for tag in tags if tag in focus) or "the implementation boundary and acceptance criteria"
    salutation = item.get("author") or "team"
    return f"""Hi {salutation},

I read your request for {item['title']}. I would start by defining {focus_text}, then ship a contained implementation with a written acceptance checklist.

For a first paid milestone, I can provide a written root-cause/architecture brief and a containerized patch or implementation-ready PR. That keeps the scope measurable before either side commits to a larger build.

Relevant engineering assets: {ASSET_CATALOG}
LinkedIn: {OWNER_LINKEDIN}

If this is still active, please share the current stack, the failing/target workflow, and the desired deadline. I will reply here with a precise written scope and fixed-price milestone.

Kunal"""


class Desk:
    def __init__(self, args: argparse.Namespace, out: Path):
        self.args, self.out = args, out
        self.web = Web(out, args.delay)
        self.accepted: list[dict[str, Any]] = []
        self.rejected: list[dict[str, Any]] = []
        self.errors: list[dict[str, str]] = []

    def add(self, source: str, source_url: str, title: str, author: str, created: datetime | None, body: str, route: str,
            reply_count: int | None, pre_reasons: list[str] | None = None) -> None:
        body = plain(body)
        reasons = list(pre_reasons or []) + reject_reasons(
            title, body, created, self.args.days, reply_count, self.args.max_replies, self.args.min_complexity
        )
        record = {
            "id": hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:16],
            "source": source,
            "source_url": source_url,
            "portal_route": route,
            "title": title.strip(),
            "author": author.strip(),
            "created_at": created.isoformat() if created else None,
            "reply_count": reply_count,
            "snippet": body[:1200],
            "matching_tags": match_tags(title, body),
            "complexity_signals": complexity(title + "\n" + body),
        }
        if reasons:
            record["reasons"] = reasons
            self.rejected.append(record)
            return
        record["opportunity_kind"] = classify(title, body)
        record["score"], record["score_reasons"] = score(record["opportunity_kind"], record["matching_tags"], body)
        record["review_status"] = "draft_only_human_submission_required"
        record["draft"] = draft_reply(record)
        self.accepted.append(record)

    def error(self, source: str, url: str, exc: Exception) -> None:
        self.errors.append({"source": source, "url": url, "error": f"{type(exc).__name__}: {exc}"})


def harvest_discourse(desk: Desk, name: str) -> None:
    root, feed_path = SOURCES[name]
    feed_url = root + feed_path
    try:
        data = desk.web.json(feed_url)
        topic_list = data.get("topic_list", {}) if isinstance(data, dict) else {}
        topics = topic_list.get("topics", []) if isinstance(topic_list, dict) else []
        for topic in topics[:desk.args.max_items]:
            if not isinstance(topic, dict) or not topic.get("id") or not topic.get("slug"):
                continue
            url = f"{root}/t/{topic['slug']}/{topic['id']}"
            try:
                detail = desk.web.json(url + ".json")
                posts = detail.get("post_stream", {}).get("posts", [])
                original = next((post for post in posts if post.get("post_number") == 1), None)
                if not original:
                    desk.error(name, url, ValueError("original post missing")); continue
                pre_reasons = []
                if topic.get("closed") is True or detail.get("closed") is True:
                    pre_reasons.append("topic_locked_or_closed")
                if topic.get("deleted_at") or detail.get("deleted_at"):
                    pre_reasons.append("topic_deleted")
                replies = topic.get("reply_count")
                if not isinstance(replies, int):
                    posts_count = topic.get("posts_count")
                    replies = posts_count - 1 if isinstance(posts_count, int) and posts_count >= 1 else None
                desk.add(name, url, str(topic.get("title", "")), str(original.get("username", "")),
                         parse_date(topic.get("created_at")), str(original.get("cooked", "")),
                         "Reply in this topic after signing in", replies, pre_reasons)
            except Exception as exc:
                desk.error(name, url, exc)
    except Exception as exc:
        desk.error(name, feed_url, exc)


def harvest_reddit(desk: Desk) -> None:
    for subreddit in ("forhire", "freelance_forhire", "jobbit"):
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={desk.args.max_items}"
        try:
            data = desk.web.json(url, api=True)
            children = data.get("data", {}).get("children", [])
            for child in children:
                post = child.get("data", {}) if isinstance(child, dict) else {}
                title = str(post.get("title", ""))
                if "hiring" not in title.casefold():
                    continue
                permalink = str(post.get("permalink", ""))
                if not permalink.startswith("/"):
                    continue
                replies = post.get("num_comments")
                desk.add("reddit", "https://www.reddit.com" + permalink, title, str(post.get("author", "")),
                         parse_date(post.get("created_utc")), str(post.get("selftext", "")),
                         "Comment or DM only if the post invites it", replies if isinstance(replies, int) else None)
        except Exception as exc:
            desk.error("reddit", url, exc)


def harvest_hn(desk: Desk) -> None:
    endpoint = "https://hn.algolia.com/api/v1/search_by_date?" + urlencode({"tags": "comment,author_whoishiring", "hitsPerPage": desk.args.max_items})
    try:
        data = desk.web.json(endpoint, api=True)
        for hit in data.get("hits", []):
            if not isinstance(hit, dict):
                continue
            identifier = str(hit.get("objectID", ""))
            if not identifier.isdigit():
                continue
            body = html.unescape(str(hit.get("comment_text", "")))
            replies = hit.get("num_comments")
            desk.add("hacker_news", f"https://news.ycombinator.com/item?id={identifier}",
                     "HN Who is Hiring: " + str(hit.get("author", "")), str(hit.get("author", "")),
                     parse_date(hit.get("created_at")), body, "Reply through Hacker News only when the post invites contact",
                     replies if isinstance(replies, int) else 0)
    except Exception as exc:
        desk.error("hacker_news", endpoint, exc)


def write_output(desk: Desk) -> None:
    desk.accepted.sort(key=lambda row: (row["score"], row.get("created_at") or ""), reverse=True)
    (desk.out / "PORTAL_REVIEW_QUEUE.json").write_text(json.dumps(desk.accepted, indent=2, ensure_ascii=False), encoding="utf-8")
    (desk.out / "REJECTED_PORTAL_POSTS.json").write_text(json.dumps(desk.rejected, indent=2, ensure_ascii=False), encoding="utf-8")
    audit = {
        "created_at_utc": utcnow().isoformat(),
        "options": {key: str(value) if isinstance(value, Path) else value for key, value in vars(desk.args).items()},
        "accepted": len(desk.accepted), "rejected": len(desk.rejected), "errors": desk.errors,
        "receipts": desk.web.receipts,
        "policy": "No login, posting, bidding, DM, email, credential access, or automatic submission is implemented.",
    }
    (desk.out / "AUDIT.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Portal opportunity review queue", "", "Every item below is a draft only. Review the post live, then submit manually through the stated portal route.", ""]
    if not desk.accepted:
        lines.append("No source-filtered opportunities were found in this run.")
    for item in desk.accepted:
        lines += [f"## {item['title']}", "", f"- **Score:** {item['score']}/100 — {', '.join(item['score_reasons'])}",
                  f"- **Source:** {item['source']} | [Open post]({item['source_url']})", f"- **Route:** {item['portal_route']}",
                  f"- **Published:** {item['created_at']} | **Replies:** {item['reply_count']}",
                  f"- **Fit:** {', '.join(item['matching_tags'])}",
                  f"- **Complexity:** {', '.join(item['complexity_signals'])}", "", "### Draft", "", item["draft"], ""]
    (desk.out / "PORTAL_REVIEW_QUEUE.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources", nargs="+", choices=[*SOURCES, "reddit", "hn"], default=[*SOURCES, "hn"],
        help="Public feeds to inspect. Reddit is opt-in because its public JSON endpoint may require a logged-in browser session.",
    )
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--max-items", type=int, default=30, help="Maximum entries fetched from each source")
    parser.add_argument("--max-replies", type=int, default=3, help="Keep posts with at most this many replies")
    parser.add_argument("--min-complexity", type=int, default=3, help="Required distinct technical-system signals")
    parser.add_argument("--delay", type=float, default=0.6)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "output")
    args = parser.parse_args()
    if args.days < 1 or args.limit < 1 or args.max_items < 1 or args.max_replies < 0 or args.min_complexity < 1 or args.delay < 0:
        parser.error("days, limit, max-items, and min-complexity must be positive; max-replies cannot be negative; delay cannot be negative")
    out = args.out / ("portal_desk_" + utcnow().strftime("%Y%m%dT%H%M%S%fZ"))
    out.mkdir(parents=True, exist_ok=False)
    desk = Desk(args, out)
    for source in args.sources:
        if source in SOURCES:
            harvest_discourse(desk, source)
        elif source == "reddit":
            harvest_reddit(desk)
        elif source == "hn":
            harvest_hn(desk)
    desk.accepted = desk.accepted[:args.limit]
    write_output(desk)
    print(json.dumps({"output": str(out), "review_queue": len(desk.accepted), "rejected": len(desk.rejected), "errors": len(desk.errors)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
