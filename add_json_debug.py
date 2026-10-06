with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    c = f.read()

# Add debug for parsed JSON object
old = """                        try:
                            j = json.loads(line[6:])
                            choices = j.get("choices") or []
                            delta = choices[0].get("delta", {}).get("content") or "" if choices else ""
                        except Exception:
                            continue
                        delta = delta.replace("*", "").replace("#", "").replace("question", "").replace("answer", "")"""

new = """                        try:
                            j = json.loads(line[6:])
                            # DEBUG: log full parsed JSON for first few lines
                            if line_count <= 5:
                                print(f"[LLM PARSED JSON {line_count}] keys={list(j.keys())} choices={len(j.get('choices',[]))}", flush=True)
                                if j.get('choices'):
                                    delta_obj = j['choices'][0].get('delta', {})
                                    print(f"[LLM DELTA OBJ] keys={list(delta_obj.keys())}", flush=True)
                                    for k, v in delta_obj.items():
                                        print(f"[LLM DELTA {k}] repr={repr(str(v)[:200])}", flush=True)
                            choices = j.get("choices") or []
                            delta = choices[0].get("delta", {}).get("content") or "" if choices else ""
                            # Also check for reasoning_content
                            if not delta and choices:
                                delta = choices[0].get("delta", {}).get("reasoning_content") or ""
                        except Exception as e:
                            if line_count <= 5:
                                print(f"[LLM JSON PARSE ERROR] {e}", flush=True)
                            continue
                        delta = delta.replace("*", "").replace("#", "").replace("question", "").replace("answer", "")"""

c = c.replace(old, new)

with open(r"D:\anonym\modal_voice_service.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Added JSON parse debug")