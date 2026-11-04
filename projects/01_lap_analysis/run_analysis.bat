@echo off
chcp 65001 >nul
cd /d "%~dp0"

title Lap analysis

rem Use Python 3.11 explicitly: it already has pandas, numpy and matplotlib.
rem Plain "python" may resolve to the Microsoft Store stub, which does nothing
rem and exits with code 0, so the analysis would silently never run.
set "PYEXE=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

echo Running lap analysis with:
echo   %PYEXE%
echo.

"%PYEXE%" analyze.py
set RC=%ERRORLEVEL%

if not "%RC%"=="0" (
    echo.
    echo Something went wrong. Please read the message above.
    if /i "%~1"=="silent" exit /b %RC%
    pause
    exit /b %RC%
)

echo.
echo Done. Opening the results folder...
start "" "%~dp0docs"
exit /b 0
