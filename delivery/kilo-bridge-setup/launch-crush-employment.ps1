$ErrorActionPreference = 'Stop'
$work = 'D:\anonym\delivery\kilo-bridge-setup'
$prompt = 'Read MISSION-RUN.txt and execute it. Resume from evidence\employment-lane\ledger.tsv, do not redo rows marked OK.'
Start-Process powershell -WindowStyle Normal -ArgumentList @(
  '-NoExit',
  '-Command',
  "cd '$work'; crush run -m nvidiafree/z-ai/glm-5.3 '$prompt'"
)
Write-Output 'LAUNCH_SENT crush + nvidiafree/z-ai/glm-5.3'
