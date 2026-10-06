Write-Host '--- kill my hung micro/probe trees ---'
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match '_token_micro|_probe_lane|_remove_test' } |
  ForEach-Object { Write-Host "killing $($_.ProcessId)  $($_.CommandLine)"; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1
Write-Host '--- surviving python ---'
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
  Select-Object ProcessId,CommandLine | Format-List