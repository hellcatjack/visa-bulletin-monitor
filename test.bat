@echo off
chcp 65001 >nul
echo ===================================
echo Testing SMS Notification
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

python main.py --mode test

echo.
pause
