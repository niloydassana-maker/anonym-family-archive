Write-Host '--- ledger source-column check (last 6 rows) ---'
$l = 'D:\anonym\delivery\kilo-bridge-setup\evidence\employment-lane\ledger.tsv'
Get-Content $l -Tail 6 | ForEach-Object {
  $c = $_ -split "`t"
  Write-Host ("  status={0,-9} score={1,-3} src={2}" -f $c[7], $c[5], $c[2].Substring(0,[Math]::Min(62,$c[2].Length)))
}
Write-Host ''
Write-Host '--- ambitionbox leaks in the NEW rows? ---'
$new = Get-Content $l -Tail 25
$bad = $new | Where-Object { $_ -match 'ambitionbox' }
if ($bad) { Write-Host ("  LEAKS: " + $bad.Count) } else { Write-Host '  none (HREF LAW holds)' }
Write-Host ''
Write-Host ("total ledger rows: " + (Get-Content $l).Count)