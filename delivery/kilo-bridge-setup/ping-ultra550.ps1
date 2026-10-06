$ErrorActionPreference = 'Continue'
Set-Location 'D:\anonym\delivery\kilo-bridge-setup'
Write-Host 'PING Ultra 550B...'
crush run -m nvidiafree/nvidia/nemotron-3-ultra-550b-a55b --quiet 'reply with the single word PONG'
Write-Host ('EXIT=' + $LASTEXITCODE)
