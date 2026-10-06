$ErrorActionPreference = 'Continue'
$dir = 'D:\anonym\delivery\kilo-bridge-setup'
$log = Join-Path $dir '_probe_lane.log'
"=== bounded lane probe $(Get-Date -Format o) ===" | Set-Content $log -Encoding UTF8
$job = Start-Job -ScriptBlock {
  param($wd, $script)
  Set-Location $wd
  & python $script 2>&1
} -ArgumentList $dir, (Join-Path $dir '_probe_lane_bounded.py')
$done = Wait-Job $job -Timeout 180
(Receive-Job $job | Out-String) | Add-Content $log -Encoding UTF8
if ($done) { "--- COMPLETED ---" | Add-Content $log -Encoding UTF8 }
else {
  "--- TIMEOUT 180s ---" | Add-Content $log -Encoding UTF8
  Stop-Job $job -ErrorAction SilentlyContinue
}
Remove-Job $job -Force -ErrorAction SilentlyContinue
"=== done $(Get-Date -Format o) ===" | Add-Content $log -Encoding UTF8