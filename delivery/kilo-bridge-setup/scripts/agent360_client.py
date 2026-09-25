import subprocess
import json
import time
import os

class Agent360Client:
    def __init__(self):
        self.proc = None
        self._msg_id = 100

    def start(self):
        cmd = [r'C:\Users\Admin\AppData\Local\hermes\node\node.exe',
               r'C:\Users\Admin\AppData\Local\hermes\node\node_modules\@agent360\browser-mcp\index.js']
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )
        # initialize MCP
        init_req = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'initialize',
            'params': {
                'protocolVersion': '2024-11-05',
                'capabilities': {},
                'clientInfo': {'name': 'kilo-agent360-runner', 'version': '1.0'}
            }
        }
        self._send(init_req)
        init_res = self._read()
        time.sleep(2.5) # allow extension websocket bridge to establish
        return init_res

    def _send(self, req):
        line = json.dumps(req)
        self.proc.stdin.write(line + '\n')
        self.proc.stdin.flush()

    def _read(self):
        while True:
            line = self.proc.stdout.readline()
            if not line:
                return None
            line = line.strip()
            if line.startswith('{'):
                try:
                    return json.loads(line)
                except Exception:
                    continue

    def call_tool(self, name, arguments=None):
        self._msg_id += 1
        req = {
            'jsonrpc': '2.0',
            'id': self._msg_id,
            'method': 'tools/call',
            'params': {
                'name': name,
                'arguments': arguments or {}
            }
        }
        self._send(req)
        res = self._read()
        if res and 'error' in res:
            return {'error': res['error'], 'isError': True}
        result = (res or {}).get('result', {})
        return result

    def navigate(self, url, new_tab=False):
        return self.call_tool('browser_navigate', {'url': url, 'new_tab': new_tab})

    def screenshot(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        return self.call_tool('browser_screenshot', {'path': path})

    def get_content(self):
        res = self.call_tool('browser_get_page_content', {})
        content = res.get('content', [])
        texts = [c.get('text', '') for c in content if c.get('type') == 'text']
        return '\n'.join(texts)

    def click(self, selector):
        return self.call_tool('browser_click', {'selector': selector})

    def fill(self, selector, value):
        return self.call_tool('browser_fill', {'selector': selector, 'value': value})

    def press_key(self, key):
        return self.call_tool('browser_press_key', {'key': key})

    def wait_for_selector(self, selector, timeout_ms=10000):
        return self.call_tool('browser_wait', {'selector': selector, 'timeout': timeout_ms})

    def execute_script(self, code):
        return self.call_tool('browser_execute_script', {'code': code})

    def list_tabs(self):
        return self.call_tool('browser_list_tabs', {})

    def switch_tab(self, tab_id):
        return self.call_tool('browser_switch_tab', {'tab_id': tab_id})

    def close_tab(self, tab_id):
        return self.call_tool('browser_close_tab', {'tab_id': tab_id})

    def close(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                self.proc.kill()
