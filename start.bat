@echo off
chcp 65001 >nul
echo ===================================
echo US Visa Bulletin Monitor
echo ===================================
echo.

cd /d "%~dp0"

:: Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env and configure your Twilio credentials.
    echo.
    pause
    exit /b 1
)

echo Starting monitor in scheduled mode...
echo Press Ctrl+C to stop
echo.

python main.py --mode schedule

pause
