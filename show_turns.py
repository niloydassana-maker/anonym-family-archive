# -*- coding: utf-8 -*-
import json

raw = open(r'D:\anonym\lastturns_hindi2.txt', encoding='utf-8').read()
try:
    evs = json.loads(raw)
    if isinstance(evs, str):
        evs = json.loads(evs)
except Exception as e:
    print('PARSE-ERR %s' % e)
    raise SystemExit

print('EVENTS %d' % len(evs))
for e in evs[-6:]:
    heard = (e.get('heard') or '')[:120]
    reply = (e.get('reply') or '')[:160]
    print('--- ts=%s stt=%s first_pcm=%s total=%s' % (e.get('ts'), e.get('stt_language'), e.get('first_pcm_ms'), e.get('total_ms')))
    with open(r'D:\anonym\turns_dump.txt', 'a', encoding='utf-8') as f:
        f.write('HEARD: %s\nREPLY: %s\n\n' % (heard, reply))
print('dumped')
