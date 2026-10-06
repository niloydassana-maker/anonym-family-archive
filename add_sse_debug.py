with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    c = f.read()

# Add more debug - log raw SSE lines
old = """                    first_token = True
                    punct = ("।", ".", "?", "!", "\n", ";")
                    for line in resp:"""

new = """                    first_token = True
                    punct = ("।", ".", "?", "!", "\n", ";")
                    line_count = 0
                    for line in resp:
                        line_count += 1
                        raw_line = line.decode("utf-8", errors="replace").strip()
                        if line_count <= 10:
                            print(f"[LLM RAW SSE LINE {line_count}] {raw_line[:500]}", flush=True)"""

c = c.replace(old, new)

with open(r"D:\anonym\modal_voice_service.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Added SSE line debug")