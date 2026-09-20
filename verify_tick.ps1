$j = Get-Content 'D:\anonym\war-log\earn-lanes.json' -Raw | ConvertFrom-Json
Write-Output "last_tick: $($j.last_tick)"
Write-Output "indusind: $($j.indusind | ConvertTo-Json -Depth 5)"