@echo off
chcp 65001 >nul
title 停止 CourseMade

echo 正在停止 CourseMate...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo 停止后端 (PID %%a)
    taskkill /PID %%a /F >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo 停止前端 (PID %%a)
    taskkill /PID %%a /F >nul 2>&1
)

echo 已停止所有服务。
pause
