import sys, json, time
sys.path.insert(0, r'D:nonym\delivery\kilo-bridge-setup\scripts')
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
# ensure we are on the list page
txt('browser_navigate', {'url': 'https://www.naukri.com/mnjuser/recommendedjobs'})
time.sleep(8)
# dump the GenAI card's anchors + onclick handlers
probe = '''(function(){
  var want='GenAI Architect';
  var arts=Array.from(document.querySelectorAll('article'));
  for(var i=0;i<arts.length;i++){
    if((arts[i].innerText||'').indexOf(want)>-1){
      var as=Array.from(arts[i].querySelectorAll('a'));
      var links=as.map(function(a){return {href:(a.getAttribute('href')||''), text:(a.innerText||'').slice(0,50), cls:a.className};});
      return JSON.stringify({card:i, onclickAttr:arts[i].getAttribute('onclick'), anchors:links});
    }
  }
  return 'notfound';})()'''
print('PROBE:', js(probe))
c.close()
