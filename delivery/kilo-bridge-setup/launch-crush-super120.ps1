# launch-crush-super120.ps1
#   Employment lane driver. Fixed 2026-10-06 after the token-hang RCA
#   (evidence/employment-lane/RCA-TOKEN-HANG-20261006.md):
#     * cwd is set EXPLICITLY to the lane root (crush resolves relative paths
#       - docs/, evidence/, scripts/ - against it; a wrong cwd = no mission files)
#     * a COLD sweep-browser.token is cleared defensively before start
#       (the client also self-heals now, but a clean start costs nothing)
#     * every run writes its own receipt so silence is never mistaken for work
$ErrorActionPreference = 'Continue'
$LANE = 'D:\anonym\delivery\kilo-bridge-setup'
$LOG  = Join-Path $LANE 'evidence\employment-lane\crush-super120-run.log'
Set-Location $LANE

function Note($m) {
  $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m
  Write-Host $line
  Add-Content -Path $LOG -Value $line -Encoding UTF8
}

Note "=== EMPLOYMENT LANE START (Super-120B) ==="
Note ("cwd = " + (Get-Location).Path)

# 1. defensive: neutralise a cold browser token (age > 300s is not a driver)
$tok = 'D:\anonym\war-log\sweep-browser.token'
if (Test-Path $tok) {
  $age = ((Get-Date) - (Get-Item $tok).LastWriteTime).TotalSeconds
  if ($age -gt 300) {
    try { Remove-Item $tok -Force -ErrorAction Stop; Note ("cleared COLD token (age {0:N0}s)" -f $age) }
    catch { Note ("could not remove cold token (age {0:N0}s) - client will overwrite-take it" -f $age) }
  } else {
    Note ("token present but FRESH (age {0:N0}s) - leaving it" -f $age)
  }
} else { Note "token absent (clean start)" }

# 2. mission
$mission = Join-Path $LANE 'MISSION-RUN.txt'
if (-not (Test-Path $mission)) { Note "ABORT: MISSION-RUN.txt missing"; exit 1 }
Note ("mission present: {0} bytes" -f (Get-Item $mission).Length)

$prompt = (@(
'You are the employment agent driving the REAL logged-in Chrome through scripts/agent360_client.py (Agent 360 MCP). ACT, do not summarize.',
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
'Resume from the first NON-OK row: Naukri Education / Career profile.',
'',
'NON-NEGOTIABLE:',
'- Browser actions ONLY via scripts/agent360_client.py. Never direct CDP, never Playwright/Selenium.',
'- The mouse path Input.dispatchMouseEvent TIMES OUT - use JS .click() and keyboard only.',
'- One screenshot per FIELD batched, not per keystroke.',
'- Append one ledger row per action to evidence/employment-lane/ledger.tsv as you go.',
'- BLOCKED beats a faked DONE. Never invent a fact - only the operator own pinned resume kilo_apply_resume.pdf is source material.',
'- Never spend money, never touch a login/password/OTP. ASCII only in submitted text.',
'- Work in this order: A. Naukri remaining profile fields  B. Naukri recommended jobs (gate on Job match score + Keysills)  C. Foundit  D. Indeed  E. LinkedIn (comments only - NEVER a link, a price, or self-promotion in a public comment).',
'',
'First real action: report the FIRST NON-OK ledger row you find, then begin that field.'
) -join ' ')

Note "invoking crush run (Super-120B) ..."
$OUTFILE = Join-Path $LANE 'evidence\employment-lane\crush-super120-out.txt'
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$crushCmd = 'C:\Users\Admin\AppData\Local\hermes\node\crush.cmd'
& $crushCmd run --quiet -m nvidiafree/nvidia/nemotron-3-super-120b-a12b $prompt 2>&1 |
  ForEach-Object {
    Write-Host $_
    Add-Content -Path $OUTFILE -Value $_ -Encoding UTF8
  }
$sw.Stop()
Note ("crush exited after {0:N0}s  exitcode={1}" -f $sw.Elapsed.TotalSeconds, $LASTEXITCODE)
Note "=== EMPLOYMENT LANE WINDOW DONE ==="
