<# 
.SYNOPSIS
    Creates Windows Task Scheduler task for EARN-LANES tick at HH:14 IST
#>

$taskName = "EARN-LANES-Tick"
$scriptPath = "D:\anonym\earn_lanes_launcher.ps1"
$pythonPath = (Get-Command python).Source

# Remove existing task if present
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed existing task: $taskName"
}

# Create trigger: repeat every hour at 14 minutes past, for 1 year
$startTime = (Get-Date).Date.AddMinutes(14)
$trigger = New-ScheduledTaskTrigger -Once -At $startTime -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 365)

# Create action
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

# Create settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Hidden

# Register task
Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action -Settings $settings -Description "EARN-LANES autonomous micro-loop tick at HH:14 IST" -Force

Write-Host "Task '$taskName' created successfully"
Write-Host "Will run at 14 minutes past every hour"
Write-Host "Logs: D:\anonym\war-log\tick.log"