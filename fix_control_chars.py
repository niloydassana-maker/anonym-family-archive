with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    c = f.read()

old = '                        delta = delta.replace("*", "").replace("#", "").replace("question", "").replace("answer", "")\n                        if not delta:\n                            continue'

new = '                        delta = delta.replace("*", "").replace("#", "").replace("question", "").replace("answer", "")\n                        # Strip control characters (U+0010 DLE etc.) that corrupt the stream\n                        delta = re.sub(r"[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f]", "", delta)\n                        if not delta:\n                            continue'

c = c.replace(old, new)

with open(r"D:\anonym\modal_voice_service.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Fixed control char stripping")