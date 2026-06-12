@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [X] .venv not found, run: uv sync
    pause
    exit /b 1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING" 2^>nul') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING" 2^>nul') do taskkill /PID %%a /F >nul 2>&1

echo Starting backend on port 8000...
start "" cmd /k "cd /d %~dp0 && .venv\Scripts\python.exe run.py"

ping -n 4 127.0.0.1 >nul

echo Starting frontend on port 5173...
start "" cmd /k "cd /d %~dp0Coder\web && npm run dev"

echo.
echo Backend : http://localhost:8000
echo Frontend: http://localhost:5173
pause
