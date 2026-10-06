with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    c = f.read()

# Add error debug for non-streaming
old = """                try:
                    with urllib.request.urlopen(req_obj, timeout=15) as resp:
                        print(f"[NONSTREAM HEADERS] {dict(resp.headers)}", flush=True)
                        raw = resp.read()
                        print(f"[NONSTREAM RAW BYTES] len={len(raw)} first_200={raw[:200]}", flush=True)
                        result = json.loads(raw.decode("utf-8", errors="replace"))
                        print(f"[NONSTREAM PARSED] {result}", flush=True)
                        return result
                except Exception as e:
                    print(f"[NONSTREAM ERROR] {e}", flush=True)
                    continue"""

new = """                try:
                    with urllib.request.urlopen(req_obj, timeout=15) as resp:
                        print(f"[NONSTREAM HEADERS] {dict(resp.headers)}", flush=True)
                        raw = resp.read()
                        print(f"[NONSTREAM RAW BYTES] len={len(raw)} first_200={raw[:200]}", flush=True)
                        result = json.loads(raw.decode("utf-8", errors="replace"))
                        print(f"[NONSTREAM PARSED] {result}", flush=True)
                        return result
                except urllib.error.HTTPError as e:
                    err_body = e.read().decode("utf-8", errors="replace")
                    print(f"[NONSTREAM HTTP ERROR {e.code}] {err_body}", flush=True)
                    continue
                except Exception as e:
                    print(f"[NONSTREAM ERROR] {type(e).__name__}: {e}", flush=True)
                    continue"""

c = c.replace(old, new)

with open(r"D:\anonym\modal_voice_service.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Added HTTP error debug")