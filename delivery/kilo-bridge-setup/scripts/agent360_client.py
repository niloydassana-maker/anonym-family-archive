import subprocess
import json
import time
import os
import sys
import shutil
import ctypes
import atexit
import queue
import threading
from ctypes import wintypes


class BridgeTimeout(RuntimeError):
    """The Agent360 child answered nothing within the deadline.

    Always means the same thing: the Chrome extension is not attached to OUR
    node child (another client's child owns 9876, or Chrome/extension is idle).
    Callers must treat it as a failed cycle with a receipt, never as a hang."""


TOKEN_PATH = os.environ.get(
    "KILO_SWEEP_BROWSER_TOKEN",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "sweep-browser.token"),
)


def _pid_alive(pid):
    if os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(0x00100000, False, int(pid))  # SYNCHRONIZE
        if not handle:
            return ctypes.get_last_error() == 5  # access denied => conservatively assume live
        try:
            return kernel32.WaitForSingleObject(handle, 0) == 0x00000102  # WAIT_TIMEOUT
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


# A token whose holder has not touched it for this long is not driving the
# browser, whatever its pid claims. 2026-10-06: a token held by DEAD pid 11204
# at age 3665s froze an entire agent tree with no log line, because (a) the
# dead-holder branch had NO deadline check and (b) os.remove() kept failing
# WinError 32 while a sibling held a read handle. Both faults fixed below.
TOKEN_DEAD_S = 300


def _acquire_browser_token(wait_seconds=600):
    """Acquire one cross-process browser token; fail closed on malformed state."""
    deadline = time.monotonic() + wait_seconds
    owner = {"pid": os.getpid(), "since": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    encoded = (json.dumps(owner, separators=(",", ":")) + "\n").encode("utf-8")
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)

    def _token_age():
        try:
            return time.time() - os.path.getmtime(TOKEN_PATH)
        except OSError:
            return 0.0

    def _drop_or_take(match_bytes, why, holder_pid):
        """Neutralise a token whose holder is NOT a real driver.

        os.remove() raises WinError 32 ("being used by another process") when a
        sibling holds a read handle, and this loop reads the file on every poll
        - so that block is the COMMON case, not the rare one. Retry briefly,
        then TAKE the token by exclusive overwrite with our own record. Bounded
        and non-raising: it must never spin, and it must never conceal a wall."""
        for _ in range(12):
            try:
                with open(TOKEN_PATH, "rb") as stream:
                    if stream.read() != match_bytes:
                        return                       # changed under us -> outer retry
                os.remove(TOKEN_PATH)
                print("BROWSER-TOKEN DROP pid %s (%s)" % (holder_pid, why), flush=True)
                return
            except PermissionError:
                time.sleep(0.05)
            except OSError:
                break
        try:
            fd = os.open(TOKEN_PATH, os.O_WRONLY | os.O_TRUNC)
            with os.fdopen(fd, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            print("BROWSER-TOKEN TAKEN by overwrite from pid %s (%s)" % (holder_pid, why), flush=True)
        except OSError as exc:
            print("BROWSER-TOKEN UNREMOVABLE pid %s (%s): %s" % (holder_pid, why, exc), flush=True)

    while True:
        try:
            fd = os.open(TOKEN_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            return owner
        except FileExistsError:
            try:
                with open(TOKEN_PATH, "rb") as stream:
                    current_bytes = stream.read()
                current = json.loads(current_bytes.decode("utf-8"))
                current_pid = int(current["pid"])
                # already ours (a take-by-overwrite in a previous pass) -> done
                if current_pid == os.getpid() and current.get("since") == owner["since"]:
                    return owner
                age = _token_age()
                # 1. a COLD token is not a driver, whatever its pid says.
                #    This is the rule that would have saved 2026-10-06.
                if age > TOKEN_DEAD_S:
                    _drop_or_take(current_bytes, "cold token %.0fs" % age, current_pid)
                    continue
                # 2. dead pid -> drop
                if not _pid_alive(current_pid):
                    _drop_or_take(current_bytes, "dead pid", current_pid)
                    continue
                # 3. live but idle past TOKEN_STALE_S -> it yields the browser
                #    (a working holder touches every call_tool, so it is safe)
                if age > TOKEN_STALE_S:
                    _drop_or_take(current_bytes, "idle yield %.0fs" % age, current_pid)
                    continue
                # 4. live and fresh: a REAL driver. Wait - and REPORT at the
                #    deadline. The old dead-holder branch could reach this
                #    state with no deadline whatsoever and spin forever, which
                #    is exactly how an agent tree froze with no receipt.
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "Agent 360 browser token held by live pid %s (age %.0fs) for %ss"
                        % (current_pid, age, wait_seconds))
                time.sleep(0.25)
                continue
            except (KeyError, ValueError, UnicodeError, json.JSONDecodeError):
                # Malformed: neutralise only if it is ALSO cold (a fresh
                # malformed token means somebody is mid-write), else fail closed.
                if _token_age() > TOKEN_DEAD_S:
                    try:
                        os.remove(TOKEN_PATH)
                        print("BROWSER-TOKEN malformed+cold removed", flush=True)
                        continue
                    except OSError:
                        pass
                raise RuntimeError("Agent 360 browser token is malformed; refusing to take it.")
        except OSError:
            if time.monotonic() >= deadline:
                raise TimeoutError("Could not acquire Agent 360 browser token.")
            time.sleep(0.25)


def _release_browser_token(owner):
    if not owner:
        return False
    try:
        with open(TOKEN_PATH, "r", encoding="utf-8") as stream:
            current = json.load(stream)
        if int(current.get("pid", -1)) != int(owner["pid"]) or current.get("since") != owner["since"]:
            return False
        os.remove(TOKEN_PATH)
        return True
    except (FileNotFoundError, OSError, KeyError, ValueError, json.JSONDecodeError):
        return False


# ---- LEASE ROTATION (2026-09-29): the file token must YIELD like the gate ----
# Root cause fixed: daemons start()-once and close() only atexit, so the first
# holder kept sweep-browser.token for LIFE and every other 24/7 watcher blocked
# 600s then crashed (gmail-yahoo, legal-watch, weaver starved; feed-watch drove
# Chrome with a reaped gate ticket). House law = ONE DRIVER, and a driver that
# is IDLE between cycles must hand the browser over - exactly what the gate's
# 90s TTL already does for the queue.
class LeaseLostError(RuntimeError):
    """Another driver legitimately took the browser while we idled."""


TOKEN_STALE_S = 120  # idle holder yields the file token (working holders touch
                     # it on every call_tool, so they are never stolen from)


def _token_owner():
    try:
        with open(TOKEN_PATH, "r", encoding="utf-8") as stream:
            return json.load(stream)
    except Exception:
        return None


def _owns_browser_token(owner):
    if not owner:
        return False
    current = _token_owner()
    if not current:
        return False
    try:
        return int(current["pid"]) == int(owner["pid"]) and current.get("since") == owner.get("since")
    except Exception:
        return False


def _touch_browser_token(owner):
    if not _owns_browser_token(owner):
        return False
    try:
        os.utime(TOKEN_PATH, None)
        return True
    except OSError:
        return False


# ---- BROWSER QUEUE GATE (HARD ROCK: one Chrome driver at a time) ----
GATE = "http://127.0.0.1:7880"

def _gate_call(path, payload, timeout=10):
    import urllib.request
    req = urllib.request.Request(GATE + path, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or '{}')

def _gate_acquire(who, wait_seconds=600, poll=0.3):
    """Acquire browser queue ticket (FIFO). Falls back silently if gate down."""
    deadline = time.monotonic() + wait_seconds
    pid = os.getpid()
    while True:
        try:
            res = _gate_call('/acquire', {'who': who, 'pid': pid})
            if res.get('granted'):
                return res.get('ticket')
        except Exception:
            # gate down -> HARD ROCK still holds: fall back to local file token only
            return None
        if time.monotonic() >= deadline:
            raise TimeoutError("browser queue: waited %ss for Chrome turn" % wait_seconds)
        time.sleep(poll)

def _gate_touch(who, ticket):
    if ticket is None: return False
    try:
        return bool(_gate_call('/touch', {'who': who, 'pid': os.getpid(), 'ticket': ticket}).get('ok'))
    except Exception:
        return False

def _gate_release(who, ticket):
    if ticket is None: return False
    try:
        return bool(_gate_call('/release', {'who': who, 'ticket': ticket}).get('ok'))
    except Exception:
        return False


def _parse_tabs(res):
    """MCP browser_list_tabs response -> LIST of tab dicts (canonical shape).
    Seen shapes: {'content':[{'type':'text','text':'[{...}]'}]}, text as
    '{"tabs":[...]}', bare {'tabs':[...]} (structuredContent), or a raw list.
    The raw dict was iterated as keys by every daemon -> 'str' has no attribute
    'get' (FEED-WATCH-ERR x4, 2026-09-29). FIXED HERE, once, for all seven."""
    if isinstance(res, list):
        return [t for t in res if isinstance(t, dict)]
    if not isinstance(res, dict):
        return []
    if isinstance(res.get("tabs"), list):
        return [t for t in res["tabs"] if isinstance(t, dict)]
    for c in res.get("content") or []:
        if isinstance(c, dict) and c.get("type") == "text":
            try:
                data = json.loads(c.get("text", ""))
            except Exception:
                continue
            if isinstance(data, list):
                return [t for t in data if isinstance(t, dict)]
            if isinstance(data, dict) and isinstance(data.get("tabs"), list):
                return [t for t in data["tabs"] if isinstance(t, dict)]
    return []
# ----------------------------------------------------------------------


class Agent360Client:
    def __init__(self):
        self.proc = None
        self._msg_id = 100
        self._browser_token = None
        self._gate_ticket = None
        self._gate_who = f"agent360:{os.getpid()}"

    def start(self):
        # 1) HARD ROCK: acquire browser queue ticket (FIFO, blocks until our turn)
        self._gate_ticket = _gate_acquire(self._gate_who)
        # 2) legacy file token — ONLY when the gate is down (it is the fallback).
        #    When the gate granted a ticket we are already the sole driver (FIFO
        #    + 90s TTL), so taking the file token too is redundant AND races
        #    mid-write with other waiters (JSONDecodeError -> 'token malformed').
        if self._gate_ticket is None and self._browser_token is None:
            self._browser_token = _acquire_browser_token()
            atexit.register(self.close)
        node = os.environ.get('KILO_AGENT360_NODE') or r'C:\Users\Admin\AppData\Local\hermes\node\node.exe'
        if not os.path.isfile(node):
            node = shutil.which('node') or node
        mcp = os.environ.get('KILO_AGENT360_MCP_ENTRYPOINT') or r'C:\Users\Admin\AppData\Local\hermes\node\node_modules\@agent360\browser-mcp\index.js'
        if not os.path.isfile(mcp):
            candidates = [
                os.path.join(os.environ.get('APPDATA', ''), 'npm', 'node_modules', '@agent360', 'browser-mcp', 'index.js'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.runtime', 'node_modules', '@agent360', 'browser-mcp', 'index.js'),
            ]
            mcp = next((p for p in candidates if os.path.isfile(p)), mcp)
        if not os.path.isfile(node):
            raise FileNotFoundError('Node.js not found; install Node.js or set KILO_AGENT360_NODE')
        if not os.path.isfile(mcp):
            raise FileNotFoundError('Agent360 browser-mcp not found; install it or set KILO_AGENT360_MCP_ENTRYPOINT')
        cmd = [node, mcp]
        try:
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
        except Exception:
            _release_browser_token(self._browser_token)
            self._browser_token = None
            raise
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
        time.sleep(1)
        self._send({
            'jsonrpc': '2.0',
            'method': 'notifications/initialized',
            'params': {}
        })
        time.sleep(3.5) # allow extension websocket bridge to establish
        return init_res

    def _send(self, req):
        line = json.dumps(req)
        self.proc.stdin.write(line + '\n')
        self.proc.stdin.flush()

    def _read(self, timeout=180):
        """Bounded read with a hard timeout (2026-10-01 fix).

        ROOT CAUSE of the silent strike hangs (2 ticks with no tick-end, 0% CPU,
        no traceback): a bare stdout.readline() blocks FOREVER when the Chrome
        extension is not attached to THIS child (another client's child holds
        9876, or the extension is asleep). The house cannot have a lane that
        hangs silently - a hang must become a named failure with a receipt.
        On timeout the child is killed (it is OURS, never a brother's) and
        BridgeTimeout is raised so every caller's except-path runs."""
        box = queue.Queue(maxsize=1)

        def _worker():
            try:
                while True:
                    line = self.proc.stdout.readline()
                    if not line:
                        box.put(None)
                        return
                    line = line.strip()
                    if line.startswith('{'):
                        try:
                            box.put(json.loads(line))
                            return
                        except Exception:
                            continue
            except Exception as exc:
                box.put(exc)

        threading.Thread(target=_worker, daemon=True).start()
        try:
            got = box.get(timeout=timeout)
        except queue.Empty:
            try:
                self.proc.kill()
            except Exception:
                pass
            raise BridgeTimeout("Agent360 tool gave no answer in %ss (extension not attached to this child?)" % timeout)
        if isinstance(got, Exception):
            raise got
        return got

    def _reacquire_lease(self):
        """We idled past TOKEN_STALE_S and another driver took the browser.
        Wait for our clean turn (the current holder touches while working and
        yields when idle, so a turn always comes) instead of failing the cycle.
        LeaseLostError fires only if no turn arrives within 600s - then the
        daemon's per-cycle handler skips the cycle rather than driving
        hands-over-hands (FIGHTING-HANDS law)."""
        try:
            return _acquire_browser_token(wait_seconds=600)
        except (TimeoutError, RuntimeError) as exc:
            raise LeaseLostError("no browser turn within 600s; yield this cycle") from exc

    def call_tool(self, name, arguments=None):
        # HARD ROCK: heartbeat the browser queue so TTL doesn't evict us while working
        _gate_touch(self._gate_who, self._gate_ticket)
        # If the gate force-released our ticket while we slept between cycles,
        # rejoin the FIFO queue (soft - the file token below is the hard mutex).
        if self._gate_ticket is not None and not _gate_touch(self._gate_who, self._gate_ticket):
            self._gate_ticket = _gate_acquire(self._gate_who, wait_seconds=10)
        # HARD mutex: keep the file token fresh, and NEVER send a tool call
        # after a legitimate stale-steal by another driver.
        if self._browser_token is not None:
            if not _touch_browser_token(self._browser_token):
                self._browser_token = self._reacquire_lease()
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
        _gate_touch(self._gate_who, self._gate_ticket)
        if self._browser_token is not None:
            _touch_browser_token(self._browser_token)
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

    def wait_for_selector(self, selector, timeout_ms=30000):
        return self.call_tool('browser_wait', {'selector': selector, 'timeout': timeout_ms})

    def execute_script(self, code):
        return self.call_tool('browser_execute_script', {'code': code})

    def list_tabs(self):
        # returns a LIST of {id,url,...} dicts (what every daemon iterates)
        return _parse_tabs(self.call_tool('browser_list_tabs', {}))

    def switch_tab(self, tab_id):
        return self.call_tool('browser_switch_tab', {'tab_id': tab_id})

    def close_tab(self, tab_id):
        return self.call_tool('browser_close_tab', {'tab_id': tab_id})

    # ===== VERIFYING VERBS (2026-10-07) - the tool layer returns POST-ACTION STATE =====
    # WHY HERE: a reasoning agent given a bare goal FABRICATED executions when it had
    # to author its own click choreography. The fix is that every verb PROVES its own
    # effect before returning: a click hands back the resulting URL + toast; a fill is
    # RE-READ from the DOM. A verb that cannot produce a post-state never claims one.
    # ADDITIVE & self-contained (uses only call_tool), so it cannot disturb the gate/
    # token logic the 20+ live a360_* daemons rely on. JS .click() only - PACE 1.

    def _js(self, expr):
        """execute_script, fully unwrapped to the raw script value.
        Handles the MCP envelope ({content:[{type:text,text:JSON}]}) AND the
        {'result': <value>} wrapper execute_script uses, and parses a JSON string
        value back to an object. Returns the value, or {'error':..} on tool error."""
        res = self.call_tool('browser_execute_script', {'code': expr})
        if isinstance(res, dict) and res.get('isError'):
            return {'error': res.get('error')}
        val = res
        if isinstance(res, dict) and res.get('content'):
            for b in res.get('content', []) or []:
                if b.get('type') == 'text':
                    t = b.get('text', '')
                    try:
                        val = json.loads(t)
                    except Exception:
                        val = t
                    break
        if isinstance(val, dict) and 'result' in val:
            val = val['result']
        if isinstance(val, str):
            sval = val.strip()
            if sval[:1] in '[{' and sval[-1:] in ']}':
                try:
                    return json.loads(sval)
                except Exception:
                    return val
        return val

    def url(self):
        """Current page URL ('' if unreadable)."""
        u = self._js('location.href')
        return u if isinstance(u, str) else ''

    def toast(self):
        """Best-effort visible toast/alert/snackbar text ('' if none)."""
        r = self._js(
            "(function(){var sels=['[role=alert]','.toast','[class*=toast]',"
            "'[class*=Toast]','[class*=snack]','[class*=Snack]','[class*=notification]',"
            "'[class*=Notification]'];for(var i=0;i<sels.length;i++){var e="
            "document.querySelector(sels[i]);var t=e?(e.innerText||'').trim():'';"
            "if(t)return t.slice(0,200);}return '';})()")
        return r if isinstance(r, str) else ''

    def readback(self, selector):
        """READ a field's ACTUAL value from the DOM (the fill-verification half).
        Handles input.value, textarea.value and contenteditable textContent."""
        r = self._js(
            "(function(){var e=document.querySelector(%s);if(!e)return {found:false,value:''};"
            "var ce=e.getAttribute('contenteditable');"
            "var v=(ce==='true')?(e.textContent||''):((e.value!==undefined)?e.value:"
            "((e.innerText!==undefined)?e.innerText:''));"
            "return {found:true,value:String(v)};})()" % json.dumps(selector))
        if isinstance(r, str):
            try:
                r = json.loads(r)
            except Exception:
                r = {}
        return r if isinstance(r, dict) else {'found': False, 'value': ''}

    def fill_verified(self, selector, value, max_retries=3):
        """Fill a field, then RE-READ it. ok is True only when readback == value.
        THE CORE FIX: the old lanes reported 'filled' while the field stayed EMPTY
        (input dispatched at the wrong node). A fill not read back is not a fill."""
        last = {}
        for attempt in range(max_retries):
            self.call_tool('browser_fill', {'selector': selector, 'value': value})
            time.sleep(0.4)
            rb = self.readback(selector)
            actual = rb.get('value') or ''
            last = {'ok': bool(rb.get('found')) and actual.strip() == str(value).strip(),
                    'selector': selector, 'expected': value, 'actual': actual,
                    'attempts': attempt + 1}
            if last['ok']:
                return last
            time.sleep(0.4 * (attempt + 1))
        return last

    def find_and_click(self, desc, max_retries=3):
        """Find an element by VISIBLE TEXT and click it (JS .click(), PACE 1).
        Returns {ok,url,toast,url_changed,clicked}, never a bare 'clicked'. ok is
        True only when a real element matched and .click() ran; the resulting URL and
        toast are handed back so the caller judges the effect. The mouse path is never
        used (Input.dispatchMouseEvent times out on this machine - PACE.md 1)."""
        want = json.dumps(desc)
        last = {'ok': False, 'url': self.url(), 'toast': '', 'clicked': 'not-found'}
        for attempt in range(max_retries):
            url_before = self.url()
            r = self._js(
                "(function(){var want=" + want + ";"
                "var all=document.querySelectorAll('button,a,[role=button],[role=link],"
                "input[type=submit],input[type=button],[role=tab],li,span,div');"
                "var best=null;"
                "for(var i=0;i<all.length;i++){var e=all[i];"
                "var t=(e.innerText||e.value||e.getAttribute('aria-label')||'').trim();"
                "if(!t)continue;if(t.toLowerCase().indexOf(String(want).toLowerCase())<0)continue;"
                "var rr=e.getBoundingClientRect();if(rr.width<1||rr.height<1)continue;"
                "if(!best||t.length<best.t.length)best={e:e,t:t};}"
                "if(!best)return {found:false};"
                "try{best.e.click();}catch(err){return {found:true,clicked:false};}"
                "return {found:true,clicked:true,label:best.t.slice(0,80)};})()")
            if not isinstance(r, dict) or not r.get('found'):
                last['clicked'] = 'not-found'
                time.sleep(0.5 * (attempt + 1))
                continue
            time.sleep(1.0)
            last = {'ok': bool(r.get('clicked')), 'url': self.url(), 'toast': self.toast(),
                    'clicked': r.get('label') or desc,
                    'url_changed': self.url() != url_before, 'attempts': attempt + 1}
            if last['ok']:
                return last
            time.sleep(0.5 * (attempt + 1))
        return last

    # Aliases matching the mission's verb vocabulary so goal-runner prose maps 1:1.
    findclick = find_and_click
    fill_checked = fill_verified

    # ===== ROBUST WRAPPERS (retry + wait + backoff) =====
    def robust_click(self, selector, max_retries=5, base_delay=1.0):
        """Click with wait_for_selector + exponential backoff retries."""
        for attempt in range(max_retries):
            try:
                self.wait_for_selector(selector, timeout_ms=20000)
                return self.click(selector)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
        return None

    def robust_fill(self, selector, value, max_retries=5, base_delay=1.0):
        """Fill with wait_for_selector + exponential backoff retries."""
        for attempt in range(max_retries):
            try:
                self.wait_for_selector(selector, timeout_ms=20000)
                return self.fill(selector, value)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
        return None

    def robust_navigate(self, url, new_tab=False, wait_after=5.0):
        """Navigate and wait for page to settle."""
        self.navigate(url, new_tab)
        time.sleep(wait_after)
        # Wait for body to be present
        try:
            self.wait_for_selector("body", timeout_ms=30000)
        except Exception:
            pass
        return True

    def robust_switch_to_messaging(self):
        """Find and switch to LinkedIn messaging tab."""
        for attempt in range(3):
            try:
                tabs = self.list_tabs()          # now a LIST of tab dicts
                for tab in tabs:
                    url = tab.get('url', '')
                    if 'messaging' in url.lower() or 'linkedin.com/messaging' in url:
                        self.switch_tab(tab['id'])
                        time.sleep(2)
                        return True
            except Exception:
                pass
            time.sleep(2)
        return False

    def close(self):
        proc = self.proc
        self.proc = None
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        # HARD ROCK: release browser queue ticket
        _gate_release(self._gate_who, self._gate_ticket)
        self._gate_ticket = None
        if self._browser_token is not None:
            _release_browser_token(self._browser_token)
            self._browser_token = None


if __name__ == "__main__" and "--token-self-check" in sys.argv:
    token = _acquire_browser_token(wait_seconds=5)
    print("BROWSER-TOKEN-ACQUIRED")
    if _release_browser_token(token):
        print("BROWSER-TOKEN-RELEASED")
    else:
        raise SystemExit("BROWSER-TOKEN-RELEASE-FAILED")
