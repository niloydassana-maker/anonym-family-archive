"""_patch_save_helper.py - add _save(js): press the panel's Save (send) button.
Panel-scoped, reports the click state. Marker insert before _answer_from_record."""
from pathlib import Path
P = Path(__file__).resolve().parent / "lane_apply.py"
s = P.read_text(encoding="utf-8")

anchor = "def _answer_from_record(question):\n"
helper = (
    'def _save(js):\n'
    '    """Press the recruiter panel\'s Save (send) button, panel-scoped.\n'
    '    Returns the click state string."""\n'
    '    SAVE_JS = ("(function(){var c=document.querySelector(\'.chatbot_MessageContainer\');"\n'
    '               "if(!c)return \'nopanel\';"\n'
    '               "var root=c.closest(\'div[class*=drawer],div[class*=Drawer],"\n'
    '               "div[class*=panel],div[class*=Panel]\')||c.parentElement;"\n'
    '               "var bs=Array.prototype.slice.call(root.querySelectorAll(\'button\'));"\n'
    '               "var b=bs.filter(function(x){return /^save$/i.test((x.innerText||\'\').trim());})[0];"\n'
    '               "if(!b)return \'nobtn\'; if(b.disabled)return \'disabled\';"\n'
    '               "b.click(); return \'clicked\';})()")\n'
    '    r = js(SAVE_JS)\n'
    '    if isinstance(r, dict):\n'
    '        r = r.get("result")\n'
    '    return r\n'
    '\n'
    '\n'
    + anchor
)

n = s.count(anchor)
if n != 1:
    raise SystemExit("anchor count != 1 (got %d) - aborting" % n)
P.write_text(s.replace(anchor, helper, 1), encoding="utf-8")
print("patch save-helper ok; lines:", len(P.read_text(encoding='utf-8').splitlines()))