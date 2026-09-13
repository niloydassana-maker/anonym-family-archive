// BLINK-GUARDIAN v1 — GHOST PROTOCOL executor (Baba order 2026-09-13)
// LAW: the phone's cellular radio is OFF unless THIS daemon opens a window. Nothing else may touch airplane mode.
// Weekly window: Sunday 12:00 local. Urgent requests blink within ~90s. Every window ends verified POWER_OFF or alarms.
// Endpoints (token GOLD24): GET /health /status | POST /request {service,urgent,note} | GET /result?id= | POST /window {force:"GOLD24BLINKONLY"}
const http = require('http');
const fs = require('fs');
const { execFile } = require('child_process');

const TOKEN = 'GOLD24';
const MASTER_BLINK = 'GOLD24BLINKONLY';
const PORT = 8768;
const ADB = 'D:\\anonym\\platform-tools\\adb.exe';
const QF = 'D:/anonym/war-log/blink-queue.json';
const SF = 'D:/anonym/war-log/blink-state.json';
const LF = 'D:/anonym/war-log/blink-log.jsonl';
const RELAY = 'http://127.0.0.1:8777/say?token=' + TOKEN;

let queue = [];
try { queue = JSON.parse(fs.readFileSync(QF, 'utf8')); } catch (e) {}
let state = { lastWindow: 0, lastMaxSmsDate: 0, blinkCount: 0, stuck: false };
try { state = Object.assign(state, JSON.parse(fs.readFileSync(SF, 'utf8'))); } catch (e) {}
let busy = false;

function persist() {
  try { fs.writeFileSync(QF, JSON.stringify(queue)); } catch (e) {}
  try { fs.writeFileSync(SF, JSON.stringify(state)); } catch (e) {}
}
function logLine(obj) {
  try { fs.appendFileSync(LF, JSON.stringify(Object.assign({ at: new Date().toISOString() }, obj)) + '\n'); } catch (e) {}
}
function wire(text) {
  const b = JSON.stringify({ body: 'KILO', text: 'BLINK-GUARD: ' + text });
  const req = http.request(RELAY, { method: 'POST', headers: { 'Content-Type': 'application/json' } }, r => r.resume());
  req.on('error', () => {});
  req.end(b);
}
function adbShell(cmd, ms) {
  return new Promise(resolve => {
    execFile(ADB, ['shell', cmd], { timeout: ms || 20000, windowsHide: true }, (err, out, errOut) => {
      resolve(String(out || '') + String(errOut || ''));
    });
  });
}
async function radioOff() {
  const o = await adbShell("dumpsys telephony.registry | grep -m2 -oE 'mVoiceRegState=[0-9]+\\([A-Z_]+\\)'");
  return (o.match(/POWER_OFF/g) || []).length >= 2;
}
async function radioReady() {
  const o = await adbShell("dumpsys telephony.registry | grep -m2 -oE 'mVoiceRegState=[0-9]+\\([A-Z_]+\\)'");
  return /IN_SERVICE/.test(o);
}
async function forceRadioOff(tries) {
  for (let i = 0; i < tries; i++) {
    await adbShell("cmd connectivity airplane-mode enable");
    for (let t = 0; t < 20; t++) {
      await new Promise(r => setTimeout(r, 1000));
      if (await radioOff()) return true;
    }
  }
  return false;
}
async function readNewSms(sinceDate) {
  const raw = await adbShell("content query --uri content://sms --projection _id:address:body:date", 30000);
  const msgs = [];
  for (const chunk of raw.split(/\n(?=Row: )/)) {
    const m = chunk.match(/_id=(\d+), address=(.*?), body=([\s\S]*?), date=(\d+)/);
    if (!m) continue;
    const id = +m[1], addr = m[2], body = m[3], date = +m[4];
    if (date > sinceDate) msgs.push({ id, addr, body, date });
  }
  msgs.sort((a, b) => a.date - b.date);
  return msgs;
}
function extractCode(body) {
  let m = body.match(/(?:OTP|otp|Otp|code|Code|passcode|verification|Verification)[^\d]{0,30}(\d{4,8})/);
  if (m) return m[1];
  m = body.match(/\b(\d{6})\b/);
  return m ? m[1] : null;
}

async function runWindow(reason, forceKey) {
  if (busy) return { ok: false, err: 'window already running' };
  if (!forceKey && reason !== 'weekly' && reason !== 'urgent') return { ok: false, err: 'bad reason' };
  busy = true;
  persist();
  const t0 = Date.now();
  logLine({ ev: 'BLINK-START', reason });
  wire('BLINK-START reason=' + reason + ' queue=' + queue.filter(q => q.status === 'WAITING').length);
  let offOk = false;
  try {
    await adbShell("cmd connectivity airplane-mode disable");
    let reg = false;
    for (let t = 0; t < 30; t++) {
      await new Promise(r => setTimeout(r, 1000));
      if (await radioReady()) { reg = true; break; }
    }
    const onMs = reg ? Date.now() : t0;
    const deadline = onMs + 45000;
    let lastMax = state.lastMaxSmsDate || 0;
    const wanted = queue.filter(q => q.status === 'WAITING');
    let newMsgs = [];
    if (wanted.length) {
      do {
        await new Promise(r => setTimeout(r, 3000));
        const msgs = await readNewSms(lastMax);
        for (const msg of msgs) {
          lastMax = Math.max(lastMax, msg.date);
          let matched = false;
          for (const q of wanted) {
            const key = String(q.service || '').toLowerCase();
            if (key && (msg.addr.toLowerCase().includes(key) || msg.body.toLowerCase().includes(key))) {
              q.status = 'CODE';
              q.code = extractCode(msg.body);
              q.from = msg.addr;
              q.snippet = msg.body.substring(0, 300);
              matched = true;
            }
          }
          newMsgs.push({ addr: msg.addr, matched, snippet: msg.body.substring(0, 120) });
        }
        if (wanted.every(q => q.status === 'CODE')) break;
      } while (Date.now() < deadline);
    }
    state.lastMaxSmsDate = lastMax;
    for (const q of wanted.filter(q => q.status === 'WAITING')) q.status = 'NO-CODE-YET';
    offOk = await forceRadioOff(3);
    const exposure = Math.round((Date.now() - onMs) / 1000);
    state.lastWindow = Date.now();
    state.blinkCount++;
    state.stuck = !offOk;
    queue = queue.filter(q => q.status === 'WAITING' || (Date.now() - q.at) < 7 * 864e5);
    CODES: {
      const codes = [];
      for (const q of wanted) if (q.status === 'CODE') codes.push(q.id + ':' + (q.code || '?'));
      persist();
      logLine({ ev: 'BLINK-DONE', reason, exposureS: exposure, verified: offOk, codes: codes.length, msgs: newMsgs.length });
      wire('BLINK-DONE reason=' + reason + ' exposure=' + exposure + 's verified=' + (offOk ? 'POWER_OFF' : 'RADIO-STUCK!!') + ' codes=[' + codes.join(',') + '] msgs=' + newMsgs.length);
    }
    if (!offOk) wire('RADIO-STUCK - guardian will keep killing radio every 60s until POWER_OFF verified');
    return { ok: offOk, exposureS: exposure, msgs: newMsgs.length, results: wanted };
  } finally {
    busy = false;
    persist();
  }
}
// stuck-radio watchdog: if POWER_OFF was never verified, hammer it every 10s.
// REBOOT-PROOF LAW: runs first check immediately at daemon birth and every 10s after -
// a phone that restarts with radio ON meets silence within seconds, not minutes.
async function enforceSilence() {
  if (busy) return;
  if (state.stuck || !(await radioOff().catch(() => true))) {
    logLine({ ev: 'RADIO-REKILL' });
    const ok = await forceRadioOff(3);
    if (ok) { state.stuck = false; persist(); wire('RADIO-REKILL SUCCESS - POWER_OFF verified'); }
    else wire('RADIO-REKILL FAILED - airplane mode re-forced, still not POWER_OFF. PHONE MAY BE RADIO-EXPOSED. Baba: check device.');
  }
}
setInterval(enforceSilence, 10000);
setTimeout(enforceSilence, 3000);

// scheduler: weekly Sunday ~12:00; urgent within 30s; boot catch-up if queue waiting and never/long-run
setInterval(() => {
  if (busy) return;
  const now = new Date();
  const needUrgent = queue.some(q => q.status === 'WAITING' && q.urgent);
  const lastAgeDays = state.lastWindow ? (Date.now() - state.lastWindow) / 864e5 : 999;
  const needWeekly = now.getDay() === 0 && now.getHours() >= 12 && lastAgeDays >= 7;
  if (needUrgent) runWindow('urgent');
  else if (needWeekly && queue.some(q => q.status === 'WAITING')) runWindow('weekly');
}, 30000);

function reply(res, code, obj) {
  const b = JSON.stringify(obj);
  res.writeHead(code, { 'Content-Type': 'application/json' });
  res.end(b);
}
function readBody(req) {
  return new Promise(resolve => { let d = ''; req.on('data', c => d += c); req.on('end', () => resolve(d)); });
}
let qid = 0;
const server = http.createServer(async (req, res) => {
  const u = require('url').parse(req.url, true);
  if (u.pathname === '/health') return reply(res, 200, { ok: true, son: 'blink-guardian', busy, queue: queue.length });
  if (u.query.token !== TOKEN) return reply(res, 401, { error: 'bad token' });
  if (u.pathname === '/status') {
    const off = await radioOff().catch(() => 'unknown');
    return reply(res, 200, { ok: true, radioOff: off, busy, waiting: queue.filter(q => q.status === 'WAITING').length, lastWindow: new Date(state.lastWindow).toISOString(), blinkCount: state.blinkCount, stuck: state.stuck });
  }
  if (u.pathname === '/request' && req.method === 'POST') {
    let p; try { p = JSON.parse(await readBody(req)); } catch (e) { return reply(res, 400, { error: 'bad json' }); }
    const item = { id: 'otp' + (++qid), service: String(p.service || ''), note: String(p.note || ''), urgent: !!p.urgent, status: 'WAITING', at: Date.now() };
    queue.push(item);
    persist();
    logLine({ ev: 'REQUEST', id: item.id, service: item.service, urgent: item.urgent });
    if (item.urgent && !busy) runWindow('urgent');
    return reply(res, 200, { ok: true, id: item.id, when: item.urgent ? 'urgent-window-now' : 'next-weekly-or-scheduled-window' });
  }
  if (u.pathname === '/result') {
    const item = queue.find(q => q.id === u.query.id);
    return reply(res, item ? 200 : 404, item || { error: 'no such id' });
  }
  if (u.pathname === '/window' && req.method === 'POST') {
    let p; try { p = JSON.parse(await readBody(req)); } catch (e) { return reply(res, 400, { error: 'bad json' }); }
    if (p.force !== MASTER_BLINK) return reply(res, 403, { error: 'need force=' + MASTER_BLINK });
    const r = await runWindow('forced-master', MASTER_BLINK);
    return reply(res, 200, r);
  }
  reply(res, 404, { error: 'no route' });
});

server.on('error', e => { if (e.code === 'EADDRINUSE') { console.log('guardian already alive on 8768 - duplicate dies'); process.exit(0); } });
server.listen(PORT, '127.0.0.1', () => { console.log('BLINK-GUARDIAN on 127.0.0.1:' + PORT); wire('GUARDIAN UP on 8768 - radio law: ONLY this daemon touches airplane mode. weekly=Sun12:00, urgent-flag, master-force key set.'); });
process.on('uncaughtException', e => { try { logLine({ ev: 'ERR', msg: String(e && e.message || e) }); } catch (_) {} });
process.on('unhandledRejection', e => { try { logLine({ ev: 'ERR', msg: String(e) }); } catch (_) {} });
