// One Gmail editor reader for both observation and filling. Keep this small and
// independently testable: Gmail renders its hint inside an editable DIV.
(function (root) {
  const HINT = "Press / to write using your Gmail & Drive";
  const SELECTORS = [
    '[role="textbox"][g_editable="true"]',
    'div[contenteditable="true"][aria-label*="Message Body" i]',
    'div.Am.Al.editable[contenteditable="true"]',
    'div[contenteditable="true"][g_editable="true"]',
    'div[contenteditable="true"][role="textbox"]'
  ];

  function rawText(editor) {
    if (!editor) return "";
    return String(editor.value !== undefined ? editor.value :
      (editor.innerText !== undefined ? editor.innerText : editor.textContent || ""));
  }

  function meaningfulText(editor) {
    const raw = rawText(editor).replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
    const flat = raw.replace(/\u00a0/g, " ").replace(/\s+/g, " ");
    return flat === HINT ? "" : raw;
  }

  function findVisible(documentRef, isVisible) {
    for (const selector of SELECTORS) {
      const candidates = [...documentRef.querySelectorAll(selector)].filter(isVisible);
      if (!candidates.length) continue;
      const active = documentRef.activeElement;
      const activeCandidate = candidates.find((editor) => editor === active ||
        (active && editor.contains && editor.contains(active)));
      // Gmail can leave a visible placeholder editor alongside the saved
      // draft editor. Prefer active meaningful content, then the longest
      // meaningful candidate, so observation and filling use the same body.
      if (activeCandidate && meaningfulText(activeCandidate)) return activeCandidate;
      const meaningful = candidates.filter((editor) => meaningfulText(editor));
      if (meaningful.length) {
        return meaningful.sort((a, b) => rawText(b).length - rawText(a).length)[0];
      }
      return activeCandidate || candidates[candidates.length - 1];
    }
    return null;
  }

  const api = { findVisible, meaningfulText, rawText, HINT };
  root.KiloGmailEditor = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(globalThis);
