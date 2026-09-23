// Kilo Bridge content script: observe the page without scrolling or focusing it.
// Explicit, gated directives may act in the one relay-selected work tab.
const RELAY = "http://127.0.0.1:8778";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const isYouTube = location.hostname.includes("youtube.com");
const isGmail = location.hostname.includes("mail.google.com");
const isNaukri = location.hostname.includes("naukri.com");
const isFoundit = location.hostname.includes("foundit.in");
const isLinkedIn = location.hostname.includes("linkedin.com");
const isLinkedInMessaging = isLinkedIn && location.pathname.includes("/messaging/");
const isLinkedInServiceMarketplace = isLinkedIn && location.pathname.includes("/service-marketplace/");
const isYouTubeFeed = isYouTube && (location.pathname.startsWith("/feed") || location.pathname.startsWith("/channels"));
// Passive polling never scrolls, focuses, or activates a tab. Site actions
// may scroll only after a scoped directive reaches the pinned work tab.
const isColdScope = isYouTube || location.hostname.includes("instagram.com") || location.hostname.includes("facebook.com");
function kiloVisible(el) {
  try {
    const r = el.getBoundingClientRect();
    if (!r || r.width < 2 || r.height < 2) return false;
    const s = getComputedStyle(el);
    if (s.visibility === "hidden" || s.display === "none") return false;
    return true;
  } catch (e) { return false; }
}
function isWalledPage(body) {
  const title = String(document.title || "").toLowerCase();
  const lead = String(body || "").slice(0, 1200).toLowerCase();
  return /just a moment|attention required|security verification/.test(title) ||
    /additional verification required|verify (that )?you are human|checking your browser before accessing/.test(lead) ||
    (lead.includes("captcha") && /complete|solve|verify/.test(lead));
}
// Normal fill refuses meaningful existing text. Explicit fillforce/fillfast
// directives can replace it, but the relay must scope a repair to known text.
// One-shot insertion preserves spaces in Gmail and avoids background-tab timer
// throttling that made per-character insertion take minutes.
let FILL_FORCE = false;
// v2.2 serve-receipt (J3-lite, Pramit E2E): hands testify. LAST_ACT carries the
// previous poll's action outcome into the next snapshot so misses are visible
// instead of silent. No extra POSTs: reported stale-by-one-cycle, fine for forensics.
// v2.3 composer reach (Baba order 2026-09-22): Farjana modal textarea
// (placeholder "Let the client know why you are a good fit...") + LinkedIn
// thread/new composer variants. Plus testimony on the silent early-return.
let LAST_ACT = null;

// Generate stable tab ID for this session (persists across refreshes via sessionStorage)
let TAB_ID = sessionStorage.getItem("kilo-tab-id");
if (!TAB_ID) {
  TAB_ID = "tab-" + Math.random().toString(36).slice(2, 10) + "-" + Date.now().toString(36);
  sessionStorage.setItem("kilo-tab-id", TAB_ID);
}

// Versioned localStorage key to ignore stale entries from previous runs.
// Scoped by hostname + first path segment so same-host pages (LinkedIn
// feed/messaging/notifications, YouTube feed/watch) elect SEPARATE primaries
// instead of flapping one shared key every 45s.
const LS_VERSION = "v4";
const PRIMARY_LEASE_MS = 3 * 60 * 1000;
const PRIMARY_SCOPE = () => {
  const seg = (location.pathname || "/").split("/").filter(Boolean)[0] || "_root";
  return location.hostname + "/" + seg;
};
const PRIMARY_KEY = (hostname) => "kilo-tab-primary-" + LS_VERSION + "-" + PRIMARY_SCOPE();

// One primary per scope. A live owner renews its lease on each poll; a stalled
// owner can be replaced after three minutes.
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

function isVisibleEnabled(el) {
  if (!el || el.disabled || el.getAttribute("aria-disabled") === "true" || el.hidden) return false;
  try {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" &&
      el.getClientRects().length > 0 && rect.width >= 2 && rect.height >= 2;
  } catch (e) {
    return false;
  }
}

function gmailVisibleEditor() {
  if (!isGmail) return false;
  return KiloGmailEditor.findVisible(document, isVisibleEnabled);
}
function gmailComposeOpen() {
  return Boolean(gmailVisibleEditor());
}

async function snapshot() {
  const url = location.href;
  const title = document.title;
  let body = "";
  try { body = document.body.innerText.slice(0, 6000); } catch (e) { body = "READ-ERR " + e; }
  // Primary election via localStorage (shared across tabs)
  const hostname = location.hostname;
  const isPrimary = claimPrimary(hostname);
  const walled = isWalledPage(body);
  const buttons = [];
  const relevantActionPattern = /\b(reply(?: all)?|forward|send|compose|apply(?: now)?|submit(?: proposal)?|save|continue|next|respond)\b/i;
  try {
    document.querySelectorAll("button, a, input[type=submit], [role=button], [role=link]").forEach((b) => {
      if (!isVisibleEnabled(b)) return;
      const t = ((b.innerText || b.value || b.getAttribute("aria-label") || "") + "").trim().slice(0, 60);
      if (t) buttons.push(t);
    });
  } catch (e) {}
  // Site-specific button extraction for better triage
  let siteButtons = [];
  if (isNaukri) {
    try {
      document.querySelectorAll('a[href*="recruiter-action"], a[href*="RecruiterAction"], button, a').forEach((b) => {
        const t = ((b.innerText || b.getAttribute("aria-label") || b.getAttribute("title") || "") + "").trim().slice(0, 60);
        if (t && (t.toLowerCase().includes("recruiter") || t.toLowerCase().includes("view all") || t.toLowerCase().includes("load more") || t.toLowerCase().includes("apply") || t.toLowerCase().includes("save") || t.toLowerCase().includes("edit profile"))) {
          siteButtons.push({ text: t, type: "naukri-action" });
        }
      });
    } catch (e) {}
  }
  if (isFoundit) {
    try {
      document.querySelectorAll('button, a').forEach((b) => {
        const t = ((b.innerText || b.getAttribute("aria-label") || b.getAttribute("title") || "") + "").trim().slice(0, 60);
        if (t && (t.toLowerCase().includes("quick apply") || t.toLowerCase().includes("apply") || t.toLowerCase().includes("save") || t.toLowerCase().includes("view detail") || t.toLowerCase().includes("complete"))) {
          siteButtons.push({ text: t, type: "foundit-action" });
        }
      });
    } catch (e) {}
  }
  if (isLinkedInServiceMarketplace) {
    try {
      document.querySelectorAll('button, a').forEach((b) => {
        const t = ((b.innerText || b.getAttribute("aria-label") || b.getAttribute("title") || "") + "").trim().slice(0, 60);
        if (t && (t.toLowerCase().includes("view request") || t.toLowerCase().includes("submit proposal") || t.toLowerCase().includes("no thanks") || t.toLowerCase().includes("message"))) {
          siteButtons.push({ text: t, type: "sm-action" });
        }
      });
    } catch (e) {}
  }
  if (isLinkedInMessaging) {
    try {
      document.querySelectorAll('button[aria-label*="Compose" i], button[aria-label*="Send" i], div[role="textbox"][contenteditable="true"]').forEach((b) => {
        const t = ((b.innerText || b.getAttribute("aria-label") || b.getAttribute("title") || "") + "").trim().slice(0, 60);
        if (t) siteButtons.push({ text: t, type: "msg-action" });
      });
    } catch (e) {}
  }
  if (isLinkedIn && !isLinkedInMessaging && !isLinkedInServiceMarketplace) {
    try {
      document.querySelectorAll('button, a').forEach((b) => {
        const t = ((b.innerText || b.getAttribute("aria-label") || b.getAttribute("title") || "") + "").trim().slice(0, 60);
        if (t && (t.toLowerCase().includes("connect") || t.toLowerCase().includes("follow") || t.toLowerCase().includes("message") || t.toLowerCase().includes("apply") || t.toLowerCase().includes("save"))) {
          siteButtons.push({ text: t, type: "li-action" });
        }
      });
    } catch (e) {}
  }
  if (isGmail) {
    try {
      document.querySelectorAll("button, [role=button], [role=link], [data-tooltip]").forEach((b) => {
        if (!isVisibleEnabled(b)) return;
        const t = ((b.innerText || b.getAttribute("aria-label") || b.getAttribute("data-tooltip") || b.getAttribute("title") || "") + "").trim().slice(0, 60);
        if (t && relevantActionPattern.test(t) && !siteButtons.some((item) => item && item.text === t)) {
          siteButtons.push({ text: t, type: "gmail-action" });
        }
      });
    } catch (e) {}
  }
  // YouTube feed: include video titles/links for hunt targeting
  let videoLinks = [];
  if (isYouTubeFeed) {
    try {
      document.querySelectorAll("ytd-rich-grid-media #video-title, ytd-video-renderer #video-title, a#video-title").forEach((v) => {
        const href = v.href || v.getAttribute("href");
        const title = (v.innerText || v.getAttribute("aria-label") || "").trim();
        if (href && title) videoLinks.push({ title: title.slice(0, 120), url: href });
      });
    } catch (e) {}
  }
  const priorityButtonTexts = [];
  for (const item of [...buttons, ...siteButtons]) {
    const t = typeof item === "string" ? item : String((item && (item.text || item.label)) || "");
    if (t && relevantActionPattern.test(t) && !priorityButtonTexts.includes(t)) priorityButtonTexts.push(t);
  }
  const snapshotButtons = [...new Set([...priorityButtonTexts, ...buttons])].slice(0, 80);
  // v2.2 composer flag (MProg E2E): Gmail compose box lives past the 6000-char
  // snapshot cut, so no text gate can ever verify it. Report openness directly.
  let composeOpen = false;
  try { composeOpen = gmailComposeOpen(); } catch (e) {}
  let composerText = "";
  try {
    const editor = gmailVisibleEditor();
    if (editor) composerText = KiloGmailEditor.meaningfulText(editor).slice(0, 1200);
  } catch (e) {}
  let bridgeVer = "2.11";
  try { bridgeVer = (chrome && chrome.runtime && chrome.runtime.getManifest && chrome.runtime.getManifest().version) || "2.11"; } catch (e) {}
  return { url, title, body, buttons: snapshotButtons, siteButtons: siteButtons.slice(0,
30), videoLinks: videoLinks.slice(0, 20), tabId: TAB_ID, isPrimary, walled, composeOpen, composerText, lastAct: LAST_ACT, bridge: bridgeVer, ts: new
Date().toISOString() };
}
async function badge(text) {
  try { await chrome.runtime.sendMessage({ badge: text }); } catch (e) {}
}
// v2.5b hang guard (Baba order 2026-09-22): a worker call that never answers
// must NEVER freeze the poll loop (shot serve hung the Gmail tab). Every
// worker call races a timeout and resolves empty on silence.
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

  // Single-tab doctrine: a scoped directive must name the exact observed URL.
  // This is a client-side safety check in addition to relay-side matching.
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
    ...(Array.isArray(snap.siteButtons) ? snap.siteButtons : [])
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

  return "";
}
let POLL_IN_FLIGHT = false;
async function poll() {
  if (POLL_IN_FLIGHT) return;
  POLL_IN_FLIGHT = true;
  try {
    const snap = await snapshot();
    const res = await callWorker(
      { type: "RELAY_EVENT", payload: { page: snap, tabId: TAB_ID } }, 30000);
    if (!res || res.timeout || res.error || res.status !== "success") {
      const detail = (res && (res.error || (res.timeout && "worker-timeout"))) || "relay-no-response";
      LAST_ACT = { action: "relay", result: String(detail).slice(0, 120) };
      await badge("ERR");
      return;
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
      await humanClick(directive.text);
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
      await humanOpen(directive.url);
    } else if (directive && directive.action === "discard" && directive.match) {
      // v2.4 spare-tab discard: worker discards background tabs whose URL
      // contains match. This tab is untouched. Testimony carries the count.
      try {
        const r = await callWorker({ type: "DISCARD_SPARE", victim: directive.match }, 25000);
        LAST_ACT = { action: "discard", match: directive.match, result: "discarded:" + (r && r.discarded !== undefined ? r.discarded : "?") };
      } catch (e) { LAST_ACT = { action: "discard", match: directive.match || "", result: "error" }; }
    } else if (directive && directive.action === "shot") {
      // v2.5 eyes: worker captures the visible tab, files it at relay /shot.
      try {
        const r = await callWorker({ type: "CAPTURE" }, 25000);
        LAST_ACT = { action: "shot", result: (r && r.saved) ? ("saved:" + r.saved) : ("error:" + ((r && r.error) || (r && r.timeout ? "timeout" : "?"))) };
      } catch (e) { LAST_ACT = { action: "shot", result: "error" }; }
    } else if (directive && directive.action === "huntvideo" && isYouTube) {
      // v1.4: click a video card by index on ANY YouTube listing (feed, channel /videos, search).
      await humanHuntVideo(directive.index || 0);
    } else if (directive && directive.action === "transcript" && isYouTube) {
      // v1.4: on a /watch page, expand description + open transcript so the next
      // poll snapshot carries transcript text in body for claim extraction.
      await humanTranscript();
    } else if (directive && directive.action === "hunt" && isYouTubeFeed) {
      // YouTube hunt: click video by index from videoLinks array
      await humanHunt(directive.index || 0);
    }
    } catch (e) { LAST_ACT = { action: (directive && directive.action) || "?", result: "error:" + (e && e.message || e) }; }
    if (directive && directive.directive_id) {
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
async function humanClick(text) {
  const want = text.toLowerCase();
  // YouTube feed: direct video link click by title match
  if (isYouTubeFeed && want.includes("http")) {
    try {
      const links = [...document.querySelectorAll("ytd-rich-grid-media #video-title, ytd-video-renderer #video-title, a#video-title")];
      const match = links.find(l => (l.href || "").includes(want) || (l.innerText || "").toLowerCase().includes(want));
      if (match) {
        await sleep(1500 + Math.random() * 2000);
        match.scrollIntoView({ block: "center" });
        await sleep(800);
        match.click();
        LAST_ACT = { action: "click", text, result: "clicked", tag: (match.tagName || "?") + ".branch" };
        return;
      }
    } catch (e) {}
  }
  // Gmail: robust compose/send button selectors
  if (isGmail) {
    const gmailSelectors = [
      // Compose button
      '[gh="cm"]', '[role="button"][aria-label*="Compose" i]', '[data-tooltip*="Compose" i]',
      // Send button
      '[role="button"][aria-label*="Send" i]', '[data-tooltip*="Send" i]', 'div[role="button"][aria-label="Send"]',
      '[data-tooltip]',
      // Generic buttons
      'button', '[role="button"]'
    ];
    for (const sel of gmailSelectors) {
      try {
        const els = [...document.querySelectorAll(sel)];
        const match = els.find(el => {
          if (!isVisibleEnabled(el)) return false;
          const t = ((el.innerText || el.getAttribute("aria-label") || el.getAttribute("data-tooltip") || el.getAttribute("title") || "") + "").replace(/\s+/g, " ").trim().toLowerCase();
          return t === want;
        });
        if (match) {
          if (!isGmail) await sleep(1500 + Math.random() * 2000);
          match.scrollIntoView({ block: "center" });
          if (!isGmail) await sleep(800);
          if (!isVisibleEnabled(match)) {
            LAST_ACT = { action: "click", text, result: "target-lost-before-click", tag: (match.tagName || "?") + ".branch" };
            return;
          }
          match.click();
          const opensComposer = want === "reply" || want === "reply all" || want === "compose";
          if (opensComposer) await sleep(600);
          LAST_ACT = {
            action: "click", text,
            result: opensComposer ? (gmailComposeOpen() ? "composer-open" : "unverified") : "dispatched",
            tag: (match.tagName || "?") + ".branch", trusted: false
          };
          return;
        }
      } catch (e) {}
    }
    LAST_ACT = { action: "click", text, result: "target-not-found-or-not-visible" };
    return;
  }
  // Naukri: recruiter actions, profile actions, apply buttons
  if (isNaukri) {
    const naukriSelectors = {
      // Recruiter actions link (shows "25" or similar number)
      recruiterActions: ['a[href*="recruiter-actions"]', 'a[href*="RecruiterAction"]', 'a'],
      // View all / Load more
      viewAll: ['button', 'a', 'button', 'a'],
      // Apply / Quick Apply buttons on job cards
      apply: ['button', 'a', 'button', '.apply-button', '[data-ga-track*="apply"]'],
      // Save job
      save: ['button', 'button[aria-label*="Save"]', '.save-job'],
      // Profile edit / update
      editProfile: ['a[href*="edit-profile"]', 'button', 'a'],
      // Profile views / Recruiter actions count links
      profileStats: ['a[href*="profile-view"]', 'a[href*="recruiter-action"]']
    };
    for (const [category, selectors] of Object.entries(naukriSelectors)) {
      for (const sel of selectors) {
        try {
          const els = [...document.querySelectorAll(sel)];
          const match = els.find(el => {
            if (!isVisibleEnabled(el)) return false;
            const t = ((el.innerText || el.getAttribute("aria-label") || el.getAttribute("title") || "") + "").trim().toLowerCase();
            return t && (t.includes(want) || want.includes(t));
          });
          if (match) {
            await sleep(1500 + Math.random() * 2000);
            match.scrollIntoView({ block: "center" });
            await sleep(800);
            if (!isVisibleEnabled(match)) { LAST_ACT = { action: "click", text, result: "target-lost-before-click" }; return; }
            match.click();
            LAST_ACT = { action: "click", text, result: "clicked", tag: (match.tagName || "?") + ".branch" };
            return;
          }
        } catch (e) {}
      }
    }
  }
  // Foundit: Quick Apply, Save, profile actions
  if (isFoundit) {
    const founditSelectors = {
      quickApply: ['button', 'a', 'button.apply-btn', '.quick-apply-btn'],
      save: ['button', 'button[aria-label*="Save"]', '.save-job-btn'],
      apply: ['button', 'a', '.apply-button'],
      profileComplete: ['button', 'a', 'button'],
      viewDetails: ['a', 'button', 'a[href*="job-detail"]']
    };
    for (const [category, selectors] of Object.entries(founditSelectors)) {
      for (const sel of selectors) {
        try {
          const els = [...document.querySelectorAll(sel)];
          const match = els.find(el => {
            if (!isVisibleEnabled(el)) return false;
            const t = ((el.innerText || el.getAttribute("aria-label") || el.getAttribute("title") || "") + "").trim().toLowerCase();
            return t && (t.includes(want) || want.includes(t));
          });
          if (match) {
            await sleep(1500 + Math.random() * 2000);
            match.scrollIntoView({ block: "center" });
            await sleep(800);
            if (!isVisibleEnabled(match)) { LAST_ACT = { action: "click", text, result: "target-lost-before-click" }; return; }
            match.click();
            LAST_ACT = { action: "click", text, result: "clicked", tag: (match.tagName || "?") + ".branch" };
            return;
          }
        } catch (e) {}
      }
    }
  }
  // LinkedIn Service Marketplace: View request, Submit proposal
  if (isLinkedInServiceMarketplace) {
    const smSelectors = {
      viewRequest: ['button', 'a', '[data-test-view-request]', 'button'],
      submitProposal: ['button', 'a', 'button', '[data-test-submit-proposal]'],
      noThanks: ['button', 'a', '[data-test-decline]'],
      messageClient: ['button', 'a', '[data-test-message]']
    };
    for (const [category, selectors] of Object.entries(smSelectors)) {
      for (const sel of selectors) {
        try {
          const els = [...document.querySelectorAll(sel)];
          const match = els.find(el => {
            if (!isVisibleEnabled(el)) return false;
            const t = ((el.innerText || el.getAttribute("aria-label") || el.getAttribute("title") || "") + "").trim().toLowerCase();
            return t && (t.includes(want) || want.includes(t));
          });
          if (match) {
            await sleep(1500 + Math.random() * 2000);
            match.scrollIntoView({ block: "center" });
            await sleep(800);
            if (!isVisibleEnabled(match)) { LAST_ACT = { action: "click", text, result: "target-lost-before-click" }; return; }
            match.click();
            LAST_ACT = { action: "click", text, result: "clicked", tag: (match.tagName || "?") + ".branch" };
            return;
          }
        } catch (e) {}
      }
    }
  }
  // LinkedIn Messaging: Compose, Send, Reply
  if (isLinkedInMessaging) {
    const msgSelectors = {
      compose: ['button[aria-label*="Compose" i]', 'a[aria-label*="Compose" i]', '[data-test-compose]', 'button'],
      send: ['button[aria-label*="Send" i]', 'button[type="submit"]', '[data-test-send]', 'button'],
      replyBox: ['div[role="textbox"][contenteditable="true"]', 'div[aria-label*="Write a message" i]', '.msg-form__contenteditable'],
      attachment: ['button[aria-label*="Attach" i]', '[data-test-attachment]'],
      closeThread: ['button[aria-label*="Close" i]', '[data-test-close-thread]']
    };
    for (const [category, selectors] of Object.entries(msgSelectors)) {
      for (const sel of selectors) {
        try {
          const els = [...document.querySelectorAll(sel)];
          const match = els.find(el => {
            if (!isVisibleEnabled(el)) return false;
            const t = ((el.innerText || el.getAttribute("aria-label") || el.getAttribute("title") || "") + "").trim().toLowerCase();
            return t && (t.includes(want) || want.includes(t));
          });
          if (match) {
            await sleep(1500 + Math.random() * 2000);
            match.scrollIntoView({ block: "center" });
            await sleep(800);
            if (!isVisibleEnabled(match)) { LAST_ACT = { action: "click", text, result: "target-lost-before-click" }; return; }
            match.click();
            LAST_ACT = { action: "click", text, result: "clicked", tag: (match.tagName || "?") + ".branch" };
            return;
          }
        } catch (e) {}
      }
    }
  }
  // LinkedIn Feed/General: Connect, Follow, Message, Apply
  if (isLinkedIn && !isLinkedInMessaging && !isLinkedInServiceMarketplace) {
    const liSelectors = {
      connect: ['button', 'button[aria-label*="Connect" i]', '.artdeco-button--primary'],
      follow: ['button', 'button[aria-label*="Follow" i]'],
      message: ['button', 'a[aria-label*="Message" i]', 'button'],
      apply: ['button', 'a[aria-label*="Apply" i]', '[data-test-apply-button]'],
      save: ['button[aria-label*="Save" i]', 'button'],
      more: ['button[aria-label*="More" i]', 'button', '[data-test-more-actions]']
    };
    for (const [category, selectors] of Object.entries(liSelectors)) {
      for (const sel of selectors) {
        try {
          const els = [...document.querySelectorAll(sel)];
          const match = els.find(el => {
            if (!isVisibleEnabled(el)) return false;
            const t = ((el.innerText || el.getAttribute("aria-label") || el.getAttribute("title") || "") + "").trim().toLowerCase();
            return t && (t.includes(want) || want.includes(t));
          });
          if (match) {
            await sleep(1500 + Math.random() * 2000);
            match.scrollIntoView({ block: "center" });
            await sleep(800);
            if (!isVisibleEnabled(match)) { LAST_ACT = { action: "click", text, result: "target-lost-before-click" }; return; }
            match.click();
            LAST_ACT = { action: "click", text, result: "clicked", tag: (match.tagName || "?") + ".branch" };
            return;
          }
        } catch (e) {}
      }
    }
  }
  // Widest net: thread rows are often plain divs. Take the deepest (most specific) match.
  // v2.1 forensic fix (MProg E2E): hidden menu items with matching text used to
  // win over the visible pill. Only VISIBLE elements may be clicked.
  const els = [...document.querySelectorAll("button, a, [role=button], [role=link], [role=option], li, h1, h2, h3, span, div, input[type=radio], input[type=checkbox], select, option")];
  const matches = els.filter((b) => {
    const t = ((b.innerText || b.getAttribute("aria-label") || "") + "").trim().toLowerCase();
    return t && t.includes(want) && t.length < want.length + 120 && isVisibleEnabled(b);
  });
  if (!matches.length) { LAST_ACT = { action: "click", text, result: "nomatch" }; return; }
  matches.sort((a, b) => ((a.innerText || "").length) - ((b.innerText || "").length));
  const el = matches[0];
  if (!isGmail) await sleep(1500 + Math.random() * 2000);
  try { el.scrollIntoView({ block: "center" }); } catch (e) {}
  if (!isGmail) await sleep(800);
  try {
    if (!isVisibleEnabled(el)) { LAST_ACT = { action: "click", text, result: "target-lost-before-click" }; return; }
    el.click();
    LAST_ACT = { action: "click", text, result: "clicked", tag: (el.tagName || "?") + "." + ((el.className || "") + "").toString().slice(0, 40) };
  } catch (e) { LAST_ACT = { action: "click", text, result: "error:" + (e && e.message || e) }; }
}
async function humanFill(match, text) {
  // Gmail: robust compose area targeting (to, subject, body)
  if (isGmail) {
    const gmailComposeSelectors = {
      to: ['[name="to"]', 'input[aria-label*="To" i]', 'textarea[aria-label*="To" i]', '[role="combobox"][aria-label*="To" i]'],
      subject: ['[name="subjectbox"]', 'input[aria-label*="Subject" i]', 'input[name="subject"]'],
      body: []
    };
    if (match) {
      const w = match.toLowerCase();
      for (const [field, selectors] of Object.entries(gmailComposeSelectors)) {
        if (field === w || w.includes(field)) {
          if (field === "body") {
            const editor = gmailVisibleEditor();
            if (editor) return fillElement(editor, text);
            LAST_ACT = { action: "fill", result: "gmail-editor-not-found" };
            return;
          }
          for (const sel of selectors) {
            try {
              const el = [...document.querySelectorAll(sel)].find(isVisibleEnabled);
              if (el) return fillElement(el, text);
            } catch (e) {}
          }
        }
      }
    }
  }
  // Naukri: application forms, profile fields, search
  if (isNaukri) {
    const naukriFillSelectors = {
      // Job search
      search: ['input[placeholder*="job title" i]', 'input[placeholder*="skill" i]', 'input[name="keyword"]', '#keywordSugg', 'input[aria-label*="Search" i]'],
      location: ['input[placeholder*="location" i]', 'input[name="location"]', '#locationSugg'],
      experience: ['input[placeholder*="experience" i]', 'select[name="experience"]', 'input[aria-label*="Experience" i]'],
      salary: ['input[placeholder*="salary" i]', 'input[name="salary"]'],
      // Application form fields
      name: ['input[name*="name" i]', 'input[placeholder*="Name" i]', 'input[aria-label*="Name" i]'],
      email: ['input[name*="email" i]', 'input[type="email"]', 'input[placeholder*="Email" i]'],
      phone: ['input[name*="phone" i]', 'input[name*="mobile" i]', 'input[placeholder*="Phone" i]', 'input[placeholder*="Mobile" i]'],
      coverLetter: ['textarea[name*="cover" i]', 'textarea[placeholder*="Cover" i]', 'textarea[aria-label*="Cover" i]', 'div[contenteditable="true"][aria-label*="Cover" i]'],
      resume: ['input[type="file"][accept*="pdf"]', 'input[type="file"][name*="resume" i]', 'input[aria-label*="Resume" i]'],
      // Profile edit
      headline: ['input[name*="headline" i]', 'textarea[name*="headline" i]', 'input[placeholder*="Headline" i]'],
      summary: ['textarea[name*="summary" i]', 'div[contenteditable="true"][aria-label*="Summary" i]'],
      skills: ['input[placeholder*="Skill" i]', 'input[aria-label*="Skill" i]', 'input[name*="skill" i]']
    };
    if (match) {
      const w = match.toLowerCase();
      for (const [field, selectors] of Object.entries(naukriFillSelectors)) {
        if (field === w || w.includes(field)) {
          for (const sel of selectors) {
            try {
              const el = [...document.querySelectorAll(sel)].find(isVisibleEnabled);
              if (el) return fillElement(el, text);
            } catch (e) {}
          }
        }
      }
    }
  }
  // Foundit: search, application, profile
  if (isFoundit) {
    const founditFillSelectors = {
      search: ['input[placeholder*="job title" i]', 'input[placeholder*="role" i]', 'input[placeholder*="skill" i]', 'input[name="keyword"]', '#searchKeyword'],
      location: ['input[placeholder*="location" i]', 'input[name="location"]', '#searchLocation'],
      experience: ['input[placeholder*="experience" i]', 'select[name="experience"]', 'input[aria-label*="Experience" i]'],
      name: ['input[name*="name" i]', 'input[placeholder*="Name" i]'],
      email: ['input[type="email"]', 'input[name*="email" i]', 'input[placeholder*="Email" i]'],
      phone: ['input[name*="phone" i]', 'input[name*="mobile" i]', 'input[placeholder*="Phone" i]'],
      coverLetter: ['textarea[name*="cover" i]', 'textarea[placeholder*="Cover" i]', 'div[contenteditable="true"][aria-label*="Cover" i]'],
      resume: ['input[type="file"][accept*="pdf"]', 'input[type="file"][name*="resume" i]']
    };
    if (match) {
      const w = match.toLowerCase();
      for (const [field, selectors] of Object.entries(founditFillSelectors)) {
        if (field === w || w.includes(field)) {
          for (const sel of selectors) {
            try {
              const el = [...document.querySelectorAll(sel)].find(isVisibleEnabled);
              if (el) return fillElement(el, text);
            } catch (e) {}
          }
        }
      }
    }
  }
  // LinkedIn Service Marketplace: proposal fields
  if (isLinkedInServiceMarketplace) {
    const smFillSelectors = {
      proposal: ['textarea[placeholder*="proposal" i]', 'textarea[name*="proposal" i]', 'div[contenteditable="true"][aria-label*="Proposal" i]', 'textarea[aria-label*="Proposal" i]', 'textarea[placeholder*="good fit" i]', 'textarea[aria-label*="Your proposal" i]', 'div[role="dialog"] textarea', 'div[contenteditable="true"][aria-label*="Your proposal" i]'],
      price: ['input[placeholder*="price" i]', 'input[name*="price" i]', 'input[aria-label*="Price" i]', 'input[type="number"][name*="budget" i]'],
      timeline: ['input[placeholder*="timeline" i]', 'input[name*="timeline" i]', 'select[name*="timeline" i]', 'input[aria-label*="Timeline" i]'],
      coverLetter: ['textarea[placeholder*="cover" i]', 'textarea[name*="cover" i]', 'div[contenteditable="true"][aria-label*="Cover" i]']
    };
    if (match) {
      const w = match.toLowerCase();
      for (const [field, selectors] of Object.entries(smFillSelectors)) {
        if (field === w || w.includes(field)) {
          for (const sel of selectors) {
            try {
              const el = [...document.querySelectorAll(sel)].find(isVisibleEnabled);
              if (el) return fillElement(el, text);
            } catch (e) {}
          }
        }
      }
    }
  }
  // LinkedIn Messaging: message compose
  if (isLinkedInMessaging) {
    const msgFillSelectors = {
      message: ['div[role="textbox"][contenteditable="true"]', 'div[aria-label*="Write a message" i]', '.msg-form__contenteditable', 'div[contenteditable="true"][data-placeholder*="message" i]', 'div[contenteditable="true"][aria-label*="Message" i]', 'form div[contenteditable="true"]'],
      subject: ['input[placeholder*="Subject" i]', 'input[name*="subject" i]', 'input[aria-label*="Subject" i]']
    };
    if (match) {
      const w = match.toLowerCase();
      for (const [field, selectors] of Object.entries(msgFillSelectors)) {
        if (field === w || w.includes(field)) {
          for (const sel of selectors) {
            try {
              const el = [...document.querySelectorAll(sel)].find(isVisibleEnabled);
              if (el) return fillElement(el, text);
            } catch (e) {}
          }
        }
      }
    }
  }
  // LinkedIn General: connection note, search
  if (isLinkedIn && !isLinkedInMessaging && !isLinkedInServiceMarketplace) {
    const liFillSelectors = {
      connectNote: ['textarea[placeholder*="note" i]', 'textarea[name*="note" i]', 'textarea[aria-label*="Note" i]', 'div[contenteditable="true"][aria-label*="Note" i]'],
      search: ['input[placeholder*="Search" i]', 'input[aria-label*="Search" i]', 'input[name="search"]', '.search-global-typeahead__input'],
      message: ['div[role="textbox"][contenteditable="true"]', 'div[aria-label*="Message" i]', '.msg-form__contenteditable']
    };
    if (match) {
      const w = match.toLowerCase();
      for (const [field, selectors] of Object.entries(liFillSelectors)) {
        if (field === w || w.includes(field)) {
          for (const sel of selectors) {
            try {
              const el = [...document.querySelectorAll(sel)].find(isVisibleEnabled);
              if (el) return fillElement(el, text);
            } catch (e) {}
          }
        }
      }
    }
  }
  // Generic fallback (v2.5: visible-first. Hidden background
  // contenteditables - chat widgets, drafts - must never win over the
  // box Baba watches. Baba screenshot 1904 proved a hidden DIV blocked
  // an empty Gmail composer.)
  const areas = [...document.querySelectorAll("textarea, input[type=text], input[type=email], input:not([type]), [contenteditable=true]")];
  const visAreas = areas.filter((a) => kiloVisible(a));
  const pool = visAreas;
  let el = null;
  if (match) {
    const w = match.toLowerCase();
    el = pool.find((a) => ((a.placeholder || a.getAttribute("aria-label") || a.name || "") + "").toLowerCase().includes(w)) || null;
  }
  if (!el) {
    const editables = pool.filter((a) => a.isContentEditable);
    el = (editables.length ? editables[editables.length - 1] : pool[0]) || null;
  }
  if (!el) { LAST_ACT = { action: "fill", match: match || "", result: "nomatch" }; return; }
  return fillElement(el, text);
}

async function fillElement(el, text) {
  el.focus();
  LAST_ACT = { action: "fill", result: "started", tag: el.tagName || "?" };
  const cur = el.value !== undefined ? el.value : el.innerText;
  const gmailBodyEditor = isGmail && (el.isContentEditable ||
    (el.getAttribute && el.getAttribute("g_editable") === "true"));
  // Gmail's one-shot path must not depend on background-tab timers. The old
  // pacing sleeps could stall the poll loop while Gmail was being refreshed.
  if (!gmailBodyEditor) await sleep(600);
  const meaningfulCur = gmailBodyEditor
    ? KiloGmailEditor.meaningfulText(el)
    : String(cur || "").replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
  if (!FILL_FORCE && meaningfulCur.length > 0) { LAST_ACT = { action: "fill", result: "skipped-nonempty", tag: el.tagName || "?", chars: meaningfulCur.length }; return; } // never overwrite human text (default)
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
  // One-shot set is the normal path. The old per-character innerText rewrite
  // discarded trailing spaces on every assignment and stalled in hidden tabs.
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
  const observed = gmailBodyEditor ? KiloGmailEditor.meaningfulText(el) : String(el.value !== undefined ? el.value : el.innerText || "");
  const comparable = (value) => String(value).replace(/\s+/g, " ").trim();
  LAST_ACT = { action: "fill", result: comparable(observed).includes(comparable(text)) ? "filled" : "unverified", tag: el.tagName || "?", chars: observed.length };
}
async function humanUncheck(match) {
  const w = (match || "").toLowerCase();
  const boxes = [...document.querySelectorAll("input[type=checkbox]")];
  for (const b of boxes) {
    const label = ((b.getAttribute("aria-label") || "") + " " + (b.parentElement ? b.parentElement.innerText : "") + "").toLowerCase();
    if (!w || label.includes(w)) {
      if (b.checked) { b.click(); await sleep(600); }
    }
  }
}
async function humanOpen(url) {
  // v1.1: the hand can WALK. https-only + bridge-territory allowlist (same
  // strictness as manifest host_permissions). match_url_substring still scopes
  // which page may launch the walk. Human-paced like every other action.
  const u = (url + "").trim();
  if (!/^https:\/\//i.test(u)) return;
  const exactHosts = new Set([
    "www.linkedin.com", "mail.google.com", "drive.google.com", "mail.yahoo.com",
    "www.foundit.in", "www.naukri.com", "kdp.amazon.com", "web.whatsapp.com",
    "www.instagram.com", "www.facebook.com", "www.notion.so", "www.notion.com", "notion.so",
    "tasklet.ai", "www.youtube.com", "discord.com"
  ]);
  const wildcardHosts = ["indeed.com", "incometax.gov.in", "notion.so", "tasklet.ai", "discord.com"];
  const okHost = (h) => exactHosts.has(h) || wildcardHosts.some((suffix) => h.endsWith("." + suffix));
  let dst = null;
  try { dst = new URL(u); } catch (e) { return; }
  if (!okHost(dst.hostname)) return;
  // v2.17: navigation itself is the scoped human-approved action. A timer
  // here can be suspended when Chrome backgrounds the pinned tab, leaving a
  // directive marked served with no navigation receipt.
  location.href = u;
}
async function humanHuntVideo(index) {
  // v1.4: click the index-th video card on any listing page. Selector covers
  // feed grids, channel /videos tabs, and search results. Navigates to /watch.
  try {
    const links = [...document.querySelectorAll(
      "ytd-rich-grid-media #video-title, ytd-video-renderer #video-title, " +
      "ytd-grid-video-renderer #video-title, a#video-title")].filter(
      a => a && a.href && a.href.includes("/watch"));
    if (!links.length || index >= links.length) return;
    const target = links[index];
    await sleep(1200 + Math.random() * 1500);
    try { target.scrollIntoView({ block: "center" }); } catch (e) {}
    await sleep(700);
    target.click();
  } catch (e) {}
}
async function humanTranscript() {
  // v1.4: expand description, open transcript panel, scroll it into view so the
  // snapshot body includes transcript lines for the claim pipeline.
  try {
    await sleep(2500);
    try {
      const expandBtn = document.querySelector(
        "#expand, ytd-video-secondary-info-renderer #expand, tp-yt-paper-button#expand, " +
        "ytd-text-inline-expander #expand");
      if (expandBtn) { expandBtn.click(); await sleep(1000); }
    } catch (e) {}
    try {
      const desc = document.querySelector("ytd-video-secondary-info-renderer, ytd-watch-metadata");
      if (desc) { desc.scrollIntoView({ block: "center" }); await sleep(600); }
    } catch (e) {}
    try {
      const moreBtn = document.querySelector(
        "#button-shape [aria-label*='More' i], ytd-menu-renderer #button, button[aria-label*='More actions' i]");
      if (moreBtn) { moreBtn.click(); await sleep(900); }
      const items = [...document.querySelectorAll(
        "tp-yt-paper-item, ytd-menu-service-item-renderer, yt-list-item-view-model")];
      const t = items.find(el => (el.innerText || "").toLowerCase().includes("transcript") ||
                                 (el.innerText || "").toLowerCase().includes("show transcript"));
      if (t) { t.click(); await sleep(2200); }
    } catch (e) {}
    try {
      const panel = document.querySelector(
        "ytd-transcript-renderer, ytd-engagement-panel-section-list-renderer[target-id='engagement-panel-searchable-transcript']");
      if (panel) { panel.scrollIntoView({ block: "center" }); await sleep(1200); }
    } catch (e) {}
  } catch (e) {}
}
async function humanHunt(index) {
  // YouTube hunt: click video at index, wait for page load, extract transcript/claims
  try {
    const links = [...document.querySelectorAll("ytd-rich-grid-media #video-title, ytd-video-renderer #video-title, a#video-title")];
    if (!links.length || index >= links.length) return;
    const target = links[index];
    await sleep(1500 + Math.random() * 2000);
    target.scrollIntoView({ block: "center" });
    await sleep(800);
    target.click();
    // Wait for video page to load
    await sleep(3000 + Math.random() * 2000);
    // Try to expand description and find transcript
    try {
      const expandBtn = document.querySelector('#expand, ytd-video-secondary-info-renderer #expand, tp-yt-paper-button#expand');
      if (expandBtn) { expandBtn.click(); await sleep(1000); }
    } catch (e) {}
    // Try to open transcript
    try {
      const moreBtn = document.querySelector('[aria-label*="More" i], ytd-menu-renderer');
      if (moreBtn) { moreBtn.click(); await sleep(800); }
      const transcriptBtn = [...document.querySelectorAll('tp-yt-paper-item, ytd-menu-service-item-renderer')].find(el => (el.innerText || "").toLowerCase().includes("transcript"));
      if (transcriptBtn) { transcriptBtn.click(); await sleep(2000); }
    } catch (e) {}
    // Report back with video page snapshot (next poll cycle will capture it)
  } catch (e) {}
}
// v2.0: cold scopes (YouTube/Instagram/Facebook) report ~every 10min.
// Hot lanes keep 45s. RAM discipline: fewer wakes, fewer discards.
let pollCount = 0;
setInterval(() => { pollCount++; if (!isColdScope || pollCount % 13 === 1) poll(); }, 45000);
poll();
chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.type === "POLL_NOW") poll();
});
