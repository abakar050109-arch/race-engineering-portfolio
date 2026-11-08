@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

title Step 2 - corner comparison
echo === STEP 2: per-corner comparison ===
echo.
"%PYEXE%" step2_corner_compare.py
echo.
echo Finished. Press any key to close.
pause >nul
