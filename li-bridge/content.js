// Kilo Bridge content script: lightweight, unified observation & action pipeline.
// Observes page state and executes gated directives in the relay-selected tab.
const RELAY = "http://127.0.0.1:8778";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const host = location.hostname;
const path = location.pathname;
const isYouTube = host.includes("youtube.com");
const isGmail = host.includes("mail.google.com");
const isNaukri = host.includes("naukri.com");
const isFoundit = host.includes("foundit.in");
const isLinkedIn = host.includes("linkedin.com");
const isLinkedInMessaging = isLinkedIn && path.includes("/messaging/");
const isLinkedInServiceMarketplace = isLinkedIn && path.includes("/service-marketplace/");
const isYouTubeFeed = isYouTube && (path.startsWith("/feed") || path.startsWith("/channels"));
const isColdScope = isYouTube || host.includes("instagram.com") || host.includes("facebook.com");

// Fast, non-thrashing element visibility check
function kiloVisible(el) {
  if (!el) return false;
  try {
    if (el.hidden || el.getAttribute("aria-hidden") === "true") return false;
    const r = el.getBoundingClientRect();
    if (!r || r.width < 2 || r.height < 2) return false;
    const s = window.getComputedStyle(el);
    return s.display !== "none" && s.visibility !== "hidden" && s.visibility !== "collapse";
  } catch (e) {
    return false;
  }
}

function isVisibleEnabled(el) {
  if (!el || el.disabled || el.getAttribute("aria-disabled") === "true" || el.hidden) return false;
  return kiloVisible(el);
}

function isWalledPage(body) {
  const title = String(document.title || "").toLowerCase();
  const lead = String(body || "").slice(0, 1200).toLowerCase();
  return /just a moment|attention required|security verification/.test(title) ||
    /additional verification required|verify (that )?you are human|checking your browser before accessing/.test(lead) ||
    (lead.includes("captcha") && /complete|solve|verify/.test(lead));
}

let FILL_FORCE = false;
let LAST_ACT = null;
let PENDING_NAV_RECEIPT = null;
let NAV_LOOKUP_DONE = false;
let PENDING_GMAIL_RECEIPT = null;
let PENDING_GMAIL_COMPOSE = null;
const GMAIL_COMPOSE_RECEIPT_KEY = "kilo-pending-gmail-compose";
const GMAIL_COMPOSE_WAIT_MS = 75000;

// Stable session tab ID
let TAB_ID = sessionStorage.getItem("kilo-tab-id");
if (!TAB_ID) {
  TAB_ID = "tab-" + Math.random().toString(36).slice(2, 10) + "-" + Date.now().toString(36);
  sessionStorage.setItem("kilo-tab-id", TAB_ID);
}

const LS_VERSION = "v4";
const PRIMARY_LEASE_MS = 3 * 60 * 1000;
const PRIMARY_SCOPE = () => {
  const seg = (location.pathname || "/").split("/").filter(Boolean)[0] || "_root";
  return location.hostname + "/" + seg;
};
const PRIMARY_KEY = (hostname) => "kilo-tab-primary-" + LS_VERSION + "-" + PRIMARY_SCOPE();

function claimPrimary(hostname) {
  const key = PRIMARY_KEY(hostname);
  const now = Date.now();
  let owner = null;
  try { owner = JSON.parse(localStorage.getItem(key) || "null"); } catch (e) {}
  if (owner && owner.tabId !== TAB_ID && now - Number(owner.ts || 0) < PRIMARY_LEASE_MS) return false;
  localStorage.setItem(key, JSON.stringify({ tabId: TAB_ID, ts: now }));
  try { return JSON.parse(localStorage.getItem(key)).tabId === TAB_ID; }
  catch (e) { return false; }
}

const KNOWN_PATH_ALIASES = {
  "/me/profile-views": "/analytics/profile-views",
  "/analytics/profile-views": "/me/profile-views",
  "/feed": "/feed/foryou",
  "/feed/foryou": "/feed",
};

function urlsMatch(expected, current) {
  if (!expected || !current) return false;
  if (expected === current) return true;
  try {
    const u1 = new URL(expected);
    const u2 = new URL(current);
    const h1 = u1.hostname.replace(/^www\./, "");
    const h2 = u2.hostname.replace(/^www\./, "");
    if (u1.protocol !== u2.protocol || h1 !== h2 || u1.port !== u2.port) return false;
    const p1 = u1.pathname.replace(/\/+$/, "");
    const p2 = u2.pathname.replace(/\/+$/, "");
    if (p1 !== p2) {
      if (h1 !== "linkedin.com" || KNOWN_PATH_ALIASES[p1] !== p2) return false;
    }
    if (u1.search !== u2.search) return false;
    return true;
  } catch (e) {
    return false;
  }
}

function findNavAnchor(el) {
  if (!el) return null;
  const a = el.tagName === "A" && el.href ? el : (el.closest ? el.closest("a[href]") : null);
  if (!a || !a.href) return null;
  const href = a.href;
  if (!href.startsWith("http://") && !href.startsWith("https://")) return null;
  if (a.target === "_blank") return null;
  if (a.hasAttribute("download")) return null;
  if (href.startsWith("javascript:") || href === location.href + "#" || href === "#") return null;
  try {
    const u = new URL(href, location.href);
    if (u.origin !== location.origin) return null;
    return u.href;
  } catch (e) {
    return null;
  }
}

async function hydratePendingNavigation(currentUrl) {
  if (NAV_LOOKUP_DONE || PENDING_NAV_RECEIPT) return;
  NAV_LOOKUP_DONE = true;
  // 1. Same-origin instantaneous handoff via sessionStorage
  try {
    const raw = sessionStorage.getItem("kilo-pending-nav");
    if (raw) {
      sessionStorage.removeItem("kilo-pending-nav");
      const pending = JSON.parse(raw);
      if (pending && urlsMatch(pending.expected_url, currentUrl)) {
        PENDING_NAV_RECEIPT = pending;
        LAST_ACT = {
          action: pending.action || "open",
          result: "navigated",
          directive_id: pending.directive_id,
          source_url: pending.source_url,
          expected_url: pending.expected_url,
          text: pending.text,
          candidate: pending.candidate,
          click_started_at: pending.click_started_at,
          elapsed_ms: pending.click_started_ms ? (Date.now() - pending.click_started_ms) : undefined,
        };
        return;
      }
    }
  } catch (e) {}
  // 2. Cross-origin / service worker fallback
  try {
    const response = await callWorker({ type: "GET_PENDING_NAV", url: currentUrl }, 3000);
    const pending = response && response.pending;
    if (pending && urlsMatch(pending.expected_url, currentUrl)) {
      PENDING_NAV_RECEIPT = pending;
      LAST_ACT = {
        action: pending.action || "open",
        result: "navigated",
        directive_id: pending.directive_id,
        source_url: pending.source_url,
        expected_url: pending.expected_url,
        text: pending.text,
        candidate: pending.candidate,
        click_started_at: pending.click_started_at,
        elapsed_ms: pending.click_started_ms ? (Date.now() - pending.click_started_ms) : undefined,
      };
    }
  } catch (e) {}
}

function hydratePendingGmailSend(currentUrl, body, composeOpen) {
  if (PENDING_GMAIL_RECEIPT) return;
  if (!isGmail || composeOpen || !/\bmessage sent\b/i.test(String(body || ""))) return;
  let pending = null;
  try { pending = JSON.parse(sessionStorage.getItem("kilo-pending-gmail-send") || "null"); } catch (e) {}
  if (!pending || pending.source_url !== currentUrl || !pending.directive_id) return;
  const age = Date.now() - Number(pending.started_ms || 0);
  if (!Number.isFinite(age) || age < 0 || age > 5 * 60 * 1000) {
    sessionStorage.removeItem("kilo-pending-gmail-send");
    return;
  }
  PENDING_GMAIL_RECEIPT = pending;
  LAST_ACT = {
    action: "click",
    text: "Send",
    result: "accepted-by-gmail",
    directive_id: pending.directive_id,
    source_url: pending.source_url,
  };
}

function composeReceiptAction(pending, result, nowMs) {
  const act = {
    action: "click", text: pending.text, result,
    directive_id: pending.directive_id,
    click_started_at: pending.click_started_at,
    elapsed_ms: Math.max(0, nowMs - Number(pending.click_started_ms || nowMs)),
    candidate: pending.candidate,
  };
  if (pending.editor_ready_at) act.editor_ready_at = pending.editor_ready_at;
  return act;
}

function savePendingGmailCompose(pending) {
  PENDING_GMAIL_COMPOSE = pending;
  try { sessionStorage.setItem(GMAIL_COMPOSE_RECEIPT_KEY, JSON.stringify(pending)); } catch (e) {}
}

function hydratePendingGmailCompose(composeOpen) {
  if (!PENDING_GMAIL_COMPOSE) {
    try { PENDING_GMAIL_COMPOSE = JSON.parse(sessionStorage.getItem(GMAIL_COMPOSE_RECEIPT_KEY) || "null"); } catch (e) {}
  }
  const pending = PENDING_GMAIL_COMPOSE;
  if (!isGmail || !pending || !pending.directive_id) return;
  const now = Date.now();
  if (composeOpen && !pending.compose_open_before) {
    if (!pending.editor_ready_at) {
      pending.editor_ready_at = new Date(now).toISOString();
      savePendingGmailCompose(pending);
    }
    LAST_ACT = composeReceiptAction(pending, "composer-open", now);
  } else if (now >= Number(pending.deadline_ms || 0)) {
    LAST_ACT = composeReceiptAction(pending, "composer-open-timeout", now);
  } else if (!pending.pending_reported) {
    LAST_ACT = composeReceiptAction(pending, "composer-opening", now);
  } else if (LAST_ACT && LAST_ACT.directive_id === pending.directive_id) {
    LAST_ACT = null;
  }
}

function gmailVisibleEditor() {
  if (!isGmail || typeof KiloGmailEditor === "undefined") return false;
  return KiloGmailEditor.findVisible(document, isVisibleEnabled);
}
function gmailComposeOpen() {
  return Boolean(gmailVisibleEditor());
}

// Bounded text reader: fast and non-blocking
function readBodyTextBounded(maxChars = 6000) {
  const root = document.body;
  if (!root) return "";
  try {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent || /^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE)$/.test(parent.tagName || "")) {
          return NodeFilter.FILTER_REJECT;
        }
        return String(node.nodeValue || "").trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    const parts = [];
    let length = 0;
    let node;
    while (length < maxChars && (node = walker.nextNode())) {
      const text = String(node.nodeValue || "").replace(/\s+/g, " ").trim();
      if (!text) continue;
      const remaining = maxChars - length;
      const part = text.slice(0, remaining);
      parts.push(part);
      length += part.length;
    }
    return parts.join("\n");
  } catch (e) {
    try { return String(root.textContent || "").slice(0, maxChars); } catch (_) { return ""; }
  }
}

function controlLabel(element) {
  if (!element) return "";
  try {
    return String(element.getAttribute("aria-label") || element.getAttribute("data-tooltip") ||
      element.getAttribute("title") || element.value || element.placeholder || element.textContent || "")
      .replace(/\s+/g, " ").trim().slice(0, 100);
  } catch (_) { return ""; }
}

// Unified, lightweight pipeline for extracting controls from DOM
function scanControlsBounded() {
  const buttons = [];
  const siteButtons = [];
  const controls = [];
  const videoLinks = [];
  const seenLabels = new Set();
  const relevantActionPattern = /\b(reply(?: all)?|forward|send|compose|apply(?: now)?|submit(?: proposal)?|save|continue|next|respond|connect|follow|message)\b/i;

  try {
    const selector = "button, a, input[type=submit], input[type=button], input[type=checkbox], input[type=radio], select, textarea, [role=button], [role=link], [role=tab], [role=menuitem], [role=checkbox], [role=option], [role=textbox], [contenteditable=true]" + (isGmail ? ", [data-tooltip], [gh='cm']" : "");
    const elements = document.querySelectorAll(selector);
    let inspected = 0;

    for (const el of elements) {
      if (inspected++ >= 200 || controls.length >= 100) break;
      if (!isVisibleEnabled(el)) continue;

      const label = controlLabel(el);
      if (!label && !el.getAttribute("role") && !el.tagName.includes("INPUT")) continue;

      const tag = el.tagName ? el.tagName.toUpperCase() : "";
      const role = el.getAttribute("role") || "";
      const type = el.getAttribute("type") || "";
      let kind = role || (tag === "INPUT" ? `input-${type || "text"}` : tag.toLowerCase());

      const item = {
        label: label || `[${kind}]`,
        tag,
        kind,
        role: role || undefined,
        type: type || undefined,
        selector: el.id ? `#${el.id}` : (el.className && typeof el.className === "string" ? `.${el.className.trim().split(/\s+/)[0]}` : undefined),
      };

      controls.push(item);

      if (label && !seenLabels.has(label.toLowerCase())) {
        seenLabels.add(label.toLowerCase());
        if (buttons.length < 80) buttons.push(label);
      }

      // Categorize site-specific actions
      const lower = label.toLowerCase();
      let siteActionType = null;
      if (isNaukri && ["recruiter", "view all", "load more", "apply", "save", "edit profile"].some(w => lower.includes(w))) {
        siteActionType = "naukri-action";
      } else if (isFoundit && ["quick apply", "apply", "save", "view detail", "complete"].some(w => lower.includes(w))) {
        siteActionType = "foundit-action";
      } else if (isLinkedInServiceMarketplace && ["view request", "submit proposal", "no thanks", "message"].some(w => lower.includes(w))) {
        siteActionType = "sm-action";
      } else if (isLinkedInMessaging && /compose|send|reply|write a message/i.test(lower)) {
        siteActionType = "msg-action";
      } else if (isLinkedIn && ["connect", "follow", "message", "apply", "save", "more"].some(w => lower.includes(w))) {
        siteActionType = "li-action";
      } else if (isGmail && relevantActionPattern.test(label)) {
        siteActionType = "gmail-action";
      }

      if (siteActionType && siteButtons.length < 40 && !siteButtons.some(b => b.text === label && b.type === siteActionType)) {
        siteButtons.push({ text: label, type: siteActionType, role: role || undefined, selector: item.selector });
      }
    }
  } catch (e) {}

  // YouTube feed video links
  if (isYouTubeFeed) {
    try {
      const vEls = document.querySelectorAll("ytd-rich-grid-media #video-title, ytd-video-renderer #video-title, a#video-title");
      let count = 0;
      for (const v of vEls) {
        if (count++ >= 30 || videoLinks.length >= 20) break;
        const href = v.href || v.getAttribute("href");
        const title = (v.innerText || v.getAttribute("aria-label") || "").trim();
        if (href && title) videoLinks.push({ title: title.slice(0, 120), url: href });
      }
    } catch (e) {}
  }

  return { buttons: buttons.slice(0, 80), siteButtons: siteButtons.slice(0, 40), controls: controls.slice(0, 100), videoLinks: videoLinks.slice(0, 20) };
}

async function snapshot() {
  const url = location.href;
  const title = document.title;
  const body = readBodyTextBounded(6000);
  const hostname = location.hostname;
  const isPrimary = claimPrimary(hostname);
  const walled = isWalledPage(body);
  const scanned = scanControlsBounded();

  let composeOpen = false;
  try { composeOpen = gmailComposeOpen(); } catch (e) {}
  let composerText = "";
  try {
    const editor = gmailVisibleEditor();
    if (editor && typeof KiloGmailEditor !== "undefined") {
      composerText = KiloGmailEditor.meaningfulText(editor).slice(0, 1200);
    }
  } catch (e) {}

  await hydratePendingNavigation(url);
  hydratePendingGmailSend(url, body, composeOpen);
  hydratePendingGmailCompose(composeOpen);

  let bridgeVer = "2.28";
  try { bridgeVer = (chrome && chrome.runtime && chrome.runtime.getManifest && chrome.runtime.getManifest().version) || "2.28"; } catch (e) {}

  return {
    url, title, body,
    buttons: scanned.buttons,
    siteButtons: scanned.siteButtons,
    controls: scanned.controls,
    videoLinks: scanned.videoLinks,
    tabId: TAB_ID,
    isPrimary,
    walled,
    composeOpen,
    composerText,
    lastAct: LAST_ACT,
    bridge: bridgeVer,
    ts: new Date().toISOString()
  };
}

async function badge(text) {
  try { await chrome.runtime.sendMessage({ badge: text }); } catch (e) {}
}

function callWorker(msg, ms) {
  return new Promise((resolve) => {
    let done = false;
    const finish = (v) => { if (!done) { done = true; resolve(v || {}); } };
    try {
      chrome.runtime.sendMessage(msg, (resp) => {
        if (chrome.runtime.lastError) finish({ error: chrome.runtime.lastError.message || "runtime-message-failed" });
        else finish(resp);
      });
    } catch (e) { finish({ error: String(e && e.message || e) }); }
    setTimeout(() => finish({ timeout: true }), ms || 25000);
  });
}

function directiveGateFailure(directive, snap) {
  if (!directive || !snap) return "missing-snapshot";
  if (directive.action === "timing_probe" &&
      (!directive.match_url_substring || String(directive.match_url_substring) !== snap.url)) {
    return "timing-probe-exact-url-required";
  }
  if (directive.action === "click" &&
      (typeof directive.text !== "string" || !directive.text.trim())) {
    return "invalid-command:click-text-required";
  }
  if (directive.action === "discard_test_draft" &&
      (directive.require_compose !== true ||
       !Object.prototype.hasOwnProperty.call(directive, "require_composer_text_equals") ||
       !String(directive.require_composer_text_equals || ""))) {
    return "discard-guard-missing";
  }
  if (directive.match_url_substring) {
    const expectedUrl = String(directive.match_url_substring).trim();
    if (expectedUrl && snap.url !== expectedUrl) return "url-mismatch";
  }
  const markers = (value) => (Array.isArray(value) ? value : [value])
    .filter((item) => item !== undefined && item !== null)
    .map((item) => String(item).trim().toLowerCase())
    .filter(Boolean);

  const bodyMarkers = markers(directive.require_body_contains);
  const body = String(snap.body || "").toLowerCase();
  if (bodyMarkers.some((marker) => !body.includes(marker))) return "body-marker-missing";

  const buttonMarkers = markers(directive.require_buttons_contains);
  const buttonText = [
    ...(Array.isArray(snap.buttons) ? snap.buttons : []),
    ...(Array.isArray(snap.siteButtons) ? snap.siteButtons : []),
    ...(Array.isArray(snap.controls) ? snap.controls : [])
  ].map((item) => {
    if (typeof item === "string") return item.toLowerCase();
    return String((item && (item.text || item.label)) || "").toLowerCase();
  });
  if (buttonMarkers.some((marker) => !buttonText.some((button) => button.includes(marker)))) {
    return "button-marker-missing";
  }
  if (Object.prototype.hasOwnProperty.call(directive, "require_compose") &&
      Boolean(snap.composeOpen) !== Boolean(directive.require_compose)) {
    return "compose-state-mismatch";
  }
  if (directive.require_empty_composer && String(snap.composerText || "").trim()) {
    return "composer-not-empty";
  }
  if (Object.prototype.hasOwnProperty.call(directive, "require_composer_text_equals") &&
      String(snap.composerText || "") !== String(directive.require_composer_text_equals || "")) {
    return "composer-text-mismatch";
  }
  return "";
}

let POLL_IN_FLIGHT = false;
async function poll() {
  if (POLL_IN_FLIGHT) return;
  POLL_IN_FLIGHT = true;
  const pollStartedMono = performance.now();
  const timingTrace = { content_poll_started_at: new Date().toISOString() };
  try {
    const snap = await snapshot();
    timingTrace.content_snapshot_ready_at = new Date().toISOString();
    timingTrace.content_snapshot_elapsed_ms = Math.round((performance.now() - pollStartedMono) * 100) / 100;
    timingTrace.content_worker_message_sent_at = new Date().toISOString();
    const res = await callWorker(
      { type: "RELAY_EVENT", payload: { page: snap, tabId: TAB_ID }, timing_trace: timingTrace }, 30000);
    timingTrace.content_worker_response_received_at = new Date().toISOString();
    timingTrace.content_poll_roundtrip_ms = Math.round((performance.now() - pollStartedMono) * 100) / 100;

    if (!res || res.timeout || res.error || res.status !== "success") {
      const detail = (res && (res.error || (res.timeout && "worker-timeout"))) || "relay-no-response";
      LAST_ACT = { action: "relay", result: String(detail).slice(0, 120) };
      await badge("ERR");
      return;
    }
    const receiptState = res && res.data && res.data.receipt_state;
    if (snap.lastAct && snap.lastAct.result === "navigated" && PENDING_NAV_RECEIPT &&
        receiptState && receiptState.status === "verified") {
      const cleared = await callWorker({ type: "CLEAR_PENDING_NAV", directive_id: snap.lastAct.directive_id }, 5000);
      if (cleared && cleared.success) PENDING_NAV_RECEIPT = null;
    }
    if (snap.lastAct && snap.lastAct.result === "accepted-by-gmail" && PENDING_GMAIL_RECEIPT &&
        receiptState && receiptState.status === "verified") {
      sessionStorage.removeItem("kilo-pending-gmail-send");
      PENDING_GMAIL_RECEIPT = null;
    }
    if (snap.lastAct && PENDING_GMAIL_COMPOSE &&
        snap.lastAct.directive_id === PENDING_GMAIL_COMPOSE.directive_id && receiptState) {
      if (snap.lastAct.result === "composer-opening" && receiptState.status === "pending") {
        PENDING_GMAIL_COMPOSE.pending_reported = true;
        savePendingGmailCompose(PENDING_GMAIL_COMPOSE);
      } else if (["verified", "failed", "unverified"].includes(receiptState.status)) {
        sessionStorage.removeItem(GMAIL_COMPOSE_RECEIPT_KEY);
        PENDING_GMAIL_COMPOSE = null;
      }
    }
    if (snap.lastAct) LAST_ACT = null;
    await badge("OK");
    const directive = res && res.data ? res.data : {};
    if (snap.walled) { await badge("WALL"); return; }
    const gateFailure = directiveGateFailure(directive, snap);
    if (gateFailure) {
      LAST_ACT = { action: directive.action || "?", result: "gate-blocked:" + gateFailure,
        directive_id: directive.directive_id || "" };
      await badge("GATE");
      return;
    }
    try {
      if (directive && directive.action === "click" && directive.text) {
        await humanClick(directive.text, directive);
      } else if (directive && directive.action === "timing_probe" && directive.directive_id) {
        const probeStartedMono = performance.now();
        const probeTrace = {
          ...(directive.timing_trace || {}),
          ...(res.timing_trace || {}),
          ...timingTrace,
          content_probe_started_at: new Date().toISOString(),
        };
        LAST_ACT = {
          action: "timing_probe", result: "probe-completed",
          directive_id: directive.directive_id, timing_trace: probeTrace,
        };
        probeTrace.content_probe_finished_at = new Date().toISOString();
        probeTrace.content_probe_elapsed_ms = Math.round((performance.now() - probeStartedMono) * 100) / 100;
      } else if (directive && directive.action === "discard_test_draft" && directive.text) {
        await humanDiscardTestDraft(directive.require_composer_text_equals, directive);
      } else if (directive && directive.action === "fill" && directive.text) {
        await humanFill(directive.match || "", directive.text);
      } else if (directive && directive.action === "fillforce" && directive.text) {
        FILL_FORCE = true;
        try { await humanFill(directive.match || "", directive.text); }
        finally { FILL_FORCE = false; }
      } else if (directive && directive.action === "fillfast" && directive.text) {
        FILL_FORCE = true;
        try { await humanFill(directive.match || "", directive.text); }
        finally { FILL_FORCE = false; }
      } else if (directive && directive.action === "uncheck" && directive.match) {
        await humanUncheck(directive.match);
      } else if (directive && directive.action === "open" && directive.url) {
        await humanOpen(directive.url, directive);
      } else if (directive && directive.action === "discard" && directive.match) {
        try {
          const r = await callWorker({ type: "DISCARD_SPARE", victim: directive.match }, 25000);
          LAST_ACT = { action: "discard", match: directive.match, result: "discarded:" + (r && r.discarded !== undefined ? r.discarded : "?") };
        } catch (e) { LAST_ACT = { action: "discard", match: directive.match || "", result: "error" }; }
      } else if (directive && directive.action === "shot") {
        try {
          const r = await callWorker({ type: "CAPTURE" }, 25000);
          LAST_ACT = { action: "shot", result: (r && r.saved) ? ("saved:" + r.saved) : ("error:" + ((r && r.error) || (r && r.timeout ? "timeout" : "?"))) };
        } catch (e) { LAST_ACT = { action: "shot", result: "error" }; }
      } else if (directive && directive.action === "huntvideo" && isYouTube) {
        await humanHuntVideo(directive.index || 0);
      } else if (directive && directive.action === "transcript" && isYouTube) {
        await humanTranscript();
      } else if (directive && directive.action === "hunt" && isYouTubeFeed) {
        await humanHunt(directive.index || 0);
      }
    } catch (e) {
      LAST_ACT = { action: (directive && directive.action) || "?", result: "error:" + (e && e.message || e) };
    }
    if (directive && directive.directive_id && directive.action !== "open") {
      LAST_ACT = { ...(LAST_ACT || { action: directive.action || "?", result: "unverified" }),
        directive_id: directive.directive_id };
    }
  } catch (e) {
    LAST_ACT = { action: "poll", result: String(e && e.message || e).slice(0, 120) };
    await badge("ERR");
  } finally {
    POLL_IN_FLIGHT = false;
  }
}

// Lightweight, declarative Click Finder & Dispatcher
async function humanClick(text, directive) {
  const want = String(text || "").trim().toLowerCase();
  const clickStart = Date.now();

  // Specialized YouTube video link match
  if (isYouTubeFeed && (want.includes("http") || want.includes("watch"))) {
    try {
      const links = [...document.querySelectorAll("ytd-rich-grid-media #video-title, ytd-video-renderer #video-title, a#video-title")];
      const match = links.find(l => (l.href || "").toLowerCase().includes(want) || (l.innerText || "").toLowerCase().includes(want));
      if (match && isVisibleEnabled(match)) {
        match.scrollIntoView({ block: "center" });
        match.click();
        LAST_ACT = {
          action: "click", text, result: "clicked", tag: String(match.tagName || "?") + ".branch",
          click_started_at: new Date(clickStart).toISOString(), elapsed_ms: Date.now() - clickStart,
          candidate: { tag: String(match.tagName || "?"), label: (match.innerText || "").trim().slice(0, 80) }
        };
        return;
      }
    } catch (e) {}
  }

  // Specialized Gmail selectors
  if (isGmail) {
    const gmailSelectors = [
      '[gh="cm"]', '[role="button"][aria-label*="Compose" i]', '[data-tooltip*="Compose" i]',
      '[role="button"][aria-label*="Send" i]', '[data-tooltip*="Send" i]', 'div[role="button"][aria-label="Send"]',
      'button', '[role="button"]', '[data-tooltip]'
    ];
    for (const sel of gmailSelectors) {
      try {
        const els = [...document.querySelectorAll(sel)];
        const match = els.find(el => {
          if (!isVisibleEnabled(el)) return false;
          const t = controlLabel(el).toLowerCase();
          return t === want || (want.length > 3 && t.includes(want));
        });
        if (match) {
          match.scrollIntoView({ block: "center" });
          if (!isVisibleEnabled(match)) {
            LAST_ACT = { action: "click", text, result: "target-lost-before-click", tag: (match.tagName || "?") + ".branch" };
            return;
          }
          const opensComposer = want === "reply" || want === "reply all" || want === "compose";
          const composeOpenBefore = opensComposer && gmailComposeOpen();
          match.click();
          if (want === "send" && directive && directive.directive_id) {
            try {
              sessionStorage.setItem("kilo-pending-gmail-send", JSON.stringify({
                directive_id: directive.directive_id,
                source_url: location.href,
                started_ms: clickStart,
              }));
            } catch (e) {}
          }
          if (opensComposer && directive && directive.directive_id) {
            const pending = {
              directive_id: directive.directive_id,
              text,
              source_url: location.href,
              click_started_ms: clickStart,
              click_started_at: new Date(clickStart).toISOString(),
              deadline_ms: clickStart + GMAIL_COMPOSE_WAIT_MS,
              pending_reported: false,
              compose_open_before: composeOpenBefore,
              candidate: {
                tag: String(match.tagName || "?"),
                id: String(match.id || "").slice(0, 80),
                label: controlLabel(match).slice(0, 100),
              },
            };
            if (gmailComposeOpen() && !composeOpenBefore) pending.editor_ready_at = new Date().toISOString();
            savePendingGmailCompose(pending);
            LAST_ACT = composeReceiptAction(pending,
              pending.editor_ready_at ? "composer-open" : "composer-opening", Date.now());
            return;
          }
          LAST_ACT = {
            action: "click", text,
            result: opensComposer ? (gmailComposeOpen() ? "composer-open" : "unverified") : "dispatched",
            tag: (match.tagName || "?") + ".branch", trusted: false,
            click_started_at: new Date(clickStart).toISOString(), elapsed_ms: Date.now() - clickStart,
            candidate: { tag: String(match.tagName || "?"), id: String(match.id || "").slice(0, 80), label: controlLabel(match).slice(0, 100) }
          };
          return;
        }
      } catch (e) {}
    }
  }

  // Unified interactive element search for all platforms
  const candidateSelectors = "button, a, input[type=submit], input[type=button], input[type=checkbox], input[type=radio], [role=button], [role=link], [role=tab], [role=menuitem], [role=option], [role=checkbox], [data-test-action], li, span, div";
  try {
    const elements = [...document.querySelectorAll(candidateSelectors)];
    const matches = [];

    for (const el of elements) {
      if (!isVisibleEnabled(el)) continue;
      const label = controlLabel(el).toLowerCase();
      if (!label) continue;
      if (label === want) {
        matches.push({ el, score: 0, label });
      } else if (label.includes(want) && label.length <= want.length + 80) {
        matches.push({ el, score: label.length - want.length, label });
      } else if (want.includes(label) && label.length >= 3) {
        matches.push({ el, score: 100 + (want.length - label.length), label });
      }
    }

    if (!matches.length) {
      LAST_ACT = { action: "click", text, result: "nomatch", directive_id: directive && directive.directive_id };
      return;
    }

    matches.sort((a, b) => a.score - b.score);
    const best = matches[0].el;

    best.scrollIntoView({ block: "center" });
    if (!isVisibleEnabled(best)) {
      LAST_ACT = { action: "click", text, result: "target-lost-before-click", directive_id: directive && directive.directive_id };
      return;
    }

    const navAnchor = findNavAnchor(best);
    if (navAnchor && directive && directive.directive_id) {
      const pending = {
        directive_id: directive.directive_id,
        action: "click",
        text,
        source_url: location.href,
        expected_url: navAnchor,
        click_started_ms: clickStart,
        click_started_at: new Date(clickStart).toISOString(),
        candidate: {
          tag: String(best.tagName || "?"),
          id: String(best.id || "").slice(0, 80),
          label: controlLabel(best).slice(0, 100),
        }
      };
      try { sessionStorage.setItem("kilo-pending-nav", JSON.stringify(pending)); } catch (e) {}
      try {
        await callWorker({
          type: "SET_PENDING_NAV",
          pending: { ...pending, tab_id: TAB_ID }
        }, 2500);
      } catch (e) {}
      best.click();
      LAST_ACT = {
        action: "click",
        text,
        result: "navigating",
        directive_id: directive.directive_id,
        source_url: location.href,
        expected_url: navAnchor,
        tag: (best.tagName || "?") + "." + (String(best.className || "").slice(0, 40)),
        click_started_at: new Date(clickStart).toISOString(),
        elapsed_ms: Date.now() - clickStart,
        candidate: pending.candidate
      };
      return;
    }

    best.click();
    LAST_ACT = {
      action: "click",
      text,
      result: "clicked",
      directive_id: directive && directive.directive_id,
      tag: (best.tagName || "?") + "." + (String(best.className || "").slice(0, 40)),
      click_started_at: new Date(clickStart).toISOString(),
      elapsed_ms: Date.now() - clickStart,
      candidate: {
        tag: String(best.tagName || "?"),
        id: String(best.id || "").slice(0, 80),
        label: controlLabel(best).slice(0, 100),
      }
    };
  } catch (e) {
    LAST_ACT = { action: "click", text, result: "error:" + String(e && e.message || e).slice(0, 100), directive_id: directive && directive.directive_id };
  }
}

async function humanDiscardTestDraft(expectedText, directive) {
  if (!isGmail || !gmailComposeOpen()) {
    LAST_ACT = { action: "discard_test_draft", result: "composer-not-open" };
    return;
  }
  const discardLabelPattern = /\b(?:discard(?: draft)?|delete(?: draft)?|trash(?: draft)?)\b/;
  const editor = gmailVisibleEditor();
  const observed = editor && typeof KiloGmailEditor !== "undefined" ? KiloGmailEditor.meaningfulText(editor) : "";
  const comparable = value => String(value || "").replace(/[\u200B-\u200D\uFEFF]/g, "");
  if (!editor || comparable(observed) !== comparable(expectedText)) {
    LAST_ACT = { action: "discard_test_draft", result: "composer-text-mismatch", chars: observed.length };
    return;
  }

  let root = editor;
  let searchDepth = 0;
  let trash = null;
  let trashLabel = "";
  const collectedCandidates = [];

  for (; searchDepth < 32 && root && root.parentElement; searchDepth++) {
    root = root.parentElement;
    const controls = [...root.querySelectorAll("button, [role='button'], [aria-label], [data-tooltip], [title]")]
      .filter(el => el !== editor && !editor.contains(el));
    for (const el of controls) {
      const label = [el.getAttribute("aria-label"), el.getAttribute("data-tooltip"), el.getAttribute("title"), el.innerText]
        .filter(Boolean).join(" ").toLowerCase();
      if (discardLabelPattern.test(label)) {
        const visible = isVisibleEnabled(el);
        collectedCandidates.push({ element: el, label, visible });
        if (visible) {
          trash = el;
          trashLabel = label;
          break;
        }
      }
    }
    if (trash) break;
  }

  if (!trash) {
    LAST_ACT = {
      action: "discard_test_draft", result: "target-not-found-or-not-visible",
      chars: observed.length, search_depth: searchDepth,
      discard_candidates: collectedCandidates.map(item => ({
        label: item.label.slice(0, 80), visible: item.visible,
      })),
    };
    return;
  }
  try { trash.click(); } catch (e) {
    LAST_ACT = { action: "discard_test_draft", result: "error:" + String(e && e.message || e).slice(0, 100) };
    return;
  }
  for (let i = 0; i < 20 && gmailComposeOpen(); i++) await sleep(250);
  LAST_ACT = {
    action: "discard_test_draft",
    result: !gmailComposeOpen() ? "discarded" : "unverified",
    chars: observed.length, search_depth: searchDepth,
    trash_control: {
      tag: String(trash.tagName || "?"),
      label: trashLabel.slice(0, 80),
    },
  };
}

async function humanFill(match, text) {
  const w = String(match || "").toLowerCase();

  // Direct editor targeting for Gmail body
  if (isGmail && (!match || w.includes("body") || w === "message")) {
    const editor = gmailVisibleEditor();
    if (editor) return fillElement(editor, text);
  }

  // Unified input field scan
  const inputSelectors = "textarea, input[type=text], input[type=email], input[type=number], input[name], [contenteditable=true]";
  try {
    const areas = [...document.querySelectorAll(inputSelectors)].filter(isVisibleEnabled);
    let el = null;
    if (match) {
      el = areas.find(a => {
        const label = (a.placeholder || a.getAttribute("aria-label") || a.name || a.id || "").toLowerCase();
        return label.includes(w) || w.includes(label);
      });
    }
    if (!el) {
      const editables = areas.filter(a => a.isContentEditable);
      el = (editables.length ? editables[editables.length - 1] : areas[0]) || null;
    }
    if (!el) {
      LAST_ACT = { action: "fill", match: match || "", result: "nomatch" };
      return;
    }
    return fillElement(el, text);
  } catch (e) {
    LAST_ACT = { action: "fill", match: match || "", result: "error:" + String(e && e.message || e) };
  }
}

async function fillElement(el, text) {
  el.focus();
  LAST_ACT = { action: "fill", result: "started", tag: el.tagName || "?" };
  const cur = el.value !== undefined ? el.value : el.innerText;
  const gmailBodyEditor = isGmail && (el.isContentEditable ||
    (el.getAttribute && el.getAttribute("g_editable") === "true"));
  if (!gmailBodyEditor) await sleep(600);
  const meaningfulCur = gmailBodyEditor && typeof KiloGmailEditor !== "undefined"
    ? KiloGmailEditor.meaningfulText(el)
    : String(cur || "").replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
  if (!FILL_FORCE && meaningfulCur.length > 0) { LAST_ACT = { action: "fill", result: "skipped-nonempty", tag: el.tagName || "?", chars: meaningfulCur.length }; return; }
  if (!FILL_FORCE && cur && !meaningfulCur) {
    if (el.value !== undefined) el.value = "";
    else el.innerText = "";
  }
  if (FILL_FORCE) {
    try {
      if (el.value !== undefined) el.value = "";
      else el.innerText = "";
      el.dispatchEvent(new Event("input", { bubbles: true }));
    } catch (e) {}
  }
  if (!gmailBodyEditor) await sleep(900 + Math.random() * 900);
  try {
    if (el.value !== undefined) el.value = text;
    else el.innerText = text;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  } catch (e) {
    LAST_ACT = { action: "fill", result: "error:" + String(e && e.message || e), tag: el.tagName || "?" };
    return;
  }
  if (!gmailBodyEditor) await sleep(900);
  const observed = gmailBodyEditor && typeof KiloGmailEditor !== "undefined"
    ? KiloGmailEditor.meaningfulText(el)
    : String(el.value !== undefined ? el.value : el.innerText || "");
  const comparable = (value) => String(value).replace(/\s+/g, " ").trim();
  LAST_ACT = { action: "fill", result: comparable(observed).includes(comparable(text)) ? "filled" : "unverified", tag: el.tagName || "?", chars: observed.length };
}
async function humanUncheck(match) {
  const w = (match || "").toLowerCase();
  const boxes = [...document.querySelectorAll("input[type=checkbox]")];
  for (const b of boxes) {
    const label = ((b.getAttribute("aria-label") || "") + " " + (b.parentElement ? b.parentElement.innerText : "") + "").toLowerCase();
    if (!w || label.includes(w)) {
      if (b.checked) { b.click(); await sleep(300); }
    }
  }
}

async function humanOpen(url, directive) {
  const u = (url + "").trim();
  if (!/^https:\/\//i.test(u)) return;
  const exactHosts = new Set([
    "www.linkedin.com", "mail.google.com", "drive.google.com", "mail.yahoo.com",
    "www.foundit.in", "www.naukri.com", "kdp.amazon.com", "web.whatsapp.com",
    "www.instagram.com", "www.facebook.com", "www.notion.so", "www.notion.com", "notion.so",
    "tasklet.ai", "www.youtube.com", "discord.com"
  ]);
  const wildcardHosts = ["indeed.com", "incometax.gov.in", "notion.so", "tasklet.ai", "discord.com", "yahoo.com", "google.com", "amazon.com", "foundit.in", "naukri.com"];
  const okHost = (h) => exactHosts.has(h) || wildcardHosts.some((suffix) => h.endsWith("." + suffix));
  let dst = null;
  try { dst = new URL(u); } catch (e) { return; }
  if (!okHost(dst.hostname)) return;
  if (!directive || !directive.directive_id) return;

  const pending = {
    directive_id: directive.directive_id,
    action: "open",
    source_url: location.href,
    expected_url: u,
    click_started_ms: Date.now(),
    click_started_at: new Date().toISOString(),
  };
  try { sessionStorage.setItem("kilo-pending-nav", JSON.stringify(pending)); } catch (e) {}
  try {
    await callWorker({
      type: "SET_PENDING_NAV",
      pending: { ...pending, tab_id: TAB_ID }
    }, 2500);
  } catch (e) {}
  try {
    const navResp = await callWorker({
      type: "NAVIGATE_TAB",
      url: u
    }, 3000);
    if (navResp && navResp.success) {
      return;
    }
  } catch (e) {}
  location.href = u;
}

async function humanHuntVideo(index) {
  try {
    const links = [...document.querySelectorAll(
      "ytd-rich-grid-media #video-title, ytd-video-renderer #video-title, " +
      "ytd-grid-video-renderer #video-title, a#video-title")].filter(
      a => a && a.href && a.href.includes("/watch"));
    if (!links.length || index >= links.length) return;
    const target = links[index];
    target.scrollIntoView({ block: "center" });
    target.click();
  } catch (e) {}
}

async function humanTranscript() {
  try {
    const expandBtn = document.querySelector(
      "#expand, ytd-video-secondary-info-renderer #expand, tp-yt-paper-button#expand, " +
      "ytd-text-inline-expander #expand");
    if (expandBtn) expandBtn.click();
    const moreBtn = document.querySelector(
      "#button-shape [aria-label*='More' i], ytd-menu-renderer #button, button[aria-label*='More actions' i]");
    if (moreBtn) moreBtn.click();
    const items = [...document.querySelectorAll(
      "tp-yt-paper-item, ytd-menu-service-item-renderer, yt-list-item-view-model")];
    const t = items.find(el => (el.innerText || "").toLowerCase().includes("transcript") ||
                               (el.innerText || "").toLowerCase().includes("show transcript"));
    if (t) t.click();
    const panel = document.querySelector(
      "ytd-transcript-renderer, ytd-engagement-panel-section-list-renderer[target-id='engagement-panel-searchable-transcript']");
    if (panel) panel.scrollIntoView({ block: "center" });
  } catch (e) {}
}

async function humanHunt(index) {
  try {
    const links = [...document.querySelectorAll("ytd-rich-grid-media #video-title, ytd-video-renderer #video-title, a#video-title")];
    if (!links.length || index >= links.length) return;
    const target = links[index];
    target.scrollIntoView({ block: "center" });
    target.click();
  } catch (e) {}
}

let pollCount = 0;
const POLL_INTERVAL_MS = isColdScope ? 30000 : 10000;
setInterval(() => { pollCount++; if (!isColdScope || pollCount % 3 === 1) poll(); }, POLL_INTERVAL_MS);
poll();
chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.type === "POLL_NOW") poll();
});
