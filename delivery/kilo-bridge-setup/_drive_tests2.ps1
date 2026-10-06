# Bind the DRIVER to the house-sanctioned reasoner (AGENTS.md 26.1:
# "driver = CRUSH CLI + reasoner = nvidia/deepseek-v4.1-flash FOREVER").
$ErrorActionPreference = 'Continue'
$LANE = 'D:\anonym\delivery\kilo-bridge-setup'
Set-Location $LANE
$crushCmd = 'C:\Users\Admin\AppData\Local\hermes\node\crush.cmd'
$prompt = 'Run these three commands IN ORDER, one tool call each: (1) cmd /c echo STEP-ONE (2) cmd /c echo STEP-TWO (3) cmd /c echo STEP-THREE. Then reply exactly: DONE. Do not summarize. Do not stop between calls.'

$cands = @(
  @{ tag='nv-deepseek41';     model='nvidiafree/deepseek-ai/deepseek-v4.1-flash' },
  @{ tag='nv-kimi-k3';        model='nvidiafree/moonshotai/kimi-k3' }
)
foreach ($c in $cands) {
  $log = Join-Path $LANE ("_drive_test_" + $c.tag + ".log")
  "=== $($c.tag)  model=$($c.model) $(Get-Date -Format o) ===" | Set-Content $log -Encoding UTF8
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  & $crushCmd run -q -m $c.model $prompt 2>&1 | ForEach-Object { $_ | Add-Content -Path $log -Encoding UTF8 }
  $sw.Stop()
  ("=== exit={0} after {1:N0}s ===" -f $LASTEXITCODE, $sw.Elapsed.TotalSeconds) | Add-Content $log -Encoding UTF8
}
"DRIVER2 DONE" | Add-Content (Join-Path $LANE '_drive_tests2.done') -Encoding UTF8