@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo    SyncSys 快速开始演示
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python
    echo 请先安装 Python 3.7 或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查核心文件
if not exist "syncsys_core.py" (
    echo 错误: 未找到 syncsys_core.py
    echo 请确保在正确的目录中运行此脚本
    pause
    exit /b 1
)

if not exist "syncsys_client.py" (
    echo 错误: 未找到 syncsys_client.py
    echo 请确保在正确的目录中运行此脚本
    pause
    exit /b 1
)

if not exist "quick_start.py" (
    echo 错误: 未找到 quick_start.py
    echo 请确保在正确的目录中运行此脚本
    pause
    exit /b 1
)

echo 检查完成，开始运行演示...
echo.

REM 运行快速开始演示
python quick_start.py

if errorlevel 1 (
    echo.
    echo 演示运行出现错误
    pause
    exit /b 1
)

echo.
echo 演示完成！
pause