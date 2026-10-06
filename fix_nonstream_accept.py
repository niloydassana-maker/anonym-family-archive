with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    c = f.read()

# Add Accept header for non-streaming
old = """                headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },"""

new = """                headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },"""

c = c.replace(old, new)

with open(r"D:\anonym\modal_voice_service.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Added Accept header for non-streaming")