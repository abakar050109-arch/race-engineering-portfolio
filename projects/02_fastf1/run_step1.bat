@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

title Step 1 - corners
echo === STEP 1: corner detection ===
echo.
"%PYEXE%" step1_corners.py
echo.
echo Finished. Press any key to close.
pause >nul
