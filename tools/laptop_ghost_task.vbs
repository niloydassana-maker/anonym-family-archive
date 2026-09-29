' KILO-LAPTOP-GHOST-LOGON zero-popup launcher
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""D:\anonym\tools\laptop-ghost.ps1""", 0, False
