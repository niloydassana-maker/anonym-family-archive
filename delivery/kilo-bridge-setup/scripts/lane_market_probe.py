"""Read-only live search E2E for the Indeed and LinkedIn market lanes."""
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lane_tools as T  # noqa: E402
from lane_jobs import SKILLS  # noqa: E402

SEARCHES = [
    ("indeed", "https://in.indeed.com/jobs?" + urlencode({"q": "Generative AI Architect", "l": "Remote"})),
    ("linkedin", "https://www.linkedin.com/jobs/search/?" + urlencode({"keywords": "Generative AI Architect", "location": "India"})),
]


def main():
    failed = []
    with T.session(T.Lane("market", "Indeed + LinkedIn live search")) as c:
        for portal, url in SEARCHES:
            lane = T.Lane(portal, "live job search")
            print("\n%s: navigate -> %s" % (portal, url), flush=True)
            c.call_tool("browser_navigate", {"url": url})
            page = {"body": "", "title": "", "url": url}
            for _ in range(10):
                time.sleep(2)
                page = T.read_page(c)
                if len(page["body"]) >= 800:
                    break
            wall = lane.wall(page["body"], page["title"])
            if wall:
                lane.row(url[:70], "-", "-", "-", "search session", T.BLOCKED,
                         "none", "login/captcha wall=" + wall)
                print("BLOCKED: visible wall: %s" % wall, flush=True)
                failed.append(portal)
                continue
            shot = lane.shot(c, "60-%s-search-%s" % (portal, time.strftime("%Y%m%d-%H%M%S")))
            if portal == "linkedin":
                raw = c._js(
                    "Array.from(document.querySelectorAll('a[href*=\"/jobs/view/\"]'),"
                    "function(a){var box=a.closest('li')||a.parentElement;"
                    "return {title:(a.innerText||a.getAttribute('aria-label')||'').trim(),"
                    "href:a.href,text:(box?(box.innerText||''):(a.innerText||''))};})"
                    ".filter(function(x){return x.title&&x.href;}).slice(0,50)")
                if isinstance(raw, str):
                    try:
                        import json
                        raw = json.loads(raw)
                    except Exception:
                        raw = []
                cards = {"n": len(raw) if isinstance(raw, list) else 0,
                         "selector": "a[href*=jobs/view]", "cards": raw if isinstance(raw, list) else []}
            else:
                cards = T.read_cards(c, portal)
            print("page chars=%d cards=%d selector=%s screenshot=%s" %
                  (len(page["body"]), cards["n"], cards["selector"], bool(shot)), flush=True)
            if len(page["body"]) < 800 or not shot or not cards["cards"]:
                reason = "body=%d cards=%d screenshot=%s" % (len(page["body"]), cards["n"], bool(shot))
                lane.row(url[:70], "-", "-", "-", "read live results", T.BLOCKED,
                         str(shot) if shot else "none", reason)
                failed.append(portal)
                continue
            unique, passed = set(), 0
            for i, card in enumerate(cards["cards"][:25], 1):
                title = (card.get("title") or "").strip()
                if not title or title in unique:
                    continue
                unique.add(title)
                score, hits = T.score_card(card.get("text"), SKILLS)
                status = T.MATCHED if score >= 2 else T.NO_MATCH
                passed += score >= 2
                lane.row((card.get("href") or url)[:70], title[:78], "-", score,
                         "search result %d skill gate" % i, status,
                         str(shot), "hits=" + ",".join(hits[:8]))
            if not unique:
                lane.row(url[:70], "-", "-", "-", "score results", T.BLOCKED,
                         str(shot), "search cards yielded no titles")
                failed.append(portal)
            print("read %d distinct job cards; %d cleared the >=2 skill gate" %
                  (len(unique), passed), flush=True)
    print("\nMARKET-LANES: " + ("RED " + ",".join(failed) if failed else "GREEN"), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
