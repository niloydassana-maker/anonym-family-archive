with open(r'D:\anonym\modal_voice_service.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Fix the function signature
old_sig = 'def sanitize_hindi_for_xtts(text: str) -> str:'
new_sig = 'def sanitize_hindi_for_xtts(text: str, lang: str = "hi") -> str:'

c = c.replace(old_sig, new_sig)

with open(r'D:\anonym\modal_voice_service.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("Function signature fixed")