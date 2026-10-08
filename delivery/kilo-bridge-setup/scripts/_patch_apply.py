import io, re
p = r'D:\anonym\delivery\kilo-bridge-setup\scripts\lane_apply.py'
src = io.open(p, encoding='utf-8').read()
lines = src.split('\n')
# locate the CLICK_JS line and the 'return 3' end of the moved-block
start = next(i for i,l in enumerate(lines) if 'CLICK_JS = (' in l)
# find the 'return 3' that closes the 'if not moved' block after start
end = None
for i in range(start, len(lines)):
    if lines[i].strip() == 'return 3' and 'if not moved' in '\n'.join(lines[max(0,i-6):i]):
        end = i
        break
assert end is not None, 'end not found'
new_block = '''        # PROVEN MECHANISM (measured 2026-10-07): recommended-jobs cards have NO <a>,
        # NO onclick, NO React nav (element.click + event dispatch both did nothing).
        # SELECT-THEN-APPLY: click styled .tuple-check-box in the card -> header button
        # turns "Apply N Job" (enabled) -> click it -> apply flow.
        # Receipt: select-01-checked.png shows checked box + blue "Apply 1 Job".
        CHECK_JS = ("(function(){var want=" + esc + ";"
                    "var arts=Array.from(document.querySelectorAll('article'));"
                    "for(var i=0;i<arts.length;i++){if(arts[i].innerText.indexOf(want)>-1){"
                    "var cb=arts[i].querySelector('.tuple-check-box');"
                    "if(cb){cb.click();return 'checked';}return 'no-checkbox';}}"
                    "return 'nocard';})()")
        before = href()
        log("A3 select card checkbox")
        sel = js(CHECK_JS)
        log("   select -> " + str(sel))
        time.sleep(2)

        APPLY_STATE_JS = ("(function(){var b=document.querySelector('.multi-apply-button')||"
                          "Array.from(document.querySelectorAll('button')).find(function(x){"
                          "return /^apply/i.test((x.innerText||'').trim());});"
                          "if(!b)return JSON.stringify({found:false});"
                          "return JSON.stringify({found:true,disabled:!!b.disabled,"
                          "label:(b.innerText||'').trim()});})()")
        ast = str(js(APPLY_STATE_JS) or "")
        log("   apply-button state = " + ast)
        p1 = shot("apply-02-selected-" + time.strftime("%Y%m%d%H%M%S"))
        log("   shot -> " + (str(p1) if p1 else "FAILED"))

        if sel != "checked":
            log("   !! could not select card - BLOCKED")
            ledger("naukri", JOBS_URL[:70], title[:70], "-", "-",
                   "select job card", "BLOCKED", str(p1) if p1 else "none",
                   "select=" + str(sel))
            return 3

        APPLY_JS = ("(function(){var b=document.querySelector('.multi-apply-button')||"
                    "Array.from(document.querySelectorAll('button')).find(function(x){"
                    "return /^apply/i.test((x.innerText||'').trim());});"
                    "if(!b)return 'nobtn'; if(b.disabled)return 'disabled';"
                    "b.click(); return 'clicked-apply';})()")
        log("A4 click Apply")
        ap = js(APPLY_JS)
        log("   apply -> " + str(ap))
        time.sleep(7)

        after = href()
        txt_after = body()
        low = txt_after.lower()
        # VERIFY: URL left the list OR a real apply-flow signal. Do NOT use
        # 'years of experience' - it appears in job descriptions (false positive).
        FLOW_SIGNALS = ["answer all the recruiter", "recruiter's question",
                        "apply for this job", "submit application",
                        "additional questions", "application submitted"]
        left_list = (after != JOBS_URL and "recommendedjobs" not in after)
        in_flow = any(s in low for s in FLOW_SIGNALS)
        moved = left_list or in_flow
        log("A5 after url=" + after[:110])
        log("   left_list=" + str(left_list) + " in_flow=" + str(in_flow)
            + " body_chars=" + str(len(txt_after)))
        tag = "apply-03-after-apply-" + time.strftime("%Y%m%d%H%M%S")
        p = shot(tag)
        log("   shot -> " + (str(p) if p else "FAILED"))

        if not moved:
            log("   !! apply did not open a flow - BLOCKED (honest, not a fake DONE)")
            ledger("naukri", after[:70], title[:70], "-", "-",
                   "open apply flow", "BLOCKED", str(p) if p else "none",
                   "select=" + str(sel) + " apply=" + str(ap))
            return 3'''
lines[start:end+1] = new_block.split('\n')
io.open(p, 'w', encoding='utf-8').write('\n'.join(lines))
print('PATCHED: replaced lines', start+1, 'to', end+1)
