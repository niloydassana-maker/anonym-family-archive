/**
 * Local proof harness for the TONEART / SOPHIA-X webhook fan-out.
 *
 * Purpose: demonstrate, on THIS machine, with real HTTP servers and a real
 * HMAC-SHA256 signature, the three properties that decide whether the
 * integration is safe for a live customer line:
 *
 *   1. An unsigned or wrongly signed request is rejected before any
 *      downstream call happens (Stream A is never touched by junk).
 *   2. A correctly signed request reaches BOTH streams byte-identically.
 *   3. The secondary stream (WhatsApp MCP worker) can be broken, slow, or
 *      absent without delaying or failing the primary stream (SOPHIA-X).
 *
 * No mocks of the logic under test: worker.js and this harness import the
 * same ./multiplexer-core.js. Only the two RECEIVERS are local stand-ins for
 * real endpoints.
 *
 * Run: node test-multiplexer.js
 */

import http from 'node:http';
import crypto from 'node:crypto';
import { handleInbound } from './multiplexer-core.js';

const APP_SECRET = 'demo-only-app-secret-not-a-real-credential';
const results = [];
let failures = 0;

function check(name, condition, detail) {
  const pass = Boolean(condition);
  if (!pass) failures += 1;
  results.push({ name, pass, detail });
  const tag = pass ? 'PASS' : 'FAIL';
  console.log(`[${tag}] ${name}${detail ? ` :: ${detail}` : ''}`);
  return pass;
}

/** Start a receiver that records the exact bytes it was given. */
function startReceiver(name, behaviour) {
  const received = [];
  const server = http.createServer((req, res) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => {
      const body = Buffer.concat(chunks);
      received.push({
        bytes: body.length,
        sha256: crypto.createHash('sha256').update(body).digest('hex'),
        body,
        at: Date.now(),
      });
      behaviour({ req, res, body });
    });
  });
  return new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      resolve({ name, server, port, url: `http://127.0.0.1:${port}/inbound`, received });
    });
  });
}

function sign(rawBody, secret) {
  return `sha256=${crypto
    .createHmac('sha256', secret)
    .update(rawBody)
    .digest('hex')}`;
}

/** Build a Node Request as it would arrive from Meta. */
function makeRequest(rawBody, signature) {
  const headers = { 'content-type': 'application/json' };
  if (signature !== null) headers['x-hub-signature-256'] = signature;
  return new Request('http://localhost/webhook', {
    method: 'POST',
    headers,
    body: rawBody,
  });
}

async function main() {
  const payload = Buffer.from(
    JSON.stringify({
      object: 'whatsapp_business_account',
      entry: [
        {
          id: 'WABA_ID',
          changes: [
            {
              field: 'messages',
              value: {
                messaging_product: 'whatsapp',
                messages: [
                  {
                    from: '4915112345678',
                    id: 'wamid.DEMO123',
                    timestamp: '1730000000',
                    type: 'text',
                    text: { body: 'Hallo, ich interessiere mich fuer SOPHIA-X.' },
                  },
                ],
              },
            },
          ],
        },
      ],
    }),
    'utf8',
  );

  console.log('='.repeat(78));
  console.log('TONEART / SOPHIA-X webhook fan-out - local verification');
  console.log(`node ${process.version}   payload ${payload.length} bytes`);
  console.log('='.repeat(78));

  // --- Healthy receivers ---------------------------------------------------
  const sophia = await startReceiver('SOPHIA-X', ({ res }) => {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end('{"ok":true}');
  });
  const mcp = await startReceiver('MCP', ({ res }) => {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end('{"ok":true}');
  });

  const config = {
    appSecret: APP_SECRET,
    primaryUrl: sophia.url,
    secondaryUrl: mcp.url,
  };

  // --- T1: missing signature is rejected before any fan-out ---------------
  {
    const res = await handleInbound(makeRequest(payload, null), config);
    const rejected = res.status === 401;
    const untouched = sophia.received.length === 0 && mcp.received.length === 0;
    check(
      'T1 unsigned request rejected with 401 and NOT forwarded',
      rejected && untouched,
      `status=${res.status} reason=${res.body.reason} sophia_hits=${sophia.received.length} mcp_hits=${mcp.received.length}`,
    );
  }

  // --- T2: wrong signature is rejected ------------------------------------
  {
    const bad = sign(payload, 'the-wrong-secret');
    const res = await handleInbound(makeRequest(payload, bad), config);
    const rejected = res.status === 401;
    const untouched = sophia.received.length === 0 && mcp.received.length === 0;
    check(
      'T2 wrong-signature request rejected with 401 and NOT forwarded',
      rejected && untouched && res.body.reason === 'signature_mismatch',
      `status=${res.status} reason=${res.body.reason} sophia_hits=${sophia.received.length}`,
    );
  }

  // --- T3: tampered body with a valid-for-original signature --------------
  {
    const tamperedPayload = Buffer.from(payload.toString('utf8').replace('Hallo', 'HALLO'), 'utf8');
    const goodSigForOriginal = sign(payload, APP_SECRET);
    const res = await handleInbound(makeRequest(tamperedPayload, goodSigForOriginal), config);
    check(
      'T3 body tampered after signing is rejected (raw-bytes HMAC)',
      res.status === 401 && sophia.received.length === 0,
      `status=${res.status} reason=${res.body.reason}`,
    );
  }

  // --- T4: valid signature reaches BOTH streams byte-identically ----------
  {
    const signature = sign(payload, APP_SECRET);
    const startedAt = Date.now();
    const res = await handleInbound(makeRequest(payload, signature), config);
    const elapsed = Date.now() - startedAt;

    // give the unawaited secondary leg a moment to land
    await new Promise((r) => setTimeout(r, 250));

    const expectedSha = crypto.createHash('sha256').update(payload).digest('hex');
    const sophiaHit = sophia.received[0];
    const mcpHit = mcp.received[0];

    check(
      'T4a valid request returns 200',
      res.status === 200,
      `status=${res.status} elapsed=${elapsed}ms`,
    );
    check(
      'T4b SOPHIA-X received the exact original bytes',
      sophiaHit && sophiaHit.sha256 === expectedSha,
      sophiaHit ? `got=${sophiaHit.sha256.slice(0, 16)} want=${expectedSha.slice(0, 16)} bytes=${sophiaHit.bytes}` : 'no delivery',
    );
    check(
      'T4c MCP received the exact original bytes (same sha256 as Stream A)',
      mcpHit && sophiaHit && mcpHit.sha256 === sophiaHit.sha256,
      mcpHit
        ? `mcp=${mcpHit.sha256.slice(0, 16)} sophia=${sophiaHit.sha256.slice(0, 16)}`
        : 'no delivery',
    );
    check(
      'T4d secondary leg is not awaited (primary returned before/independent of it)',
      res.diagnostics && res.diagnostics.secondaryPromise instanceof Promise,
      'secondary returned as an in-flight promise, not resolved inside the handler',
    );
  }

  // --- T5: secondary SLOW (3s) must not slow the primary ------------------
  {
    await new Promise((r) => setTimeout(r, 50));
    const slow = await startReceiver('MCP-SLOW', ({ res }) => {
      setTimeout(() => {
        res.writeHead(200);
        res.end('slow');
      }, 3000);
    });
    const before = sophia.received.length;
    const startedAt = Date.now();
    const res = await handleInbound(makeRequest(payload, sign(payload, APP_SECRET)), {
      appSecret: APP_SECRET,
      primaryUrl: sophia.url,
      secondaryUrl: slow.url,
    });
    const primaryElapsed = Date.now() - startedAt;
    check(
      'T5 a 3000ms secondary does NOT delay the primary response',
      res.status === 200 && primaryElapsed < 1500,
      `status=${res.status} primary_path=${primaryElapsed}ms (secondary is 3000ms)`,
    );
    check(
      'T5b primary still received its delivery while secondary was hanging',
      sophia.received.length === before + 1,
      `sophia_hits ${before} -> ${sophia.received.length}`,
    );
    await new Promise((r) => setTimeout(r, 3200));
    slow.server.close();
  }

  // --- T6: secondary DOWN must not fail the primary -----------------------
  {
    const deadPort = await new Promise((resolve) => {
      const s = http.createServer();
      s.listen(0, '127.0.0.1', () => {
        const p = s.address().port;
        s.close(() => resolve(p));
      });
    });
    const before = sophia.received.length;
    const startedAt = Date.now();
    const res = await handleInbound(makeRequest(payload, sign(payload, APP_SECRET)), {
      appSecret: APP_SECRET,
      primaryUrl: sophia.url,
      secondaryUrl: `http://127.0.0.1:${deadPort}/inbound`,
    });
    const elapsed = Date.now() - startedAt;
    check(
      'T6 secondary connection-refused does NOT fail the request',
      res.status === 200,
      `status=${res.status} elapsed=${elapsed}ms dead_port=${deadPort}`,
    );
    check(
      'T6b SOPHIA-X was still delivered exactly once',
      sophia.received.length === before + 1,
      `sophia_hits ${before} -> ${sophia.received.length}`,
    );
  }

  // --- T7: secondary failure is observable in diagnostics -----------------
  {
    const deadPort = await new Promise((resolve) => {
      const s = http.createServer();
      s.listen(0, '127.0.0.1', () => {
        const p = s.address().port;
        s.close(() => resolve(p));
      });
    });
    const res = await handleInbound(makeRequest(payload, sign(payload, APP_SECRET)), {
      appSecret: APP_SECRET,
      primaryUrl: sophia.url,
      secondaryUrl: `http://127.0.0.1:${deadPort}/inbound`,
    });
    const secondary = await res.diagnostics.secondaryPromise;
    check(
      'T7 a broken secondary is REPORTED (not silently swallowed)',
      secondary.ok === false && secondary.error !== null,
      `secondary.ok=${secondary.ok} error=${secondary.error}`,
    );
  }

  // --- T8: replayed identical body is still signature-valid --------------
  {
    const signature = sign(payload, APP_SECRET);
    const before = sophia.received.length;
    const r1 = await handleInbound(makeRequest(payload, signature), config);
    const r2 = await handleInbound(makeRequest(payload, signature), config);
    await new Promise((r) => setTimeout(r, 200));
    check(
      'T8 two identical deliveries both reach SOPHIA-X (proxy is not a deduper)',
      r1.status === 200 && r2.status === 200 && sophia.received.length === before + 2,
      `hits ${before} -> ${sophia.received.length}`,
    );
  }

  sophia.server.close();
  mcp.server.close();

  console.log('-'.repeat(78));
  const passed = results.filter((r) => r.pass).length;
  console.log(`RESULT: ${passed}/${results.length} checks passed`);
  console.log(`VERDICT: ${failures === 0 ? 'FAN-OUT VERIFIED' : 'FAILURES PRESENT'}`);
  console.log('-'.repeat(78));
  if (failures > 0) process.exitCode = 1;
}

main().catch((err) => {
  console.error('HARNESS ERROR:', err && err.stack ? err.stack : err);
  process.exitCode = 2;
});
