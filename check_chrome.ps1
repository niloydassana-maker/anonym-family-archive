$procs = Get-Process chrome -ErrorAction SilentlyContinue
foreach ($p in $procs) {
    if ($p.MainWindowTitle -like '*kdp.amazon.com*') {
        Write-Output "PID: $($p.Id) Title: $($p.MainWindowTitle)"
    }
}