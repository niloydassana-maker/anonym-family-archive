<#
install-task.ps1 — register the unattended loop (buyer copy, Run as Admin for SYSTEM-level, or normal for logon-level).
Usage: powershell -ExecutionPolicy Bypass -File install-task.ps1
Uninstall: schtasks /delete /tn KILO-MISSION-LOOP /f
#>
$DIR = Split-Path -Parent $PSScriptRoot
$PS1 = Join-Path $DIR "scripts\self-loop.ps1"
$TASK = "KILO-MISSION-LOOP"
schtasks /create /tn $TASK /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PS1`"" /sc onlogon /rl limited /f
if ($?) { Write-Host "Installed $TASK — runs at every logon. Reboot or run: schtasks /run /tn $TASK" } else { Write-Host "Install failed — run this file as Administrator." }
