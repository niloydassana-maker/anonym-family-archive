"""_patch_save2.py - robust Save click. The panel control is NOT a <button>
(measured 2026-10-07: only Apply/Yes/No are buttons). Find any leaf element whose
text is exactly Save/Send, take the RIGHTMOST (right-hand drawer), climb to a
clickable ancestor, click it. Marker-scanned, count==1."""
from pathlib import Path
P = Path(__file__).resolve().parent / "lane_apply.py"
s = P.read_text(encoding="utf-8")

old = (
    '    SAVE_JS = ("(function(){var c=document.querySelector(\'.chatbot_MessageContainer\');"\n'
    '               "if(!c)return \'nopanel\';"\n'
    '               "var root=c.closest(\'div[class*=drawer],div[class*=Drawer],"\n'
    '               "div[class*=panel],div[class*=Panel]\')||c.parentElement;"\n'
    '               "var bs=Array.prototype.slice.call(root.querySelectorAll(\'button\'));"\n'
    '               "var b=bs.filter(function(x){return /^save$/i.test((x.innerText||\'\').trim());})[0];"\n'
    '               "if(!b)return \'nobtn\'; if(b.disabled)return \'disabled\';"\n'
    '               "b.click(); return \'clicked\';})()")\n'
)
new = (
    '    SAVE_JS = ("(function(){function clicky(el){var e=el;for(var i=0;i<4&&e;i++){"\n'
    '               "if(e.tagName===\'BUTTON\'||e.getAttribute(\'role\')===\'button\'||"\n'
    '               "/btn|button|save|send/i.test(e.className||\'\'))return e;e=e.parentElement;}"\n'
    '               "return el;}var els=document.querySelectorAll(\'*\'),c=[];"\n'
    '               "for(var i=0;i<els.length;i++){var e=els[i];"\n'
    '               "if(e.childElementCount>2)continue;var t=(e.innerText||\'\').trim();"\n'
    '               "if(t===\'Save\'||t===\'Send\'){var r=e.getBoundingClientRect();"\n'
    '               "if(r.width>0&&r.height>0)c.push({e:e,x:r.x,t:t});}}"\n'
    '               "if(!c.length)return \'nobtn\';c.sort(function(a,b){return b.x-a.x;});"\n'
    '               "var tgt=clicky(c[0].e);try{tgt.click();}catch(e){return \'clickerr\';}"\n'
    '               "return \'clicked:\'+c[0].t+\'@\'+Math.round(c[0].x);})()")\n'
)

n = s.count(old)
if n != 1:
    raise SystemExit("marker count != 1 (got %d) - aborting" % n)
P.write_text(s.replace(old, new, 1), encoding="utf-8")
print("patch save2 ok; lines:", len(P.read_text(encoding='utf-8').splitlines()))