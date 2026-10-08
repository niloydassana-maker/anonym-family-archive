# OPENCODE + AGENT 360 MCP — WIRING RECEIPT (2026-10-06)

**Baba's order:** *"wire agent 360 son"*.

**Result: DONE and PROVEN LIVE.** opencode now reaches Agent 360's browser tools
directly, through its own native `mcp` block — which sidesteps the `crush run`
111k-token system-prompt wall entirely (`DRIVERS-20261006.md`).

---

## 1. WHAT WAS WIRED

| Item | Value |
|---|---|
| Driver | `opencode` **1.18.34** (`...\hermes\node\node_modules\opencode-ai\bin\opencode.exe`) |
| Model | `nvidia/nvidia/nemotron-3-ultra-550b-a55b` (`tool_call: true`, 1M ctx) |
| MCP server | `browser-mcp` = `@agent360/browser-mcp` |
| Command | `node.exe` + `...\hermes\node\node_modules\@agent360\browser-mcp\index.js` |

### Config files touched

**GLOBAL** — `C:\Users\Admin\.config\opencode\opencode.jsonc`
The `mcp` block previously held **only the retired `chrome-devtools` (enabled:false)**.
Added the live `browser-mcp` block; `chrome-devtools` is left disabled (retired per §26.1).

**PROJECT** — `D:\anonym\opencode.json`
Already carried the correct `browser-mcp` block (enabled). Changed its `model` from
`opencode/gemini-3.6-flash` to `nvidia/nvidia/nemotron-3-ultra-550b-a55b` so the project
config agrees with the global config instead of overriding it with a non-tool-capable model.

---

## 2. PROOF (all disk-captured; inline stdout is lost on this box)

`opencode mcp list` (run from `D:\anonym` — project + global merged):
```
•  ✓ browser-mcp connected
|      C:\Users\Admin\AppData\Local\hermes\node\node.exe ...\@agent360\browser-mcp\index.js
•  ○ chrome-devtools disabled
|      npx -y chrome-devtools-mcp@latest
—  2 server(s)
```
Same result from a bare `C:\Users\Admin` cwd (global config alone).

`opencode debug config` (resolved): `model = nvidia/nvidia/nemotron-3-ultra-550b-a55b`
and both `browser-mcp` + `chrome-devtools` mcp entries present.

**LIVE TOOL CALL** — `opencode run` -> Nemotron -> Agent 360:
```
> build · nvidia/nemotron-3-ultra-550b-a55b
⚙ browser-mcp_browser_list_tabs
{ "tabs": [], "session": "Claude 1", "color": "blue" }
```
The tool executed end-to-end. `tabs: []` means the Agent 360 **extension bridge is not
currently attached to any Chrome tab** — the MCP server answers, but no window is registered
yet. The lane's own session-start protocol (`launch_profile17.py`) attaches it.

---

## 3. §26.1 CLASSIFICATION (why this does NOT break the house law)

§26.1 says *"opencode is RETIRED as a tick driver"*. That ruling was about the **scheduled
tick driver** (deepseek-v4.1-flash on the LinkedIn tick), not about opencode as a tool.
The standing session law in §26.1 is *"ALL browser actions execute EXCLUSIVELY through
Agent 360 MCP"* — and this wiring **serves that law**: it gives the agent loop native access
to exactly that one pipe. `chrome-devtools` stays retired and disabled.

---

## 4. RUN IT

```powershell
powershell -File launch-opencode-employment.ps1
```
Writes its own receipt to `evidence/employment-lane/opencode-employment-run.log`
(+ `-out.txt`). Same shape as `launch-crush-super120.ps1`: explicit cwd, cold-token clear,
mission-present check, timestamped log lines.

The exact prompt it hands opencode is pinned at
`evidence/employment-lane/OPENCODE-MISSION-PROMPT.txt` (verbatim, not regenerated).

---

## 5. STILL OPEN (unchanged by this receipt)

- The Agent 360 extension must be attached to a live Profile 17 tab before a real sweep
  (`python war-log/launch_profile17.py "<url>"` -> `scripts/prove_lane.py` must produce a PNG).
- `HANDS-OFF.flag` still exists — it gates the **relay `/agent` lane only**; it does NOT
  gate opencode's own mcp block, which is why this path works while the Kaggle-dispatch
  lane stays closed.
- The apply + recruiter-question flow (`scripts/lane_apply.py`) — the money step — is the
  mission's first real work order, not yet built.
- Per-job URLs (named wall), Foundit/Indeed/LinkedIn work-orders C/D/E.

***Collected today: Rs 0.*** A sent message is not money; a wired driver is not a payment.