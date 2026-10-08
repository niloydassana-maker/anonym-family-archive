# launch-opencode-employment.ps1
#   Employment-lane driver #3, added 2026-10-06 after Agent 360 MCP was wired
#   into opencode (see evidence/employment-lane/OPENCODE-AGENT360-WIRING-20261006.md).
#
#   WHY opencode AND NOT crush:
#     crush's system prompt is 111,464 tokens - free endpoints answer HTTP 413 and
#     reasoning models reply with crush's context-summary schema instead of tool
#     calls (evidence/employment-lane/DRIVERS-20261006.md). opencode probes
#     nvidia/nvidia/nemotron-3-ultra-550b-a55b directly (tool_call=true, 1M ctx)
#     and reaches Agent 360 through its own native mcp block.
#
#   LAWS THIS OBEYS:
#     * cwd is set EXPLICITLY to the lane root - docs/, scripts/, evidence/ resolve there
#     * every run writes its own receipt (a run with no log did not happen)
#     * ACT, do not summarize: browser actions via scripts/agent360_client.py
$ErrorActionPreference = 'Continue'
$LANE = 'D:\anonym\delivery\kilo-bridge-setup'
$LOG  = Join-Path $LANE 'evidence\employment-lane\opencode-employment-run.log'
$OUT  = Join-Path $LANE 'evidence\employment-lane\opencode-employment-out.txt'
Set-Location $LANE

function Note($m) {
  $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m
  Write-Host $line
  Add-Content -Path $LOG -Value $line -Encoding UTF8
}

Note "=== EMPLOYMENT LANE START (opencode + Nemotron-550B) ==="
Note ("cwd = " + (Get-Location).Path)

# 1. defensive: neutralise a cold browser token (age > 300s is not a driver)
$tok = Join-Path $LANE 'war-log\sweep-browser.token'
if (Test-Path $tok) {
  $age = ((Get-Date) - (Get-Item $tok).LastWriteTime).TotalSeconds
  if ($age -gt 300) {
    try { Remove-Item $tok -Force -ErrorAction Stop; Note (("cleared COLD token (age {0:N0}s)" -f $age)) }
    catch { Note (("could not remove cold token (age {0:N0}s) - client will overwrite-take it" -f $age)) }
  } else { Note (("token present but FRESH (age {0:N0}s) - leaving it" -f $age)) }
} else { Note "token absent (clean start)" }

# 2. mission
$mission = Join-Path $LANE 'MISSION-RUN.txt'
if (-not (Test-Path $mission)) { Note "ABORT: MISSION-RUN.txt missing"; exit 1 }
Note (("mission present: {0} bytes" -f (Get-Item $mission).Length))

$py = Join-Path $LANE 'venv\Scripts\python.exe'

$prompt = (@(
'You are the employment agent driving the REAL logged-in Chrome through war-log/agent360_client.py (Agent 360 MCP). ACT, do not summarize.',
'',
'ALL ARTIFACTS ARE IN THE SETUP FOLDER: D:\anonym\delivery\kilo-bridge-setup\',
'- Python venv: venv\Scripts\python.exe (use for ALL python execution)',
'- Python scripts: war-log\agent360_client.py, war-log\launch_profile17.py',
'- Pinned resume: kilo_apply_resume.pdf (SHA256 DE81F585...FC339F, Author Kunal Das)',
'- Ledger: evidence\employment-lane\ledger.tsv',
'- Mission prompt: evidence\employment-lane\OPENCODE-MISSION-PROMPT.txt',
'',
'Read these files first, in order, and obey them:',
'1. MISSION-RUN.txt',
'2. docs/AGENTS-EMPLOYMENT.md   (the constitution: single browser pipe, named walls, the laws)',
'3. docs/EMPLOYMENT-LANE-MISSION.md  (the run-book)',
'4. docs/PACE.md  (how to run fast WITHOUT lying - obey hard)',
'5. evidence/employment-lane/ledger.tsv  (RESUME - every OK row is DONE, never redo it)',
'',
'Already done, do NOT repeat: Naukri profile read (100%, Kolkata, 22y, 32L, email+phone verified); key skills Generative AI + AI Agents added (chip count 22, cap 22); resume headline rewritten (221/250). Agentic AI and LangChain are NOT in Naukri dictionary - do not retry.',
'',
'Resume from the first NON-OK row. Then do the money step: open one MATCHED card, walk the apply flow, and ANSWER any in-flow recruiter question from the operator record.',
'',
'NON-NEGOTIABLE:',
'- Browser actions ONLY via the browser-mcp tools. Never direct CDP, never Playwright/Selenium, never chrome-devtools.',
'- The mouse path Input.dispatchMouseEvent TIMES OUT - use JS .click() and keyboard only.',
'- One screenshot per FIELD batched, not per keystroke.',
'- Append one ledger row per action to evidence/employment-lane/ledger.tsv as you go.',
'- BLOCKED beats a faked DONE. Never invent a fact - only the operator own pinned resume kilo_apply_resume.pdf is source material.',
'- Never spend money, never touch a login/password/OTP. ASCII only in submitted text.',
'- Work in this order: A. Naukri remaining profile fields  B. Naukri recommended jobs (gate on Job match score + Keysills)  C. Foundit  D. Indeed  E. LinkedIn (comments only - NEVER a link, a price, or self-promotion in a public comment).',
'',
'PYTHON EXECUTION RULE: ALWAYS use venv\Scripts\python.exe war-log\<script>.py',
'',
'First real action: report the FIRST NON-OK ledger row you find, then begin that field.'
) -join ' ')

$exe = 'C:\Users\Admin\AppData\Local\hermes\node\node_modules\opencode-ai\bin\opencode.exe'
if (-not (Test-Path $exe)) { Note "ABORT: opencode.exe not found at $exe"; exit 1 }

Note "invoking opencode run (nvidia/nvidia/nemotron-3-ultra-550b-a55b, --auto) ..."
$sw = [System.Diagnostics.Stopwatch]::StartNew()
& $exe run --auto -m 'nvidia/nvidia/nemotron-3-ultra-550b-a55b' $prompt 2>&1 |
  ForEach-Object {
    Write-Host $_
    Add-Content -Path $OUT -Value $_ -Encoding UTF8
  }
$sw.Stop()
Note (("opencode exited after {0:N0}s  exitcode={1}" -f $sw.Elapsed.TotalSeconds, $LASTEXITCODE))
Note "=== EMPLOYMENT LANE WINDOW DONE ==="