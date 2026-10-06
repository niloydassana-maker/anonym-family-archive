# -*- coding: utf-8 -*-
import ast

src = open(r'D:\anonym\modal_voice_service_isearch.py', encoding='utf-8').read()
tree = ast.parse(src)
found = 0
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'WEB_DEMO_HTML':
                val = ast.literal_eval(node.value)
                print('type=%s len=%d' % (type(val).__name__, len(val)))
                lone = [hex(ord(ch)) for ch in val if 0xD800 <= ord(ch) <= 0xDFFF]
                print('lone surrogates: %d %s' % (len(lone), lone[:10]))
                print('nul bytes:', val.count('\x00'))
                try:
                    b = val.encode('utf-8')
                    print('utf8 encode OK bytes=%d' % len(b))
                except Exception as e:
                    print('ENCODE FAIL: %s' % e)
                found += 1
print('assignments found: %d' % found)
