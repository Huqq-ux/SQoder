@echo off
title 停止 CourseMate

echo Stopping CourseMate...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING" 2^>nul') do (
    echo Stop backend (PID %%a)
    taskkill /PID %%a /F >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING" 2^>nul') do (
    echo Stop frontend (PID %%a)
    taskkill /PID %%a /F >nul 2>&1
)

echo All services stopped.
pause
