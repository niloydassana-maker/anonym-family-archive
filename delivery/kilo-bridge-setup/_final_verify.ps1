Write-Host '=== FINAL VERIFICATION ==='
Write-Host ''
Write-Host '--- 1. agent360_client fix present in BOTH copies ---'
Get-FileHash 'D:\anonym\war-log\agent360_client.py','D:\anonym\delivery\kilo-bridge-setup\scripts\agent360_client.py' -Algorithm SHA256 |
  Select-Object Hash,@{n='file';e={Split-Path $_.Path -Leaf}},@{n='dir';e={Split-Path (Split-Path $_.Path) -Leaf}} |
  Format-Table -AutoSize

Write-Host '--- 2. browser token state (clean = no driver holding) ---'
$t = 'D:\anonym\war-log\sweep-browser.token'
if (Test-Path $t) { Write-Host ("  HELD: " + (Get-Content $t -Raw)) } else { Write-Host '  CLEAN (absent)' }

Write-Host '--- 3. stray processes ---'
$cr = Get-Process crush -ErrorAction SilentlyContinue
if ($cr) { Write-Host ("  crush running: " + ($cr.Id -join ',')) } else { Write-Host '  no crush process' }

Write-Host '--- 4. ledger rows (should be 12 + 3 new = 15) ---'
$l = 'D:\anonym\delivery\kilo-bridge-setup\evidence\employment-lane\ledger.tsv'
Write-Host ("  total rows: " + (Get-Content $l).Count)
Write-Host '  last 4:'
Get-Content $l -Tail 4 | ForEach-Object { Write-Host ("    " + $_.Substring(0,[Math]::Min(150,$_.Length))) }

Write-Host '--- 5. evidence screenshots ---'
Get-ChildItem 'D:\anonym\delivery\kilo-bridge-setup\evidence\employment-lane' -Filter '*.png' |
  Sort-Object LastWriteTime | Select-Object Name,Length | Format-Table -AutoSize

Write-Host '--- 6. new artifacts ---'
foreach ($f in @('DRIVERS-20261006.md',
                 'evidence\employment-lane\RCA-TOKEN-HANG-20261006.md',
                 'evidence\employment-lane\ARCHITECTURE-FINDING-20261006.md',
                 'scripts\lane_resume.py','scripts\lane_jobs.py')) {
  $p = Join-Path 'D:\anonym\delivery\kilo-bridge-setup' $f
  if (Test-Path $p) { Write-Host ("  OK   {0}  ({1} b)" -f $f, (Get-Item $p).Length) }
  else { Write-Host ("  MISS {0}" -f $f) }
}

Write-Host '--- 7. git status ---'
Set-Location 'D:\anonym'
git status --short -- delivery/kilo-bridge-setup 2>&1 | Select-Object -First 25