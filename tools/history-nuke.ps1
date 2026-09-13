# HISTORY-NUKE v1 - kills chrome-army browsing history, restarts it with tabs intact.
# History files (History, Top Sites, Shortcuts, Favicons, "Network Action Predictor") get deleted while chrome is down;
# TABS SURVIVE (Sessions/Session Restore untouched) and cookies stay (LinkedIn/KDP logins intact).
$ErrorActionPreference = 'Continue'
$log = 'D:\anonym\war-log\history-nuke.log'
function L($m) { Add-Content -LiteralPath $log -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $m" }
L "HISTORY-NUKE START"
$prof = 'D:\anonym\chrome-army'

# 1. kill chrome-army by cmdline match (Baba's main chrome untouched)
$killed = 0
foreach ($p in @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -match 'chrome-army' })) {
    try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop; $killed++ } catch {}
}
L "killed $killed chrome-army processes (main chrome untouched)"
Start-Sleep -Seconds 3

# 2. delete history artifacts in every profile dir
$targets = 'History','History-journal','Top Sites','Top Sites-journal','Shortcuts','Shortcuts-journal','Favicons','Favicons-journal','Login Data-journal'
$deleted = 0
foreach ($pd in (Get-ChildItem $prof -Directory -EA SilentlyContinue | Where-Object { Test-Path (Join-Path $_.FullName 'Preferences') })) {
    foreach ($t in $targets) {
        $f = Join-Path $pd.FullName $t
        if (Test-Path $f) { try { Remove-Item -LiteralPath $f -Force -ErrorAction Stop; $deleted++ } catch { L "in-use skip: $f" } }
    }
}
L "deleted $deleted history files"

# 3. relaunch identical to watchdog recipe
Start-Process -FilePath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList '--remote-debugging-port=9224','--remote-allow-origins=*','--user-data-dir=D:\anonym\chrome-army','--no-first-run','--no-default-browser-check','https://www.linkedin.com/feed/'
Start-Sleep -Seconds 8
try { $null = Invoke-RestMethod 'http://127.0.0.1:9224/json/version' -TimeoutSec 10; L "CHROME BACK UP on 9224" } catch { L "CHROME NOT BACK by timeout - watchdog will retry" }
L "HISTORY-NUKE DONE"
