# STANDALONE SETUP - LIVE LAUNCH DRIVE RECEIPT (2026-10-06)

**Baba:** *"yes"* (fire the `-Launch` drive after the e2e passed).

Run: `kilo-bridge-setup.ps1 -Launch` in its own visible window (pid 6944).
Full chain, observed live in `evidence/employment-lane/opencode-employment-out.txt`:

## THE CHAIN, STEP BY STEP (all real, all disk-captured)
1. **Setup** — preflight OK, NVIDIA key injected, configs wired, verify = browser-mcp
   CONNECTED + chrome-devtools DISABLED, **live tool proof passed** (`setup-live-proof.txt`,
   23:49:29) → verdict GREEN.
2. **Mission window opened** — `launch-opencode-employment.ps1`, opencode pid **21264**
   (23:49:42), `invoking opencode run (nvidia/nvidia/nemotron-3-ultra-550b-a55b, --auto)`.
3. **Agent read the constitution in prompt order:** MISSION-RUN.txt → AGENTS-EMPLOYMENT.md
   → EMPLOYMENT-LANE-MISSION.md → PACE.md → ledger.tsv.
4. **Agent reasoned from the ledger:** profile already 100%, first NON-OK rows are the known
   dictionary rejections (Agentic AI / LangChain / chip cap 22). Identified the money step:
   *"The money step is next: apply to a MATCHED job."*
5. **Self-corrected two walls on its own** (no hand-holding):
   - relative path `war-log\launch_profile17.py` failed against cwd → located absolute
     `D:\anonym\war-log\launch_profile17.py`.
   - Python `await c.call_tool(...)` TypeError (returns dict) → read `agent360_client.py`
     and switched to the sync API (`c.start()` / `c.navigate()` / `c.list_tabs()`).
6. **Launched real Chrome Profile 17** (PID 17896) → Naukri recommended jobs.
7. **Agent 360 MCP confirmed live:** `serverInfo {"name":"agent360-browser","version":"1.30.0"}`;
   tab registered (the earlier `tabs: []` empty state resolved once Chrome attached).
8. **Drove to the logged-in Naukri page:**
   `NAV: {"title":"Recommended Jobs | Mynaukri","url":"https://www.naukri.com/mnjuser/recommendedjobs","tab_id":826635872}`
   and **read live page content**: *"Recommended jobs for you … GenAI Architect | Generative AI |
   LLM | RAG | Agentic AI — Connect iO …"*
9. **Proceeding to the apply flow:** *"Highest match is 'GenAI Architect' at Connectio It
   (score 10). Taking screenshot receipt, then clicking to apply."*

## VERDICT: THE STANDALONE SETUP IS FULL-FLEGGED AND E2E-PROVEN
One script did everything Baba asked for: **full setup + agent360 setup + opencode wiring +
NVIDIA NIM key integration + verify + live proof + launch** — and the launched agent actually
reached the logged-in Naukri apply flow in the real browser.

## OPEN (stated honestly)
- The **apply + in-flow recruiter question** (`lane_apply.py`) is still not a dedicated driver;
  the agent is driving it ad-hoc via `agent360_client`. That is the money step — watch for an
  APPLIED ledger row with a screenshot before calling any application "done".
- **Collected today: Rs 0.** Reaching the apply button is not an application; an application
  is not a payment. Screenshots decide.

## FILES
- Drive log: `opencode-employment-out.txt` / `opencode-employment-run.log`
- Live proof: `setup-live-proof.txt` (+ `.err.txt`)
- Launcher: `launch-opencode-employment.ps1` · Setup: `kilo-bridge-setup.ps1`