import json
import re

with open('d:/anonym/modal_voice_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

urls = set(re.findall(r'https://[a-zA-Z0-9_\.-]+\.modal\.run[^\s\"\'\<\>]*', text))
print("Modal URLs in modal_voice_service.py:")
for u in sorted(urls):
    print(" -", u)
