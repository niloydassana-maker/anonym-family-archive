with open(r'D:\anonym\modal_voice_service_isearch.py', 'r', encoding='utf-8') as f:
    c = f.read()

def rep(old, new, name):
    global c
    n = c.count(old)
    if n != 1:
        raise SystemExit('ABORT: %s matched %d times. No changes written.' % (name, n))
    c = c.replace(old, new)
    print('patched: %s' % name)

rep('''        payload = {
            "model": VOICE_LLM_MODEL,
            "messages": messages,
            "max_tokens": 90,
            "temperature": 0.45,
            "top_p": 0.9,
            "stream": True,
            "chat_template_kwargs": {"enable_thinking": False},
        }''', '''        payload = {
            "model": VOICE_LLM_MODEL,
            "messages": messages,
            "max_tokens": 220,
            "temperature": 0.45,
            "top_p": 0.9,
            "stream": True,
            "chat_template_kwargs": {"enable_thinking": False},
        }''', 'max_tokens room for reasoning+answer')

rep('''                        try:
                            j = json.loads(line[6:])
                            choices = j.get("choices") or []
                            delta = choices[0].get("delta", {}).get("content") or "" if choices else ""
                        except Exception:
                            continue
                        delta = delta.replace("*", "").replace("#", "").replace("<think>", "").replace("</think>", "")
                        delta = re.sub(r"[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f]", "", delta)
                        if not delta:
                            continue''', '''                        try:
                            j = json.loads(line[6:])
                            choices = j.get("choices") or []
                            _d = choices[0].get("delta", {}) if choices else {}
                            # Nemotron streams thinking in reasoning_content and keeps
                            # content null until thinking ends. Never voice thinking.
                            _reason = _d.get("reasoning_content") or ""
                            if _reason:
                                _rstats[0] += len(_reason)
                            delta = _d.get("content") or ""
                        except Exception:
                            continue
                        delta = delta.replace("*", "").replace("#", "").replace("<think>", "").replace("</think>", "")
                        delta = re.sub(r"[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f\\u200b-\\u200f\\ufeff\\ufffd]", "", delta)
                        if not delta:
                            continue''', 'reasoning-aware delta parse')

rep('''        for key in keys:
            buf = ""
            emitted = False
            key_t0 = time.time()''', '''        for key in keys:
            buf = ""
            emitted = False
            _rstats = [0]
            key_t0 = time.time()''', 'reasoning counter init')

rep('''                    if buf.strip():
                        part = buf.strip()
                        if part[-1] not in "।.!?":
                            part += "।"
                        emitted = True
                        yield part
                    return''', '''                    if buf.strip():
                        part = buf.strip()
                        if part[-1] not in "।.!?":
                            part += "।"
                        emitted = True
                        yield part
                    if _rstats[0]:
                        print(f"[LLM REASONING SKIPPED] {_rstats[0]} chars thinking discarded, voiced only content", flush=True)
                    return''', 'reasoning skip log')

with open(r'D:\anonym\modal_voice_service_isearch.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('REASONING FIX APPLIED')
