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
txt('browser_navigate', {'url':'https://www.naukri.com/mnjuser/recommendedjobs'})
time.sleep(7)
# What renders the checkbox square? Inspect elements at the card's left edge + any role=checkbox
probe = '''(function(){
  var want='GenAI Architect';
  var arts=Array.from(document.querySelectorAll('article'));
  var card=null; for(var i=0;i<arts.length;i++){ if((arts[i].innerText||'').indexOf(want)>-1){card=arts[i];break;} }
  if(!card) return 'nocard';
  var rc = card.querySelector('[role=checkbox],[role=button],span[class*=check],div[class*=check],i[class*=check]');
  var info={};
  if(rc){ for(var k=0;k<rc.attributes.length;k++){info[rc.attributes[k].name]=rc.attributes[k].value.slice(0,70);} }
  // also scan for any element whose class mentions check/select/tick on whole page
  var cand=Array.from(document.querySelectorAll('[class*=check],[class*=select],[role=checkbox]')).slice(0,6).map(function(e){return {tag:e.tagName,cls:(e.className||'').toString().slice(0,70),role:e.getAttribute('role')};});
  return JSON.stringify({cardSel: rc?info:null, candidates:cand});
})()'''
print('SEL:', js(probe))
# screenshot the card region
r = c.call_tool('browser_screenshot', {'format':'png'}) or {}
for b in r.get('content', []):
    if b.get('type')=='image':
        open(EVID + r'\apply-select-state.png','wb').write(base64.b64decode(b['data']))
        print('SHOT saved')
c.close()
