$t = 'D:\anonym\war-log\sweep-browser.token'
if (Test-Path $t) {
  Write-Host "--- token content ---"
  Get-Content $t -Raw
  $age = (Get-Date) - (Get-Item $t).LastWriteTime
  Write-Host "--- token age: $([int]$age.TotalSeconds)s ---"
} else { Write-Host 'token ABSENT' }
Write-Host '--- who is alive? ---'
Get-Process python,node -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime | Format-Table -AutoSize
Write-Host '--- my probe processes ---'
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
  Select-Object ProcessId,ParentProcessId,CommandLine | Format-List