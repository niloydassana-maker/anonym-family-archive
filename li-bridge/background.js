// Kilo Bridge service worker: relay messages and toolbar status (PNA-safe).
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ installed_at: new Date().toISOString() });
});
const RELAY = "http://127.0.0.1:8778";
const PENDING_NAV_PREFIX = "kilo-pending-navigation-";

function pendingNavKey(tabId) {
  return PENDING_NAV_PREFIX + String(tabId);
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
    if (u1.search && u1.search !== u2.search) return false;
    return true;
  } catch (e) {
    return false;
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.badge) {
    const t = new Date();
    const hh = String(t.getHours()).padStart(2, "0");
    const mm = String(t.getMinutes()).padStart(2, "0");
    try {
      if (chrome.action && chrome.action.setBadgeText) {
        const status = String(msg.badge);
        const text = /^(OK|ERR|GATE|WALL)$/.test(status) ? status : hh + mm;
        const color = status === "ERR" ? "#b91c1c" : (status === "GATE" || status === "WALL" ? "#b45309" : "#0a7d2c");
        chrome.action.setBadgeText({ text });
        chrome.action.setBadgeBackgroundColor({ color });
      }
    } catch (e) {}
  }
  if (msg && msg.type === "RELAY_EVENT") {
    const workerMessageReceivedMono = performance.now();
    const timingTrace = { ...(msg.timing_trace || {}), worker_message_received_at: new Date().toISOString() };
    const source = msg.payload || {};
    const sourcePage = source.page || {};
    const chromeTabId = sender && sender.tab && sender.tab.id;
    const payload = {
      ...source,
      timing_trace: timingTrace,
      page: chromeTabId === undefined ? sourcePage :
        { ...sourcePage, chromeTabId, chromeTabActive: Boolean(sender.tab.active) }
    };
    timingTrace.worker_fetch_started_at = new Date().toISOString();
    fetch(RELAY + "/event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(async (res) => {
        timingTrace.worker_http_response_at = new Date().toISOString();
        const data = await res.json();
        timingTrace.worker_response_parsed_at = new Date().toISOString();
        timingTrace.worker_fetch_elapsed_ms = Math.round((performance.now() - workerMessageReceivedMono) * 100) / 100;
        if (data && data.missionTab && chromeTabId !== undefined) {
          chrome.storage.local.set({ missionTabId: chromeTabId }).catch(() => {});
        }
        sendResponse({ status: "success", data, timing_trace: timingTrace });
      })
      .catch((err) => sendResponse({ status: "error", error: err.toString() }));
    return true;
  }
  // Navigation crosses origins, so content-script sessionStorage cannot carry
  // the directive nonce to the destination. Keep the short-lived handoff in
  // extension storage, keyed to the exact source Chrome tab.
  if (msg && msg.type === "SET_PENDING_NAV") {
    const tabId = (sender && sender.tab && sender.tab.id) || (msg.pending && msg.pending.tab_id) || "global";
    const pending = msg.pending && typeof msg.pending === "object" ? msg.pending : null;
    if (!pending || !pending.directive_id || !pending.expected_url) {
      sendResponse({ success: false, error: "invalid-navigation-handoff" });
      return false;
    }
    const storeObj = {
      [pendingNavKey(tabId)]: { ...pending, tab_id: tabId, stored_at: new Date().toISOString() },
      [pendingNavKey("global")]: { ...pending, tab_id: tabId, stored_at: new Date().toISOString() }
    };
    chrome.storage.local.set(storeObj)
      .then(() => sendResponse({ success: true }))
      .catch((err) => sendResponse({ success: false, error: String(err) }));
    return true;
  }
  if (msg && msg.type === "GET_PENDING_NAV") {
    const tabId = (sender && sender.tab && sender.tab.id) || "global";
    const currentUrl = String(msg.url || "");
    chrome.storage.local.get([pendingNavKey(tabId), pendingNavKey("global")]).then((data) => {
      const pending = (data && data[pendingNavKey(tabId)]) || (data && data[pendingNavKey("global")]);
      if (!pending || !urlsMatch(pending.expected_url, currentUrl)) {
        sendResponse({ pending: null });
        return;
      }
      const age = Date.now() - Date.parse(pending.stored_at || "");
      if (!Number.isFinite(age) || age < 0 || age > 5 * 60 * 1000) {
        chrome.storage.local.remove([pendingNavKey(tabId), pendingNavKey("global")]).catch(() => {});
        sendResponse({ pending: null, error: "navigation-handoff-expired" });
        return;
      }
      sendResponse({ pending });
    }).catch((err) => sendResponse({ pending: null, error: String(err) }));
    return true;
  }
  if (msg && msg.type === "CLEAR_PENDING_NAV") {
    const tabId = sender && sender.tab && sender.tab.id;
    if (!Number.isInteger(tabId)) { sendResponse({ success: false, error: "unknown-tab" }); return false; }
    chrome.storage.local.get(pendingNavKey(tabId)).then((data) => {
      const pending = data && data[pendingNavKey(tabId)];
      if (pending && pending.directive_id === msg.directive_id) {
        return chrome.storage.local.remove(pendingNavKey(tabId));
      }
    }).then(() => sendResponse({ success: true })).catch((err) => sendResponse({ success: false, error: String(err) }));
    return true;
  }
  if (msg && msg.type === "NAVIGATE_TAB" && msg.url) {
    const tabId = (sender && sender.tab && sender.tab.id) || (Number.isInteger(msg.tabId) ? msg.tabId : null);
    const doUpdate = (targetTabId) => {
      chrome.tabs.update(targetTabId, { url: msg.url }, () => {
        if (chrome.runtime.lastError) {
          sendResponse({ success: false, error: chrome.runtime.lastError.message });
        } else {
          sendResponse({ success: true, tabId: targetTabId });
        }
      });
    };
    if (Number.isInteger(tabId)) {
      doUpdate(tabId);
    } else {
      chrome.storage.local.get("missionTabId").then(({ missionTabId }) => {
        if (Number.isInteger(missionTabId)) {
          doUpdate(missionTabId);
        } else {
          sendResponse({ success: false, error: "no-valid-tab-id" });
        }
      }).catch((err) => sendResponse({ success: false, error: String(err) }));
    }
    return true;
  }
  // Spare-tab discard (Baba order 2026-09-22, v2.4): content on any live
  // tab can ask the worker to discard tabs whose URL contains victim.
  // Worker never discards the ACTIVE tab (whatever Baba watches is safe).
  // Discard frees RAM; the tab stays in the strip and rehydrates on click.
  if (msg && msg.type === "DISCARD_SPARE" && msg.victim) {
    (async () => {
      try {
        const tabs = await chrome.tabs.query({});
        const want = String(msg.victim).toLowerCase();
        let n = 0;
        for (const t of tabs) {
          try {
            if (!t || !t.url || !t.url.toLowerCase().includes(want)) continue;
            if (t.active) continue;
            await chrome.tabs.discard(t.id);
            n++;
          } catch (e) {}
        }
        sendResponse({ success: true, discarded: n });
      } catch (e) {
        sendResponse({ success: false, error: e.toString() });
      }
    })();
    return true;
  }
  // v2.5 eyes (Baba order 2026-09-22): hands take screenshots. Content asks,
  // worker captures the visible tab and POSTs it to relay /shot for filing.
  if (msg && msg.type === "CAPTURE") {
    (async () => {
      try {
        const sourceTab = sender && sender.tab;
        if (!sourceTab || !Number.isInteger(sourceTab.id) || !Number.isInteger(sourceTab.windowId)) {
          return sendResponse({ success: false, error: "unknown-source-tab" });
        }
        const activeTabs = await chrome.tabs.query({ active: true, windowId: sourceTab.windowId });
        if (!activeTabs.some((tab) => tab.id === sourceTab.id)) {
          return sendResponse({ success: false, error: "mission-tab-not-visible" });
        }
        const url = await chrome.tabs.captureVisibleTab(sourceTab.windowId, { format: "jpeg", quality: 40 });
        const r = await fetch(RELAY + "/shot", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tabId: sourceTab.id, dataUrl: url })
        });
        const j = await r.json();
        sendResponse({ success: true, saved: j.saved || null });
      } catch (e) {
        sendResponse({ success: false, error: e.toString().slice(0, 120) });
      }
    })();
    return true;
  }
});

// Wake only the relay-confirmed mission tab. A message prompts its existing
// content script to poll; it never activates, navigates, or reloads the tab.
if (chrome.alarms) {
  chrome.runtime.onStartup.addListener(() => { chrome.alarms.create("kilo-beat", { periodInMinutes: 0.5 }); });
  chrome.runtime.onInstalled.addListener(() => { chrome.alarms.create("kilo-beat", { periodInMinutes: 0.5 }); });
  chrome.alarms.onAlarm.addListener((a) => {
    if (a && a.name === "kilo-beat") {
      fetch(RELAY + "/health").catch(() => {});
      chrome.storage.local.get("missionTabId").then(({ missionTabId }) => {
        if (Number.isInteger(missionTabId)) {
          chrome.tabs.sendMessage(missionTabId, { type: "POLL_NOW" }, () => {
            if (chrome.runtime.lastError) { /* tab may be discarded */ }
          });
        }
      }).catch(() => {});
    }
  });
  chrome.alarms.create("kilo-beat", { periodInMinutes: 0.5 });
}
