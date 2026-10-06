Write-Host '--- crush CPU sample (16-bit CPU time / 32 = percent) ---'
$p = Get-Process crush -ErrorAction SilentlyContinue
if ($p) {
  $c1 = $p.CPU; Start-Sleep -Seconds 6; $p2 = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if ($p2) {
    $c2 = $p2.CPU
    Write-Host ("crush pid={0}  delta_cpu={1:N2}s in 6s  -> {2:N1}% busy" -f $p.Id, ($c2-$c1), (($c2-$c1)/6*100))
  } else { Write-Host 'crush exited' }
} else { Write-Host 'no crush running' }

Write-Host ''
Write-Host '--- what driver produced the 17:22-17:54 run? (crush/agent360 recent files) ---'
Get-ChildItem 'D:\anonym\war-log' -Filter '*.py' -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-2) } |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 20 Name,Length,LastWriteTime | Format-Table -AutoSize

Write-Host '--- agent-school related recent ---'
Get-ChildItem 'D:\anonym\war-log' -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-2) -and $_.Name -match 'school|seeker|employ' } |
  Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize