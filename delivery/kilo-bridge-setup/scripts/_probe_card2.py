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
txt('browser_navigate', {'url': 'https://www.naukri.com/mnjuser/recommendedjobs'})
time.sleep(8)
probe = '''(function(){
  var want='GenAI Architect';
  var arts=Array.from(document.querySelectorAll('article'));
  for(var i=0;i<arts.length;i++){
    if((arts[i].innerText||'').indexOf(want)>-1){
      var attrs={};
      for(var k=0;k<arts[i].attributes.length;k++){var a=arts[i].attributes[k];attrs[a.name]=a.value.slice(0,80);}
      // child data attrs + any element with data-job or similar
      var kids=Array.from(arts[i].querySelectorAll('[data-job-id],[data-id],[data-url],a'));
      var kd=kids.map(function(e){return {tag:e.tagName,href:(e.getAttribute&&e.getAttribute('href'))||'',did:e.getAttribute('data-job-id')||e.getAttribute('data-id')||'',durl:e.getAttribute('data-url')||''};});
      return JSON.stringify({card:i, attrs:attrs, kids:kd.slice(0,10)});
    }
  }
  return 'notfound';})()'''
print('PROBE2:', js(probe))
c.close()
