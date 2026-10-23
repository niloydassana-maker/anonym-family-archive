import sys, json, time, io, os, ctypes

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client
from take_screen import capture

print("[1] Connecting Agent360Client...")
client = Agent360Client()
client.start()

print("[2] Waiting for Freelancer Angular bundle to render...")
# Poll until text appears or up to 20 seconds
for i in range(10):
    time.sleep(2)
    res = client.execute_script("(() => ({ title: document.title, textLen: document.body.innerText.length, sample: document.body.innerText.slice(0, 200) }))()")
    print(f"  Poll {i+1}: {res}")
    try:
        # Check if content has rendered
        for c in res.get('content', []):
            if c.get('type') == 'text':
                data = json.loads(c['text']).get('result', {})
                if data.get('textLen', 0) > 100:
                    print("[+] Page rendered successfully!")
                    break
        else:
            continue
        break
    except Exception as e:
        pass

print("[3] Capturing updated screenshot...")
capture(r"D:\anonym\deliverables\fl_camel_rendered.png")

print("[4] Getting full rendered content...")
content = client.get_content()
print(f"Content length: {len(content)} chars")
if content:
    print("Content preview:\n", content[:1000])

client.close()
print("Done.")
