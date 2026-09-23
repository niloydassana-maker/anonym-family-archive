const test = require("node:test");
const assert = require("node:assert/strict");
const editor = require("./gmail-editor.js");

test("Gmail's visible hint is not user-authored content", () => {
  assert.equal(editor.HINT.length, 41);
  assert.equal(editor.meaningfulText({ innerText: editor.HINT }), "");
  assert.equal(editor.meaningfulText({ innerText: `  ${editor.HINT}\u00a0` }), "");
});

test("real draft content is never classified as placeholder", () => {
  assert.equal(editor.meaningfulText({ innerText: "Hi Pooja,\nThanks for reaching out." }),
    "Hi Pooja,\nThanks for reaching out.");
  assert.equal(editor.meaningfulText({ innerText: `${editor.HINT} and my reply` }),
    `${editor.HINT} and my reply`);
});

test("read and write selection prefers the visible Gmail body textbox", () => {
  const hidden = { visible: false, innerText: "old hidden draft" };
  const body = { visible: true, innerText: editor.HINT };
  const other = { visible: true, innerText: "unrelated" };
  const doc = {
    activeElement: body,
    querySelectorAll(selector) {
      if (selector.includes('[role="textbox"][g_editable="true"]')) return [hidden, body];
      if (selector.includes('[role="textbox"]')) return [other];
      return [];
    }
  };
  assert.equal(editor.findVisible(doc, (element) => element.visible), body);
  assert.equal(editor.meaningfulText(editor.findVisible(doc, (element) => element.visible)), "");
});

test("no visible editor fails closed", () => {
  const doc = { activeElement: null, querySelectorAll: () => [{ visible: false }] };
  assert.equal(editor.findVisible(doc, (element) => element.visible), null);
});

test("saved draft wins over a visible placeholder editor", () => {
  const placeholder = { visible: true, innerText: editor.HINT };
  const saved = { visible: true, innerText: "Hi Pooja,\n\nSaved reply body" };
  const doc = {
    activeElement: placeholder,
    querySelectorAll: () => [placeholder, saved]
  };
  assert.equal(editor.findVisible(doc, (element) => element.visible), saved);
});
