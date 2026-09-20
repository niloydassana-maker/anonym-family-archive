if (Test-Path 'D:\anonym\war-log\kdp-lane.json') {
    $mtime = (Get-Item 'D:\anonym\war-log\kdp-lane.json').LastWriteTime
    $diff = (Get-Date) - $mtime
    if ($diff.TotalMinutes -lt 15) {
        Write-Host 'TICK-SKIPPED'
        exit 0
    } else {
        Write-Host 'PROCEED'
    }
} else {
    Write-Host 'PROCEED'
}