# TONEART GmbH - WhatsApp / SOPHIA-X coexistence: verifiable demo

This bundle exists to answer one question: **does the fan-out proxy keep SOPHIA-X
completely intact while the WhatsApp MCP server also receives every message?**

> **As delivered by email, every file carries a trailing `.txt`** because Gmail's
> outbound filter rejects JavaScript attachments. Strip the `.txt` from the three
> source files before running:
> `multiplexer-core.js.txt`, `worker.js.txt`, `test-multiplexer.js.txt` ->
> `.js`. `README-TONEART.txt` can stay as it is. Nothing in these files executes
> on open; they are read by node only when you run the harness. The bytes are
> exactly what we tested.

You do not have to take that on trust. It runs on your machine with no
dependencies, no network access, and no credentials.

## Contents

| File | What it is |
|---|---|
| `multiplexer-core.js` | The shared logic: HMAC verification + fan-out. Platform-neutral. |
| `worker.js` | The Cloudflare Worker entry that deploys the core at the edge. |
| `test-multiplexer.js` | The proof harness. Real HTTP servers, real HMAC-SHA256, 13 assertions. |
| `receipt-fanout-*.txt` | The captured output of the run we performed. |

`worker.js` and `test-multiplexer.js` both import the same `multiplexer-core.js`.
There is no second implementation that could drift from the one under test.

## Run it yourself

```
node test-multiplexer.js
```

Requires Node 18 or newer (Web Crypto is used). Nothing else. No npm install.

Expected final line: `VERDICT: FAN-OUT VERIFIED` with `13/13 checks passed`.

## What the 13 checks prove

**The signature gate (checks T1-T3).** An unsigned request, a wrongly signed
request, and a request whose body was modified after signing are all rejected
with HTTP 401 **before any downstream call is made**. Stream A is never
touched by unauthenticated traffic. This matters directly because the public
`spirit122/whatsapp-mcp-server` source has the signature rejection commented
out at `src/index.ts` L345-L347 - that branch is enforced here.

**The dual delivery (checks T4a-T4d).** A correctly signed request returns 200,
SOPHIA-X receives the request body byte-for-byte (verified by SHA-256 equality
against the original), and the MCP worker receives the byte-identical payload.
Stream A is awaited; Stream B is returned as an in-flight promise, never awaited
inside the request path.

**The isolation (checks T5-T7).** This is the property that protects your live
customer line:

- With the MCP endpoint deliberately hanging for 3000 ms, the primary path to
  SOPHIA-X completed in **18 ms** and returned 200.
- With the MCP endpoint refusing the connection entirely, the request still
  returned 200 and SOPHIA-X was delivered exactly once.
- The MCP failure is still **visible in the diagnostics** - it is contained, not
  hidden.

A broken or slow MCP worker therefore cannot drop a customer message or delay
SOPHIA-X.

**Non-interference (check T8).** The proxy is not a deduplicator: two identical
webhook deliveries both reach SOPHIA-X. It does not silently swallow retries.

## One correction to our earlier note

Our earlier note said the multiplexer adds "0ms added latency". That was
imprecise and I would rather correct it now than have you discover it in
staging: the proxy adds **one HTTP hop** to your own SOPHIA-X endpoint. What is
true and measured is that the proxy adds no *waiting* - the secondary leg never
gates the primary. In our run, the primary completed in 18 ms while the
secondary was hanging for 3000 ms. The honest figure for added latency is the
round-trip time between the Worker and your SOPHIA-X endpoint, which we measure
in Phase 2 with your staging endpoint, not a number we invent here.

## What is deliberately NOT in this bundle

This bundle proves the coexistence mechanic. It does not configure your Meta
App, does not include the ADR, does not include the hardened signature patch
applied to the MCP source at `src/index.ts`, and does not include the test-number
staging run against your real SOPHIA-X. Those are the Phase 1 and Phase 2
deliverables.

Nothing here touches your production: there is no outbound network call, no
credential, and no write to any Meta or SOPHIA-X endpoint.
