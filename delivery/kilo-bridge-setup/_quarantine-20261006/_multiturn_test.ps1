# DECISIVE TEST: does `crush run` execute a MULTI-TURN tool loop?
# If yes -> the narration was a model behaviour (fix = model or prompt).
# If no  -> `crush run` is effectively single-shot and the lane needs a loop wrapper.
$ErrorActionPreference = 'Continue'
$LANE = 'D:\anonym\delivery\kilo-bridge-setup'
$LOG  = Join-Path $LANE '_multiturn_test.log'
Set-Location $LANE
"=== MULTI-TURN TOOL TEST $(Get-Date -Format o) ===" | Set-Content $LOG -Encoding UTF8

$crushCmd = 'C:\Users\Admin\AppData\Local\hermes\node\crush.cmd'
$prompt = 'Using your shell tool, run these three commands IN ORDER, one tool call each: (1) cmd /c echo STEP-ONE (2) cmd /c echo STEP-TWO (3) cmd /c echo STEP-THREE . Then reply with the single word DONE. Make three separate tool calls.'

$sw = [System.Diagnostics.Stopwatch]::StartNew()
& $crushCmd run -v -m nvidiafree/nvidia/nemotron-3-super-120b-a12b $prompt 2>&1 |
  ForEach-Object { $_ | Add-Content -Path $LOG -Encoding UTF8 }
$sw.Stop()
("=== exit={0} after {1:N0}s ===" -f $LASTEXITCODE, $sw.Elapsed.TotalSeconds) | Add-Content $LOG -Encoding UTF8