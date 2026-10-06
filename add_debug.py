with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    c = f.read()

# Add debug after delta cleaning
old = """                        delta = delta.replace("*", "").replace("#", "").replace("question", "").replace("answer", "")
                        if not delta:
                            continue
                        if first_token:"""

new = """                        delta = delta.replace("*", "").replace("#", "").replace("question", "").replace("answer", "")
                        # DEBUG: log first few raw deltas
                        if first_token:
                            print(f"[LLM RAW DELTA] repr={repr(delta[:200])}", flush=True)
                        if not delta:
                            continue
                        if first_token:"""

c = c.replace(old, new)

with open(r"D:\anonym\modal_voice_service.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Debug added")