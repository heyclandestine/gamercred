@echo off
echo 🎮 Building Gamer Cred Desktop...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

echo Python found. Installing requirements...
pip install -r requirements.txt

echo.
echo Building executable...
python build_exe.py

echo.
echo Build process completed!
echo Check the dist/ folder for your executable.
pause 