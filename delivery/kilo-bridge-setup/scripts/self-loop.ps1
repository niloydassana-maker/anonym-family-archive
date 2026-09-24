<#
self-loop.ps1 — unattended mission loop (buyer copy).
Runs your AI agent over the mission prompt forever: execute -> rest -> execute.
Quota-safe: provider holds pause launches until reset; one owner at a time (mutex).
Usage: powershell -ExecutionPolicy Bypass -File self-loop.ps1 [-RestSec 300]
Stop: delete this task in Task Scheduler, or create STOP.loop in this folder.
#>
param([int]$RestSec = 300)

$HOME_DIR = Split-Path -Parent $PSScriptRoot
$MISSION  = Join-Path $HOME_DIR "docs\FINAL-AGY-PROMPT-2026-09-24.md"
$LOG      = Join-Path $HOME_DIR "mission.log"
$HOLD     = Join-Path $HOME_DIR "quota-hold-until.txt"
$STOP     = Join-Path $HOME_DIR "STOP.loop"
$AGY      = "$env:LOCALAPPDATA\agy\bin\agy.exe"
$mutex    = New-Object System.Threading.Mutex($false, "Global\KiloMission")

function Say($m) {
  $ts = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
  Add-Content -LiteralPath $LOG "$ts SELF-LOOP $m" -Encoding utf8
}
Say "loop starting. Mission: $MISSION"
while ($true) {
  if (Test-Path -LiteralPath $STOP) { Say "STOP.loop found — exiting."; exit 0 }
  if (Test-Path -LiteralPath $HOLD) {
    try {
      $until = [DateTimeOffset]::Parse((Get-Content -LiteralPath $HOLD -Raw).Trim()).UtcDateTime
      if ([DateTime]::UtcNow -lt $until) { Say "quota hold until $until — resting"; Start-Sleep -Seconds $RestSec; continue }
      Remove-Item -LiteralPath $HOLD -Force; Say "quota hold expired — resuming"
    } catch { Say "bad hold marker — waiting: $_"; Start-Sleep -Seconds $RestSec; continue }
  }
  if (-not $mutex.WaitOne(0)) { Say "another owner holds the mission — resting"; Start-Sleep -Seconds $RestSec; continue }
  try {
    Say "launching agent over mission file"
    & $AGY -p "Read and execute the mission in $MISSION top to bottom. Slow pace on LinkedIn (15/day, 3-min gaps). Screenshot every act. Reply DONE with a receipt list." --output-format stream-json >> $LOG 2>&1
    Say "agent pass exited code $LASTEXITCODE"
  } catch { Say "agent error: $_" } finally { $mutex.ReleaseMutex() }
  Say "resting $RestSec seconds"
  Start-Sleep -Seconds $RestSec
}
