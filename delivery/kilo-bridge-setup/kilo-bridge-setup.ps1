<#
  Kilo Bridge client setup and employment mission-agent launcher.
  All package paths are rooted at this script; no D:\anonym, vault, OpenCode,
  model key, or machine-specific project config is read or edited.

  Launch the configured mission agent:
    powershell -ExecutionPolicy Bypass -File .\kilo-bridge-setup.ps1 -Launch
  One real, explicitly authorized Naukri application:
    powershell -ExecutionPolicy Bypass -File .\kilo-bridge-setup.ps1 -Launch `
      -SubmitOne -Title "Exact matched role title"
  Install the Agent360 MCP package locally in this folder if missing:
    powershell -ExecutionPolicy Bypass -File .\kilo-bridge-setup.ps1 -InstallMcp
#>
[CmdletBinding()]
param(
    [switch]$Launch,
    [switch]$SubmitOne,
    [switch]$InstallMcp,
    [string]$Title,
    [string]$CandidateConfig = 'candidate-profile.json'
)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Scripts = Join-Path $Root 'scripts'
$Evidence = Join-Path $Root 'evidence\employment-lane'
$Runtime = Join-Path $Root '.runtime'
$Py = $null
$Node = $null
$Mcp = $null
$OpenCode = $null

function Fail([string]$Message) {
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    exit 1
}

Write-Host 'Kilo Bridge standalone employment agent launcher' -ForegroundColor Cyan
Write-Host "Package root: $Root"

if ($SubmitOne -and -not $Launch) { Fail '-SubmitOne requires -Launch.' }
if ($SubmitOne -and [string]::IsNullOrWhiteSpace($Title)) { Fail '-SubmitOne requires -Title with the exact current matched role.' }
if (-not $SubmitOne -and -not [string]::IsNullOrWhiteSpace($Title)) { Fail '-Title is only used with -SubmitOne.' }

# Prefer a packaged interpreter, but the automation itself uses only Python stdlib.
$PackagedPy = Join-Path $Root 'venv\Scripts\python.exe'
if (Test-Path $PackagedPy) { $Py = $PackagedPy }
else {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCommand) { $Py = $PythonCommand.Source }
}
if (-not $Py) { Fail 'Python 3 is required. Install Python 3.11+ and rerun.' }
$PyParts = @(& $Py -c 'import sys; print(sys.version_info[0]); print(sys.version_info[1])')
$PyVersion = "$($PyParts[0]).$($PyParts[1])"
if ($PyVersion -notmatch '^3\.(1[1-9]|[2-9][0-9])$') { Fail "Python 3.11+ required; found $PyVersion" }
Write-Host "[ OK ] Python $PyVersion ($Py)" -ForegroundColor Green

$HermesNode = Join-Path $env:LOCALAPPDATA 'hermes\node\node.exe'
if (Test-Path $HermesNode) { $Node = $HermesNode }
else {
    $NodeCommand = Get-Command node -ErrorAction SilentlyContinue
    if ($NodeCommand) { $Node = $NodeCommand.Source }
}
if (-not $Node) { Fail 'Node.js is required for Agent360 MCP. Install Node.js 20+ and rerun.' }
$NodeVersion = (& $Node --version).Trim()
if ($NodeVersion -notmatch '^v?(\d+)\.') { Fail "Could not parse Node.js version: $NodeVersion" }
if ([int]$Matches[1] -lt 20) { Fail "Node.js 20+ required for Agent360 MCP; found $NodeVersion" }
Write-Host "[ OK ] Node $NodeVersion" -ForegroundColor Green

$Candidates = @(
    (Join-Path $Runtime 'node_modules\@agent360\browser-mcp\index.js'),
    (Join-Path $env:LOCALAPPDATA 'hermes\node\node_modules\@agent360\browser-mcp\index.js'),
    (Join-Path $env:APPDATA 'npm\node_modules\@agent360\browser-mcp\index.js')
)
$Mcp = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Mcp -and $InstallMcp) {
    $Npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $Npm) { Fail 'npm was not found. Install Node.js with npm or provide Agent360 MCP.' }
    New-Item -ItemType Directory -Force -Path $Runtime | Out-Null
    Write-Host 'Installing @agent360/browser-mcp locally in the package folder...'
    & $Npm.Source install --prefix $Runtime --no-save '@agent360/browser-mcp@latest'
    if ($LASTEXITCODE -ne 0) { Fail "Agent360 MCP install failed (exit $LASTEXITCODE)." }
    $Mcp = Join-Path $Runtime 'node_modules\@agent360\browser-mcp\index.js'
}
if (-not $Mcp -or -not (Test-Path $Mcp)) { Fail 'Agent360 browser-mcp missing. Run once with -InstallMcp.' }
Write-Host "[ OK ] Agent360 MCP: $Mcp" -ForegroundColor Green

$OpenCodeCandidates = @(
    (Join-Path $env:LOCALAPPDATA 'hermes\node\node_modules\opencode-ai\bin\opencode.exe'),
    (Join-Path $env:APPDATA 'npm\opencode.cmd'),
    (Join-Path $env:LOCALAPPDATA 'Programs\opencode\opencode.exe')
)
$OpenCode = $OpenCodeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $OpenCode) {
    $OpenCodeCommand = Get-Command opencode -ErrorAction SilentlyContinue
    if ($OpenCodeCommand) { $OpenCode = $OpenCodeCommand.Source }
}
if (-not $OpenCode) { Fail 'OpenCode CLI is required to launch the mission agent. Install/configure OpenCode and Agent360 MCP, then rerun.' }

$Required = @('agent360_client.py','lane_tools.py','prove_lane.py','lane_resume.py',
              'lane_jobs.py','lane_foundit.py','lane_market_probe.py','lane_apply.py',
              'apply_answers.example.txt')
foreach ($Name in $Required) {
    if (-not (Test-Path (Join-Path $Scripts $Name))) { Fail "Package file missing: scripts\$Name" }
}
if (-not (Test-Path (Join-Path $Root 'candidate-profile.example.json'))) { Fail 'Package file missing: candidate-profile.example.json' }

# Installation/setup must be possible before per-candidate private data is configured.
if (-not $Launch) {
    Write-Host "`nSETUP-VERDICT: READY" -ForegroundColor Green
    Write-Host 'Agent360 and package files are available. Copy candidate-profile.example.json to candidate-profile.json, fill in verified candidate settings, then run -Launch.'
    exit 0
}

$ConfigPath = if ([IO.Path]::IsPathRooted($CandidateConfig)) { $CandidateConfig } else { Join-Path $Root $CandidateConfig }
if (-not (Test-Path $ConfigPath)) { Fail "Candidate config missing: $ConfigPath. Copy candidate-profile.example.json to candidate-profile.json and set your own resume path/hash/skills/answers file." }
$Config = Get-Content -Raw -Path $ConfigPath | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($Config.resume_path) -or [string]::IsNullOrWhiteSpace($Config.resume_sha256)) { Fail 'Candidate config must include resume_path and resume_sha256.' }
if ($Config.resume_sha256 -notmatch '^[A-Fa-f0-9]{64}$') { Fail 'Candidate config resume_sha256 must be a 64-character SHA256 hex digest.' }
$Resume = if ([IO.Path]::IsPathRooted($Config.resume_path)) { $Config.resume_path } else { Join-Path (Split-Path $ConfigPath -Parent) $Config.resume_path }
if (-not (Test-Path $Resume)) { Fail "Candidate resume is missing: $Resume" }
$ResumeHash = (Get-FileHash -Algorithm SHA256 $Resume).Hash
if ($ResumeHash -ne $Config.resume_sha256.ToUpperInvariant()) { Fail "Candidate resume hash mismatch: $ResumeHash" }
if ([string]::IsNullOrWhiteSpace($Config.answers_file)) { Fail 'Candidate config must include answers_file.' }
$AnswersPath = if ([IO.Path]::IsPathRooted($Config.answers_file)) { $Config.answers_file } else { Join-Path (Split-Path $ConfigPath -Parent) $Config.answers_file }
if (-not (Test-Path $AnswersPath)) { Fail "Candidate answer file is missing: $AnswersPath. Copy scripts\apply_answers.example.txt to your configured private answer file." }
if ($Config.skills -isnot [array] -or $Config.skills.Count -lt 2) { Fail 'Candidate config skills must be an array with at least two verified resume skills.' }
$env:KILO_CANDIDATE_CONFIG = $ConfigPath
Write-Host '[ OK ] Candidate resume hash and answer file verified' -ForegroundColor Green

$MissionFiles = @(
    (Join-Path $Root 'MISSION-RUN.txt'),
    (Join-Path $Root 'docs\AGENTS-EMPLOYMENT.md'),
    (Join-Path $Root 'docs\EMPLOYMENT-LANE-MISSION.md'),
    (Join-Path $Root 'docs\PACE.md'),
    (Join-Path $Evidence 'ledger.tsv')
)
foreach ($Path in $MissionFiles) {
    if (-not (Test-Path -LiteralPath $Path)) { Fail "Mission input missing: $Path" }
}

$env:KILO_AGENT360_NODE = $Node
$env:KILO_AGENT360_MCP_ENTRYPOINT = $Mcp
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null
$RunLog = Join-Path $Evidence 'mission-agent-run.log'
$RunOutput = Join-Path $Evidence 'mission-agent-output.txt'
$Prompt = @'
Execute the employment mission now using the attached mission files and the configured Agent360 browser MCP. This is an agent mission launch, not a lane-test command. Do not invoke kilo-bridge-setup.ps1 -Launch recursively: this launcher has already completed environment and candidate preflight. Read the attached files in their prescribed order, inspect the current ledger chronologically, and perform the next authorized mission actions through the browser MCP tools. Keep receipts in the package evidence folder and report completed, blocked, and pending work honestly. Follow every approval, candidate-fact, dedupe, and submission rule in the mission documents.
'@
if ($SubmitOne) {
    $Prompt += "`nFor this run only, limit application submission to the exact currently matched role title: $Title. Verify title and employer in the live UI and candidate facts before any submit; never submit another role."
}

Write-Host "`nLaunching OpenCode mission agent (no deterministic/live lane test loop will run)." -ForegroundColor Cyan
Write-Host "Agent CLI: $OpenCode"
Write-Host "Mission receipts: $Evidence"
Write-Host "Agent log: $RunLog"
$AgentArgs = @('run',$Prompt,'--dir',$Root,'--title','Kilo Bridge employment mission')
foreach ($Path in $MissionFiles) { $AgentArgs += @('--file',$Path) }
$Started = Get-Date
"[$($Started.ToString('s'))] Agent mission started; launcher preflight passed." | Set-Content -LiteralPath $RunLog -Encoding UTF8
$PreviousErrorActionPreference = $ErrorActionPreference
try {
    # External CLI errors should be captured and reported through the exit code,
    # not converted into a terminating PowerShell NativeCommandError.
    $ErrorActionPreference = 'Continue'
    & $OpenCode @AgentArgs 2>&1 | Tee-Object -FilePath $RunOutput -Append | ForEach-Object {
        Write-Host $_
        Add-Content -LiteralPath $RunLog -Value $_ -Encoding UTF8
    }
}
finally { $ErrorActionPreference = $PreviousErrorActionPreference }
$AgentExit = $LASTEXITCODE
"[$((Get-Date).ToString('s'))] Agent mission ended; exitcode=$AgentExit" | Add-Content -LiteralPath $RunLog -Encoding UTF8
if ($AgentExit -ne 0) { Fail "OpenCode mission agent exited with code $AgentExit. Review $RunOutput and the latest ledger/screenshot before retrying." }
Write-Host "`nMISSION-AGENT-VERDICT: agent process exited successfully; inspect its receipts and final report before treating any task as complete." -ForegroundColor Green
Write-Host "Agent output: $RunOutput"
Write-Host "Agent log: $RunLog"
Write-Host "Receipts: $Evidence"
