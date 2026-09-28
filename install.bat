@echo off
chcp 65001 >nul 2>&1
title AI Learning System - 一键安装依赖
echo ============================================
echo    AI 多智能体个性化学习系统 - 依赖安装
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

echo [1/3] 安装后端 Python 依赖...
cd /d "%~dp0backend"
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [错误] 后端依赖安装失败
    pause
    exit /b 1
)
echo       后端依赖安装完成

echo [2/3] 安装 AI Tutor Python 依赖（可选，视频生成功能需要）...
cd /d "%~dp0ai-tutor"
if exist requirements.txt (
    echo       检测到 ai-tutor 目录，正在安装依赖（可能需要较长时间）...
    pip install -r requirements.txt -q
    if %errorlevel% neq 0 (
        echo [警告] ai-tutor 依赖安装失败，视频生成功能将不可用
        echo        其他功能不受影响
    ) else (
        echo       ai-tutor 依赖安装完成
    )
) else (
    echo       未检测到 ai-tutor 目录，跳过
)

echo [3/3] 安装前端 Node.js 依赖...
cd /d "%~dp0frontend"
if not exist node_modules (
    npm install
    if %errorlevel% neq 0 (
        echo [错误] 前端依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo       前端依赖已存在，跳过安装
)
echo       前端依赖安装完成

echo.
echo ============================================
echo  所有依赖安装完成！
echo  请运行 start.bat 启动系统
echo ============================================
pause
