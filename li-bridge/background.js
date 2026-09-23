// Kilo Bridge service worker: relay messages and toolbar status (PNA-safe).
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ installed_at: new Date().toISOString() });
});
const RELAY = "http://127.0.0.1:8778";

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
    const source = msg.payload || {};
    const sourcePage = source.page || {};
    const chromeTabId = sender && sender.tab && sender.tab.id;
    const payload = {
      ...source,
      page: chromeTabId === undefined ? sourcePage :
        { ...sourcePage, chromeTabId, chromeTabActive: Boolean(sender.tab.active) }
    };
    fetch(RELAY + "/event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then((res) => res.json())
      .then((data) => {
        if (data && data.missionTab && chromeTabId !== undefined) {
          chrome.storage.local.set({ missionTabId: chromeTabId }).catch(() => {});
        }
        sendResponse({ status: "success", data });
      })
      .catch((err) => sendResponse({ status: "error", error: err.toString() }));
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
