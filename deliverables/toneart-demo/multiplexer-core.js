/**
 * SOPHIA-X / WhatsApp-MCP coexistence — webhook fan-out core.
 *
 * Platform-agnostic: this exact file is imported by BOTH the Cloudflare Worker
 * entry (worker.js) and the local proof harness (test-multiplexer.js). What is
 * proven locally is therefore the code that ships — no re-implementation drift.
 *
 * Responsibilities:
 *   1. Verify the Meta Cloud API signature (x-hub-signature-256) once, on the
 *      raw bytes, before ANY downstream call.
 *   2. Deliver Stream A (SOPHIA-X) synchronously — it owns the live customer SLA.
 *   3. Deliver Stream B (WhatsApp MCP worker) asynchronously, isolated: a
 *      failure or slowness there must never affect Stream A.
 *
 * Constants are named; nothing is silently defaulted except the documented
 * timeout values.
 */

export const SIGNATURE_HEADER = 'x-hub-signature-256';
export const DEFAULT_PRIMARY_TIMEOUT_MS = 4000;
export const DEFAULT_SECONDARY_TIMEOUT_MS = 4000;

/** Constant-time string comparison (avoids timing side-channel on the MAC). */
function timingSafeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

/** Hex-encode an ArrayBuffer using the Web Crypto API (Workers + Node 18+). */
function toHex(buffer) {
  const bytes = new Uint8Array(buffer);
  let out = '';
  for (let i = 0; i < bytes.length; i += 1) {
    out += bytes[i].toString(16).padStart(2, '0');
  }
  return out;
}

/**
 * Verify a Meta signature header of the form `sha256=<hex>` against the raw
 * request body. Returns { ok, reason }.
 *
 * NOTE: the HMAC is computed over the RAW bytes exactly as received. Parsing
 * and re-serialising JSON here would change the bytes and break verification —
 * that is the single most common integration bug in this class of proxy.
 */
export async function verifySignature(rawBodyOctets, signatureHeader, appSecret) {
  if (!appSecret) return { ok: false, reason: 'no_app_secret_configured' };
  if (typeof signatureHeader !== 'string' || signatureHeader.length === 0) {
    return { ok: false, reason: 'missing_signature_header' };
  }
  const parts = signatureHeader.split('=');
  if (parts.length !== 2 || parts[0].toLowerCase() !== 'sha256') {
    return { ok: false, reason: 'malformed_signature_header' };
  }
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(appSecret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const mac = await crypto.subtle.sign('HMAC', key, rawBodyOctets);
  const expected = toHex(mac);
  const provided = parts[1].toLowerCase();
  if (!timingSafeEqual(expected, provided)) {
    return { ok: false, reason: 'signature_mismatch' };
  }
  return { ok: true, reason: 'verified' };
}

/** POST raw bytes to one target with a hard timeout. Never throws. */
async function postBytes(url, rawBodyOctets, headers, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const startedAt = Date.now();
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers,
      body: rawBodyOctets,
      signal: controller.signal,
    });
    return {
      ok: res.ok,
      status: res.status,
      ms: Date.now() - startedAt,
      error: null,
    };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      ms: Date.now() - startedAt,
      error: err && err.name ? err.name : 'fetch_failed',
    };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Fan one verified inbound event out to both streams.
 *
 * Stream A (primary): awaited. Its result is reported to Meta.
 * Stream B (secondary): started immediately, not awaited. Any failure is
 * swallowed into the returned diagnostics — it can never fail the request,
 * which is what keeps SOPHIA-X's SLA independent of the MCP worker.
 *
 * @returns {Promise<{primary, secondaryPromise}>}
 */
export async function fanOut(rawBodyOctets, opts) {
  const {
    primaryUrl,
    secondaryUrl,
    primaryTimeoutMs = DEFAULT_PRIMARY_TIMEOUT_MS,
    secondaryTimeoutMs = DEFAULT_SECONDARY_TIMEOUT_MS,
    forwardHeaders = {},
  } = opts;

  if (!primaryUrl) throw new Error('primaryUrl is required');

  // Start the secondary leg first so its latency overlaps the primary leg,
  // then await only the primary. The secondary promise is already in flight.
  const secondaryPromise = secondaryUrl
    ? postBytes(secondaryUrl, rawBodyOctets, forwardHeaders, secondaryTimeoutMs)
    : Promise.resolve({ ok: false, status: 0, ms: 0, error: 'no_secondary_url' });

  const primary = await postBytes(
    primaryUrl,
    rawBodyOctets,
    forwardHeaders,
    primaryTimeoutMs,
  );

  return { primary, secondaryPromise };
}

/**
 * Full request pipeline: verify, then fan out.
 * Returns a plain object so the Worker and the harness share one code path.
 */
export async function handleInbound(request, config) {
  const rawBodyOctets = new Uint8Array(await request.arrayBuffer());
  const signature = request.headers.get(SIGNATURE_HEADER);
  const verification = await verifySignature(
    rawBodyOctets,
    signature,
    config.appSecret,
  );
  if (!verification.ok) {
    return {
      status: 401,
      body: { error: 'signature_rejected', reason: verification.reason },
      diagnostics: null,
    };
  }

  const forwardHeaders = {
    'content-type':
      request.headers.get('content-type') || 'application/json',
  };

  const { primary, secondaryPromise } = await fanOut(rawBodyOctets, {
    primaryUrl: config.primaryUrl,
    secondaryUrl: config.secondaryUrl,
    forwardHeaders,
  });

  // Attach a diagnostic drain so an unhandled rejection can never surface.
  secondaryPromise.then(() => {}).catch(() => {});

  return {
    status: primary.ok ? 200 : 502,
    body: { forwarded: primary.ok },
    diagnostics: { primary, secondaryPromise },
  };
}

/**
 * Execute the fan-out and wait for BOTH legs to settle, for reporting/proof.
 * Production callers use handleInbound (secondary not awaited); this is the
 * harness-facing variant that returns the complete picture.
 */
export async function fanOutAndSettle(rawBodyOctets, opts) {
  const { primary, secondaryPromise } = await fanOut(rawBodyOctets, opts);
  const secondary = await secondaryPromise;
  return { primary, secondary };
}
