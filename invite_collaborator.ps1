<# 
.SYNOPSIS
    Bulk GitHub collaborator invitation - FIXED VERSION v2
    Grants READ-only access to a verified GitHub user across 49 repositories
    
.FIXES from v1:
    1. Pre-validates GitHub username BEFORE invitations (the 404-as-truthy bug)
    2. Uses $LASTEXITCODE for all gh api calls (never trusts raw output)
    3. Correct 49 repo list from corpus-final.json
    4. GitHub API permission is "pull" for READ-only (v1 wrongly used "read")
#>

$ErrorActionPreference = "Continue"
$owner = "isearchxsolve"

# 49 Repositories - verbatim from corpus-final.json
$repos = @(
    "_fleet_flutter_release_20260817"
    "_fleet_flutter_release_attempt2_20260817"
    "_live_flutter_verification_20260817"
    "_live_proof_fastapi_react_20260822"
    "ack"
    "ai_video_monetizer"
    "antigravity-kandover"
    "api_money_bot_complete"
    "ases_v3_1"
    "claude_code_clone"
    "convergence_framework"
    "crypto-ai-auto-trader"
    "crypto-app-by-replit"
    "crypto-trading-ai-agent"
    "emergentsh_latest"
    "frontend"
    "god_ai_scripts"
    "guardian_app"
    "gumroad-products"
    "hsf"
    "idea-terminal-engine"
    "ideation_to_prototype"
    "ikon_agent-main"
    "kdp-polished"
    "lasthelp"
    "lateststablecode"
    "nemo_test"
    "neon_unified"
    "oiioii_clone"
    "oiioii_clone2"
    "oiioii_clone3"
    "oiioii_clone_final"
    "oiioii_clone_final2"
    "oiioii_clone_final3"
    "oiioii_clone_full"
    "oiioii_clone_gen"
    "oioi"
    "omega"
    "omniroute-monetizer"
    "omniroute_dashboard"
    "scratch"
    "screen_guard_final"
    "solana-auto-trader-live"
    "stabletcode"
    "test_coding_agent"
    "the-beholder-project"
    "timeofmylife"
    "voice_agent_avatar"
    "war-pipe"
)

Write-Host "Loaded $($repos.Count) repositories" -ForegroundColor Cyan

# ============================================================
# STEP 1: VERIFY THE GITHUB USERNAME EXISTS
# ============================================================
Write-Host ""
Write-Host "STEP 1: Verifying GitHub username..." -ForegroundColor Cyan
Write-Host "Email provided: prafullprince12@gmail.com" -ForegroundColor Yellow
Write-Host ""

$candidates = @("prafullprince12", "prafull-prince12", "prafullprince", "prafulprince12")
$verifiedUsername = $null

foreach ($candidate in $candidates) {
    Write-Host "Checking username: $candidate ... " -NoNewline
    $raw = gh api "users/$candidate" 2>$null
    $code = $LASTEXITCODE
    
    if ($code -eq 0 -and $raw) {
        try {
            $obj = $raw | ConvertFrom-Json
            if ($obj.login) {
                Write-Host "EXISTS" -ForegroundColor Green
                Write-Host "  login: $($obj.login)" -ForegroundColor Green
                $verifiedUsername = $obj.login
                break
            }
        } catch {
            Write-Host "PARSE ERROR" -ForegroundColor Red
        }
    } else {
        Write-Host "NOT FOUND (404)" -ForegroundColor Red
    }
}

if (-not $verifiedUsername) {
    Write-Host ""
    Write-Host "BLOCKED: GitHub username not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "ACTION: Ask for the EXACT GitHub username, or search github.com" -ForegroundColor Cyan
    Write-Host "Then edit this script: set `$collaborator to their username" -ForegroundColor Green
    exit 1
}

$collaborator = $verifiedUsername
$permission = "pull"  # GitHub API: pull = READ-only

Write-Host ""
Write-Host "Using: $collaborator with permission=$permission" -ForegroundColor Green
Write-Host ""

# ============================================================
# STEP 2: INVITE TO ALL 49 REPOSITORIES
# ============================================================
Write-Host "STEP 2: Sending invitations..." -ForegroundColor Cyan
Write-Host ""

$success = @()
$failed = @()
$skipped = @()

for ($i = 0; $i -lt $repos.Count; $i++) {
    $repo = $repos[$i]
    $num = $i + 1
    Write-Host "[$num/$($repos.Count)] $repo ... " -NoNewline
    
    # Verify repo exists
    gh api "repos/$owner/$repo" --jq ".full_name" 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "REPO NOT FOUND" -ForegroundColor DarkYellow
        $skipped += $repo
        continue
    }
    
    # Check if already has access - PROPER exit-code check
    gh api "repos/$owner/$repo/collaborators/$collaborator" --jq ".permissions.pull" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "ALREADY HAS ACCESS" -ForegroundColor Yellow
        $skipped += $repo
        continue
    }
    
    # Send invitation
    $putOut = gh api -X PUT "repos/$owner/$repo/collaborators/$collaborator" -f permission=$permission 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "INVITED" -ForegroundColor Green
        $success += $repo
    } else {
        $err = ($putOut | Out-String).Trim()
        Write-Host "FAILED: $err" -ForegroundColor Red
        $failed += "$repo : $err"
    }
    
    Start-Sleep -Milliseconds 300
}

# ============================================================
# SUMMARY
# ============================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FINAL SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total: $($repos.Count)" -ForegroundColor White
Write-Host "Invited: $($success.Count)" -ForegroundColor Green
Write-Host "Skipped: $($skipped.Count)" -ForegroundColor Yellow
Write-Host "Failed: $($failed.Count)" -ForegroundColor Red
Write-Host ""

if ($failed.Count -gt 0) {
    Write-Host "Failed repos:" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
}
