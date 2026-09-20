$out = 'D:\anonym\switch-log.txt'
'--- switch started ---' | Out-File $out
$wg = 'C:\Program Files\WireGuard\wireguard.exe'

# 1. Stop WARP (wgcf-profile) tunnel
& $wg /uninstalltunnelservice 'wgcf-profile' 2>&1 | Out-File $out -Append
Start-Sleep 6
"warp service: $((Get-Service 'WireGuardTunnel$wgcf-profile' -ErrorAction SilentlyContinue).Status)" | Out-File $out -Append

# 2. Install Proton NL tunnel
& $wg /installtunnelservice 'D:\anonym\laptop-nl-NL-FREE-2.conf' 2>&1 | Out-File $out -Append
Start-Sleep 10
"proton service: $((Get-Service 'WireGuardTunnel$laptop-nl-NL-FREE-2' -ErrorAction SilentlyContinue).Status)" | Out-File $out -Append

# 3. Verify exit IP
try {
    $ip = (Invoke-RestMethod -Uri 'https://api.ipify.org?format=json' -TimeoutSec 20).ip
    $r = Invoke-RestMethod -Uri "https://ipinfo.io/$ip/json" -TimeoutSec 20
    "ip: $ip | city: $($r.city), $($r.country) | org: $($r.org)" | Out-File $out -Append
} catch {
    "ip check failed: $($_.Exception.Message)" | Out-File $out -Append
}
'SWITCH_DONE' | Out-File $out -Append
