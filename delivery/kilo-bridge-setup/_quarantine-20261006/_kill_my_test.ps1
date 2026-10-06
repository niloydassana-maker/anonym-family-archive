$mine = @(19844, 1904, 19976)
foreach ($i in $mine) {
  $p = Get-Process -Id $i -ErrorAction SilentlyContinue
  if ($p) { Stop-Process -Id $i -Force -ErrorAction SilentlyContinue; Write-Host "killed $i ($($p.ProcessName))" }
  else { Write-Host "$i already gone" }
}
Start-Sleep -Seconds 2
Write-Host '--- survivors ---'
Get-Process crush,python -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime | Format-Table -AutoSize
Write-Host '--- token ---'
$t = 'D:\anonym\delivery\kilo-bridge-setup\scripts\sweep-browser.token'
if (Test-Path $t) { Get-Content $t } else { 'NO TOKEN (clean)' }