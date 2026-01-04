@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM SyncSys 系统监控脚本
REM 用于Windows环境监控系统状态

echo ================================================
echo SyncSys 数据库同步系统 - 系统监控工具
echo ================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.7或更高版本
    pause
    exit /b 1
)

REM 检查必要文件
if not exist "system_monitor.py" (
    echo 错误: 监控文件 system_monitor.py 不存在
    pause
    exit /b 1
)

if not exist "config.json" (
    echo 错误: 配置文件 config.json 不存在
    pause
    exit /b 1
)

echo 请选择监控模式:
echo 1. 单次检查系统状态
echo 2. 生成健康报告
echo 3. 持续监控 (30秒间隔)
echo 4. 持续监控 (自定义间隔)
echo 5. 退出
echo.
set /p choice="请输入选择 (1-5): "

if "!choice!"=="1" (
    echo.
    echo 正在检查系统状态...
    python system_monitor.py
) else if "!choice!"=="2" (
    echo.
    echo 正在生成健康报告...
    python system_monitor.py --report
) else if "!choice!"=="3" (
    echo.
    echo 开始持续监控 (30秒间隔)...
    echo 按 Ctrl+C 停止监控
    echo.
    python system_monitor.py --continuous 30 --report
) else if "!choice!"=="4" (
    set /p interval="请输入监控间隔秒数: "
    echo.
    echo 开始持续监控 (!interval!秒间隔)...
    echo 按 Ctrl+C 停止监控
    echo.
    python system_monitor.py --continuous !interval! --report
) else if "!choice!"=="5" (
    echo 退出监控工具
    exit /b 0
) else (
    echo 无效选择，请重新运行脚本
)

echo.
echo 监控完成
pause