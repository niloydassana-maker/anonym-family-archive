@echo off
title UPGRADE EXISTING DELIVERIES TO FULL CODE PATCHES
color 0A
echo ========================================================
echo  ⚡ REVISIT & UPGRADE PROPOSALS WITH FULL-STACK CODE
echo  Standard: Delete Old Summaries, Deliver Working Code & Tests
echo  Commercial Channel: isearch.xsolve@gmail.com
echo ========================================================
echo.
cd /d D:\anonym
python scripts\autonomous_icu_pipeline.py --upgrade-existing --live
echo.
pause
