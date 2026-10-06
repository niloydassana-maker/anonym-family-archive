with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    c = f.read()

# Add debug for response headers
old = """            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    first_token = True"""

new = """            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    # DEBUG: print response headers
                    print(f"[LLM RESPONSE HEADERS] {dict(resp.headers)}", flush=True)
                    content_encoding = resp.headers.get("Content-Encoding", "none")
                    print(f"[LLM CONTENT ENCODING] {content_encoding}", flush=True)
                    first_token = True"""

c = c.replace(old, new)

with open(r"D:\anonym\modal_voice_service.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Added response headers debug")