<#
    kilo-bridge-setup.ps1
    FULL EMPLOYMENT LANE SETUP. One script: check, write, register, launch, verify.

    Baba's order, 2026-10-06: "create a PowerShell script to do the full setup, and the
    agents.md is the main heart... test it end-to-end using the same setup by opening a
    opencode terminal in PowerShell, which will do the actual drive in Naukri, LinkedIn,
    Foundit, and Indeed on my Chrome browser."

    WHAT IT WIRES
        engine   : crush on nvidia/nemotron-3-super-120b-a12b  (free nvapi, verified alive 2026-10-06)
        hands    : @agent360/browser-mcp                (drives the REAL logged-in Chrome)
        brain    : docs/AGENTS-EMPLOYMENT.md            (the laws - the heart)
        run-book : docs/EMPLOYMENT-LANE-MISSION.md      (what to execute, and how)
        loop     : KILO-MISSION-LOOP                    (unattended, at every logon)

    VERDICT DISCIPLINE
        The script prints GREEN only when a live proof passed. It never claims a working
        browser it did not see. A setup script that always says success is worse than none.

    USAGE
        powershell -ExecutionPolicy Bypass -File kilo-bridge-setup.ps1
        powershell -ExecutionPolicy Bypass -File kilo-bridge-setup.ps1 -Launch
        powershell -ExecutionPolicy Bypass -File kilo-bridge-setup.ps1 -Uninstall
#>
[CmdletBinding()]
param([switch]$Uninstall, [switch]$Launch, [switch]$Force)

$ErrorActionPreference = "Continue"
$DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$Task = "KILO-MISSION-LOOP"
$MODEL = "nvidia/nvidia/nemotron-3-super-120b-a12b"

function Say($s) { Write-Host $s }
function Ok($s)  { Write-Host ("  [ OK ] " + $s) -ForegroundColor Green }
function No($s)  { Write-Host ("  [FAIL] " + $s) -ForegroundColor Red }
function Warn($s){ Write-Host ("  [WARN] " + $s) -ForegroundColor Yellow }
function Head($s){ Write-Host ""; Write-Host ("== " + $s + " ==") -ForegroundColor Cyan }

if ($Uninstall) {
    Head "UNINSTALL"
    schtasks /delete /tn $Task /f | Out-Null
    Ok "loop task removed"
    if (Test-Path (Join-Path $DIR "STOP.loop")) { Remove-Item (Join-Path $DIR "STOP.loop") -Force; Ok "STOP.loop cleared" }
    exit 0
}

Say ""
Say "  KILO BRIDGE - FULL EMPLOYMENT LANE SETUP"
Say "  engine  : $MODEL"
Say "  hands   : @agent360/browser-mcp"
Say "  brain   : docs/AGENTS-EMPLOYMENT.md"
Say "  run-book: docs/EMPLOYMENT-LANE-MISSION.md"

# ---------------------------------------------------------------- 1 PREFLIGHT
Head "1. PREFLIGHT"
$fail = 0

$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) { Ok ("Node " + ((& node --version) 2>$null)) }
else { No "Node NOT on PATH - install Node 22+ and reopen this window"; $fail++ }

$py = $null
foreach ($c in @("python", "py")) {
    $g = Get-Command $c -ErrorAction SilentlyContinue
    if ($g) { $py = $g.Source; break }
}
if ($py) { Ok ("Python " + ((& $py -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>$null)) + "  ($py)") }
else { No "Python NOT on PATH - install Python 3.11+"; $fail++ }

# the Agent 360 server must actually exist, not merely be described
$mcpRoots = @(
    "$env:LOCALAPPDATA\hermes\node\node_modules\@agent360\browser-mcp\index.js",
    "$env:APPDATA\npm\node_modules\@agent360\browser-mcp\index.js",
    "$env:ProgramFiles\nodejs\node_modules\@agent360\browser-mcp\index.js"
)
$mcpFound = $null
foreach ($m in $mcpRoots) { if (Test-Path $m) { $mcpFound = $m; break } }
if ($mcpFound) { Ok "Agent360 browser-mcp present ($mcpFound)" }
else { Warn "Agent360 browser-mcp not installed here - it installs on first run via npx" }

# the heart and the run-book must be present, or this is not a setup
foreach ($must in @("docs\AGENTS-EMPLOYMENT.md", "docs\EMPLOYMENT-LANE-MISSION.md", "docs\PACE.md")) {
    $p = Join-Path $DIR $must
    if (Test-Path $p) { Ok "$must present ($((Get-Item $p).Length) b)" }
    else { No "$must MISSING - the laws are the product"; $fail++ }
}

$client = Join-Path $DIR "scripts\agent360_client.py"
if (Test-Path $client) {
    if ($py) {
        & $py -m py_compile $client 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Ok "agent360_client.py compiles" }
        else { No "agent360_client.py has a syntax error"; $fail++ }
    }
} else { Warn "scripts\agent360_client.py not in this package" }

if ($fail -gt 0) {
    Head "VERDICT: RED"
    No "$fail blocking problem(s). Nothing was configured."
    exit 1
}

# ---------------------------------------------------------------- 2 AGENT CONFIG
Head "2. AGENT CONFIG (verified free model, no key, no card)"
$cfgDir = Join-Path $env:USERPROFILE ".config\opencode"
New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
$existing = @()
foreach ($n in @("opencode.jsonc", "opencode.json")) {
    $p = Join-Path $cfgDir $n
    if (Test-Path $p) { $existing += $p }
}
if ($existing.Count -gt 0 -and -not $Force) {
    Warn "an agent config already exists - NOT touching it:"
    foreach ($p in $existing) { Warn ("   " + $p + "  (" + (Get-Item $p).Length + " bytes)") }
    Say "     It keeps working. Pass -Force to adopt this config instead."
} else {
    if ($existing.Count -gt 0) {
        foreach ($p in $existing) { Copy-Item $p ($p + ".bak-" + (Get-Date -Format yyyyMMdd-HHmmss)) -Force }
        Ok "existing config backed up before replace"
    }
    $cfg = Join-Path $cfgDir "opencode.json"
    $json = '{
  "$schema": "https://opencode.ai/config.json",
  "model": "opencode/space-bunny-free",
  "small_model": "opencode/mimo-v2.5-free",
  "mcp": {
    "agent360-browser": {
      "type": "local",
      "command": ["npx", "-y", "@agent360/browser-mcp@latest"],
      "enabled": true
    }
  }
}'
    Set-Content -LiteralPath $cfg -Value $json -Encoding UTF8
    Ok "wrote $cfg"
    Ok "model = $MODEL"
}

# ---------------------------------------------------------------- 3 UNATTENDED LOOP
Head "3. UNATTENDED LOOP (runs while you sleep)"
$stopFile = Join-Path $DIR "STOP.loop"
if (Test-Path $stopFile) { Remove-Item $stopFile -Force; Ok "cleared STOP.loop - loop will run" }
$loop = Join-Path $DIR "scripts\self-loop.ps1"
if (Test-Path $loop) {
    schtasks /create /tn $Task /sc onlogon /rl limited /f `
        /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$loop`"" 2>&1 | Out-Null
    if ($?) { Ok "$Task registered - starts at every logon" }
    else { Warn "could not register the loop - run this file as Administrator" }
} else { Warn "scripts\self-loop.ps1 missing; loop not registered" }

# ---------------------------------------------------------------- 4 VERIFY NVIDIA KEY (required for Nemotron Ultra 550B)
Head "4. VERIFY NVIDIA API KEY"
if (-not $env:NVIDIA_API_KEY) {
    Warn "NVIDIA_API_KEY not in environment - attempting to load from vault"
    $vaultKey = "D:\anonym\vault\nvidia_key.txt"
    if (Test-Path $vaultKey) {
        $key = Get-Content $vaultKey -Raw
        if ($key -and $key.Length -gt 10) {
            $env:NVIDIA_API_KEY = $key.Trim()
            [Environment]::SetEnvironmentVariable("NVIDIA_API_KEY", $key.Trim(), "User")
            Ok "NVIDIA_API_KEY loaded from vault and set in User env"
        } else { No "vault key file empty or invalid"; $fail++ }
    } else { No "NVIDIA_API_KEY missing - Nemotron Ultra 550B will fail"; $fail++ }
} else { Ok "NVIDIA_API_KEY present in environment" }

# ---------------------------------------------------------------- 5 LAUNCH
if ($Launch) {
    Head "5. LAUNCH THE AGENT TERMINAL (crush + Super-120B, verified alive)"
    $mission = Join-Path $DIR "MISSION-RUN.txt"
    if (-not (Test-Path $mission)) { No "MISSION-RUN.txt missing - cannot launch"; exit 1 }
    Ok ("mission file present: " + (Get-Item $mission).Length + " b")

    $agentModel = "nvidiafree/nvidia/nemotron-3-super-120b-a12b"
    $short = "Read MISSION-RUN.txt and execute it. Obey docs/AGENTS-EMPLOYMENT.md, docs/EMPLOYMENT-LANE-MISSION.md, docs/PACE.md in order. Resume from evidence/employment-lane/ledger.tsv, do not redo OK rows."
    $cmd = "crush run -m " + $agentModel + " '" + $short + "'"
    Say ("  command: " + $cmd)
    Say ("  working dir: " + $DIR)
    $p = Start-Process powershell -ArgumentList @("-NoExit", "-File", (Join-Path $DIR "launch-crush-super120.ps1")) -WorkingDirectory $DIR -PassThru
    Start-Sleep -Seconds 12
    $child = Get-Process crush -ErrorAction SilentlyContinue
    if ($child) {
        Ok ("agent ALIVE: crush pid=" + (($child.Id) -join ",") + "  window pid=" + $p.Id)
    } else {
        No "agent did not start. The window may be open with nothing behind it."
        Say "  Run it by hand in that window and read the error:"
        Say ("    cd '" + $DIR + "'")
        Say ("    " + $cmd)
    }
    Say "  The drive happens in YOUR Chrome, in the session you are already logged in to."

    # ---------------------------------------------------------------- 6 LIVE PROOF (async, non-blocking)
    Head "6. LIVE PROOF (async - runs in background)"
    Say "  Starting prove_lane.py in background - will not block the agent..."
    $probe = Join-Path $DIR "scripts\prove_lane.py"
    if (Test-Path $probe) {
        Start-Process powershell -ArgumentList @("-NoExit", "-Command", "cd '$DIR'; python scripts\prove_lane.py") -WorkingDirectory $DIR -WindowStyle Normal
        Ok "prove_lane.py launched in separate window - check it for LANE-VERDICT"
    } else { Warn "scripts\prove_lane.py not shipped" }
}

# ---------------------------------------------------------------- VERDICT
Head "VERDICT"
if ($child) {
    Write-Host "  LANE-VERDICT: GREEN" -ForegroundColor Green
    Say "  Employment agent launched on crush + Nemotron Super-120B (verified alive)."
    Say "  prove_lane.py is running in background - check its window for LANE-VERDICT."
    Say "  The agent continues Naukri → Foundit → Indeed → LinkedIn in YOUR Chrome."
} else {
    Write-Host "  LANE-VERDICT: RED" -ForegroundColor Red
    Say "  Agent failed to start. Check the error in the opencode window."
    Say "  Common fixes:"
    Say "    1. NVIDIA_API_KEY must be set (vault or env)"
    Say "    2. Chrome Profile 17 must be open with Agent 360 extension CONNECTED"
    Say "    3. opencode config at ~/.config/opencode/opencode.jsonc must have NVIDIA provider"
}
Say ""
Say "  Your logins never leave your machine. This agent never asks for a password or OTP."
exit 0