with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    c = f.read()

# Remove chat_template_kwargs for Llama models (not supported)
old = """        payload = {
            "model": VOICE_LLM_MODEL,
            "messages": messages,
            "max_tokens": 90,
            "temperature": 0.45,
            "top_p": 0.9,
            "stream": True,
            "chat_template_kwargs": {"enable_thinking": False},
        }"""

new = """        payload = {
            "model": VOICE_LLM_MODEL,
            "messages": messages,
            "max_tokens": 90,
            "temperature": 0.45,
            "top_p": 0.9,
            "stream": True,
            # chat_template_kwargs not supported for Llama models
        }"""

c = c.replace(old, new)

with open(r"D:\anonym\modal_voice_service.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Removed chat_template_kwargs")