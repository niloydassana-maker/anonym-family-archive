import sys
import subprocess
import json
import time

cmd = [r'C:\Users\Admin\AppData\Local\hermes\node\node.exe',
       r'C:\Users\Admin\AppData\Local\hermes\node\node_modules\@agent360\browser-mcp\index.js']

proc = subprocess.Popen(
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

# Send initialize request
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

import threading
import queue

def read_stdout(proc, q):
    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                q.put(('stdout', None))
                return
            q.put(('stdout', line.strip()))
    except Exception as e:
        q.put(('stdout', e))

def read_stderr(proc, q):
    try:
        while True:
            line = proc.stderr.readline()
            if not line:
                q.put(('stderr', None))
                return
            q.put(('stderr', line.strip()))
    except Exception as e:
        q.put(('stderr', e))

q = queue.Queue()
t1 = threading.Thread(target=read_stdout, args=(proc, q), daemon=True)
t2 = threading.Thread(target=read_stderr, args=(proc, q), daemon=True)
t1.start()
t2.start()

proc.stdin.write(json.dumps(init_req) + '\n')
proc.stdin.flush()

# Wait for response
for _ in range(50):
    try:
        src, msg = q.get(timeout=1)
        if msg is None:
            print(f"{src}: EOF")
            break
        print(f"{src}: {msg}")
        if src == 'stdout' and msg.startswith('{'):
            try:
                res = json.loads(msg)
                if 'result' in res or 'error' in res:
                    print(f"Got response: {res}")
                    break
            except:
                pass
    except queue.Empty:
        print("Timeout waiting for response")
        break

# Send initialized notification
proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': {}}) + '\n')
proc.stdin.flush()

time.sleep(2)

# Try list_tabs
list_req = {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'browser_list_tabs', 'arguments': {}}}
proc.stdin.write(json.dumps(list_req) + '\n')
proc.stdin.flush()

for _ in range(50):
    try:
        src, msg = q.get(timeout=1)
        if msg is None:
            print(f"{src}: EOF")
            break
        print(f"{src}: {msg}")
    except queue.Empty:
        print("Timeout waiting for list_tabs")
        break

proc.terminate()