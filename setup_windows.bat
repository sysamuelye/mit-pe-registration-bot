@echo off
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m playwright install chromium
if errorlevel 1 goto failed
echo Setup complete. Run test_windows.bat first.
pause
exit /b 0
:failed
echo Setup failed. Check the message above. Python 3.10 or newer is required.
pause
exit /b 1
