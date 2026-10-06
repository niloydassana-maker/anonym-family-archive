Write-Host '--- killing MY crush tree only ---'
$mine = @(22056, 10672, 10132, 14764)
foreach ($i in $mine) {
  $p = Get-Process -Id $i -ErrorAction SilentlyContinue
  if ($p) { Stop-Process -Id $i -Force -ErrorAction SilentlyContinue; Write-Host "killed $i ($($p.ProcessName))" }
  else { Write-Host "$i already gone" }
}
Start-Sleep -Seconds 2
Write-Host '--- survivors of MY tree ---'
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crush') } |
  Select-Object ProcessId,Name | Format-Table -AutoSize
$t = 'D:\anonym\war-log\sweep-browser.token'
if (Test-Path $t) { Write-Host ("token now: " + (Get-Content $t -Raw)) } else { Write-Host 'token absent' }