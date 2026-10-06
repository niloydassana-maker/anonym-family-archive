with open(r'D:\anonym\modal_voice_service_isearch.py', 'r', encoding='utf-8') as f:
    c = f.read()

start_anchor = '        @web_app.post("/debug/llm_raw")'
end_anchor = '        @web_app.get("/health")'
si = c.find(start_anchor)
ei = c.find(end_anchor)
if si < 0 or ei < 0 or si > ei:
    raise SystemExit('ABORT: anchors not found si=%d ei=%d' % (si, ei))
block = c[si:ei]
if 'debug_llm_raw' not in block:
    raise SystemExit('ABORT: block content unexpected')
c = c[:si] + c[ei:]
print('removed debug block (%d chars)' % (ei - si))

old_marker = '"build": "isearch-en-005",'
new_marker = '"build": "isearch-en-006-final",'
if c.count(old_marker) != 1:
    raise SystemExit('ABORT: marker matched %d' % c.count(old_marker))
c = c.replace(old_marker, new_marker)
print('marker bumped')

with open(r'D:\anonym\modal_voice_service_isearch.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('FINAL CLEANUP APPLIED')
