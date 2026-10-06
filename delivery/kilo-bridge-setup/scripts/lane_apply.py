"""lane_apply.py - the money step: ONE MATCHED title -> the apply flow -> answer -> receipt.

Thin GOAL-RUNNER (2026-10-07). The mechanism lives in lane_tools.py:
  * session / ledger / screenshot / wall        -> T.Lane, T.session
  * card read that MEASURES its selector        -> T.read_cards
  * the recruiter-panel reader (measured wall)  -> T.read_recruiter_question
  * verified answer + save (read-back)          -> T.answer_and_save
This file states the GOAL: open the matched job's apply flow, answer the recruiter
gate from the operator's OWN record, screenshot, ledger - and NEVER claim APPLIED
without a submission-success signal. Every step is APPLIED with evidence,
APPLIED_STEP (gate answered, no submit), or BLOCKED with the exact reason.

LAWS OBEYED: JS .click()/keyboard only (mouse path is dead); screenshot = receipt;
never invent a fact; never force-submit past an unanswered gate; never spend money;
never touch login/password/OTP; ASCII out; BLOCKED beats a faked DONE.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lane_tools as T  # noqa: E402

JOBS_URL = "https://www.naukri.com/mnjuser/recommendedjobs"
DEFAULT_TITLE = "GenAI Architect | Generative AI | LLM | RAG | Agentic AI"
ANSWERS = HERE / "apply_answers.txt"

# VERIFY signals: a real apply-flow state marker (NOT 'years of experience', which
# appears in job descriptions -> false positive).
FLOW_SIGNALS = ["answer all the recruiter", "recruiter's question", "apply for this job",
                "submit application", "additional questions", "application submitted"]
SUCCESS = ["application submitted", "successfully applied",
           "you have successfully applied", "applied successfully"]


def _top_matched_title(lane):
    try:
        rows = lane.ledger_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return None
    for ln in reversed(rows):
        p = ln.split("\t")
        if len(p) >= 8 and p[7].strip() == T.MATCHED:
            return p[3].strip() or None
    return None


def main(argv):
    lane = T.Lane("naukri", "apply")
    title = " ".join(argv[1:]).strip() or _top_matched_title(lane) or DEFAULT_TITLE
    lane.log("LANE_APPLY start :: title = " + title)
    with T.session(lane) as c:
        # A1 - open the recommended list (NAVIGATE-FIRST: attach to the active tab)
        lane.log("A1 navigate -> " + JOBS_URL)
        c.call_tool("browser_navigate", {"url": JOBS_URL})
        time.sleep(12)

        # A2 - locate the job's card by exact title, POLLING (the SPA hydrates late:
        # article count 0 at +10s cold, 63 at +12s. A fixed sleep read an empty list.)
        idx, sel_used = -1, None
        for _ in range(15):
            cards = T.read_cards(c, "naukri")
            sel_used = cards["selector"]
            names = [(cd.get("title") or "") for cd in cards["cards"]]
            hits = [i for i, nm in enumerate(names) if title and title in nm]
            if hits:
                idx = hits[0]
                break
            lane.log("   A2 wait cards: n=%s selector=%s" % (cards["n"], cards["selector"]))
            time.sleep(2)
        lane.log("A2 card index = %d (selector=%s)" % (idx, sel_used))
        if idx < 0:
            lane.row(JOBS_URL[:70], title[:70], "-", "-", "locate job card", T.BLOCKED,
                     "none", "card not found by exact title")
            return 2

        # A3 - select the card, then press Apply. Naukri recommended-jobs cards carry
        # no <a>/onclick/React nav (element.click + event dispatch both no-op):
        # SELECT-THEN-APPLY is the proven mechanism (.tuple-check-box -> header button).
        sel = c._js(
            "(function(){var want=%s;var a=document.querySelectorAll('article');"
            "for(var i=0;i<a.length;i++){if((a[i].innerText||'').indexOf(want)>-1){"
            "var cb=a[i].querySelector('.tuple-check-box');if(cb){cb.click();return 'checked';}"
            "return 'no-checkbox';}}return 'nocard';})()" % json.dumps(title))
        lane.log("A3 select -> " + str(sel))
        time.sleep(2)
        ap = c._js(
            "(function(){var b=document.querySelector('.multi-apply-button')||"
            "Array.prototype.slice.call(document.querySelectorAll('button')).filter(function(x){"
            "return /^apply/i.test((x.innerText||'').trim());})[0];"
            "if(!b)return 'nobtn';if(b.disabled)return 'disabled';"
            "b.click();return 'clicked-apply';})()")
        lane.log("A4 apply -> " + str(ap))

        # A5 - wait for the recruiter panel and read the QUESTION itself (the panel
        # opens with a spinner + a header; the question renders seconds later).
        panel_q, in_flow = None, False
        page = {"url": JOBS_URL, "title": "", "body": ""}
        for _ in range(25):
            page = T.read_page(c)
            panel_q = T.read_recruiter_question(c)
            if panel_q:
                in_flow = True
                break
            low = page["body"].lower()
            if "answer all the recruiter" in low or "apply for this job" in low:
                in_flow = True
            time.sleep(2)
        after, low = page["url"], page["body"].lower()
        left_list = after != JOBS_URL and "recommendedjobs" not in after
        in_flow = in_flow or any(s in low for s in FLOW_SIGNALS)
        moved = left_list or in_flow
        p = lane.shot(c, "apply-03-after-apply-" + time.strftime("%Y%m%d%H%M%S"))
        lane.log("A5 url=%s left_list=%s in_flow=%s chars=%d"
                 % (after[:110], left_list, in_flow, len(page["body"])))
        if not moved:
            lane.log("   !! apply did not open a flow - BLOCKED (honest, not a fake DONE)")
            lane.row(after[:70], title[:70], "-", "-", "open apply flow", T.BLOCKED,
                     str(p) if p else "none", "select=%s apply=%s" % (sel, ap))
            return 3

        # A6 - answer the recruiter question(s): read question -> answer from the
        # operator's OWN record -> READ BACK -> Save -> next. Never invent an answer.
        seen, saves_ok, final = set(), 0, None
        for _round in range(1, 6):
            rq = T.read_recruiter_question(c)
            if not rq or rq in seen:
                break
            ran = T.answer_from_record(rq, ANSWERS)
            if not ran:
                lane.log("   !! not answerable from record -> BLOCKED: " + rq[:120])
                pf = lane.shot(c, "apply-05-blocked-" + time.strftime("%H%M%S"))
                lane.row(after[:70], title[:70], "-", "-", "recruiter question", T.BLOCKED,
                         str(pf) if pf else "none", "UNANSWERABLE Q=" + rq[:150])
                return 4
            seen.add(rq)
            lane.log("   ANSWERING: %s -> %s" % (rq[:110], ran))
            res = T.answer_and_save(c, rq, ran)
            lane.log("   fill elem=%s readback=%s save=%s"
                     % (res["elem"], str(res["actual"])[:25], res["save"]))
            if not res["ok"]:
                lane.log("   !! fill did NOT land - BLOCKED (not a fake APPLIED_STEP)")
                pf = lane.shot(c, "apply-05-fillfail-" + time.strftime("%H%M%S"))
                lane.row(after[:70], title[:70], "-", "-", "recruiter question", T.BLOCKED,
                         str(pf) if pf else "none",
                         "FILL FAILED elem=%s readback=%s" % (res["elem"], str(res["actual"])[:40]))
                return 4
            if str(res["save"]).startswith("clicked"):
                saves_ok += 1
            final = lane.shot(c, "apply-06-answered-%d-%s" % (_round, time.strftime("%H%M%S")))

        if seen and saves_ok:
            lane.row(after[:70], title[:70], "-", "-", "recruiter questions answered",
                     T.APPLIED_STEP, str(final) if final else "none",
                     "answered %d gate(s); saved; no force-submit" % len(seen))
            lane.log("ANSWERED %d gate(s), Save clicked, read-back verified." % len(seen))
            lane.summary()
            return 0
        if seen:
            lane.log("   !! answered but Save did not register -> BLOCKED (no honest submit)")
            lane.row(after[:70], title[:70], "-", "-", "recruiter questions answered",
                     T.BLOCKED, str(final) if final else "none",
                     "answered %d but save not confirmed" % len(seen))
            return 4

        # HONESTY: an open panel is NOT an application. APPLIED requires a submission
        # success signal; a panel with no question and no success text is BLOCKED.
        page = T.read_page(c)
        if any(s in page["body"].lower() for s in SUCCESS):
            lane.row(after[:70], title[:70], "-", "-", "application submitted", T.APPLIED,
                     str(p) if p else "none", "submitted url=" + after[:110])
            lane.log("DONE - submission success signal present.")
            lane.summary()
            return 0
        lane.log("   !! panel open but no recruiter question and no submission evidence"
                 " - BLOCKED (never a fake APPLIED)")
        lane.row(after[:70], title[:70], "-", "-", "open apply flow", T.BLOCKED,
                 str(p) if p else "none", "panel_open=%s no question rendered" % in_flow)
        return 4


if __name__ == "__main__":
    sys.exit(main(sys.argv))