with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    c = f.read()

# Remove all debug additions
# 1. Remove SSE line debug
c = c.replace("""                    line_count = 0
                    for line in resp:
                        line_count += 1
                        raw_line = line.decode("utf-8", errors="replace").strip()
                        if line_count <= 10:
                            print(f"[LLM RAW SSE LINE {line_count}] {raw_line[:500]}", flush=True)""", 
    """                    for line in resp:""")

# 2. Remove JSON parse debug
c = c.replace("""                        try:
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
                        delta = delta.replace("*", "").replace("#", "").replace("question", "").replace("answer", "")""",
    """                        try:
                            j = json.loads(line[6:])
                            choices = j.get("choices") or []
                            delta = choices[0].get("delta", {}).get("content") or "" if choices else ""
                        except Exception:
                            continue
                        delta = delta.replace("*", "").replace("#", "").replace("question", "").replace("answer", "")""")

# 3. Remove response headers debug
c = c.replace("""            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    # DEBUG: print response headers
                    print(f"[LLM RESPONSE HEADERS] {dict(resp.headers)}", flush=True)
                    content_encoding = resp.headers.get("Content-Encoding", "none")
                    print(f"[LLM CONTENT ENCODING] {content_encoding}", flush=True)
                    first_token = True""",
    """            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    first_token = True""")

# 4. Remove RAW DELTA debug
c = c.replace("""                        delta = delta.replace("*", "").replace("#", "").replace("question", "").replace("answer", "")
                        # DEBUG: log first few raw deltas
                        if first_token:
                            print(f"[LLM RAW DELTA] repr={repr(delta[:200])}", flush=True)
                        if not delta:
                            continue""",
    """                        delta = delta.replace("*", "").replace("#", "").replace("question", "").replace("answer", "")
                        if not delta:
                            continue""")

# 5. Remove non-streaming test endpoint
c = c.replace("""        @web_app.post("/test/llm_nonstream")
        async def test_llm_nonstream(req: Request):
            import urllib.request, json, os
            data = await req.json()
            user_text = data.get("text", "What are the clinic timings?")
            
            payload = {
                "model": VOICE_LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "Reply in concise spoken English."},
                    {"role": "user", "content": user_text}
                ],
                "max_tokens": 90,
                "temperature": 0.45,
                "top_p": 0.9,
                "stream": False,
            }
            data_json = json.dumps(payload).encode("utf-8")
            
            keys = [k.strip() for k in os.environ.get("NVIDIA_API_KEYS", "").split(",") if k.strip()]
            for key in keys:
                req_obj = urllib.request.Request(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    data=data_json,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    method="POST",
                )
                try:
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
                    continue
            return {"error": "All keys failed"}

        @web_app.get("/health")
        def health():""",
    """        @web_app.get("/health")
        def health():""")

# 6. Remove non-streaming error debug (already covered above)

# 7. Remove chat_template_kwargs comment line if present
c = c.replace("""        payload = {
            "model": VOICE_LLM_MODEL,
            "messages": messages,
            "max_tokens": 90,
            "temperature": 0.45,
            "top_p": 0.9,
            "stream": True,
            # chat_template_kwargs not supported for Llama models
        }""",
    """        payload = {
            "model": VOICE_LLM_MODEL,
            "messages": messages,
            "max_tokens": 90,
            "temperature": 0.45,
            "top_p": 0.9,
            "stream": True,
        }""")

with open(r"D:\anonym\modal_voice_service.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Cleaned up debug code")