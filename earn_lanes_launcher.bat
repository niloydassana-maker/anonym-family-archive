@echo off
REM EARN-LANES TICK LAUNCHER
REM Schedule with Windows Task Scheduler: Run at 14 minutes past every hour
REM Action: cmd.exe /c "D:\anonym\earn_lanes_launcher.bat"

cd /d D:\anonym
python earn_lanes_tick.py --once >> war-log/tick.log 2>&1