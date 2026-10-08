import sys, json, time
sys.path.insert(0, r'D:\anonym\delivery\kilo-bridge-setup\scripts')
import agent360_client as A
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
def body():
    return str(js('document.body.innerText') or '')
txt('browser_navigate', {'url':'https://www.naukri.com/mnjuser/recommendedjobs'})
time.sleep(7)
# locate checkbox in GenAI card + the Apply button; report their identity
probe = '''(function(){
  var want='GenAI Architect';
  var arts=Array.from(document.querySelectorAll('article'));
  var card=null;
  for(var i=0;i<arts.length;i++){ if((arts[i].innerText||'').indexOf(want)>-1){card=arts[i];break;} }
  if(!card) return 'nocard';
  var cb=card.querySelector('input[type=checkbox]');
  var cbInfo = cb ? {checked:cb.checked, id:cb.id, name:cb.name, cls:cb.className} : 'no-checkbox-in-card';
  // all checkboxes count + Apply buttons on page
  var allCb = document.querySelectorAll('input[type=checkbox]').length;
  var btns=Array.from(document.querySelectorAll('button,a')).filter(function(b){var t=(b.innerText||'').trim().toLowerCase();return t==='apply'||t==='apply now';}).map(function(b){return {tag:b.tagName,text:(b.innerText||'').trim(),cls:(b.className||'').slice(0,60),disabled:b.disabled};});
  return JSON.stringify({cb:cbInfo, allCb:allCb, applyBtns:btns});
})()'''
print('PROBE:', js(probe))
c.close()
