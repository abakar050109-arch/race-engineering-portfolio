@echo off
chcp 65001 >nul
cd /d "%~dp0"

title Project 02 - corner comparison
echo Building the per-corner comparison for Abu Dhabi 2021...
echo.

python step2_corner_compare.py

echo.
echo Done. Press any key to close.
pause >nul
