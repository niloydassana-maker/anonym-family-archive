"""_patch_fill_b.py - _fill_question returns (elem, actual) with read-back.
Marker-scanned, count==1 enforced."""
from pathlib import Path
P = Path(__file__).resolve().parent / "lane_apply.py"
s = P.read_text(encoding="utf-8")

old = (
    'def _fill_question(js, answer):\n'
    '    esc = json.dumps(answer)\n'
    '    FILL_JS = ("(function(){var ans=" + esc + ";"\n'
    '               "var f=document.querySelector(\'textarea\')||"\n'
    '               "document.querySelector(\'input[type=text]\');"\n'
    '               "if(!f)return \'nofield\';f.focus();"\n'
    '               "var s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,\'value\');"\n'
    '               "var t=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,\'value\');"\n'
    '               "var d=(f.tagName===\'TEXTAREA\'?t:s);"\n'
    '               "if(d&&d.set){d.set.call(f,ans);}else{f.value=ans;}"\n'
    '               "f.dispatchEvent(new Event(\'input\',{bubbles:true}));"\n'
    '               "f.dispatchEvent(new Event(\'change\',{bubbles:true}));"\n'
    '               "return \'filled\';})()")\n'
    '    return js(FILL_JS)\n'
)
new = (
    'def _fill_question(js, answer):\n'
    '    """Find the recruiter input (panel-scoped), write `answer`, READ IT BACK.\n'
    '    Return (elem_tag, actual_value). Caller MUST verify actual == answer:\n'
    '    2026-10-07 the old version returned \'filled\' while the field stayed EMPTY."""\n'
    '    esc = json.dumps(answer)\n'
    '    FILL_JS = ("(function(){var ans=" + esc + ";"\n'
    '               "var scope=document.querySelector(\'.chatbot_MessageContainer\');"\n'
    '               "scope=scope?(scope.parentElement||scope):document;"\n'
    '               "var f=scope.querySelector(\'textarea\')||"\n'
    '               "scope.querySelector(\'input[type=text]\')||"\n'
    '               "scope.querySelector(\'[contenteditable=true]\')||"\n'
    '               "document.querySelector(\'input[placeholder]\');"\n'
    '               "if(!f)return JSON.stringify({elem:\'nofield\',actual:\'\'});"\n'
    '               "try{f.focus();}catch(e){}"\n'
    '               "if(f.getAttribute(\'contenteditable\')===\'true\'){f.textContent=ans;}"\n'
    '               "else{var d=Object.getOwnPropertyDescriptor((f.tagName===\'TEXTAREA\'?"\n'
    '               "window.HTMLTextAreaElement:window.HTMLInputElement).prototype,\'value\');"\n'
    '               "if(d&&d.set){d.set.call(f,ans);}else{f.value=ans;}}"\n'
    '               "try{f.dispatchEvent(new Event(\'input\',{bubbles:true}));"\n'
    '               "f.dispatchEvent(new Event(\'change\',{bubbles:true}));}catch(e){}"\n'
    '               "var v=(f.getAttribute(\'contenteditable\')===\'true\')?"\n'
    '               "f.textContent:(f.value||\'\');"\n'
    '               "var tag=f.tagName+\'.\'+((f.className||\'\').toString().split(\' \')[0]);"\n'
    '               "return JSON.stringify({elem:tag,actual:v});})()")\n'
    '    r = js(FILL_JS)\n'
    '    if isinstance(r, dict):\n'
    '        r = r.get("result")\n'
    '    d = {}\n'
    '    if isinstance(r, str) and r.strip().startswith("{"):\n'
    '        try:\n'
    '            d = json.loads(r)\n'
    '        except Exception:\n'
    '            d = {}\n'
    '    return d.get("elem", ""), d.get("actual", "")\n'
)

n = s.count(old)
if n != 1:
    raise SystemExit("marker count != 1 (got %d) - aborting" % n)
P.write_text(s.replace(old, new, 1), encoding="utf-8")
print("patch B ok; lines:", len(P.read_text(encoding='utf-8').splitlines()))