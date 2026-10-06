$ErrorActionPreference = 'Continue'
# kill previous hung probe tree (mine only)
foreach ($i in @(21256, 22412)) {
  $p = Get-Process -Id $i -ErrorAction SilentlyContinue
  if ($p) { Stop-Process -Id $i -Force -ErrorAction SilentlyContinue; Write-Host "killed $i" }
}
Start-Sleep -Seconds 1
Write-Host '--- survivors ---'
Get-Process python,node -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime | Format-Table -AutoSize
$t = 'D:\anonym\war-log\sweep-browser.token'
Write-Host ("token: " + (if (Test-Path $t) { (Get-Content $t -Raw) } else { 'ABSENT' }))