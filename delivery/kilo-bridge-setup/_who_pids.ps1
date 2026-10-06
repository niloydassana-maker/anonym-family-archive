$ids = @(1904, 19976)
foreach ($i in $ids) {
  $p = Get-CimInstance Win32_Process -Filter "ProcessId=$i" -ErrorAction SilentlyContinue
  if ($p) {
    Write-Host "PID $i parent=$($p.ParentProcessId) started=$($p.CreationDate)"
    Write-Host "  CMD: $($p.CommandLine)"
  } else {
    Write-Host "PID $i gone (already exited)"
  }
}
Write-Host '--- crush tree ---'
Get-CimInstance Win32_Process -Filter "Name='crush.exe'" -ErrorAction SilentlyContinue | ForEach-Object {
  Write-Host "crush PID $($_.ProcessId) parent=$($_.ParentProcessId)"
}
Write-Host '--- log ---'
Get-Content 'D:\anonym\delivery\kilo-bridge-setup\_crush_tool_test.log' -Raw