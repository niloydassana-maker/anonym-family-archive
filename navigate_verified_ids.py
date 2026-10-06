import sys
import os
import time
import json
import subprocess

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

def main():
    client = Agent360Client()
    client.start()
    try:
        url = "https://console.twilio.com/us1/develop/phone-numbers/manage/verified-caller-ids"
        print(f"Navigating to {url} ...")
        client.navigate(url)
        time.sleep(6)
        
        client.screenshot("D:/anonym/verified_caller_ids.png")
        print("Screenshot saved to D:/anonym/verified_caller_ids.png")
        
        content = client.get_content()
        print("Page Content Summary:")
        print(content[:1500])
    finally:
        client.close()

if __name__ == "__main__":
    main()
