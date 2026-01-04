@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM SyncSys 处理器启动脚本
REM 用于Windows环境快速启动处理器

echo ================================================
echo SyncSys 数据库同步系统 - 处理器启动脚本
echo ================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.7或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 显示Python版本
echo 检测到Python版本:
python --version
echo.

REM 检查配置文件
if not exist "config.json" (
    echo 错误: 配置文件 config.json 不存在
    echo 请先配置系统参数
    pause
    exit /b 1
)

REM 检查核心文件
if not exist "syncsys_core.py" (
    echo 错误: 核心文件 syncsys_core.py 不存在
    pause
    exit /b 1
)

if not exist "start_processor.py" (
    echo 错误: 启动文件 start_processor.py 不存在
    pause
    exit /b 1
)

echo 正在检查系统环境...
echo.

REM 询问是否初始化数据库
set /p init_db="是否需要初始化数据库? (y/N): "
if /i "!init_db!"=="y" (
    echo 正在初始化数据库...
    if exist "schema.json" (
        python start_processor.py --init-db --schema schema.json
    ) else (
        python start_processor.py --init-db
    )
    if errorlevel 1 (
        echo 数据库初始化失败
        pause
        exit /b 1
    )
    echo 数据库初始化完成
    echo.
)

echo 启动处理器...
echo 按 Ctrl+C 停止处理器
echo ================================================
echo.

REM 启动处理器
python start_processor.py

echo.
echo 处理器已停止
pause