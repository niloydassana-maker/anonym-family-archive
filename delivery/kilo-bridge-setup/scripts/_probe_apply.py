import sys, json, time, base64
sys.path.insert(0, r'D:\anonym\delivery\kilo-bridge-setup\scripts')
import agent360_client as A
EVID = r'D:\anonym\delivery\kilo-bridge-setup\evidence\employment-lane'
c = A.Agent360Client(); c.start()
def txt(name, args=None):
    r = c.call_tool(name, args or {}) or {}
    for b in r.get('content', []):
        if b.get('type') == 'text':
            try: return json.loads(b.get('text',''))
            except Exception: return b.get('text','')
    return ''
def js(e):
    r = txt('browser_execute_script', {'code': e})
    return r.get('result') if isinstance(r, dict) else r
def body(): return str(js('document.body.innerText') or '')
def shot(tag):
    r = c.call_tool('browser_screenshot', {'format':'png'}) or {}
    for b in r.get('content', []):
        if b.get('type')=='image':
            p = EVID + '\\' + tag + '.png'; open(p,'wb').write(base64.b64decode(b['data'])); return p
    return None
txt('browser_navigate', {'url':'https://www.naukri.com/mnjuser/recommendedjobs'})
time.sleep(7)
# 1. click the tuple-check-box in the GenAI card
sel = '''(function(){var want='GenAI Architect';var arts=Array.from(document.querySelectorAll('article'));
 for(var i=0;i<arts.length;i++){if((arts[i].innerText||'').indexOf(want)>-1){var cb=arts[i].querySelector('.tuple-check-box');if(cb){cb.click();return 'clicked-check';}return 'no-check';}}
 return 'nocard';})()'''
print('CHECK:', js(sel))
time.sleep(2)
# 2. is Apply enabled now?
state = '''(function(){var b=Array.from(document.querySelectorAll('button')).find(function(x){return (x.innerText||'').trim().toLowerCase()==='apply';});
 return JSON.stringify({applyDisabled: b?b.disabled:'no-btn', applyCls: b?(b.className||'').slice(0,50):''});})()'''
print('APPLY-STATE:', js(state))
shot('select-01-checked')
# 3. click Apply
ap = '''(function(){var b=Array.from(document.querySelectorAll('button')).find(function(x){return (x.innerText||'').trim().toLowerCase()==='apply';});
 if(!b) return 'nobtn'; if(b.disabled) return 'disabled'; b.click(); return 'clicked-apply';})()'''
print('APPLY-CLICK:', js(ap))
time.sleep(6)
print('href:', str(js('location.href'))[:110])
b=body(); low=b.lower()
print('body_chars:', len(b), ' has_applyflow:', ('apply for this job' in low or 'recruiter' in low or 'submit' in low))
for kw in ['answer all the recruiter','how many years of experience','apply for this job','submit application','additional questions','current ctc','notice period']:
    if kw in low: print('  MARKER:', kw)
shot('select-02-after-apply')
c.close()
