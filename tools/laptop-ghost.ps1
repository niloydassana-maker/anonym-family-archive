# LAPTOP-GHOST v1.1 - idempotent location law (re-applies at every startup/logon via KILO-LAPTOP-GHOST task)
# LAW: this machine exposes no location, no telemetry, no bluetooth. Re-runs after every restart/update; all ops idempotent.
$ErrorActionPreference = 'Continue'
$log = 'D:\anonym\war-log\laptop-ghost.log'
function L($m) { try { Add-Content -LiteralPath $log -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $m" } catch {} }
L "LAPTOP-GHOST v1.1 RUN START"

function SetReg($path, $name, $val) {
  try {
    if (-not (Test-Path $path)) { New-Item -Force -Path $path | Out-Null }
    Set-ItemProperty -LiteralPath $path -Name $name -Value $val -Type DWord -Force
    L "OK $path\$name=$val"
  } catch { L "FAIL $path\$name : $($_.Exception.Message)" }
}

# 1. LOCATION + SENSORS
$las = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors'
SetReg $las 'DisableLocation' 1
SetReg $las 'DisableLocationScripting' 1
SetReg $las 'DisableSensors' 1
$cs = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location'
if (Test-Path $cs) { try { Set-ItemProperty -LiteralPath $cs -Name Value -Value 'Deny' -Force; L "OK consent-location Deny" } catch { L "FAIL consent: $($_.Exception.Message)" } }
$ws = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search'
SetReg $ws 'AllowCortana' 0
SetReg $ws 'AllowSearchToUseLocation' 0

# 2. TELEMETRY zero
$dc1 = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection'
SetReg $dc1 'AllowTelemetry' 0
SetReg $dc1 'MaxTelemetryAllowed' 0
$dc2 = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection'
SetReg $dc2 'AllowTelemetry' 0
foreach ($svc in 'DiagTrack','dmwappushservice') { try { Set-Service $svc -StartupType Disabled -EA Stop; Stop-Service $svc -Force -EA SilentlyContinue; L "OK svc $svc disabled" } catch { L "svc $svc : $($_.Exception.Message)" } }

# 3. ADVERTISING ID
SetReg 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo' 'DisabledByGroupPolicy' 1

# 4. NCSI active probing off
$ini = 'HKLM:\SYSTEM\CurrentControlSet\Services\NlaSvc\Parameters\Internet'
if (Test-Path $ini) { Set-ItemProperty -LiteralPath $ini -Name EnableActiveProbing -Value 0 -Type DWord -Force; L "OK NCSI probing off" }

# 5. BLUETOOTH off (adapter + service)
try { Get-PnpDevice -Class Bluetooth -Status OK -ErrorAction SilentlyContinue | ForEach-Object { Disable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false }; L "OK bluetooth pass done" } catch { L "bt: $($_.Exception.Message)" }
try { Set-Service bthserv -StartupType Disabled -EA Stop; L "OK bthserv disabled" } catch { L "bthserv: $($_.Exception.Message)" }

# 6. lfsvc kill-switch
try { Set-Service lfsvc -StartupType Disabled -EA Stop; L "OK lfsvc disabled" } catch { L "lfsvc: $($_.Exception.Message)" }

L "LAPTOP-GHOST RUN DONE"
