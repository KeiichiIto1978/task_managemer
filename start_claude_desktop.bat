@echo off
setlocal
cd /d %~dp0

REM Refresh Google tokens (if enabled) and launch Claude Desktop.
python scripts\start_claude_desktop.py %*

endlocal

pause
