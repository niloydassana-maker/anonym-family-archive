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
# ensure on list
txt('browser_navigate', {'url':'https://www.naukri.com/mnjuser/recommendedjobs'})
time.sleep(7)
before = body(); bhref = str(js('location.href') or '')
# Try React-aware click: use the title element, dispatch pointer/mouse events in order
probe = '''(function(){
  var want='GenAI Architect';
  var els=Array.from(document.querySelectorAll('article *'));
  var t=null;
  for(var i=0;i<els.length;i++){ if((els[i].innerText||'')===want || (els[i].innerText||'').indexOf(want)===0){ t=els[i]; if(t.tagName==='P'||t.tagName==='A'||t.tagName==='H2'||t.tagName==='SPAN') break; } }
  if(!t) return 'no-title-el';
  ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(function(ev){
    t.dispatchEvent(new MouseEvent(ev,{bubbles:true,cancelable:true,view:window}));
  });
  return 'dispatched-on-'+t.tagName;
})()'''
print('CLICK:', js(probe))
time.sleep(6)
after = body(); ahref = str(js('location.href') or '')
print('href before:', bhref[:80]); print('href after :', ahref[:80])
print('url_changed:', ahref!=bhref, ' body', len(before),'->',len(after))
# detect modal / new dialog
for kw in ['apply for this job','apply now','recruiter','how many years','submit','easy apply']:
    if kw in after.lower(): print('  marker:', kw)
# detect open modal element
modal = js('''(function(){var m=document.querySelector('[role=dialog],.modal,.apply-dialog,[class*=modal],[class*=dialog]');return m?(m.className||'').slice(0,80)+' || '+(m.innerText||'').slice(0,200):'none';})()''')
print('MODAL:', modal)
# tabs?
print('TABS:', json.dumps(c.list_tabs()))
c.close()
