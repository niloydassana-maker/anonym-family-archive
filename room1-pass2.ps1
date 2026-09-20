$ErrorActionPreference = 'Continue'
$log = New-Object System.Collections.Generic.List[string]
$log.Add("ROOM1-PASS2 RUN $(Get-Date -Format s)")

# 1. SmartScreen on (warns before unknown apps/runs)
try {
    New-Item -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' -Force | Out-Null
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' -Name EnableSmartScreen -Value 1 -Type DWord -Force
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' -Name ShellSmartScreenLevel -Value 'Warn' -Type String -Force
    $log.Add("SmartScreen: policy ON, level=Warn")
} catch { $log.Add("SmartScreen FAIL: $($_.Exception.Message)") }

# 2. AutoRun/AutoPlay fully off (USB sticks and phones cannot auto-execute)
try {
    New-Item -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer' -Force | Out-Null
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer' -Name NoAutorun -Value 1 -Type DWord -Force
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer' -Name NoDriveTypeAutoRun -Value 255 -Type DWord -Force
    $log.Add("AutoRun: OFF for all drive types")
} catch { $log.Add("AutoRun FAIL: $($_.Exception.Message)") }

# 3. Defender: real-time protection must be ON, engine fresh
try {
    $st = Get-MpComputerStatus
    if (-not $st.RealTimeProtectionEnabled) { Set-MpPreference -DisableRealtimeMonitoring $false }
    $st2 = Get-MpComputerStatus
    $log.Add("Defender: RealTime=$($st2.RealTimeProtectionEnabled) Tamper=$($st2.IsTamperProtected) SigAgeDays=$($st2.AntivirusSignatureAge)")
} catch { $log.Add("Defender FAIL: $($_.Exception.Message)") }

# 4. Windows Update service must not be disabled
try {
    $s = Get-Service wuauserv
    if ($s.StartType -eq 'Disabled') { Set-Service wuauserv -StartupType Manual; $log.Add("WindowsUpdate: was disabled -> set Manual") }
    else { $log.Add("WindowsUpdate: service $($s.Status) / $($s.StartType) (ok)") }
} catch { $log.Add("WindowsUpdate FAIL: $($_.Exception.Message)") }

# 5. FINALLY VERIFY BITLOCKER (the audit could never do this)
try {
    foreach ($d in 'C:','D:') {
        $out = manage-bde -status $d 2>&1
        $out | Where-Object { $_ -match 'Conversion Status|Protection Status|Percentage Encrypted' } | ForEach-Object { $log.Add("BitLocker $d $_".Trim()) }
    }
} catch { $log.Add("BitLocker FAIL: $($_.Exception.Message)") }

$log | Set-Content -Path 'D:\anonym\room1-hardening2-log.txt' -Encoding UTF8
Write-Output 'ROOM1_PASS2_DONE'
