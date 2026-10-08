# STANDALONE FULL-SETUP E2E TEST — 2026-10-06 (Baba: "test e2e using that standalone setup")

**Order:** *"does the powershell setup script is the standalone and the full fledged script?
Like it can do all the setup, full setup, agent360 setup, wiring with the open code, then
NVIDIA nim, API key integration, everything… we should test e2e using that standalone setup."*

## WHAT WAS BUILT
`kilo-bridge-setup.ps1` was stale — frozen in the **crush era** (engine = crush + Super-120B,
no Agent360-MCP config step, no NVIDIA-key-into-opencode step). It is now the one true
standalone. The crush-era original is preserved as `kilo-bridge-setup.CRUSH-ERA-20261006.ps1`.

**New chain (one script, one visible window):**
```
1 PREFLIGHT   node, python, @agent360/browser-mcp present, hermes node.exe, Chrome, opencode
2 NVIDIA NIM  key from env OR vault (nvidia_key.txt / clinic_brain / free_engine_pool.json),
              masked, set as User env, NEVER printed or logged
3 WIRE        scripts/_wire_opencode.py — idempotent config surgery on BOTH
              global (.config/opencode/opencode.jsonc) and project (D:\anonym\opencode.json):
              browser-mcp enabled, chrome-devtools disabled, model=Nemotron-550B,
              provider.nvidia options + model metadata, apiKey injected
4 VERIFY      opencode mcp list = browser-mcp CONNECTED + chrome-devtools DISABLED,
              debug config = resolved model
5 LIVE PROOF  opencode run -> Nemotron-550B -> browser-mcp_browser_list_tabs -> real JSON
              (disk-captured; inline stdout is lost on this box)
6 LAUNCH      (-Launch only) opens the mission window via launch-opencode-employment.ps1
VERDICT       GREEN only if the live proof passed
```

## E2E RESULT: PASSED
Run in its own visible window (window pid 22304), no `-Launch` (single test drive).
- Preflight: all checks green (node, python, agent360 index.js, hermes node.exe, Chrome, opencode 1.18.34).
- NVIDIA key: loaded from env (masked), injected into both configs.
- Wiring: **idempotent — semantic diff vs PRE-E2E backups = 0 removed / 0 lost.**
  - global: 1 value change = `provider.nvidia.options.apiKey` rotated to the vault key (intended).
  - project: 15 keys added = `chrome-devtools` disabled + full `provider.nvidia` block.
  - both configs re-parse as valid JSON after surgery.
- Verify: `opencode mcp list` = **browser-mcp ✓ connected**, **chrome-devtools ○ disabled**, 2 servers.
- **LIVE PROOF (the whole point):** `setup-live-proof.txt` =
  *"`browser_list_tabs` tool returned the raw JSON `{\"tabs\": [], …}`"* —
  stderr shows `> build · nvidia/nemotron-3-ultra-550b-a55b` then
  `⚙ browser-mcp_browser_list_tabs`. **opencode + Nemotron → Agent 360 fired, end to end,
  from inside the standalone setup.**

## THE ONE OPEN FACT (stated, not hidden)
The proof returned `tabs: []` — the MCP server answers and the tool executes, but the
Agent 360 **extension bridge has no Chrome tab attached** in this headless proof run. Before a
real employment sweep: `python war-log/launch_profile17.py` then `scripts/prove_lane.py`
must produce a PNG. The setup warns on this exact condition (does not claim a browser it did not see).

## FILES
- Setup: `delivery/kilo-bridge-setup/kilo-bridge-setup.ps1`
- Config helper: `scripts/_wire_opencode.py` (py_compile clean) + `scripts/_semantic_diff.py`
- Launcher: `launch-opencode-employment.ps1` (parse clean)
- Mission prompt: `evidence/employment-lane/OPENCODE-MISSION-PROMPT.txt`
- Proof: `evidence/employment-lane/setup-live-proof.txt` + `.err.txt`
- Backups: `*.PRE-E2E-20261006.bak` (both configs) + `*.bak-<ts>` (per-run, from step 3)
- Ledger: 2 new OK rows (wiring + full-standalone-e2e)

## HOW TO RUN
```powershell
powershell -ExecutionPolicy Bypass -File kilo-bridge-setup.ps1              # setup + live proof
powershell -ExecutionPolicy Bypass -File kilo-bridge-setup.ps1 -Launch      # + open mission window
powershell -ExecutionPolicy Bypass -File kilo-bridge-setup.ps1 -InstallMcp  # npm-install agent360 if absent
powershell -ExecutionPolicy Bypass -File kilo-bridge-setup.ps1 -Uninstall   # remove loop task
```

***Collected today: Rs 0.*** A wiring that fires is not a payment; the apply + recruiter
question flow is still the money step.