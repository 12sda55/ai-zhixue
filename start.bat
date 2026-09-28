@echo off
chcp 65001 >nul 2>&1
title AI Learning System - 一键启动
echo ============================================
echo    AI 多智能体个性化学习系统 - 一键启动
echo ============================================
echo.

:: 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查 Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js 18+
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

:: 检查后端 .env
if not exist "%~dp0backend\.env" (
    echo [提示] 后端 .env 不存在，从 .env.example 复制...
    copy "%~dp0backend\.env.example" "%~dp0backend\.env" >nul
    echo       请编辑 backend\.env 填入 API Key 后重新启动
    echo.
)

:: 检查前端 node_modules
if not exist "%~dp0frontend\node_modules" (
    echo [提示] 前端依赖未安装，正在安装...
    cd /d "%~dp0frontend"
    npm install
    if %errorlevel% neq 0 (
        echo [错误] 前端依赖安装失败
        pause
        exit /b 1
    )
)

echo [1/3] 启动后端服务 (端口 8000)...
cd /d "%~dp0backend"
start "AI-Learning-Backend" cmd /k "python run.py"
echo       后端服务已启动，等待就绪...
timeout /t 3 /nobreak >nul

echo [2/3] 启动 AI Tutor 服务 (端口 8001，可选)...
cd /d "%~dp0ai-tutor"
if exist app\main.py (
    if exist .env (
        start "AI-Tutor-Service" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8001"
        echo       AI Tutor 服务已启动
    ) else (
        echo [跳过] ai-tutor\.env 不存在，视频生成功能不可用
        echo        如需启用，请复制 .env.example 为 .env 并填入配置
    )
) else (
    echo [跳过] 未检测到 ai-tutor 服务
)

echo [3/3] 启动前端开发服务 (端口 5173)...
cd /d "%~dp0frontend"
start "AI-Learning-Frontend" cmd /k "npm run dev"
echo       前端开发服务已启动

echo.
echo ============================================
echo  启动完成！请稍等几秒后访问:
echo.
echo    http://localhost:5173
echo.
echo  默认账号（首次启动自动创建）:
echo    管理员: admin / admin123
echo    学生:   student1 / 123456
echo.
echo  注意:
echo    - 前端使用 Vite 开发服务器（支持热更新）
echo    - AI Tutor 为可选服务，不影响核心功能
echo    - 如需配置 API Key，请编辑 backend\.env
echo ============================================
echo.
echo 按任意键打开浏览器...
pause >nul
start http://localhost:5173
