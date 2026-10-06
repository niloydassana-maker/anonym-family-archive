with open(r'D:\anonym\modal_voice_service_isearch.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Add control char stripping
old_delta = '                        delta = delta.replace("*", "").replace("#", "").replace("question", "").replace("answer", "")\n                        if not delta:\n                            continue'

new_delta = '''                        delta = delta.replace("*", "").replace("#", "").replace("question", "").replace("answer", "")
                        # Strip control characters (U+0010 DLE etc.) that corrupt the stream
                        delta = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", delta)
                        if not delta:
                            continue'''

c = c.replace(
    '                        delta = delta.replace("*", "").replace("#", "").replace("question", "").replace("answer", "")\n                        if not delta:\n                            continue',
    new_delta
)

with open(r"D:\anonym\modal_voice_service_isearch.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Added control char stripping")