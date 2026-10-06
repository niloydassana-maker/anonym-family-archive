"""_test_lane_tools.py - OFFLINE regression tests for the hardened tool layer.

No Chrome, no browser, no network. Proves the pure logic of lane_tools.py and that
the new verifying verbs exist on Agent360Client. Run:
    python _test_lane_tools.py
Exit 0 = all pass. This is the receipt that the refactor's logic is sound before
any live lane runs it.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lane_tools as T          # noqa: E402
import agent360_client as A     # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ((" :: " + detail) if detail else ""))
    if not cond:
        FAILS.append(name)


# 1. score_card: counts real skills, gate is callers' job
n, hits = T.score_card("We need GenAI and RAG with Python and AWS", ["genai", "rag", "python", "azure"])
check("score_card counts present skills", n == 3, "n=%d hits=%s" % (n, hits))
check("score_card sees the right hits", set(hits) == {"genai", "rag", "python"})
n0, _ = T.score_card("", ["genai"])
check("score_card on empty text = 0", n0 == 0)

# 2. answer_from_record: reads the operator's record, substring match, never invents
rec = HERE / "apply_answers.txt"
ans = T.answer_from_record("How many years of hands-on experience do you have in GenAI/LLM?", rec)
check("answer_from_record matches genai question", ans == "2", "ans=%r" % ans)
check("answer_from_record returns None for unknown", T.answer_from_record("What is your shoe size?", rec) is None)

# 3. wall detection: by NAME, never on length alone
check("wall detects login", T.Lane("x", "t").wall("Jobseeker's Login: Search the Best Jobs") == "jobseeker's login")
check("wall detects captcha", T.Lane("x", "t").wall("please verify you are human") is not None)
check("wall silent on a real page", T.Lane("x", "t").wall("Recommended jobs for you. Apply now. " * 50) is None)

# 4. the new verifying verbs exist on the client
for verb in ("_js", "url", "toast", "readback", "fill_verified", "find_and_click",
             "findclick", "fill_checked"):
    check("client has verb %s" % verb, hasattr(A.Agent360Client, verb))

# 5. the JS builders format without error (no live call - just the string ops)
try:
    sels = T.CARD_SELECTORS["naukri"]
    js = T._READ_CARDS_JS % (__import__("json").dumps(sels), 60)
    check("_READ_CARDS_JS formats", "querySelectorAll" in js and "naukri" not in js)
    fill = T._FILL_JS % __import__("json").dumps("2")
    check("_FILL_JS formats", "chatbot_MessageContainer" in fill and '"2"' in fill)
    check("_PANEL_Q_JS present", ".chatbot_MessageContainer" in T._PANEL_Q_JS)
    check("_SAVE_JS present", "'Save'" in T._SAVE_JS and "'Send'" in T._SAVE_JS)
except Exception as e:
    check("JS builders format", False, repr(e))

# 6. status vocabulary is the mission's exact set
check("statuses present", {T.MATCHED, T.APPLIED, T.APPLIED_STEP, T.BLOCKED,
                           T.NO_MATCH, T.RATE_LIMITED, T.FAILED, T.OK}
      == {"MATCHED", "APPLIED", "APPLIED_STEP", "BLOCKED", "NO_MATCH", "RATE_LIMITED", "FAILED", "OK"})


# 7. _fill_panel unwrap: _js already parses the JSON string to a dict, so the panel
#    helper MUST read the dict directly (the 2026-10-07 double-unwrap defect).
class _FakeClient:
    def __init__(self, ret):
        self.ret = ret
    def _js(self, expr):
        return self.ret
    def call_tool(self, name, args=None):
        return {}


elem, actual = T._fill_panel(_FakeClient({"elem": "TEXTAREA.x", "actual": "2"}), "2")
check("_fill_panel reads dict-direct", (elem, actual) == ("TEXTAREA.x", "2"), "%r" % ((elem, actual),))
elem2, actual2 = T._fill_panel(_FakeClient({"result": {"elem": "INPUT.y", "actual": "2"}}), "2")
check("_fill_panel tolerates result-wrap", (elem2, actual2) == ("INPUT.y", "2"))
elem3, actual3 = T._fill_panel(_FakeClient('{"elem":"INPUT.z","actual":"2"}'), "2")
check("_fill_panel parses a JSON string", (elem3, actual3) == ("INPUT.z", "2"))

res = T.answer_and_save(_FakeClient({"elem": "TEXTAREA.x", "actual": "2"}), "Q?", "2")
check("answer_and_save ok when readback matches", res["ok"] is True, "res=%r" % res)
res2 = T.answer_and_save(_FakeClient({"elem": "TEXTAREA.x", "actual": ""}), "Q?", "2")
check("answer_and_save NOT ok when field empty", res2["ok"] is False)

print("")
if FAILS:
    print("TESTS FAILED: %d" % len(FAILS))
    for f in FAILS:
        print("  - " + f)
    sys.exit(1)
print("ALL LANE-TOOLS TESTS PASSED")