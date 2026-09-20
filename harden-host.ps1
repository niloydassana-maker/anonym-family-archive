$ErrorActionPreference = 'Continue'
$log = 'D:\anonym\hardening-log.txt'
Start-Transcript -Path $log -Force

try {
    # 1. Telemetry level: 0 = Security only (lowest allowed on Pro)
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection' -Name 'AllowTelemetry' -Value 0 -Type DWord
    Write-Output "Telemetry level set to 0 (Security)"

    # 2. Kill connected-user experiences + telemetry service
    Stop-Service DiagTrack -Force -ErrorAction SilentlyContinue
    Set-Service DiagTrack -StartupType Disabled -ErrorAction SilentlyContinue
    Stop-Service dmwappushservice -Force -ErrorAction SilentlyContinue
    Set-Service dmwappushservice -StartupType Disabled -ErrorAction SilentlyContinue
    Write-Output "DiagTrack + dmwappush disabled"

    # 3. Advertising ID off
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo' -Name 'DisabledByGroupPolicy' -Value 1 -Type DWord -ErrorAction SilentlyContinue
    Write-Output "Advertising ID blocked"

    # 4. Activity history / timeline off
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' -Name 'EnableActivityFeed' -Value 0 -Type DWord -ErrorAction SilentlyContinue
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' -Name 'PublishUserActivities' -Value 0 -Type DWord -ErrorAction SilentlyContinue
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' -Name 'UploadUserActivities' -Value 0 -Type DWord -ErrorAction SilentlyContinue
    Write-Output "Activity history off"

    # 5. Scheduled telemetry tasks killed
    $tasks = @('\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser',
               '\Microsoft\Windows\Application Experience\ProgramDataUpdater',
               '\Microsoft\Windows\Customer Experience Improvement Program\Consolidator',
               '\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip')
    foreach ($t in $tasks) { Disable-ScheduledTask -TaskPath (Split-Path $t) -TaskName (Split-Path $t -Leaf) -ErrorAction SilentlyContinue | Out-Null }
    Write-Output "Telemetry scheduled tasks disabled"

    # 6. Wi-Fi Sense (hotspot auto-share) off
    Set-ItemProperty -Path 'HKLM:\Software\Microsoft\PolicyManager\default\WiFi\AllowWiFiHotSpotReporting' -Name 'Value' -Value 0 -Type DWord -ErrorAction SilentlyContinue
    Set-ItemProperty -Path 'HKLM:\Software\Microsoft\PolicyManager\default\WiFi\AllowAutoConnectToWiFiSenseHotspots' -Name 'Value' -Value 0 -Type DWord -ErrorAction SilentlyContinue
    Write-Output "WiFi Sense off"

    # 7. Clear existing telemetry from the DiagTrack database
    Remove-Item -Path "$env:ProgramData\Microsoft\Diagnosis\ETLLogs\AutoLogger\AutoLogger-Diagtrack-Listener.etl" -Force -ErrorAction SilentlyContinue
    Write-Output "Old telemetry logs cleared"

    Write-Output "ALL_HARDENING_DONE"
} catch {
    Write-Output "ERROR: $($_.Exception.Message)"
}
Stop-Transcript
