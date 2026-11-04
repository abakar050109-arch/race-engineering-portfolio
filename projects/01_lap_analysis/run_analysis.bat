@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================================
echo   Lap analysis
echo ================================================
echo.

python analyze.py

echo.
echo Results are in the "docs" folder next to this file.
echo.
pause
