@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM SyncSys 数据库管理脚本
REM 用于Windows环境管理数据库

echo ================================================
echo SyncSys 数据库同步系统 - 数据库管理工具
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
if not exist "db_manager.py" (
    echo 错误: 数据库管理文件 db_manager.py 不存在
    pause
    exit /b 1
)

if not exist "config.json" (
    echo 错误: 配置文件 config.json 不存在
    pause
    exit /b 1
)

:menu
echo.
echo 请选择数据库管理操作:
echo 1. 创建示例Schema文件
echo 2. 从Schema创建表结构
echo 3. 列出所有表
echo 4. 查看表信息
echo 5. 备份数据库
echo 6. 恢复数据库
echo 7. 获取数据库统计信息
echo 8. 检查数据库完整性
echo 9. 压缩数据库
echo 0. 退出
echo.
set /p choice="请输入选择 (0-9): "

if "!choice!"=="1" (
    echo.
    echo 正在创建示例Schema文件...
    python db_manager.py --create-schema
    echo Schema文件创建完成: schema.json
    goto menu
) else if "!choice!"=="2" (
    if exist "schema.json" (
        echo.
        echo 正在从Schema创建表结构...
        python db_manager.py --schema schema.json
        echo 表结构创建完成
    ) else (
        echo.
        echo 错误: schema.json 文件不存在，请先创建Schema文件
    )
    goto menu
) else if "!choice!"=="3" (
    echo.
    echo 数据库表列表:
    python db_manager.py --list
    goto menu
) else if "!choice!"=="4" (
    set /p table_name="请输入表名: "
    echo.
    echo 表 !table_name! 的信息:
    python db_manager.py --info !table_name!
    goto menu
) else if "!choice!"=="5" (
    echo.
    echo 正在备份数据库...
    python db_manager.py --backup
    echo 数据库备份完成
    goto menu
) else if "!choice!"=="6" (
    echo.
    echo 可用的备份文件:
    dir /b *.db 2>nul
    echo.
    set /p backup_file="请输入备份文件名: "
    if exist "!backup_file!" (
        echo 正在恢复数据库...
        python db_manager.py --restore !backup_file!
        echo 数据库恢复完成
    ) else (
        echo 错误: 备份文件 !backup_file! 不存在
    )
    goto menu
) else if "!choice!"=="7" (
    echo.
    echo 数据库统计信息:
    python db_manager.py --stats
    goto menu
) else if "!choice!"=="8" (
    echo.
    echo 正在检查数据库完整性...
    python db_manager.py --check
    goto menu
) else if "!choice!"=="9" (
    echo.
    echo 正在压缩数据库...
    python db_manager.py --vacuum
    echo 数据库压缩完成
    goto menu
) else if "!choice!"=="0" (
    echo 退出数据库管理工具
    exit /b 0
) else (
    echo 无效选择，请重新选择
    goto menu
)

echo.
pause
goto menu