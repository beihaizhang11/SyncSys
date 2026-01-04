#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速开始脚本
帮助用户快速设置和测试SyncSys系统
"""

import os
import sys
import json
import time
import tempfile
import threading
from pathlib import Path
from syncsys_core import SyncProcessor
from syncsys_client import SyncClient
from db_manager import DatabaseInitializer

class QuickStart:
    """快速开始助手"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.demo_dir = None
        self.processor = None
        self.processor_thread = None
        
    def welcome(self):
        """显示欢迎信息"""
        print("=" * 60)
        print("🚀 欢迎使用 SyncSys 快速开始向导")
        print("=" * 60)
        print()
        print("这个向导将帮助您：")
        print("1. 创建演示环境")
        print("2. 初始化数据库")
        print("3. 启动处理器")
        print("4. 运行客户端示例")
        print("5. 展示系统功能")
        print()
    
    def setup_demo_environment(self):
        """设置演示环境"""
        print("📁 设置演示环境...")
        
        # 创建临时演示目录
        self.demo_dir = Path(tempfile.mkdtemp(prefix="syncsys_demo_"))
        print(f"演示目录: {self.demo_dir}")
        
        # 创建子目录
        (self.demo_dir / "requests").mkdir()
        (self.demo_dir / "responses").mkdir()
        (self.demo_dir / "data").mkdir()
        (self.demo_dir / "logs").mkdir()
        
        # 创建演示配置
        demo_config = {
            "shared_folder": {
                "requests": str(self.demo_dir / "requests"),
                "responses": str(self.demo_dir / "responses")
            },
            "database": {
                "path": str(self.demo_dir / "data" / "demo.db"),
                "backup_path": str(self.demo_dir / "backup")
            },
            "processor": {
                "poll_interval": 0.5,
                "max_concurrent_requests": 5,
                "request_timeout": 10,
                "cleanup_interval": 60
            },
            "client": {
                "poll_interval": 0.3,
                "request_timeout": 10,
                "retry_attempts": 2,
                "retry_delay": 0.5
            },
            "logging": {
                "level": "INFO",
                "file": str(self.demo_dir / "logs" / "demo.log")
            }
        }
        
        # 保存配置
        config_path = self.demo_dir / "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(demo_config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 演示环境已创建")
        return str(config_path)
    
    def initialize_demo_database(self, config_path: str):
        """初始化演示数据库"""
        print("🗄️ 初始化演示数据库...")
        
        db_init = DatabaseInitializer(config_path)
        
        # 创建演示表
        tables = {
            'users': {
                'columns': {
                    'id': 'INTEGER',
                    'username': 'TEXT NOT NULL UNIQUE',
                    'email': 'TEXT',
                    'full_name': 'TEXT',
                    'created_at': 'REAL',
                    'updated_at': 'REAL'
                },
                'primary_key': 'id',
                'indexes': ['username', 'email', 'created_at']
            },
            'products': {
                'columns': {
                    'id': 'INTEGER',
                    'name': 'TEXT NOT NULL',
                    'description': 'TEXT',
                    'price': 'REAL',
                    'stock': 'INTEGER DEFAULT 0',
                    'category': 'TEXT',
                    'created_at': 'REAL',
                    'updated_at': 'REAL'
                },
                'primary_key': 'id',
                'indexes': ['name', 'category', 'price']
            },
            'orders': {
                'columns': {
                    'id': 'INTEGER',
                    'user_id': 'INTEGER',
                    'total_amount': 'REAL',
                    'status': 'TEXT DEFAULT "pending"',
                    'created_at': 'REAL',
                    'updated_at': 'REAL'
                },
                'primary_key': 'id',
                'indexes': ['user_id', 'status', 'created_at']
            }
        }
        
        for table_name, table_info in tables.items():
            db_init.create_table(
                table_name,
                table_info['columns'],
                primary_key=table_info['primary_key'],
                indexes=table_info.get('indexes', [])
            )
            print(f"  ✅ 创建表: {table_name}")
        
        print("✅ 数据库初始化完成")
    
    def start_demo_processor(self, config_path: str):
        """启动演示处理器"""
        print("⚙️ 启动演示处理器...")
        
        self.processor = SyncProcessor(config_path)
        
        def run_processor():
            try:
                self.processor.start()
                while True:
                    time.sleep(0.1)
            except Exception as e:
                print(f"处理器错误: {e}")
        
        self.processor_thread = threading.Thread(target=run_processor, daemon=True)
        self.processor_thread.start()
        
        # 等待处理器启动
        time.sleep(1)
        print("✅ 处理器已启动")
    
    def run_basic_demo(self, config_path: str):
        """运行基本功能演示"""
        print("\n" + "=" * 40)
        print("🎯 基本功能演示")
        print("=" * 40)
        
        client = SyncClient(config_path)
        
        try:
            # 1. 插入用户数据
            print("\n1️⃣ 插入用户数据")
            users_data = [
                {'username': 'alice', 'email': 'alice@example.com', 'full_name': 'Alice Smith', 'created_at': time.time()},
                {'username': 'bob', 'email': 'bob@example.com', 'full_name': 'Bob Johnson', 'created_at': time.time()},
                {'username': 'charlie', 'email': 'charlie@example.com', 'full_name': 'Charlie Brown', 'created_at': time.time()}
            ]
            
            for user_data in users_data:
                result = client.insert('users', user_data)
                if result.success:
                    print(f"  ✅ 插入用户: {user_data['username']} (ID: {result.data['inserted_id']})")
                else:
                    print(f"  ❌ 插入失败: {result.error}")
            
            # 2. 查询用户
            print("\n2️⃣ 查询用户数据")
            result = client.select('users', columns=['id', 'username', 'full_name', 'email'])
            if result.success:
                print(f"  📊 找到 {len(result.data)} 个用户:")
                for user in result.data:
                    print(f"    - {user['full_name']} ({user['username']}) - {user['email']}")
            else:
                print(f"  ❌ 查询失败: {result.error}")
            
            # 3. 插入产品数据
            print("\n3️⃣ 插入产品数据")
            products_data = [
                {'name': '笔记本电脑', 'description': '高性能办公笔记本', 'price': 5999.99, 'stock': 10, 'category': '电子产品', 'created_at': time.time()},
                {'name': '无线鼠标', 'description': '人体工学设计', 'price': 199.99, 'stock': 50, 'category': '电子产品', 'created_at': time.time()},
                {'name': '办公椅', 'description': '舒适办公椅', 'price': 899.99, 'stock': 20, 'category': '家具', 'created_at': time.time()}
            ]
            
            for product_data in products_data:
                result = client.insert('products', product_data)
                if result.success:
                    print(f"  ✅ 插入产品: {product_data['name']} (ID: {result.data['inserted_id']})")
                else:
                    print(f"  ❌ 插入失败: {result.error}")
            
            # 4. 查询产品
            print("\n4️⃣ 查询产品数据")
            result = client.select('products', columns=['name', 'price', 'stock', 'category'], order_by='price DESC')
            if result.success:
                print(f"  📦 产品列表 (按价格排序):")
                for product in result.data:
                    print(f"    - {product['name']}: ¥{product['price']} (库存: {product['stock']}) [{product['category']}]")
            else:
                print(f"  ❌ 查询失败: {result.error}")
            
            # 5. 创建订单
            print("\n5️⃣ 创建订单")
            # 先获取用户和产品ID
            user_result = client.find_one('users', where={'username': 'alice'})
            product_result = client.find_one('products', where={'name': '笔记本电脑'})
            
            if user_result.success and product_result.success and user_result.data and product_result.data:
                order_data = {
                    'user_id': user_result.data['id'],
                    'total_amount': product_result.data['price'],
                    'status': 'confirmed',
                    'created_at': time.time(),
                    'updated_at': time.time()
                }
                
                result = client.insert('orders', order_data)
                if result.success:
                    print(f"  ✅ 创建订单: ID {result.data['inserted_id']}, 金额 ¥{order_data['total_amount']}")
                else:
                    print(f"  ❌ 创建订单失败: {result.error}")
            
            # 6. 更新库存
            print("\n6️⃣ 更新产品库存")
            result = client.update('products', 
                                 values={'stock': 9, 'updated_at': time.time()},
                                 where={'name': '笔记本电脑'})
            if result.success:
                print(f"  ✅ 更新库存: 影响 {result.data['rows_affected']} 行")
            else:
                print(f"  ❌ 更新失败: {result.error}")
            
            # 7. 统计查询
            print("\n7️⃣ 统计查询")
            
            # 用户总数
            result = client.count('users')
            if result.success:
                print(f"  👥 用户总数: {result.data}")
            
            # 产品总数
            result = client.count('products')
            if result.success:
                print(f"  📦 产品总数: {result.data}")
            
            # 订单总数
            result = client.count('orders')
            if result.success:
                print(f"  📋 订单总数: {result.data}")
            
            # 8. 条件查询
            print("\n8️⃣ 条件查询演示")
            
            # 查询电子产品
            result = client.select('products', where={'category': '电子产品'}, columns=['name', 'price'])
            if result.success:
                print(f"  💻 电子产品 ({len(result.data)} 个):")
                for product in result.data:
                    print(f"    - {product['name']}: ¥{product['price']}")
            
            # 查询高价产品
            result = client.execute_sql(
                "SELECT name, price FROM products WHERE price > ? ORDER BY price DESC",
                (1000,)
            )
            if result.success:
                print(f"  💰 高价产品 (>¥1000):")
                for row in result.data:
                    print(f"    - {row['name']}: ¥{row['price']}")
            
        finally:
            client.close()
    
    def run_advanced_demo(self, config_path: str):
        """运行高级功能演示"""
        print("\n" + "=" * 40)
        print("🔥 高级功能演示")
        print("=" * 40)
        
        # 使用表封装器
        print("\n🎯 使用表封装器")
        
        from syncsys_client import SyncTable, SyncDatabase
        
        with SyncDatabase(config_path) as db:
            users_table = db.table('users')
            products_table = db.table('products')
            
            # 检查数据是否存在
            result = users_table.exists(where={'username': 'david'})
            if not (result.success and result.data):
                # 插入新用户
                result = users_table.insert({
                    'username': 'david',
                    'email': 'david@example.com',
                    'full_name': 'David Wilson',
                    'created_at': time.time()
                })
                if result.success:
                    print(f"  ✅ 使用表封装器插入用户: david")
            
            # 获取用户总数
            result = users_table.count()
            if result.success:
                print(f"  📊 当前用户总数: {result.data}")
            
            # 获取最新产品
            result = products_table.find_one(order_by='created_at DESC')
            if result.success and result.data:
                print(f"  🆕 最新产品: {result.data['name']}")
    
    def run_performance_demo(self, config_path: str):
        """运行性能演示"""
        print("\n" + "=" * 40)
        print("⚡ 性能演示")
        print("=" * 40)
        
        client = SyncClient(config_path)
        
        try:
            # 批量插入测试
            print("\n📈 批量插入性能测试")
            
            start_time = time.time()
            batch_size = 20
            
            for i in range(batch_size):
                result = client.insert('users', {
                    'username': f'perf_user_{i}',
                    'email': f'perf{i}@example.com',
                    'full_name': f'Performance User {i}',
                    'created_at': time.time()
                })
                
                if not result.success:
                    print(f"  ❌ 插入失败: {result.error}")
                    break
            
            duration = time.time() - start_time
            rate = batch_size / duration
            
            print(f"  ✅ 插入 {batch_size} 条记录")
            print(f"  ⏱️ 耗时: {duration:.2f} 秒")
            print(f"  🚀 速率: {rate:.1f} 条/秒")
            
            # 查询性能测试
            print("\n🔍 查询性能测试")
            
            start_time = time.time()
            query_count = 10
            
            for i in range(query_count):
                result = client.select('users', where={'username': f'perf_user_{i}'}, limit=1)
                if not result.success:
                    print(f"  ❌ 查询失败: {result.error}")
                    break
            
            duration = time.time() - start_time
            rate = query_count / duration
            
            print(f"  ✅ 执行 {query_count} 次查询")
            print(f"  ⏱️ 耗时: {duration:.2f} 秒")
            print(f"  🚀 速率: {rate:.1f} 次/秒")
            
        finally:
            client.close()
    
    def show_system_info(self, config_path: str):
        """显示系统信息"""
        print("\n" + "=" * 40)
        print("📊 系统信息")
        print("=" * 40)
        
        try:
            from system_monitor import SystemMonitor
            
            monitor = SystemMonitor(config_path)
            status = monitor.collect_system_status()
            
            print(f"\n🖥️ 系统状态")
            print(f"  处理器状态: {'✅ 运行中' if status.processor_running else '❌ 未运行'}")
            print(f"  数据库状态: {'✅ 正常' if status.database_accessible else '❌ 异常'}")
            print(f"  共享文件夹: {'✅ 可访问' if status.shared_folders_accessible else '❌ 不可访问'}")
            
            print(f"\n📈 请求统计")
            print(f"  待处理请求: {status.pending_requests}")
            print(f"  已处理请求: {status.processed_requests_last_hour}")
            print(f"  错误请求: {status.error_count_last_hour}")
            
            print(f"\n💾 数据库信息")
            print(f"  数据库大小: {status.database_size / 1024 / 1024:.2f} MB")
            print(f"  平均响应时间: {status.response_time_avg * 1000:.1f} ms")
            
            if status.cpu_usage is not None:
                print(f"\n🖥️ 系统资源")
                print(f"  CPU 使用率: {status.cpu_usage:.1f}%")
                print(f"  内存使用率: {status.memory_usage:.1f}%")
            
        except ImportError:
            print("  ⚠️ 系统监控模块不可用")
        except Exception as e:
            print(f"  ❌ 获取系统信息失败: {e}")
    
    def cleanup(self):
        """清理演示环境"""
        if self.processor:
            print("\n🛑 停止处理器...")
            self.processor.stop()
            # 等待处理器完全停止
            time.sleep(2)
        
        if self.demo_dir and self.demo_dir.exists():
            print(f"🧹 清理演示目录: {self.demo_dir}")
            import shutil
            import gc
            
            # 强制垃圾回收，确保所有数据库连接都被关闭
            gc.collect()
            time.sleep(1)
            
            try:
                shutil.rmtree(self.demo_dir)
                print("✅ 清理完成")
            except PermissionError as e:
                print(f"⚠️ 清理时遇到权限问题: {e}")
                print(f"📁 演示文件保留在: {self.demo_dir}")
                print("您可以稍后手动删除该目录")
            except Exception as e:
                print(f"⚠️ 清理时出现错误: {e}")
                print(f"📁 演示文件保留在: {self.demo_dir}")
    
    def run_complete_demo(self):
        """运行完整演示"""
        try:
            # 欢迎信息
            self.welcome()
            
            # 设置环境
            config_path = self.setup_demo_environment()
            
            # 初始化数据库
            self.initialize_demo_database(config_path)
            
            # 启动处理器
            self.start_demo_processor(config_path)
            
            # 运行演示
            self.run_basic_demo(config_path)
            self.run_advanced_demo(config_path)
            self.run_performance_demo(config_path)
            
            # 显示系统信息
            self.show_system_info(config_path)
            
            # 结束信息
            print("\n" + "=" * 60)
            print("🎉 演示完成！")
            print("=" * 60)
            print()
            print("您已经看到了 SyncSys 的主要功能：")
            print("✅ 数据库操作 (增删改查)")
            print("✅ 并发处理")
            print("✅ 错误处理")
            print("✅ 性能优化")
            print("✅ 系统监控")
            print()
            print("接下来您可以：")
            print("1. 查看完整的 README.md 文档")
            print("2. 运行 test_system.py 进行完整测试")
            print("3. 使用 deploy.py 部署到生产环境")
            print("4. 参考 client_example.py 开发您的应用")
            print()
            print(f"演示文件位置: {self.demo_dir}")
            print("按 Enter 键清理演示环境...")
            
            input()
            
        except KeyboardInterrupt:
            print("\n\n⚠️ 演示被中断")
        except Exception as e:
            print(f"\n❌ 演示过程中出现错误: {e}")
        finally:
            self.cleanup()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='SyncSys 快速开始演示')
    parser.add_argument('--no-cleanup', action='store_true', help='演示结束后不清理文件')
    
    args = parser.parse_args()
    
    demo = QuickStart()
    
    if args.no_cleanup:
        # 如果不清理，重写cleanup方法
        original_cleanup = demo.cleanup
        def no_cleanup():
            if demo.processor:
                print("\n🛑 停止处理器...")
                demo.processor.stop()
            print(f"\n📁 演示文件保留在: {demo.demo_dir}")
        demo.cleanup = no_cleanup
    
    demo.run_complete_demo()

if __name__ == "__main__":
    main()