#!/bin/bash
#
# Bulk GitHub collaborator invitation script for 49 repositories
# Grants READ-only access to prafullprince12@gmail.com
#
# PREREQUISITES
#   - GitHub CLI (gh) installed and authenticated with admin:repo_hook or repo scope
#   - Run: gh auth login --scopes admin:repo_hook,repo
#
# USAGE
#   chmod +x invite_collaborator.sh
#   ./invite_collaborator.sh

set -euo pipefail

# 49 Measured Repositories - verbatim from corpus-final.json
repos=(
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

collaborator="prafullprince12"
permission="read"  # READ-only access
owner="isearchxsolve"

echo "Starting bulk collaborator invitation for ${#repos[@]} repositories..."
echo "Target: $collaborator with $permission access"
echo "Owner: $owner"
echo ""

success=0
failed=0
already=0

for repo in "${repos[@]}"; do
    echo -n "Processing: $repo ... "
    
    # Check if already a collaborator
    if gh api "repos/$owner/$repo/collaborators/$collaborator" --jq '.permissions' >/dev/null 2>&1; then
        echo "ALREADY COLLABORATOR"
        ((already++))
        continue
    fi
    
    # Add collaborator with read permission
    if gh api -X PUT "repos/$owner/$repo/collaborators/$collaborator" -f permission="$permission" --silent 2>/dev/null; then
        echo "INVITED (read-only)"
        ((success++))
    else
        echo "FAILED"
        ((failed++))
    fi
    
    # Rate limit courtesy delay
    sleep 0.5
done

echo ""
echo "========================================"
echo "SUMMARY"
echo "========================================"
echo "Total repositories: ${#repos[@]}"
echo "Successfully invited: $success"
echo "Already collaborators: $already"
echo "Failed: $failed"
echo ""

if [ $failed -gt 0 ]; then
    echo "Check failed repositories manually via GitHub web UI."
fi