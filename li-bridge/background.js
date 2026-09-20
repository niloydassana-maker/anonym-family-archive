// Kilo Bridge service worker: keep-alive + toolbar badge + relay bridge (PNA-safe).
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
        chrome.action.setBadgeText({ text: hh + mm });
        chrome.action.setBadgeBackgroundColor({ color: "#0a7d2c" });
      }
    } catch (e) {}
  }
  if (msg && msg.type === "RELAY_EVENT") {
    fetch(RELAY + "/event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(msg.payload)
    })
      .then((res) => res.json())
      .then((data) => sendResponse({ status: "success", data }))
      .catch((err) => sendResponse({ status: "error", error: err.toString() }));
    return true;
  }
});

