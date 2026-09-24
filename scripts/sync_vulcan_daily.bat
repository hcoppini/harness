@echo off
setlocal
cd /d "%~dp0\.."
py -3.12 scripts\sync_vulcan_daily.py 2>nul || python scripts\sync_vulcan_daily.py
endlocal
