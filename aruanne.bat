@echo off
cd /d "%~dp0"
python -m pctimelogger report
echo.
python -m pctimelogger timeline
pause
