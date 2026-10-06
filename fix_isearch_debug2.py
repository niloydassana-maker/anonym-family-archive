with open(r'D:\anonym\modal_voice_service_isearch.py', 'r', encoding='utf-8') as f:
    c = f.read()

def rep(old, new, name):
    global c
    n = c.count(old)
    if n != 1:
        raise SystemExit('ABORT: %s matched %d times. No changes written.' % (name, n))
    c = c.replace(old, new)
    print('patched: %s' % name)

anchor = '''        @web_app.get("/health")
        def health():'''
debug_ep = '''        @web_app.post("/debug/llm_raw")
        async def debug_llm_raw(req: Request):
            from fastapi.responses import JSONResponse
            import urllib.request
            try:
                data = await req.json()
            except Exception:
                data = {}
            user_text = (data.get("text") or "What are the clinic timings?").strip()
            mode = (data.get("mode") or "nonstream").strip().lower()
            keys = provider_api_keys()
            if not keys:
                return JSONResponse({"ok": False, "error": "no keys"})
            key = keys[0]
            payload = {
                "model": VOICE_LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "Reply in concise spoken English."},
                    {"role": "user", "content": user_text},
                ],
                "max_tokens": 60,
                "temperature": 0.45,
                "top_p": 0.9,
                "stream": (mode == "stream"),
            }
            body = json.dumps(payload).encode("utf-8")
            headers = {
                "Authorization": "Bearer " + key[:8] + "..." + key[-4:],
                "note": "key redacted",
            }
            req_obj = urllib.request.Request(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                data=body,
                headers={
                    "Authorization": "Bearer " + key,
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream" if mode == "stream" else "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req_obj, timeout=20) as resp:
                    resp_headers = dict(resp.headers)
                    raw = resp.read() if mode != "stream" else b""
                    lines = []
                    if mode == "stream":
                        for i, line in enumerate(resp):
                            if i >= 8:
                                break
                            lines.append(line.decode("utf-8", errors="replace")[:600])
                    else:
                        txt = raw.decode("utf-8", errors="replace")
                        return JSONResponse({
                            "ok": True, "mode": mode,
                            "resp_headers": resp_headers,
                            "raw_len": len(raw),
                            "body_ascii": txt[:2000].encode("ascii", errors="backslashreplace").decode("ascii"),
                        })
                    return JSONResponse({
                        "ok": True, "mode": mode,
                        "resp_headers": resp_headers,
                        "sse_lines_ascii": [l.encode("ascii", errors="backslashreplace").decode("ascii") for l in lines],
                    })
            except Exception as e:
                import urllib.error
                detail = ""
                if isinstance(e, urllib.error.HTTPError):
                    try:
                        detail = e.read().decode("utf-8", errors="replace")[:1000]
                    except Exception:
                        detail = "unreadable"
                    return JSONResponse({"ok": False, "http": e.code, "detail_ascii": detail.encode("ascii", errors="backslashreplace").decode("ascii")})
                return JSONResponse({"ok": False, "error": type(e).__name__ + ": " + str(e)[:500]})

        @web_app.get("/health")
        def health():'''
rep(anchor, debug_ep, 'debug endpoint')

with open(r'D:\anonym\modal_voice_service_isearch.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('DEBUG ENDPOINT ADDED')
