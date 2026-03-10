@echo off
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found! Please install Python first.
    pause
    exit /b 1
)

echo Installing required libraries...
pip install pyautogui opencv-python -q

echo Running script...
python find_and_click.py
pause
