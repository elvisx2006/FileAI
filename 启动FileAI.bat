@echo off
title FileAI
cd /d "%~dp0"

:: 如果 8000 端口已占用，先关闭
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: 激活虚拟环境并启动后端
call backend\venv\Scripts\activate.bat
start /B python run_server.py

:: 等待后端就绪
echo 正在启动 FileAI...
:wait
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if errorlevel 1 goto wait

:: 打开浏览器
start http://127.0.0.1:8000
echo FileAI 已启动: http://127.0.0.1:8000
echo 关闭此窗口将停止服务
pause
