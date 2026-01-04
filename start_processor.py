#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步处理器启动脚本
用于启动处理设备上的同步处理器
"""

import sys
import os
import signal
import time
import argparse
from pathlib import Path
from syncsys_core import SyncProcessor
from db_manager import DatabaseInitializer
import logging

def setup_signal_handlers(processor):
    """设置信号处理器"""
    def signal_handler(signum, frame):
        print("\n接收到停止信号，正在关闭处理器...")
        processor.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def check_environment(config_path):
    """检查运行环境"""
    if not os.path.exists(config_path):
        print(f"错误: 配置文件 {config_path} 不存在")
        return False
    
    try:
        from syncsys_core import ConfigManager
        config = ConfigManager(config_path)
        
        # 检查共享文件夹路径
        request_folder = config.get('shared_folder.requests')
        response_folder = config.get('shared_folder.responses')
        db_path = config.get('database.path')
        
        # 创建必要的目录
        for folder in [request_folder, response_folder, os.path.dirname(db_path)]:
            if folder:
                os.makedirs(folder, exist_ok=True)
                print(f"确保目录存在: {folder}")
        
        return True
        
    except Exception as e:
        print(f"环境检查失败: {e}")
        return False

def init_database(config_path, schema_file=None):
    """初始化数据库"""
    try:
        db_init = DatabaseInitializer(config_path)
        
        if schema_file and os.path.exists(schema_file):
            print(f"从 {schema_file} 创建表结构...")
            db_init.create_tables_from_schema(schema_file)
        
        print("数据库初始化完成")
        return True
        
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='同步处理器启动脚本')
    parser.add_argument('--config', '-c', default='config.json', help='配置文件路径')
    parser.add_argument('--schema', '-s', help='数据库schema文件路径')
    parser.add_argument('--init-db', action='store_true', help='初始化数据库')
    parser.add_argument('--daemon', '-d', action='store_true', help='以守护进程模式运行')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='日志级别')
    
    args = parser.parse_args()
    
    # 设置日志级别
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 50)
    print("SyncSys 同步处理器")
    print("=" * 50)
    
    # 检查环境
    print("检查运行环境...")
    if not check_environment(args.config):
        sys.exit(1)
    
    # 初始化数据库
    if args.init_db or args.schema:
        print("初始化数据库...")
        if not init_database(args.config, args.schema):
            sys.exit(1)
    
    # 创建处理器
    try:
        processor = SyncProcessor(args.config)
        setup_signal_handlers(processor)
        
        print(f"使用配置文件: {args.config}")
        print("启动同步处理器...")
        
        processor.start()
        
        print("同步处理器已启动")
        print("按 Ctrl+C 停止处理器")
        print("-" * 50)
        
        # 主循环
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)
    
    finally:
        print("\n正在停止处理器...")
        try:
            processor.stop()
        except:
            pass
        print("处理器已停止")

if __name__ == "__main__":
    main()