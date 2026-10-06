$ErrorActionPreference = 'Continue'
Set-Location 'D:\anonym\delivery\kilo-bridge-setup'
$log = Join-Path (Get-Location) '_crush_tool_test.log'
"=== crush tool-use test started $(Get-Date -Format o) ===" | Set-Content $log -Encoding UTF8
$prompt = 'Use your shell tool to run exactly this command: python _now.py  -- then report the raw CHARS: number you saw, nothing else. Do not explain. Do not repeat the instruction.'
$crushCmd = 'C:\Users\Admin\AppData\Local\hermes\node\crush.cmd'
$job = Start-Job -ScriptBlock {
  param($exe, $prmpt, $wd)
  Set-Location $wd
  $out = & $exe run --quiet -m nvidiafree/nvidia/nemotron-3-super-120b-a12b $prmpt 2>&1
  $out | Out-String
} -ArgumentList $crushCmd, $prompt, 'D:\anonym\delivery\kilo-bridge-setup'
$done = Wait-Job $job -Timeout 240
if ($done) {
  "--- JOB COMPLETED ---" | Add-Content $log -Encoding UTF8
  (Receive-Job $job | Out-String) | Add-Content $log -Encoding UTF8
} else {
  "--- TIMEOUT 240s ---" | Add-Content $log -Encoding UTF8
  (Receive-Job $job | Out-String) | Add-Content $log -Encoding UTF8
  Stop-Job $job -ErrorAction SilentlyContinue
}
Remove-Job $job -Force -ErrorAction SilentlyContinue
"=== test done $(Get-Date -Format o) ===" | Add-Content $log -Encoding UTF8