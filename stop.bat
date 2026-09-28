@echo off
chcp 65001 >nul 2>&1
title AI Learning System - 停止服务
echo ============================================
echo    AI 多智能体个性化学习系统 - 停止服务
echo ============================================
echo.

echo 正在停止后端服务...
taskkill /fi "WINDOWTITLE eq AI-Learning-Backend*" /f >nul 2>&1

echo 正在停止 AI Tutor 服务...
taskkill /fi "WINDOWTITLE eq AI-Tutor-Service*" /f >nul 2>&1

echo 正在停止前端服务...
taskkill /fi "WINDOWTITLE eq AI-Learning-Frontend*" /f >nul 2>&1

echo.
echo 所有服务已停止
pause
