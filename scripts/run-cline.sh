#!/usr/bin/env bash
set -euo pipefail

TARGET_REPO="${TARGET_REPO:-unknown/repo}"
ISSUE_NUMBER="${ISSUE_NUMBER:-0}"
CLINE_TIMEOUT="${CLINE_TIMEOUT:-3600}"

echo "=== STARTING CLINE ENGINEERING TURN ==="
echo "Target: ${TARGET_REPO}#${ISSUE_NUMBER}"
echo "Runway budget: ${CLINE_TIMEOUT}s"

# Prepare issue context
CONTEXT_FILE="../harness/issue_context.json"
if [ ! -f "$CONTEXT_FILE" ]; then
    echo "Fetching issue #${ISSUE_NUMBER} details from GitHub..."
    gh issue view "$ISSUE_NUMBER" --repo "$TARGET_REPO" --json number,title,body,labels,author > "$CONTEXT_FILE" || echo "{}" > "$CONTEXT_FILE"
fi

echo "Injecting issue instructions into workspace..."
PROMPT="You are resolving issue #${ISSUE_NUMBER} in repository ${TARGET_REPO}.
Read the full requirements, reproduce with a test, implement the minimal correct change, and ensure 100% existing tests pass.
Do not modify workflows, CI secrets, or licensing. Follow repository native conventions."

# Ensure TokenHarbor Proxy is running for Cline turn
export OPENAI_BASE_URL="http://127.0.0.1:8080/v1"
export OPENAI_API_KEY="tokenharbor"

if [ -f "../harness/scripts/tokenharbor_cline_proxy.py" ]; then
    echo "Starting TokenHarbor Proxy in background..."
    python3 ../harness/scripts/tokenharbor_cline_proxy.py &
    for i in {1..10}; do
        if curl -s http://127.0.0.1:8080/health >/dev/null 2>&1; then
            echo "✓ TokenHarbor Proxy is healthy on 127.0.0.1:8080"
            break
        fi
        sleep 1
    done
fi

# Execute Cline turn with timeout guard
if command -v cline >/dev/null 2>&1; then
    timeout "$CLINE_TIMEOUT" cline -y --auto-approve true -P openai-compatible -m deepseek-v4.1-flash:free --cwd "$(pwd)" "$PROMPT" || echo "Cline execution finished."
else
    echo "Running local engineering repair fallback turn..."
    # Local fallback runner if cline CLI is packaged via npx or python
    if [ -f "../harness/scripts/cline_runner.py" ]; then
        python3 ../harness/scripts/cline_runner.py "$PROMPT"
    fi
fi

echo "✓ Cline turn completed."
