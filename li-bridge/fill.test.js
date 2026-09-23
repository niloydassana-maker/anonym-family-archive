const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const gmail = require("./gmail-editor.js");

// Exercise the actual content-script fill routine without starting its browser
// polling loop. A fake editable imitates Gmail dropping trailing spaces when a
// script rewrites innerText one character at a time.
const source = fs.readFileSync(path.join(__dirname, "content.js"), "utf8");
const functionSource = source.match(/async function fillElement\(el, text\) \{[\s\S]*?\n\}\n(?=async function humanUncheck)/)?.[0];
assert.ok(functionSource, "fillElement should be available for this test");

function fillRoutine(force = false) {
  const create = new Function("KiloGmailEditor", "Event", "sleep", "FILL_FORCE", `
    let LAST_ACT = null;
    const isGmail = true;
    ${functionSource}
    return async (element, text) => { await fillElement(element, text); return LAST_ACT; };
  `);
  return create(gmail, class Event { constructor(type) { this.type = type; } },
    async () => {}, force);
}

function editable(initial) {
  return {
    _text: initial, tagName: "DIV", isContentEditable: true,
    focus() {}, getAttribute(name) { return name === "g_editable" ? "true" : null; },
    dispatchEvent() {},
    get innerText() { return this._text; },
    set innerText(value) { this._text = String(value).replace(/ +$/gm, ""); }
  };
}

test("normal fill keeps internal spaces in a Gmail editor", async () => {
  const target = editable(gmail.HINT);
  const result = await fillRoutine()(target, "Hi Pooja,\n\nThank you for reaching out.");
  assert.equal(target.innerText, "Hi Pooja,\n\nThank you for reaching out.");
  assert.equal(result.result, "filled");
});

test("normal fill never replaces meaningful existing text", async () => {
  const target = editable("My own reply");
  const result = await fillRoutine()(target, "Hi Pooja");
  assert.equal(target.innerText, "My own reply");
  assert.equal(result.result, "skipped-nonempty");
});
