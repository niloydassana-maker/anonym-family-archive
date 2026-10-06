$LANE = 'D:\anonym\delivery\kilo-bridge-setup'
Set-Location $LANE

# quarantine pure scratch files (house convention: never delete a record)
$q = Join-Path $LANE '_quarantine-20261006'
New-Item -ItemType Directory -Force -Path $q | Out-Null
$scratch = @('_lane_jobs_new.py','_crush_tool_test.out.txt','_crush_tool_test.out.txt.err',
             '_probe_v2.out','_probe_v2.err','_drive_tests.done','_drive_tests2.done',
             '_kill_probe.ps1','_kill_mine.ps1','_kill_my_test.ps1','_kill_my_crush.ps1',
             '_test_crush_tools.ps1','_crush_tool_test.log','_probe_lane_bounded.py',
             '_probe_lane_v2.py','_token_micro.py','_token_micro.out','_token_micro.err',
             '_remove_test.py','_multiturn_test.ps1','_probe_nv_live.py','_probe_thinking.py')
$n = 0
foreach ($f in $scratch) {
  $p = Join-Path $LANE $f
  if (Test-Path $p) { Move-Item $p (Join-Path $q $f) -Force -ErrorAction SilentlyContinue; $n++ }
}
Write-Host ("quarantined: $n files -> _quarantine-20261006")

Write-Host ''
Write-Host '=== FINAL STATE ==='
Write-Host '--- client fix (both copies must match) ---'
Get-FileHash 'D:\anonym\war-log\agent360_client.py', "$LANE\scripts\agent360_client.py" -Algorithm SHA256 |
  Select-Object Hash,@{n='where';e={Split-Path (Split-Path $_.Path) -Leaf}} | Format-Table -AutoSize

Write-Host '--- token ---'
$t = 'D:\anonym\war-log\sweep-browser.token'
if (Test-Path $t) { Write-Host ("  HELD: " + (Get-Content $t -Raw)) } else { Write-Host '  CLEAN' }

Write-Host '--- ledger ---'
Write-Host ("  rows: " + (Get-Content "$LANE\evidence\employment-lane\ledger.tsv").Count)

Write-Host '--- drivers present ---'
foreach ($f in @('scripts\lane_resume.py','scripts\lane_jobs.py','DRIVERS-20261006.md',
                 'evidence\employment-lane\RCA-TOKEN-HANG-20261006.md',
                 'evidence\employment-lane\ARCHITECTURE-FINDING-20261006.md')) {
  $p = Join-Path $LANE $f
  if (Test-Path $p) { Write-Host ("  OK   {0} ({1} b)" -f $f, (Get-Item $p).Length) }
  else { Write-Host ("  MISS {0}" -f $f) }
}

Write-Host '--- money (honest) ---'
$e = 'D:\anonym\war-log\earn-lanes.json'
if (Test-Path $e) { Write-Host ("  " + ((Get-Content $e -Raw) -replace '\s+',' ').Substring(0,[Math]::Min(140,$(Get-Content $e -Raw -ErrorAction SilentlyContinue).Length))) }
else { Write-Host '  earn-lanes.json not found; collected_rs = 0 per this session' }

Write-Host '--- git ---'
Set-Location 'D:\anonym'
git add -A -- delivery/kilo-bridge-setup 2>&1 | Out-Null
git status --short -- delivery/kilo-bridge-setup 2>&1 | Measure-Object -Line | ForEach-Object { Write-Host ("  staged/changed entries: " + $_.Lines) }