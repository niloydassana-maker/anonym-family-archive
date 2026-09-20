// Kilo Bridge content script: READ page, REPORT to local relay, ACT only on local directives.
// No visible DOM changes. No remote servers. Human-paced delays on every action.
const RELAY = "http://127.0.0.1:8778";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function snapshot() {
  const url = location.href;
  const title = document.title;
  let body = "";
  try { body = document.body.innerText.slice(0, 6000); } catch (e) { body = "READ-ERR " + e; }
  // Deep read: scroll main column stepwise, collect full list text (lists, search results, threads).
  try {
    const scroller = document.scrollingElement || document.body;
    const prevTop = scroller.scrollTop;
    let deep = "";
    for (let i = 0; i < 8; i++) {
      scroller.scrollTop = (i + 1) * 900;
      await sleep(350);
      const t = (document.body.innerText || "").slice(0, 15000);
      if (t.length > deep.length) deep = t;
      if (scroller.scrollTop + window.innerHeight + 200 >= scroller.scrollHeight) break;
    }
    scroller.scrollTop = prevTop;
    if (deep.length > body.length) body = deep.slice(0, 15000);
  } catch (e) {}
  if (!body || body.length < 500) {
    // Background-tab fallback: innerText needs layout; textContent does not.
    try {
      const clone = document.body.cloneNode(true);
      clone.querySelectorAll("script, style, noscript").forEach((n) => n.remove());
      body = (clone.textContent || "").replace(/\s+/g, " ").trim().slice(0, 6000);
    } catch (e) {}
  }
  const buttons = [];
  try {
    document.querySelectorAll("button, a, input[type=submit]").forEach((b) => {
      const t = ((b.innerText || b.value || b.getAttribute("aria-label") || "") + "").trim().slice(0, 60);
      if (t) buttons.push(t);
    });
  } catch (e) {}
  return { url, title, body, buttons: buttons.slice(0, 40), ts: new Date().toISOString() };
}
async function badge(text) {
  try { await chrome.runtime.sendMessage({ badge: text }); } catch (e) {}
}
async function poll() {
  try {
    const snap = await snapshot();
    const res = await new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(
        { type: "RELAY_EVENT", payload: { page: snap } },
        (response) => {
          if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
          else resolve(response);
        }
      );
    });
    await badge("OK");
    try {
      const t = new Date();
      document.title = "●" + String(t.getHours()).padStart(2, "0") + String(t.getMinutes()).padStart(2, "0") + " " + document.title.replace(/^●\d{4} /, "");
    } catch (e) {}
    const directive = res && res.data ? res.data : {};
    if (directive && directive.action === "click" && directive.text) {
      await humanClick(directive.text);
    } else if (directive && directive.action === "fill" && directive.text) {
      await humanFill(directive.match || "", directive.text);
    } else if (directive && directive.action === "uncheck" && directive.match) {
      await humanUncheck(directive.match);
    }
  } catch (e) { /* relay down: stay silent, retry next cycle */ }
}
async function humanClick(text) {
  const want = text.toLowerCase();
  // Widest net: thread rows are often plain divs. Take the deepest (most specific) match.
  const els = [...document.querySelectorAll("button, a, [role=button], [role=link], [role=option], li, h1, h2, h3, span, div, input[type=radio], input[type=checkbox], select, option")];
  const matches = els.filter((b) => {
    const t = ((b.innerText || b.getAttribute("aria-label") || "") + "").trim().toLowerCase();
    return t && t.includes(want) && t.length < want.length + 120;
  });
  if (!matches.length) return;
  matches.sort((a, b) => ((a.innerText || "").length) - ((b.innerText || "").length));
  const el = matches[0];
  await sleep(1500 + Math.random() * 2000);
  try { el.scrollIntoView({ block: "center" }); } catch (e) {}
  await sleep(800);
  el.click();
}
async function humanFill(match, text) {
  const areas = [...document.querySelectorAll("textarea, input[type=text], input[type=email], input:not([type]), [contenteditable=true]")];
  let el = null;
  if (match) {
    // Explicit match wins: test placeholder, aria-label, name, then text proximity.
    const w = match.toLowerCase();
    el = areas.find((a) => ((a.placeholder || a.getAttribute("aria-label") || a.name || "") + "").toLowerCase().includes(w)) || null;
  }
  if (!el) {
    // No match given: prefer the LAST contenteditable (message composers sit after search boxes).
    const editables = areas.filter((a) => a.isContentEditable);
    el = (editables.length ? editables[editables.length - 1] : areas[0]) || null;
  }
  if (!el) return;
  el.focus();
  await sleep(600);
  const cur = el.value !== undefined ? el.value : el.innerText;
  if (cur && cur.length > 0) return; // never overwrite human text
  for (const ch of text) {
    if (el.value !== undefined) el.value += ch;
    else el.innerText += ch;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    await sleep(25 + Math.random() * 45);
  }
  el.dispatchEvent(new Event("change", { bubbles: true }));
  await sleep(800);
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
setInterval(poll, 45000);
poll();
