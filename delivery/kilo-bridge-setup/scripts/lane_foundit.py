"""lane_foundit.py - work-order C: read Foundit job cards, gate, report.

Thin GOAL-RUNNER (2026-10-07). Same shape as lane_jobs.py, on Foundit's DOM.
Foundit is the rebrand of monsterindia.com; the seeker session lives in Profile 17,
so a logged search returns real cards with no login wall.

The FOUNDIT-DOM WALL is handled in the TOOL LAYER, not here: `T.read_cards` sweeps
candidate selectors and picks the one with the most real nodes (MEASURE, never
guess). If none yields cards it records BLOCKED with the measured counts.

It READS and SCORES. It does not apply.
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lane_tools as T  # noqa: E402

FOUNDIT_HOME = "https://www.foundit.in/"
DEFAULT_QUERY = "artificial intelligence"

# The operator's REAL skills - IDENTICAL to lane_jobs.py so scores are comparable
# across portals. From the pinned resume + live profile headline. Never invent one.
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


def main(argv):
    query = " ".join(argv[1:]).strip() or DEFAULT_QUERY
    search_url = FOUNDIT_HOME
    lane = T.Lane("foundit", "search: " + query)
    lane.log("LANE_FOUNDIT start :: query = " + query)
    with T.session(lane) as c:
        lane.log("C1 navigate -> " + search_url)
        c.call_tool("browser_navigate", {"url": search_url})
        time.sleep(8)

        # Search through the live page control. The former /search/?query= path
        # now returns a 404; the authenticated home exposes this measured field.
        field = c._js("JSON.stringify(Array.from(document.querySelectorAll('input')).map(e=>({id:e.id,placeholder:e.placeholder,visible:!!(e.offsetWidth||e.offsetHeight)})))")
        if "heroSectionDesktop-skillsAutoComplete--input" not in str(field):
            lane.row(search_url[:70], "-", "-", "-", "find search control", T.BLOCKED,
                     "none", "measured job search input not present: " + str(field)[:150])
            return 2
        fill = c.fill("#heroSectionDesktop-skillsAutoComplete--input", query)
        lane.log("C2 fill search control -> " + str(fill)[:180])
        if "artificial intelligence" in query.lower():
            suggestion = c.find_and_click("Artificial Intelligence in Skill")
            lane.log("C2a select visible suggestion -> " + str(suggestion)[:180])
        submitted = c.find_and_click("Search")
        lane.log("C2b click visible Search -> " + str(submitted)[:180])
        time.sleep(10)

        page = T.read_page(c)
        lane.log("   url   = " + page["url"][:110])
        lane.log("   chars = %d" % len(page["body"]))

        if "/home/user" in page["url"]:
            p = lane.shot(c, "50-foundit-search-not-submitted-%s" % time.strftime("%Y%m%d-%H%M%S"))
            lane.row(page["url"][:70], "-", "-", "-", "submit search", T.BLOCKED,
                     str(p) if p else "none", "Search control did not navigate to a results page")
            return 2

        # A wall is declared only when the page is SHORT and carries a login marker
        # (a logged-OUT Foundit search still returns cards - length alone is a lie).
        wall = lane.wall(page["body"], page["title"])
        if wall and len(page["body"]) < 6000:
            lane.log("   !! login wall (%s) - BLOCKED" % wall)
            lane.row(search_url[:70], "-", "-", "-", "session check", T.BLOCKED,
                     "(none)", "login wall: " + wall)
            return 2
        if len(page["body"]) < 800:
            lane.log("   !! page empty/short - BLOCKED, not a fake DONE")
            lane.row(search_url[:70], "-", "-", "-", "open foundit search", T.BLOCKED,
                     "(none)", "body chars=%d" % len(page["body"]))
            return 2

        search_url = page["url"]
        p = lane.shot(c, "50-foundit-search-%s" % time.strftime("%Y%m%d-%H%M%S"))
        lane.log("   shot -> " + (str(p) if p else "FAILED"))

        # The DOM result DECIDES; measure, never guess a Foundit selector.
        got = T.read_cards(c, "foundit")
        lane.log("C3 cards: selector=%s n=%s" % (got["selector"], got["n"]))
        if not got["cards"]:
            lane.log("   !! no candidate selector yielded cards - BLOCKED with counts")
            lane.row(search_url[:70], "-", "-", "-", "read foundit cards", T.BLOCKED,
                     str(p) if p else "(none)",
                     "selector=%s n=%s" % (got["selector"], got["n"]))
            return 2

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
            lane.row((cd.get("href") or search_url)[:70], title[:78], "-", score,
                     "jobcard %d read+gated" % i,
                     T.MATCHED if gate else T.NO_MATCH,
                     str(p) if p else "(none)", "hits=" + ",".join(hits[:8]))

        lane.log("C4 evaluated=%d  gate-passed=%d" % (min(len(seen), 25), passed))
        if passed == 0 and seen:
            lane.log("   no card cleared the gate - honest result, not a failure to hide")
        lane.summary()
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
