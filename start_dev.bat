@echo off
chcp 65001 >nul
title CourseMate 开发服务器

:: 处理 5173 端口占用
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo 端口 5173 被 PID %%a 占用，正在释放...
    taskkill /PID %%a /F >nul 2>&1
)

:: 启动后端
echo === 启动后端 (端口 8000) ===
start "CourseMate Backend" cmd /c "python run.py"

:: 启动前端
echo === 启动前端 (端口 5173) ===
start "CourseMate Frontend" cmd /c "cd Coder\web && npm run dev"

echo.
echo 后端: http://localhost:8000
echo 前端: http://localhost:5173
echo 关闭窗口以停止服务，或直接关闭两个子窗口。
pause
