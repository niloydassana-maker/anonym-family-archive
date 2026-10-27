/**
 * Cloudflare Worker — Meta Cloud API webhook fan-out for TONEART GmbH
 * (SOPHIA-X coexistence with the WhatsApp MCP server).
 *
 * Deploy shape:
 *   - Register THIS worker's URL as the single Meta WABA webhook.
 *   - Secrets (wrangler secret put):
 *       META_APP_SECRET   verification secret for x-hub-signature-256
 *       SOPHIA_X_URL      existing SOPHIA-X inbound endpoint (Stream A)
 *       MCP_WORKER_URL    WhatsApp MCP server inbound endpoint (Stream B)
 *       VERIFY_TOKEN      Meta webhook GET verification token
 *
 * Behaviour:
 *   GET  /  -> Meta webhook verification handshake (hub.challenge echo).
 *   POST /  -> verify signature, deliver to SOPHIA-X synchronously, mirror to
 *              the MCP worker asynchronously. A down MCP worker never affects
 *              the SOPHIA-X delivery.
 */

import { handleInbound } from './multiplexer-core.js';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // --- Meta webhook verification handshake -------------------------------
    if (request.method === 'GET') {
      const mode = url.searchParams.get('hub.mode');
      const token = url.searchParams.get('hub.verify_token');
      const challenge = url.searchParams.get('hub.challenge');
      if (mode === 'subscribe' && token && token === env.VERIFY_TOKEN) {
        return new Response(challenge ?? '', { status: 200 });
      }
      return new Response('verification_failed', { status: 403 });
    }

    if (request.method !== 'POST') {
      return new Response('method_not_allowed', { status: 405 });
    }

    const result = await handleInbound(request, {
      appSecret: env.META_APP_SECRET,
      primaryUrl: env.SOPHIA_X_URL,
      secondaryUrl: env.MCP_WORKER_URL,
    });

    // Stream A's health is the only thing Meta is told about. The secondary
    // leg's outcome is logged, never surfaced as a failure to Meta — otherwise
    // a broken MCP worker would trigger Meta retries against SOPHIA-X too.
    if (result.diagnostics) {
      const { primary } = result.diagnostics;
      console.log(
        JSON.stringify({
          event: 'fanout',
          primary_status: primary.status,
          primary_ms: primary.ms,
          primary_ok: primary.ok,
        }),
      );
    }

    return new Response(JSON.stringify(result.body), {
      status: result.status,
      headers: { 'content-type': 'application/json' },
    });
  },
};
