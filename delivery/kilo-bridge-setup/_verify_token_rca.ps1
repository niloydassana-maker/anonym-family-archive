Write-Host '--- is PID 11204 alive? ---'
$p = Get-CimInstance Win32_Process -Filter "ProcessId=11204" -ErrorAction SilentlyContinue
if ($p) { Write-Host "ALIVE: $($p.Name)  cmd=$($p.CommandLine)" } else { Write-Host 'PID 11204 = DEAD (does not exist)' }

Write-Host '--- probe stdout (STEAL prints here) ---'
foreach ($f in @('_probe_v2.out','_probe_v2.err')) {
  $full = Join-Path 'D:\anonym\delivery\kilo-bridge-setup' $f
  Write-Host "  [$f]"
  if (Test-Path $full) { $c = Get-Content $full -Raw; if ($c) { Write-Host $c } else { Write-Host '   (empty)' } }
  else { Write-Host '   (missing)' }
}

Write-Host '--- token file attributes ---'
$t = 'D:\anonym\war-log\sweep-browser.token'
if (Test-Path $t) { (Get-Item $t).Attributes } else { Write-Host 'absent' }

Write-Host '--- killing my probe tree (infinite loop) ---'
foreach ($i in @(7724,16432)) {
  $q = Get-Process -Id $i -ErrorAction SilentlyContinue
  if ($q) { Stop-Process -Id $i -Force -ErrorAction SilentlyContinue; Write-Host "killed $i" } else { Write-Host "$i gone" }
}
Start-Sleep -Seconds 1
Get-Process python -ErrorAction SilentlyContinue | Select-Object Id,StartTime | Format-Table -AutoSize