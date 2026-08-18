@echo off
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.12 64-bit is required. Install it from https://www.python.org/downloads/
  pause
  exit /b 1
)
py -3.12 live_drone_sim.py --env maze --controller paper --duration 180 --show-neurons
pause
