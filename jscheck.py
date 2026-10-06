# -*- coding: utf-8 -*-
import re
src = open(r'D:\anonym\modal_voice_service_isearch.py', encoding='utf-8').read()
i = src.find('<script>')
j = src.find('</script>', i)
assert i > 0 and j > i, 'script tags not found'
js = src[i + len('<script>'):j]
open(r'D:\anonym\web_demo_check.js', 'w', encoding='utf-8').write(js)
# sanity: balanced braces/parens (rough)
print('js chars=%d braces=%d/%d parens=%d/%d' % (
    len(js), js.count('{'), js.count('}'), js.count('('), js.count(')')))
# key symbols present exactly once where required
for pat, want in [
    (r'function applyLang\(\)', 1), (r'function toggleLang\(\)', 1),
    (r'function pageLang\(\)', 1), (r'function snapshotOrig\(\)', 1),
    (r'var STR_EN', 1), (r'function updateLiveButton\(\)', 1),
    (r'function L\(k\)', 1),
]:
    n = len(re.findall(pat, js))
    print('%s x%d (want %d) %s' % (pat, n, want, 'OK' if n == want else 'MISMATCH'))
print('extracted')
