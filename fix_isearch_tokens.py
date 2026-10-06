with open(r'D:\anonym\modal_voice_service_isearch.py', 'r', encoding='utf-8') as f:
    c = f.read()

def rep(old, new, name):
    global c
    n = c.count(old)
    if n != 1:
        raise SystemExit('ABORT: %s matched %d times. No changes written.' % (name, n))
    c = c.replace(old, new)
    print('patched: %s' % name)

rep('"max_tokens": 220,', '"max_tokens": 350,', 'token room 350')

rep("hint = \"Reply in simple spoken Hindi, Devanagari script.\" if lang == \"hi\" else \"Reply in concise spoken English.\"",
    "hint = \"Reply in simple spoken Hindi, Devanagari script. Answer the question directly with the facts. Do NOT greet again, do NOT repeat any welcome line.\" if lang == \"hi\" else \"Reply in concise spoken English. Answer the question directly with the facts. Do NOT greet again, do NOT repeat any welcome line.\"",
    'no-regreet hint')

with open(r'D:\anonym\modal_voice_service_isearch.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('TOKEN FIX APPLIED')
