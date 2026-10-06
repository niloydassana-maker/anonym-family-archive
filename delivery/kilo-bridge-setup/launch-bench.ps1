$ErrorActionPreference = 'Stop'
Start-Process powershell -WindowStyle Normal -ArgumentList @(
  '-NoExit',
  '-Command',
  "cd 'D:\anonym\delivery\kilo-bridge-setup'; python bench-nvidia-vision.py"
)
Write-Output 'BENCH_LAUNCHED'
