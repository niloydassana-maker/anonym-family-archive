Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win {
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr hWnd);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
}
"@

$log = "D:\anonym\delivery\kilo-bridge-setup\evidence\employment-lane\window-restore.log"
$lines = @()

$fg = [Win]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder 512
[void][Win]::GetWindowText($fg, $sb, 512)
$lines += "FOREGROUND_BEFORE: '$($sb.ToString())'"

$chrome = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 }
if (-not $chrome) {
  $lines += "NO_CHROME_MAINWINDOW_FOUND"
} else {
  foreach ($p in $chrome) {
    $h = $p.MainWindowHandle
    $sb2 = New-Object System.Text.StringBuilder 512
    [void][Win]::GetWindowText($h, $sb2, 512)
    $title = $sb2.ToString()
    $iconic = [Win]::IsIconic($h)
    $vis = [Win]::IsWindowVisible($h)
    $lines += "WIN pid=$($p.Id) iconic=$iconic visible=$vis title='$title'"
    if ($title -match 'Chrome') {
      [void][Win]::ShowWindow($h, 9)   # SW_RESTORE
      [void][Win]::BringWindowToTop($h)
      [void][Win]::SetForegroundWindow($h)
      Start-Sleep -Milliseconds 700
      $fg2 = [Win]::GetForegroundWindow()
      $sb3 = New-Object System.Text.StringBuilder 512
      [void][Win]::GetWindowText($fg2, $sb3, 512)
      $lines += "AFTER_ACTIVATE pid=$($p.Id) foreground_now='$($sb3.ToString())'"
    }
  }
}

$lines | ForEach-Object { Write-Output $_ }
$lines | Out-File -FilePath $log -Encoding utf8
