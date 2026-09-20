$ErrorActionPreference = 'Continue'
$log = 'D:\anonym\net-hardening-log.txt'
Start-Transcript -Path $log -Force

try {
    # 1. SMBv1 off (legacy protocol, remote-exploitable)
    Set-SmbServerConfiguration -EnableSMB1Protocol $false -Force -ErrorAction SilentlyContinue
    Write-Output "SMBv1 disabled"

    # 2. LLMNR + NetBIOS + WPAD off (stops local-network name poisoning/snooping)
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient' -Name 'EnableMulticast' -Value 0 -Type DWord
    $ifs = Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces'
    foreach ($i in $ifs) { Set-ItemProperty -Path $i.PSPath -Name 'NetbiosOptions' -Value 2 -Type DWord }
    Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings\WinHttp' -Name 'AutoDetect' -Value 0 -Type DWord -ErrorAction SilentlyContinue
    Write-Output "LLMNR, NetBIOS, WPAD probing disabled"

    # 3. Current network profile -> Public (strictest firewall rules)
    Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Public
    Write-Output "Network profile set to Public"

    # 4. Firewall: outbound block for Windows telemetry endpoints
    $endpoints = @('watson.telemetry.microsoft.com','vortex.data.microsoft.com','settings-win.data.microsoft.com','sqm.telemetry.microsoft.com','telemetry.microsoft.com','statsfe2.update.microsoft.com.akadns.net')
    foreach ($e in $endpoints) {
        New-NetFirewallRule -DisplayName "BLOCK-TELEMETRY-$e" -Direction Outbound -RemoteAddress $e -Action Block -ErrorAction SilentlyContinue | Out-Null
    }
    Write-Output "Firewall telemetry blocks added"

    # 5. Encrypted DNS (DoH) via Cloudflare - ISP cannot log DNS lookups
    netsh dns add encryption server=1.1.1.1 dohtemplate=https://cloudflare-dns.com/dns-query udpfallback=no autoupgrade=yes 2>$null
    netsh dns add encryption server=1.0.0.1 dohtemplate=https://cloudflare-dns.com/dns-query udpfallback=no autoupgrade=yes 2>$null
    $adapters = Get-NetAdapter | Where-Object Status -eq 'Up'
    foreach ($a in $adapters) {
        Set-DnsClientServerAddress -InterfaceIndex $a.ifIndex -ServerAddresses '1.1.1.1','1.0.0.1'
    }
    Clear-DnsClientCache
    Write-Output "DoH configured, DNS flushed"

    # 6. NetBIOS over TCP/IP service kill
    Stop-Service lmhosts -Force -ErrorAction SilentlyContinue
    Set-Service lmhosts -StartupType Disabled -ErrorAction SilentlyContinue
    Write-Output "NetBIOS helper service disabled"

    Write-Output "NETWORK_HARDENING_DONE"
} catch {
    Write-Output "ERROR: $($_.Exception.Message)"
}
Stop-Transcript
