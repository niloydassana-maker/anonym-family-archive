# Which model actually DRIVES? Same 3-step test across candidate drivers.
$ErrorActionPreference = 'Continue'
$LANE = 'D:\anonym\delivery\kilo-bridge-setup'
Set-Location $LANE
$crushCmd = 'C:\Users\Admin\AppData\Local\hermes\node\crush.cmd'
$prompt = 'Run these three commands IN ORDER, one tool call each: (1) cmd /c echo STEP-ONE (2) cmd /c echo STEP-TWO (3) cmd /c echo STEP-THREE. Then reply exactly: DONE. Do not summarize. Do not stop between calls.'

$cands = @(
  @{ tag='groq-oss120b';      model='groq/openai/gpt-oss-120b' },
  @{ tag='nv-llama32-11b';    model='nvidiafree/meta/llama-3.2-11b-vision-instruct' },
  @{ tag='nv-super120-low';   model='nvidiafree/nvidia/nemotron-3-super-120b-a12b'; extra='--reasoning-effort low' }
)

foreach ($c in $cands) {
  $log = Join-Path $LANE ("_drive_test_" + $c.tag + ".log")
  "=== $($c.tag)  model=$($c.model) $(Get-Date -Format o) ===" | Set-Content $log -Encoding UTF8
  $args = @('run','-q','-m',$c.model)
  if ($c.extra) { $args = @('run','-q','-m',$c.model) + ($c.extra -split ' ') }
  $args += $prompt
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  & $crushCmd @args 2>&1 | ForEach-Object { $_ | Add-Content -Path $log -Encoding UTF8 }
  $sw.Stop()
  ("=== exit={0} after {1:N0}s ===" -f $LASTEXITCODE, $sw.Elapsed.TotalSeconds) | Add-Content $log -Encoding UTF8
}
"ALL DRIVER TESTS DONE" | Add-Content (Join-Path $LANE '_drive_tests.done') -Encoding UTF8