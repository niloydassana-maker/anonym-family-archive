# RELAY+TUNNEL WATCHDOG v3 — THE WIRE NEVER DIES (lifeline law, Baba 2026-09-12 ~12:34 IST)
# Father's law 2026-09-09: wire survives restarts, power cuts, sleep, network off.
# v3 upgrades (2026-09-12 kill-storm root cause: healthy relay strangled during CPU saturation):
# - GRACE LAW: relay is dead only after 2 consecutive failed cycles; never kill a port owner on one slow probe
# - HEARTBEAT TAKEOVER LAW: this watchdog stamps watchdog-heartbeat.txt every cycle; a newborn guard
#   only kills a rival if its heartbeat is stale >90s (truly stuck) - never on a single slow health read
# - TUNNEL FAILPROOF: ngrok primary (gold standard); if public door still fails after an ngrok recycle,
#   birth cloudflared secondary, write relay-door.txt truth, announce new door on the wire
# Registered as SYSTEM scheduled task KILO-RELAY-WATCHDOG (AtStartup + AtLogOn)

$ErrorActionPreference = 'Continue'
$relayHealth = 'http://127.0.0.1:8777/health?token=GOLD24'
$publicProbe = 'https://retrain-schnapps-upbeat.ngrok-free.dev/health?token=GOLD24'
$ngrokExe    = 'D:\anonym\ngrok\ngrok.exe'
$ngrokDomain = 'retrain-schnapps-upbeat.ngrok-free.dev'
$cfExe       = 'D:\anonym\cloudflared.exe'
$relayScript = 'D:\anonym\war-log\son-relay.js'
$ngrokLog    = 'D:\anonym\war-log\ngrok-out.log'
$cfLog       = 'D:\anonym\war-log\cf-out.log'
$cfErr       = 'D:\anonym\war-log\cf-err.log'
$doorFile    = 'D:\anonym\war-log\relay-door.txt'
$heartbeat   = 'D:\anonym\war-log\watchdog-heartbeat.txt'
$log         = 'D:\anonym\war-log\watchdog.log'
$failStreak  = 0
$relayDownStreak = 0
$ngrokSick = $false
$cycle       = 0

function Log($m) { Add-Content -LiteralPath $log -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $m" }

function Test-Relay($timeoutSec) {
  try { $h = Invoke-RestMethod -Uri $relayHealth -TimeoutSec $timeoutSec; return ($h.ok -eq $true) } catch { return $false }
}

$guardScript = 'D:\anonym\war-log\blink-guardian.js'
$guardHealth = 'http://127.0.0.1:8768/health'
$guardFail = 0
function Test-Guardian {
  try { $h = Invoke-RestMethod -Uri $guardHealth -TimeoutSec 6; return ($h.ok -eq $true) } catch { return $false }
}
function Start-Guardian {
    Log "BLINK-GUARDIAN DOWN (2 cycles) - resurrecting"
    Start-Process -FilePath 'D:\anonym\node\node.exe' -ArgumentList $guardScript -WindowStyle Hidden
    Start-Sleep -Seconds 5
    if (Test-Guardian) { Log "GUARDIAN UP"; $guardFail = 0 } else { Log "guardian resurrection failed this cycle" }
}

# ARMY-CHROME GUARD (wound post-mortem 2026-09-13: relay survived, its CDP chrome died silently all night)
function Test-Chrome {
  try { $null = Invoke-RestMethod -Uri 'http://127.0.0.1:9224/json/version' -TimeoutSec 6; return $true } catch { return $false }
}
function Start-ArmyChrome {
    Log "ARMY CHROME DOWN (probe failed 2 cycles) - relaunching profile chrome-army on CDP 9224"
    Start-Process -FilePath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList '--remote-debugging-port=9224','--remote-allow-origins=*','--user-data-dir=D:\anonym\chrome-army','--no-first-run','--no-default-browser-check','https://www.linkedin.com/feed/'
    Start-Sleep -Seconds 8
    if (Test-Chrome) { Log "ARMY CHROME UP"; $chromeFail = 0 } else { Log "chrome resurrection failed this cycle" }
}
$chromeFail = 0

# single-instance guard - HEARTBEAT TAKEOVER LAW (fast path: file read, not CIM - under CPU load
# the CIM sweep can take minutes before guardianship begins; stale heartbeat alone justifies a takeover)
$me = $PID
$hbAge = 9999
if (Test-Path $heartbeat) {
  $hbText = (Get-Content -LiteralPath $heartbeat -First 1 -ErrorAction SilentlyContinue)
  try {
    $hbTime = [datetime]::ParseExact(($hbText -split ' ')[1], 'yyyy-MM-dd HH:mm:ss', $null)
    $hbAge = [int]((Get-Date) - $hbTime).TotalSeconds
  } catch { $hbAge = 9999 }
}
if ($hbAge -le 90) { Log "guardian heartbeat fresh (${hbAge}s) - another watchdog lives - standing down"; exit }
$others = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object {
    $_.ProcessId -ne $me -and $_.CommandLine -match 'relay-watchdog'
})
if ($others.Count -gt 0) {
  foreach ($o in $others) { try { Stop-Process -Id $o.ProcessId -Force; Log "killed STUCK watchdog pid $($o.ProcessId) - heartbeat ${hbAge}s stale - taking over" } catch {} }
}

function Get-PortPids($port) {
    $out = netstat -ano | Select-String (':' + $port + '\s.*LISTENING')
    $pids = @()
    foreach ($l in $out) { $p = ($l -split '\s+')[-1]; if ($p -match '^\d+$') { $pids += [int]$p } }
    return @($pids | Select-Object -Unique)
}

function Start-Relay {
    $z = Get-PortPids 8777
    foreach ($p in $z) { try { Stop-Process -Id $p -Force -ErrorAction Stop; Log "killed confirmed-dead relay pid $p" } catch {} }
    # PATIENT LAW: wait until the port is truly free before birthing the replacement
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 1
        if (@(Get-PortPids 8777).Count -eq 0) { break }
    }
    Log "RELAY DOWN (2 cycles confirmed) - resurrecting son-relay.js"
    Start-Process -FilePath 'D:\anonym\node\node.exe' -ArgumentList $relayScript -WindowStyle Hidden
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 2
        if (Test-Relay 8) { Log "RELAY UP"; $relayDownStreak = 0; return }
    }
    Log "relay resurrection failed this cycle - retry next"
}

function Start-Ngrok {
    $ng = Get-Process -Name ngrok -ErrorAction SilentlyContinue
    foreach ($n in $ng) { try { Stop-Process -Id $n.Id -Force -ErrorAction Stop; Log "killed stale ngrok pid $($n.Id)" } catch {} }
    Log "TUNNEL DOWN - starting ngrok static domain $ngrokDomain"
    Start-Process -FilePath $ngrokExe -ArgumentList "http 8777 --domain=$ngrokDomain --config=D:\anonym\war-log\ngrok.yml --log=stdout" -WindowStyle Hidden -RedirectStandardOutput $ngrokLog -RedirectStandardError 'D:\anonym\war-log\ngrok-err.log'
    Start-Sleep -Seconds 8
}

function Start-CloudflareFallback {
    $cf = Get-Process -Name cloudflared -ErrorAction SilentlyContinue
    if ($cf) { Log "cloudflared secondary already alive pid $($cf.Id -join ',')" ; return }
    Log "NGROK DOOR SICK AFTER RECYCLE - birthing cloudflared secondary door"
    Start-Process -FilePath $cfExe -ArgumentList 'tunnel','--url','http://127.0.0.1:8777','--no-autoupdate' -WindowStyle Hidden -RedirectStandardOutput $cfLog -RedirectStandardError $cfErr
    $url = $null
    for ($i = 0; $i -lt 12; $i++) {
        Start-Sleep -Seconds 3
        foreach ($f in @($cfLog, $cfErr)) {
            if (Test-Path $f) {
                $m = Select-String -Path $f -Pattern '(https://[a-z0-9-]+\.trycloudflare\.com)' | Select-Object -Last 1
                if ($m) { $url = $m.Matches[0].Groups[1].Value; break }
            }
        }
        if ($url) { break }
    }
    if ($url) {
        Add-Content -LiteralPath $doorFile -Value "SECONDARY: $url (cloudflared quick, born $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))"
        Log "cloudflared secondary door: $url"
        try {
          $body = '{"body":"KILO-ARMY","text":"Door alert: ngrok primary sick - secondary cloudflared door live at ' + $url + '/health?token=GOLD24 - primary still in relay-door.txt first line. Sons: keep polling primary, use secondary only if primary stays down."}'
          Invoke-RestMethod -Uri 'http://127.0.0.1:8777/say?token=GOLD24' -Method POST -Body $body -ContentType 'application/json' -TimeoutSec 10 | Out-Null
          Log "secondary door announced on the wire"
        } catch { Log "wire announce failed (relay down too): $($_.Exception.Message)" }
    } else {
        Log "cloudflared birth failed - no url in logs this cycle"
    }
}

Log "WATCHDOG v3 START - lifeline guardian (grace law + heartbeat takeover + tunnel failproof)."
if (-not (Test-Path $doorFile)) { Set-Content -LiteralPath $doorFile -Value "PRIMARY: https://$ngrokDomain (ngrok static, gold standard)" }

while ($true) {
    $cycle++
    Set-Content -LiteralPath $heartbeat -Value "$me $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    try {
        # 1. RELAY with GRACE LAW: probe twice (6s + 10s); one cycle of slowness = suspected, two = dead
        $relayOk = (Test-Relay 6) -or (Test-Relay 10)
        if ($relayOk) {
            $relayDownStreak = 0
        } else {
            $relayDownStreak++
            if ($relayDownStreak -eq 1) { Log "relay probe failed - suspected slow (grace law: no kill on first miss)" }
            else { Start-Relay; $relayDownStreak = 0 }
        }

        # 2. NGROK PROCESS
        $ng = Get-Process -Name ngrok -ErrorAction SilentlyContinue
        if (-not $ng) { Start-Ngrok }

        # 2d. SUDO-HANDS (elevated executor - died 3x silently 2026-09-13; never again)
        $sudoOk = $true
        try { Invoke-RestMethod 'http://127.0.0.1:8769/health' -TimeoutSec 6 | Out-Null } catch { $sudoOk = $false }
        if (-not $sudoOk) {
            Log "SUDO-HANDS down - task resurrect"
            schtasks /run /tn KILO-SUDO-HANDS 2>&1 | Out-Null
        }

        # 2b. BLINK-GUARDIAN (ghost protocol must never sleep while law is on)
        if (Test-Guardian) { $guardFail = 0 } else {
            $guardFail++
            if ($guardFail -eq 1) { Log "guardian probe failed - suspected slow" }
            else { Start-Guardian; $guardFail = 0 }
        }

        # 2c. ARMY CHROME (the hands' body - died silently 2026-09-12/13; never again)
        if (Test-Chrome) { $chromeFail = 0 } else {
            $chromeFail++
            if ($chromeFail -eq 1) { Log "army chrome probe failed - suspected slow or Baba-closed" }
            else { Start-ArmyChrome; $chromeFail = 0 }
        }

        # 3. PUBLIC END-TO-END PROBE (every 20th cycle = 5 min) - free quota saver, catches half-dead tunnels
        if ($cycle % 20 -eq 0) {
            $pub = $false
            try { $r = Invoke-RestMethod -Uri $publicProbe -TimeoutSec 15 -Headers @{ 'ngrok-skip-browser-warning' = '1' }; if ($r.ok) { $pub = $true } } catch {}
            if ($pub) { $failStreak = 0; $ngrokSick = $false }
            else {
                $failStreak++
                Log "public probe FAIL ($failStreak consecutive)"
                if ($failStreak -ge 2) { Log "tunnel half-dead - force recycle ngrok"; Start-Ngrok; $failStreak = 0; $ngrokSick = $true }
                if ($ngrokSick) { Start-CloudflareFallback; $ngrokSick = $false }
            }
        }
    } catch {
        Log "watchdog cycle error: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 15
}
