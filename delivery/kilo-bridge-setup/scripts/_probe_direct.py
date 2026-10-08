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
jid = '051026007395'
# candidate direct URLs for a naukri job id
cands = [
  'https://www.naukri.com/job-details-' + jid,
  'https://www.naukri.com/job-apply-' + jid,
]
for u in cands:
    txt('browser_navigate', {'url': u})
    time.sleep(7)
    href = str(js('location.href') or '')
    b = body()
    low = b.lower()
    mark = ('apply' in low, 'job-details' in href or 'job-apply' in href, len(b))
    print('URL:', u)
    print('  -> landed:', href[:120])
    print('  -> has_apply_word:', ('apply' in low), ' body_chars:', len(b))
    # look for a recruiter question or an Apply button
    print('  -> recruiter_q:', 'recruiter' in low, ' years_exp:', 'years of experience' in low)
    print('  -> head:', b[:200].replace(chr(10),' | '))
    print('---')
c.close()
