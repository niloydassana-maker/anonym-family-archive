$ErrorActionPreference = 'Continue'
$log = New-Object System.Collections.Generic.List[string]
$log.Add("FIX-GAPS RUN $(Get-Date -Format s)")

# 1. LLMNR off (the gap the audit found)
try {
    New-Item -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient' -Force | Out-Null
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient' -Name EnableMulticast -Value 0 -Type DWord -Force
    $v = (Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient').EnableMulticast
    $log.Add("LLMNR EnableMulticast = $v (expect 0)")
} catch { $log.Add("LLMNR FAIL: $($_.Exception.Message)") }

# 2. Advertising ID blocked by machine policy (the gap the audit found)
try {
    New-Item -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo' -Force | Out-Null
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo' -Name DisabledByGroupPolicy -Value 1 -Type DWord -Force
    $v = (Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo').DisabledByGroupPolicy
    $log.Add("AdvertisingID DisabledByGroupPolicy = $v (expect 1)")
} catch { $log.Add("AdvertisingID FAIL: $($_.Exception.Message)") }

# 3. NetBIOS off on EVERY interface (one was left at default)
try {
    $ifs = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces\tcpip_*'
    foreach ($i in $ifs) {
        Set-ItemProperty -Path $i.PSPath -Name NetbiosOptions -Value 2 -Type DWord -Force
    }
    $after = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces\tcpip_*').NetbiosOptions -join ','
    $log.Add("NetBIOS NetbiosOptions = $after (expect all 2)")
} catch { $log.Add("NetBIOS FAIL: $($_.Exception.Message)") }

# NOTE: DoH and domain-name firewall rules were deliberately NOT recreated:
# Windows 10 Pro does not support either natively. DNS already travels
# encrypted inside the Proton tunnel, and telemetry services/tasks are
# already disabled at the source. This matches the independent audit.

$log | Set-Content -Path 'D:\anonym\fix-gaps-log.txt' -Encoding UTF8
$log | ForEach-Object { Write-Output $_ }
Write-Output 'FIX_GAPS_DONE'
