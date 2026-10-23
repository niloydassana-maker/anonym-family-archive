import sys
import os
import time

sys.path.insert(0, r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    print("[1] Initializing Agent360Client...")
    client = Agent360Client()
    try:
        client.start()
        print("[2] Connected to Agent 360 Extension!")
        
        target = "https://www.freelancer.com/projects/azure/Senior-Camel-Integration-Support"
        print(f"[3] Navigating to: {target}")
        res = client.navigate(target, new_tab=True)
        print("Navigate reply:", res)
        
        print("[4] Waiting 8 seconds for page render...")
        time.sleep(8)
        
        print("[5] Taking screenshot...")
        shot_path = r"D:\anonym\deliverables\fl_camel_live.png"
        client.screenshot(shot_path)
        print(f"Saved screenshot to {shot_path} (exists={os.path.exists(shot_path)})")
        
        print("[6] Extracting page content...")
        content = client.get_content()
        print(f"Content length: {len(content)} chars")
        if content:
            print("Preview:\n", content[:600])
            
        print("[7] Inspecting bid form fields...")
        js_code = """(() => {
            const textareas = Array.from(document.querySelectorAll('textarea')).map(t => ({id: t.id, name: t.name, placeholder: t.placeholder}));
            const inputs = Array.from(document.querySelectorAll('input')).map(t => ({id: t.id, name: t.name, placeholder: t.placeholder, type: t.type, value: t.value}));
            const buttons = Array.from(document.querySelectorAll('button')).map(b => (b.innerText || '').trim()).filter(Boolean);
            return {
                title: document.title,
                url: location.href,
                textareas,
                inputs: inputs.slice(0, 15),
                buttons: buttons.slice(0, 20)
            };
        })()"""
        inspect_res = client.execute_script(js_code)
        print("DOM Details:", inspect_res)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()
        print("[*] Client closed.")

if __name__ == "__main__":
    main()
