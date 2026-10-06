with open(r'D:\anonym\modal_voice_service_isearch.py', 'r', encoding='utf-8') as f:
    c = f.read()

def rep(old, new, name):
    global c
    n = c.count(old)
    if n != 1:
        raise SystemExit('ABORT: %s matched %d times. No changes written.' % (name, n))
    c = c.replace(old, new)
    print('patched: %s' % name)

start_anchor = '        @web_app.post("/debug/llm_raw")'
end_anchor = '        @web_app.get("/health")'
si = c.find(start_anchor)
ei = c.find(end_anchor)
if si < 0 or ei < 0 or si > ei:
    raise SystemExit('ABORT: debug block anchors not found')
block = c[si:ei]
if '/debug/llm_raw' not in block or 'NONSTREAM' not in block:
    raise SystemExit('ABORT: debug block content unexpected')
c = c[:si] + c[ei:]
print('removed: debug endpoint block (%d chars)' % (ei - si))

rep('"build": "isearch-en-005",', '"build": "isearch-en-006-final",', 'build marker 006')

with open(r'D:\anonym\modal_voice_service_isearch.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('FINAL CLEANUP APPLIED')
