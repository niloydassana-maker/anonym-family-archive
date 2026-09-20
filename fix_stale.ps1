$j = Get-Content 'D:\anonym\war-log\earn-lanes.json' -Raw | ConvertFrom-Json
$j.stale.feed_watch = '2026-09-20T15:50:12.184123+05:30'
$j.stale.weaver = 'DEAD'
$j.stale.awareness = '2026-09-20T15:50:12.236433+05:30'
$j | ConvertTo-Json -Depth 10 | Set-Content 'D:\anonym\war-log\earn-lanes.json'