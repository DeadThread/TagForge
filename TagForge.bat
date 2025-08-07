@echo off
setlocal

set "SCRIPT=TagForge.py"
set "PYTHON_EXEC=python"
set "SCRIPT_PATH=%~dp0%SCRIPT%"

echo Launching %SCRIPT_PATH%...
"%PYTHON_EXEC%" "%SCRIPT_PATH%"

pause
