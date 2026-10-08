"""lane_jobs.py - work-order B: Naukri recommended jobs -> score -> gate -> report.

Thin GOAL-RUNNER (2026-10-07). The mechanism - session, ledger, screenshot, the
card read that MEASURES its own selector, the wall test - lives in lane_tools.py,
one hardened copy shared with every other lane. This file states the GOAL only.

It READS and SCORES. It does not apply; the money step is lane_apply.py.
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lane_tools as T  # noqa: E402

JOBS_URL = "https://www.naukri.com/mnjuser/recommendedjobs"

# The operator's REAL skills - IDENTICAL to lane_foundit.py so scores are comparable
# across portals. From the pinned resume + live profile headline. Never invent one.
# (kilo_apply_resume.pdf, SHA256 DE81F585...FC339F)
DEFAULT_SKILLS = [
    "ai agents", "agentic", "langchain", "rag", "vector", "generative ai",
    "genai", "llm", "prompt", "python", "java", "spring", "node", "nodejs",
    "aws", "cloud", "api", "microservice", "webrtc", "upi", "npci", "payments",
    "fintech", "sqlite", "sql", "rest", "docker", "kubernetes", "architect",
    "backend", "full stack", "fullstack", "team lead", "technical lead",
    "solution architect", "principal", "staff engineer", "engineering manager",
    "distributed", "scalable", "devops", "ci/cd", "git",
]
SKILLS = T.candidate_skills() or DEFAULT_SKILLS


def main():
    lane = T.Lane("naukri", "recommended jobs")
    with T.session(lane) as c:
        # NAVIGATE-FIRST LAW: the client attaches to the active tab, which may be
        # about:blank. Always navigate, then read.
        lane.log("B1 navigate -> " + JOBS_URL)
        c.call_tool("browser_navigate", {"url": JOBS_URL})
        time.sleep(12)

        page = T.read_page(c)
        lane.log("   url   = " + page["url"][:110])
        lane.log("   chars = %d" % len(page["body"]))

        wall = lane.wall(page["body"], page["title"])
        if wall:
            lane.log("   !! login wall (%s) - BLOCKED, never a fake DONE" % wall)
            lane.row(JOBS_URL[:70], "-", "-", "-", "session check", T.BLOCKED,
                     "(none)", "login wall: " + wall)
            return 2
        if len(page["body"]) < 800:
            lane.log("   !! page empty/short - recording BLOCKED, not a fake DONE")
            lane.row(JOBS_URL[:70], "-", "-", "-", "open recommended jobs", T.BLOCKED,
                     "(none)", "body chars=%d" % len(page["body"]))
            return 2

        p = lane.shot(c, "40-naukri-recommended-%s" % time.strftime("%Y%m%d-%H%M%S"))
        lane.log("   shot -> " + (str(p) if p else "FAILED"))

        got = T.read_cards(c, "naukri")
        lane.log("B3 cards: selector=%s n=%s" % (got["selector"], got["n"]))
        seen, passed = set(), 0
        for i, cd in enumerate(got["cards"][:25], 1):
            title = (cd.get("title") or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            score, hits = T.score_card(cd.get("text"), SKILLS)
            gate = score >= 2
            passed += 1 if gate else 0
            lane.log("   [%02d] score=%-2d %-4s %s"
                     % (i, score, "PASS" if gate else "skip", title[:78]))
            lane.row((cd.get("href") or JOBS_URL)[:70], title[:78], "-", score,
                     "jobcard %d read+gated" % i,
                     T.MATCHED if gate else T.NO_MATCH,
                     str(p) if p else "(none)", "hits=" + ",".join(hits[:8]))

        lane.log("B4 evaluated=%d  gate-passed=%d" % (min(len(seen), 25), passed))
        if passed == 0 and seen:
            lane.log("   no card cleared the gate - honest result, not a failure to hide")
        lane.summary()
        return 0


if __name__ == "__main__":
    sys.exit(main())
