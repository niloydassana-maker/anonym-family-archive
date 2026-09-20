$j = Get-Content 'D:\anonym\war-log\earn-lanes.json' -Raw | ConvertFrom-Json
$j.stale | ConvertTo-Json -Depth 5