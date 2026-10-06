import sys
import os
import time
import json

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def eval_js(client, code):
    res = client.execute_script(code)
    if isinstance(res, dict) and 'content' in res:
        for c in res.get('content', []):
            if isinstance(c, dict) and c.get('type') == 'text':
                try:
                    return json.loads(c.get('text', '{}'))
                except Exception:
                    return c.get('text')
    return res

def main():
    client = Agent360Client()
    client.start()
    try:
        # Check current inputs on page
        info = eval_js(client, """
            () => {
                const inputs = Array.from(document.querySelectorAll('input')).map(i => ({
                    id: i.id,
                    name: i.name,
                    type: i.type,
                    placeholder: i.placeholder,
                    className: i.className
                }));
                const buttons = Array.from(document.querySelectorAll('button')).map(b => ({
                    id: b.id,
                    name: b.name,
                    type: b.type,
                    text: b.innerText,
                    className: b.className
                }));
                return {
                    url: window.location.href,
                    inputs,
                    buttons
                };
            }
        """)
        print("DOM on current page:")
        print(info)
    finally:
        client.close()

if __name__ == "__main__":
    main()
