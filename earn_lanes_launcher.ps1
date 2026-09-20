<# 
.SYNOPSIS
    EARN-LANES Tick Engine - Runs at 14 minutes past each hour IST
.DESCRIPTION
    This script executes the autonomous micro-loop per EARN-LANES-SPEC v1.0
    Logs everything to the bank (EARN-LEDGER.md + war-log/earn-lanes.json)
    Implements 429 rate limiting rule
#>

$scriptPath = "D:\anonym\earn_lanes_tick.py"
$logPath = "D:\anonym\war-log\tick.log"
$pythonExe = "python"

try {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] Starting EARN-LANES tick..."
    
    & $pythonExe $scriptPath --once 2>&1 | Tee-Object -FilePath $logPath -Append
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] Tick completed"
}
catch {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Error "[$timestamp] Tick failed: $_"
    "$timestamp Tick failed: $_" | Out-File -FilePath $logPath -Append
}