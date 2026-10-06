$ErrorActionPreference = 'Continue'
$LANE = 'D:\anonym\delivery\kilo-bridge-setup'
Set-Location $LANE
$LOG = Join-Path $LANE 'evidence\employment-lane\lane_jobs-run.log'
"[$(Get-Date -Format o)] lane_jobs.py start" | Set-Content $LOG -Encoding UTF8
& python 'scripts\lane_jobs.py' 2>&1 | ForEach-Object { Write-Host $_; Add-Content -Path $LOG -Value $_ -Encoding UTF8 }
"[$(Get-Date -Format o)] exit=$LASTEXITCODE" | Add-Content $LOG -Encoding UTF8