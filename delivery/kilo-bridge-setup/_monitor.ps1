Write-Host '--- lane processes ---'
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crush|agent360|_now\.py|prove_lane|job_discover|demo_keep') } |
  Select-Object ProcessId,Name,ParentProcessId,@{n='cmd';e={$_.CommandLine.Substring(0,[Math]::Min(105,$_.CommandLine.Length))}} |
  Format-List

Write-Host '--- browser token ---'
$t = 'D:\anonym\war-log\sweep-browser.token'
if (Test-Path $t) {
  Get-Content $t -Raw
  Write-Host ("age: {0:N0}s" -f ((Get-Date) - (Get-Item $t).LastWriteTime).TotalSeconds)
} else { Write-Host 'absent (no driver holding)' }

Write-Host '--- run log ---'
$l = 'D:\anonym\delivery\kilo-bridge-setup\evidence\employment-lane\crush-super120-run.log'
if (Test-Path $l) { Get-Content $l } else { Write-Host 'no run log' }

Write-Host '--- agent stdout (tail) ---'
$o = 'D:\anonym\delivery\kilo-bridge-setup\evidence\employment-lane\crush-super120-out.txt'
if (Test-Path $o) { Get-Content $o -Tail 25 } else { Write-Host 'no stdout yet' }

Write-Host '--- ledger tail ---'
$g = 'D:\anonym\delivery\kilo-bridge-setup\evidence\employment-lane\ledger.tsv'
if (Test-Path $g) { Write-Host ("lines: " + (Get-Content $g).Count) } else { Write-Host 'no ledger' }