$ErrorActionPreference = 'Continue'
$LANE = 'D:\anonym\delivery\kilo-bridge-setup'
Set-Location $LANE
$LOG = Join-Path $LANE 'evidence\employment-lane\_probe_jobs_dom.log'
"[$(Get-Date -Format o)] probe start" | Set-Content $LOG -Encoding UTF8
& python 'scripts\_probe_jobs_dom.py' 2>&1 | ForEach-Object { Write-Host $_; Add-Content -Path $LOG -Value $_ -Encoding UTF8 }
"[$(Get-Date -Format o)] exit=$LASTEXITCODE" | Add-Content $LOG -Encoding UTF8