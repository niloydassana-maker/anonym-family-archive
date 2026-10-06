Write-Host '=== DRIVE TEST STATE ==='
foreach ($f in @('_drive_test_nv-deepseek41.log','_drive_test_nv-kimi-k3.log','_drive_tests2.done')) {
  $p = Join-Path 'D:\anonym\delivery\kilo-bridge-setup' $f
  if (Test-Path $p) {
    Write-Host ("[{0}] {1} bytes  mtime={2}" -f $f, (Get-Item $p).Length, (Get-Item $p).LastWriteTime)
  } else { Write-Host "[$f] absent" }
}
Write-Host ''
Write-Host '--- crush tree ---'
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -and $_.CommandLine -match 'crush|_drive_test' } |
  Select-Object ProcessId,Name,ParentProcessId,CreationDate,@{n='cmd';e={$_.CommandLine.Substring(0,[Math]::Min(95,$_.CommandLine.Length))}} |
  Format-List
Write-Host '--- deepseek log full ---'
Get-Content 'D:\anonym\delivery\kilo-bridge-setup\_drive_test_nv-deepseek41.log' -Raw