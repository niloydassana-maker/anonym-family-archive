@echo off
REM Whonix launcher - starts Gateway first, waits for Tor, then Workstation
set VBM=C:\Program Files\Oracle\VirtualBox\VBoxManage.exe

echo [1/3] Starting Whonix-Gateway...
"%VBM%" startvm "Whonix-Gateway"

echo [2/3] Waiting 90 seconds for Gateway boot + Tor connection...
timeout /t 90 /nobreak

echo [3/3] Starting Whonix-Workstation...
"%VBM%" startvm "Whonix-Workstation"

echo.
echo Done. Do all private work ONLY inside Whonix-Workstation.
echo Default logins: user / (blank password, set on first boot)
pause
