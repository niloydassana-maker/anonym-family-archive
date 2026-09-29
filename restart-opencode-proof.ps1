# restart-opencode-proof.ps1 — kill + fresh-start opencode with logged proof at every step.
# Usage: powershell -ExecutionPolicy Bypass -File D:\anonym\restart-opencode-proof.ps1
# Log:   D:\anonym\war-log\restart-proof-<timestamp>.log
# Exit 0 = every proof passed. Exit 1 = named step failed (see log tail).
$ErrorActionPreference = "Continue"
$EXE = "C:\Users\Admin\AppData\Local\hermes\node\node_modules\opencode-ai\bin\opencode.exe"
$STAMP = Get-Date -Format "yyyyMMddTHHmmss"
$LOG = "D:\anonym\war-log\restart-proof-$STAMP.log"
function Say($m) { $line = "$(Get-Date -Format o) $m"; $line | Tee-Object -FilePath $LOG -Append | Out-String | Write-Host }
function Fail($m) { Say "PROOF-FAIL: $m"; exit 1 }
if (!(Test-Path -LiteralPath $EXE)) { Fail "opencode exe missing: $EXE" }
Say "PROOF-START restart-opencode-proof $STAMP"
# 1. BEFORE: record live PIDs
$before = @(Get-Process -Name opencode -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
Say "PROOF-1 before-pids: $($before -join ',')"
if (!$before.Count) { Say "PROOF-1 note: no opencode running (clean start)"; }
# 2. KILL: graceful, then force; prove zero remain
foreach ($opid in $before) { try { Stop-Process -Id $opid -Force -ErrorAction Stop; Say "PROOF-2 killed $opid" } catch { Say "PROOF-2 kill-note $opid : $($_.Exception.Message)" } }
Start-Sleep -Seconds 5
$left = @(Get-Process -Name opencode -ErrorAction SilentlyContinue)
if ($left.Count) { Fail "opencode still alive: $($left.Id -join ',')" }
Say "PROOF-2 zero-processes-confirmed"
# 3. START fresh (detached TUI window Baba can see)
$app = Start-Process -FilePath $EXE -WorkingDirectory "D:\anonym" -PassThru
Say "PROOF-3 started pid=$($app.Id)"
Start-Sleep -Seconds 10
if ($app.HasExited) { Fail "opencode exited immediately after start" }
Say "PROOF-3 alive pid=$($app.Id)"
# 4. NEW PID differs from all before-PIDs
if ($before -contains $app.Id) { Fail "pid reused ($($app.Id)) not a fresh process" }
Say "PROOF-4 fresh-pid-confirmed $($app.Id) not in [$($before -join ',')]"
# 5. MCP: browser-mcp connected via `opencode mcp list` (60s budget)
$ok = $false
for ($i = 0; $i -lt 6; $i++) {
  $out = & $EXE mcp list 2>&1 | Out-String
  if ($out -match 'browser-mcp' -and $out -match 'connected') { $ok = $true; break }
  Say "PROOF-5 retry $($i): waiting for browser-mcp connected"
  Start-Sleep -Seconds 10
}
if (!$ok) { Fail "browser-mcp not connected after 60s. Last output: $out" }
Say "PROOF-5 browser-mcp-connected"
# 6. SERVER PROCESS: node cli.js child alive
$node = cmd /c "wmic process where (Name='node.exe') get CommandLine 2>&1" | Select-String 'browser-mcp'
if (!$node) { Fail "no node browser-mcp process found" }
Say "PROOF-6 server-process: $($node.Line.Trim().Substring(0,120))"
Say "PROOF-DONE all proofs passed. Log: $LOG"
exit 0
