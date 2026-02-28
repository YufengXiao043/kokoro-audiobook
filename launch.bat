@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo Setup is incomplete. Please run setup.bat first.
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "src\launcher.py"
