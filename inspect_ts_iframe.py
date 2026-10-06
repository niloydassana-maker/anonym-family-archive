import sys
import os
import time
import json

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
        res = eval_js(client, """
            () => {
                const iframes = Array.from(document.querySelectorAll('iframe')).map(f => {
                    const r = f.getBoundingClientRect();
                    return {
                        src: f.src,
                        x: r.x,
                        y: r.y,
                        width: r.width,
                        height: r.height,
                        top: r.top,
                        left: r.left
                    };
                });
                const tsInput = document.querySelector('[name="cf-turnstile-response"]');
                return {
                    iframes,
                    tsValue: tsInput ? tsInput.value : null
                };
            }
        """)
        print("Iframe & Turnstile info:", json.dumps(res, indent=2))
    finally:
        client.close()

if __name__ == "__main__":
    main()
