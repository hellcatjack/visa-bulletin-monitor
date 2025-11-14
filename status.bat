@echo off
chcp 65001 >nul
echo ===================================
echo Checking Monitor Status
echo ===================================
echo.

cd /d "%~dp0"

python main.py --mode status

echo.
pause
