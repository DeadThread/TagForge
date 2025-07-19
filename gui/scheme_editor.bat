@echo off
REM Change directory to the script location
cd /d "%~dp0"

REM Run the scheme editor Python script with python3 or python
python scheme_editor.py

REM Pause so you can see any output/errors before the window closes
pause