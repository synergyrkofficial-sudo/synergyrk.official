@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

:: Ensure Virtual Environment exists
if not exist ".venv" (
    echo [INFO] Creating .venv for Python 3.13...
    python -m venv .venv
)

:: Activate and Install
echo [INFO] Updating dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install flask flask-cors

:: Start Backend in a separate visible window for debugging
echo [INFO] Launching Synergy RK Backend...
start "Synergy_Backend" cmd /k "".venv\Scripts\python.exe" app.py"

:: Wait for startup then open dashboard
timeout /t 3
start "" "index.html"

echo [SUCCESS] Synergy RK is initializing. Check the other window for logs.
pause