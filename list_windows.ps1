Get-Process | Where-Object { $_.MainWindowTitle.Length -gt 0 } | Select-Object ProcessName, MainWindowTitle | Format-Table -AutoSize
