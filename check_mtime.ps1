$f = 'D:\anonym\war-log\kdp-lane.json'
if (Test-Path $f) {
    $diff = (Get-Date) - (Get-Item $f).LastWriteTime
    if ($diff.TotalMinutes -lt 15) { 'TICK-SKIPPED' } else { 'PROCEED' }
} else { 'PROCEED' }