with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    c = f.read()

# Add a test endpoint for non-streaming LLM request
old = """        @web_app.get("/health")
        def health():"""

new = """        @web_app.post("/test/llm_nonstream")
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
                except Exception as e:
                    print(f"[NONSTREAM ERROR] {e}", flush=True)
                    continue
            return {"error": "All keys failed"}

        @web_app.get("/health")
        def health():"""

c = c.replace(old, new)

with open(r"D:\anonym\modal_voice_service.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Added non-streaming test endpoint")