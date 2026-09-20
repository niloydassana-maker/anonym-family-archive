import json
import urllib.request
import websocket

try:
    req = urllib.request.urlopen("http://127.0.0.1:9224/json/list")
    pages = json.loads(req.read())
except Exception as e:
    print(f"Failed to reach Chrome on port 9224: {e}")
    exit()

ws_url = None
for page in pages:
    if 'linkedin.com' in page.get('url', '') and 'webSocketDebuggerUrl' in page:
        ws_url = page['webSocketDebuggerUrl']
        break

if not ws_url:
    print("Error: Could not find an active Chrome tab.")
    exit()

ws = websocket.create_connection(ws_url, timeout=10)

js_payload = """
(() => {
    const elements = Array.from(document.querySelectorAll('button, [role="button"], .artdeco-button'));
    for (const el of elements) {
        if (el.textContent.includes('Send proposal')) {
            el.removeAttribute('disabled');
            el.classList.remove('disabled');
            el.removeAttribute('aria-disabled');
            el.click();
            el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true}));
            el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true}));
            return 'Dushtu click forced through the illusion.';
        }
    }
    return 'Target completely absent from DOM.';
})()
"""

msg = {
    "id": 1,
    "method": "Runtime.evaluate",
    "params": {
        "expression": js_payload,
        "returnByValue": True
    }
}

ws.send(json.dumps(msg))
response = json.loads(ws.recv())
print("Result:", response.get("result", {}).get("result", {}).get("value"))
ws.close()