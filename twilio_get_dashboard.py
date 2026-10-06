import sys
import os
import time
import json
import re

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def eval_js(client, code):
    c = code.strip()
    if c.startswith('() =>') and not c.endswith(')()'):
        c = f"({c})()"
    elif not (c.startswith('(') and c.endswith(')()')):
        if not c.startswith('('):
            c = f"(() => {{ {c} }})()"
            
    res = client.execute_script(c)
    if isinstance(res, dict) and 'content' in res:
        for item in res.get('content', []):
            if isinstance(item, dict) and item.get('type') == 'text':
                try:
                    return json.loads(item.get('text', '{}'))
                except Exception:
                    return item.get('text')
    return res

def ensure_active_tab(client):
    try:
        tabs = client.list_tabs()
        if tabs:
            tab_id = tabs[0].get('id')
            client.switch_tab(tab_id)
            time.sleep(1)
            return tab_id
    except Exception as e:
        pass
    return None

def main():
    print("=" * 60)
    print("TWILIO CONSOLE: EXTRACT CREDENTIALS & PHONE NUMBER")
    print("=" * 60)
    
    client = Agent360Client()
    client.start()
    
    try:
        print("[1] Navigating to https://console.twilio.com/ ...")
        client.navigate("https://console.twilio.com/")
        time.sleep(8)
        ensure_active_tab(client)
        time.sleep(3)
        
        client.screenshot("D:/anonym/twilio_console_dashboard.png")
        print("[+] Screenshot: D:/anonym/twilio_console_dashboard.png")
        
        content = client.get_content()
        print("\n--- CONSOLE PAGE CONTENT ---")
        print(content[:3000])
        print("----------------------------")
        
        # Search for Account SID (ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
        sids = re.findall(r'\bAC[a-f0-9]{32}\b', content)
        print("Found Account SIDs:", sids)
        
        # Save page text to inspection file
        with open(r"D:\anonym\twilio_console_text.txt", "w", encoding="utf-8") as f:
            f.write(content)
        print("[+] Full text saved to D:\\anonym\\twilio_console_text.txt")
        
    except Exception as e:
        print("Error reading dashboard:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
