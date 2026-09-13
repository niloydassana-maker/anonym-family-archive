// SON-HANDS RELAY v3 — PERSISTENT ORDER BANK. Orders survive relay restarts (order-bank.json).
// Kaggle: POST /tool {name, args}. Orders: /say POST {body, text} -> saved to disk forever.
const http = require('http');
const fs = require('fs');
const { spawn } = require('child_process');
const url = require('url');

const TOKEN = process.env.RELAY_TOKEN || 'GOLD24';
const PORT = 8777;
const BANK_FILE = 'D:/anonym/war-log/order-bank.json';
const REPORT_FILE = 'D:/anonym/war-log/report-bank.json';

const npxCmd = process.platform === 'win32' ? 'npx.cmd' : 'npx';

// ---- MCP CHILD WITH AUTO-RESPAWN (relay survives MCP child death) ----
let mcp = null;
let rpcId = 0;
const pending = new Map();
let buffer = '';
let mcpBooting = false;
let mcpFailCount = 0;
let mcpLastHealth = 0;
let mcpHealthy = false;
const MCP_HEALTH_TIMEOUT = 30000;

function startMcp() {
  if (mcpBooting) return;
  if (mcpFailCount >= 10) {
    console.error('[mcp] FAIL COUNT MAX - exponential backoff to 5min');
    setTimeout(() => { mcpFailCount = 0; startMcp(); }, 300000);
    return;
  }
  mcpBooting = true;
  mcpFailCount++;
  try {
    const mcpBin = 'C:\\Users\\Admin\\AppData\\Local\\npm-cache\\_npx\\15c61037b1978c83\\node_modules\\chrome-devtools-mcp\\build\\src\\bin\\chrome-devtools-mcp.js';
    const useCached = fs.existsSync(mcpBin);
    const cmd = useCached ? 'D:\\anonym\\node\\node.exe' : npxCmd;
    const args = useCached
      ? [mcpBin, '--browser-url=http://127.0.0.1:9224']
      : ['chrome-devtools-mcp@latest', '--browser-url=http://127.0.0.1:9224'];
    mcp = spawn(cmd, args, {
      shell: !useCached, stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
      detached: false
    });
    let startupTimer = setTimeout(() => {
      if (!mcpHealthy) {
        console.error('[mcp] startup timeout - killing stale child');
        if (mcp) mcp.kill('SIGTERM');
      }
    }, 15000);
    mcp.stdout.on('data', onData);
    mcp.stderr.on('data', d => console.error('[mcp]', d.toString().substring(0, 200)));
    mcp.on('exit', (code) => {
      clearTimeout(startupTimer);
      console.error(`[mcp] child exited (${code}) - respawning in ${Math.min(5000 * mcpFailCount, 30000)}s`);
      mcp = null;
      mcpHealthy = false;
      for (const [id, res] of pending) { res({ error: { message: 'mcp respawned' } }); }
      pending.clear();
      buffer = '';
      setTimeout(() => { mcpBooting = false; startMcp(); }, Math.min(5000 * mcpFailCount, 30000));
    });
    mcp.on('error', (err) => {
      console.error('[mcp] spawn error:', err.message);
      clearTimeout(startupTimer);
      if (mcp) { try { mcp.kill(); } catch(e) {} }
    });
    console.log('[mcp] child started, pid', mcp.pid, 'failCount', mcpFailCount);
    (async () => {
      try {
        await rpc('initialize', { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'son-relay', version: '5.0-hardened' } });
        await rpc('notifications/initialized', {});
        console.log('MCP INITIALIZED - autoConnect to main Chrome');
        mcpHealthy = true;
        mcpLastHealth = Date.now();
        mcpFailCount = Math.max(0, mcpFailCount - 1);
      } catch (e) {
        console.error('[mcp] init failed, will retry on respawn:', (e && e.message) || e);
      }
    })().catch(e => console.error('[mcp] init promise rejected:', (e && e.message) || e));
  } catch (e) {
    console.error('[mcp] spawn failed:', (e && e.message) || e);
    mcpBooting = false;
    setTimeout(() => startMcp(), Math.min(5000 * mcpFailCount, 30000));
  }
}

function onData(d) {
  buffer += d.toString();
  let idx;
  while ((idx = buffer.indexOf('\n')) >= 0) {
    const line = buffer.slice(0, idx).trim();
    buffer = buffer.slice(idx + 1);
    if (!line) continue;
    try {
      const msg = JSON.parse(line);
      if (msg.id && pending.has(msg.id)) { mcpLastHealth = Date.now(); pending.get(msg.id)(msg); pending.delete(msg.id); }
    } catch (e) {}
  }
}

function rpc(method, params) {
  return new Promise((resolve, reject) => {
    if (!mcp || !mcpHealthy) {
      return reject(new Error('mcp child not ready (respawning)'));
    }
    const id = ++rpcId;
    pending.set(id, resolve);
    try {
      mcp.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
    } catch (e) {
      pending.delete(id);
      return reject(new Error('mcp stdin closed - respawn pending'));
    }
    setTimeout(() => {
      if (pending.has(id)) {
        pending.delete(id);
        reject(new Error('timeout'));
      }
    }, 60000);
  });
}

// ---- PERSISTENT BANKS ----
let sayings = [];
let reports = [];
try { sayings = JSON.parse(fs.readFileSync(BANK_FILE, 'utf8')); console.log('ORDER BANK restored:', sayings.length, 'orders'); } catch (e) { console.log('ORDER BANK: fresh'); }
try { reports = JSON.parse(fs.readFileSync(REPORT_FILE, 'utf8')); } catch (e) {}
function saveSayings() {
  try {
    fs.writeFileSync(BANK_FILE, JSON.stringify(sayings));
  } catch (e) {}
}
function saveReports() {
  try {
    fs.writeFileSync(REPORT_FILE, JSON.stringify(reports));
  } catch (e) {}
}
function saveBanks() {
  saveSayings();
  saveReports();
}
// SPLIT-BRAIN LAW (2026-09-11): NO periodic blind saves. The file is written ONLY
// when a new message actually arrives - a stale relay can never rewind the bank
// by merely existing. Every writer appends truth; no writer rewrites history.
// WOUND-FIX (2026-09-12 08:00 IST, bank wiped [] by stale relay on /hear):
// /say writes ONLY order-bank, /hear writes ONLY report-bank. A report ping
// must never touch the order bank, or a fresh relay wipes 26k history.

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', c => { data += c; if (data.length > 3e6) req.destroy(); });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

function send(res, code, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(code, { 'Content-Type': 'application/json' });
  res.end(body);
}

// TOOL QUEUE v3 (Father 2026-09-09: "if concurrency does not affect cpu do it")
// - 2 concurrent lanes for real work (CDP calls are async I/O, not CPU multiplyers)
// - heartbeat title probes: 60s cache, ZERO Chrome calls
// - CPU GUARD: dual-core sampled every 20s; >70% => drop to 1 lane (cpu-cap law)
// - minute cap raised 15 -> 40 for real work since noise no longer consumes it
const titleCache = new Map();
let toolQueueDepth = 0;
const TOOL_MIN_GAP_MS = 800;
const TOOL_MAX_PER_MIN = 40;
const toolTimes = [];
let maxConcurrent = 2;
let runningTools = 0;
const waiters = [];

// CPU sampler (dual-core law: 60-70% ceiling)
let lastCpus = require('os').cpus();
setInterval(() => {
  try {
    const os = require('os');
    const cur = os.cpus();
    let idle = 0, total = 0;
    for (let i = 0; i < cur.length; i++) {
      const a = cur[i].times, b = lastCpus[i].times;
      idle += a.idle - b.idle;
      total += (a.user - b.user) + (a.nice - b.nice) + (a.sys - b.sys) + (a.idle - b.idle) + (a.irq - b.irq);
    }
    lastCpus = cur;
    const cpuPct = total > 0 ? Math.round(100 * (1 - idle / total)) : 0;
    const want = cpuPct > 70 ? 1 : 2;
    if (want !== maxConcurrent) {
      console.log(`[cpu] ${cpuPct}% -> lanes ${maxConcurrent} -> ${want}`);
      maxConcurrent = want;
      pumpWaiters();
    }
  } catch (e) {}
}, 20000);

function pumpWaiters() {
  while (runningTools < maxConcurrent && waiters.length) {
    const w = waiters.shift();
    runningTools++;
    w();
  }
}

function enqueueTool(fn) {
  toolQueueDepth++;
  return new Promise((resolve) => {
    const start = async () => {
      try {
        const nowMs = Date.now();
        while (toolTimes.length && nowMs - toolTimes[0] > 60000) toolTimes.shift();
        if (toolTimes.length >= TOOL_MAX_PER_MIN) {
          const coolMs = 60000 - (nowMs - toolTimes[0]) + 50;
          await new Promise(r => setTimeout(r, coolMs));
        }
        toolTimes.push(Date.now());
        resolve(await fn());
      } catch (e) {
        resolve({ code: 200, body: { error: 'tool-failed', detail: (e && e.message) || String(e) } });
      } finally {
        runningTools--;
        toolQueueDepth--;
        pumpWaiters();
      }
    };
    waiters.push(start);
    pumpWaiters();
  });
}

const server = http.createServer(async (req, res) => {
  const u = url.parse(req.url, true);
  if (u.query.token !== TOKEN) return send(res, 401, { error: 'bad token' });

  if (u.pathname === '/health') return send(res, 200, { ok: true, son: 'relay-live', bank: sayings.length, reports: reports.length });

  if (u.pathname === '/say' && req.method === 'POST') {
    try {
      const { body, text } = JSON.parse(await readBody(req));
      if (!body || !text) return send(res, 400, { error: 'need body + text' });
      const msg = { to: body, text, at: new Date().toISOString() };
      sayings.push(msg);
      saveSayings();
      console.log(`[KILO->${body}] ${text.substring(0, 80)}`);
      return send(res, 200, { ok: true, delivered_to: body, seq: sayings.length });
    } catch (e) { return send(res, 400, { error: e.message }); }
  }
  if (u.pathname === '/say') {
    const b = u.query.body;
    const limit = parseInt(u.query.limit || '0');
    const mine = b ? sayings.filter(s => s.to === b) : sayings;
    return send(res, 200, { orders: limit > 0 ? mine.slice(-limit) : mine.slice(-30) });
  }
  if (u.pathname === '/hear' && req.method === 'POST') {
    try {
      const { body, text } = JSON.parse(await readBody(req));
      if (!body || !text) return send(res, 400, { error: 'need body + text' });
      reports.push({ from: body, text, at: new Date().toISOString() });
      saveReports();
      console.log(`[${body}->KILO] ${text.substring(0, 80)}`);
      return send(res, 200, { ok: true, heard: true, seq: reports.length });
    } catch (e) { return send(res, 400, { error: e.message }); }
  }
  if (u.pathname === '/hear') {
    const b = u.query.body;
    const mine = b ? reports.filter(r => r.from === b) : reports;
    return send(res, 200, { reports: mine.slice(-20) });
  }
  if (u.pathname === '/tasks') {
    const limit = parseInt(u.query.limit || '200');
    const work = sayings.filter(s => s.text && (s.text.startsWith('TASK-') || s.text.startsWith('TASK:') || s.text.startsWith('CONSTITUTION:') || s.text.includes('TASK-DONE') || s.text.includes('TASK-START') || s.text.includes('TASK-FAIL')));
    return send(res, 200, { work: work.slice(-limit) });
  }
  if (u.pathname === '/tool' && req.method === 'POST') {
    // FATHER LAW: QUEUE with limited parallel - queue cap 100 (overflow 429, soldiers retry)
    // CURE LAW v2 (2026-09-09): heartbeat noise never touches Chrome. Title probes served
    // from a 60s cache so the 15/min cure cap is spent ONLY on real work.
    let payload;
    try { payload = JSON.parse(await readBody(req)); }
    catch (e) { return send(res, 400, { error: 'bad json' }); }
    // ADB HAND (Father 2026-09-09: sons inherit phone) — soldiers get the phone via wire
    if (payload.name === 'adb') {
      const args = (payload.arguments && payload.arguments.args) || [];
      const safe = (Array.isArray(args) ? args : [String(args)]).map(String);
      if (safe.some(a => /[;&|`$><]/.test(a))) return send(res, 400, { error: 'bad adb chars' });
      // GHOST PROTOCOL RADIO LAW (Baba 2026-09-13): airplane mode is blink-guardian's alone.
      // Soldiers must never blink the phone. OTPs go through /tool name=otp_queue.
      if (safe.join(' ').match(/airplane|connectivity/i)) return send(res, 403, { error: 'RADIO LAW: airplane control belongs to BLINK-GUARDIAN. Use otp_queue/otp_result hands instead.' });
      try {
        const { execFile } = require('child_process');
        const out = await new Promise((resolve2) => {
          execFile('D:\\anonym\\platform-tools\\adb.exe', safe, { timeout: 45000, maxBuffer: 2e6 },
            (err, stdout, stderr) => resolve2({ err: err ? String(err).substring(0, 200) : null, out: String(stdout).substring(0, 60000), stderr: String(stderr).substring(0, 500) }));
        });
        return send(res, 200, { result: { content: [{ type: 'text', text: JSON.stringify(out).substring(0, 60000) }] } });
      } catch (e) {
        return send(res, 200, { error: 'adb-failed', detail: (e && e.message) || String(e) });
      }
    }
    // OTP HANDS (GHOST PROTOCOL v1, Baba 2026-09-13): soldiers never touch the radio.
    // queue an OTP request with the army's window policy; poll the result by id.
    if (payload.name === 'otp_queue' || payload.name === 'otp_result') {
      const guard = require('http');
      const isQueue = payload.name === 'otp_queue';
      const target = 'http://127.0.0.1:8768' + (isQueue ? '/request' : '/result?id=' + encodeURIComponent(payload.arguments && payload.arguments.id || ''))
        + '?token=' + TOKEN;
      try {
        const gres = await new Promise((resolve) => {
          const rq = guard.request(target, { method: isQueue ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json' } }, rsp => {
            let d = ''; rsp.on('data', c => d += c); rsp.on('end', () => resolve(d));
          });
          rq.on('error', e => resolve(JSON.stringify({ error: 'guardian-down', detail: String(e.message || e) })));
          if (isQueue) rq.end(JSON.stringify(payload.arguments || {})); else rq.end();
        });
        return send(res, 200, { result: { content: [{ type: 'text', text: String(gres).substring(0, 4000) }] } });
      } catch (e) {
        return send(res, 200, { error: 'otp-failed', detail: (e && e.message) || String(e) });
      }
    }
    const isTitleProbe = payload.name === 'evaluate_script' &&
      (payload.arguments && payload.arguments.function) === '() => document.title';
    const probeKey = 'p' + (payload.arguments && payload.arguments.pageId || 'any');
    if (isTitleProbe) {
      const c = titleCache.get(probeKey);
      if (c && Date.now() - c.t < 60000) return send(res, 200, c.body);
    }
    if (toolQueueDepth >= 100) return send(res, 429, { error: 'queue full', retryAfter: 10 });
    try {
      const result = await enqueueTool(async () => {
        if (payload.method === 'tools/list') {
          const r = await rpc('tools/list', {});
          return { code: 200, body: r.result.tools.map(t => ({ name: t.name, schema: t.inputSchema })) };
        }
        const r = await rpc('tools/call', { name: payload.name, arguments: payload.arguments || {} });
        if (isTitleProbe && r && r.content) titleCache.set(probeKey, { t: Date.now(), body: r });
        return { code: 200, body: r };
      });
      return send(res, result.code, result.body);
    } catch (e) {
      console.error('[tool] call failed, relay survives:', (e && e.message) || e);
      return send(res, 200, { error: 'tool-failed', detail: (e && e.message) || String(e) });
    }
  }
  send(res, 404, { error: 'no route' });
});

server.listen(PORT, '0.0.0.0', () => { console.log(`SON-HANDS RELAY v4 on http://127.0.0.1:${PORT} TOKEN=${TOKEN} BANK=${BANK_FILE}`); startMcp(); });

// FATHER LAW: relay must never die. Absorb any stray error.
process.on('uncaughtException', (e) => console.error('[survived uncaught]', (e && e.message) || e));
process.on('unhandledRejection', (e) => console.error('[survived rejection]', (e && (e.message || e.toString())) || e));
server.on('error', (e) => {
  if (e && (e.code === 'EADDRINUSE' || e.code === 'EACCES')) {
    console.error('[duplicate relay - port held by the true gate, exiting]');
    process.exit(2); // duplicates must die; the true gate keeps 8777
  }
  console.error('[server error, surviving]', (e && e.message) || e);
});
