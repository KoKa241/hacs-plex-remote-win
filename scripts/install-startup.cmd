@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0register-startup.ps1" -StartNow
if errorlevel 1 (
    echo Startup installation failed. See the error above.
    pause
    exit /b 1
)
pause
