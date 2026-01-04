#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统功能测试脚本
用于验证SyncSys系统的各项功能
"""

import os
import time
import json
import tempfile
import shutil
from pathlib import Path
from syncsys_client import SyncClient, SyncDatabase
from syncsys_core import SyncProcessor, ConfigManager
from db_manager import DatabaseInitializer
import threading
import logging

class SystemTester:
    """系统测试器"""
    
    def __init__(self, test_config_path: str = None):
        self.test_dir = None
        self.config_path = test_config_path
        self.processor = None
        self.processor_thread = None
        self.test_results = []
        
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def setup_test_environment(self):
        """设置测试环境"""
        print("设置测试环境...")
        
        # 创建临时测试目录
        self.test_dir = Path(tempfile.mkdtemp(prefix="syncsys_test_"))
        print(f"测试目录: {self.test_dir}")
        
        # 创建测试配置
        test_config = {
            "shared_folder": {
                "requests": str(self.test_dir / "requests"),
                "responses": str(self.test_dir / "responses")
            },
            "database": {
                "path": str(self.test_dir / "test.db"),
                "backup_path": str(self.test_dir / "backup")
            },
            "processor": {
                "poll_interval": 0.1,
                "max_concurrent_requests": 5,
                "request_timeout": 10,
                "cleanup_interval": 60
            },
            "client": {
                "poll_interval": 0.1,
                "request_timeout": 10,
                "retry_attempts": 2,
                "retry_delay": 0.5
            },
            "logging": {
                "level": "INFO",
                "file": str(self.test_dir / "test.log")
            }
        }
        
        # 保存测试配置
        self.config_path = self.test_dir / "test_config.json"
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)
        
        # 初始化数据库
        db_init = DatabaseInitializer(str(self.config_path))
        
        # 创建测试表
        db_init.create_table('test_users', {
            'id': 'INTEGER',
            'username': 'TEXT NOT NULL UNIQUE',
            'email': 'TEXT',
            'created_at': 'REAL',
            'updated_at': 'REAL'
        }, primary_key='id', indexes=['username', 'created_at'])
        
        db_init.create_table('test_products', {
            'id': 'INTEGER',
            'name': 'TEXT NOT NULL',
            'price': 'REAL',
            'stock': 'INTEGER DEFAULT 0'
        }, primary_key='id')
        
        print("测试环境设置完成")
    
    def start_test_processor(self):
        """启动测试处理器"""
        print("启动测试处理器...")
        
        self.processor = SyncProcessor(str(self.config_path))
        
        def run_processor():
            try:
                self.processor.start()
                # 保持运行
                while True:
                    time.sleep(0.1)
            except Exception as e:
                logging.error(f"处理器运行错误: {e}")
        
        self.processor_thread = threading.Thread(target=run_processor, daemon=True)
        self.processor_thread.start()
        
        # 等待处理器启动
        time.sleep(1)
        print("测试处理器已启动")
    
    def stop_test_processor(self):
        """停止测试处理器"""
        if self.processor:
            print("停止测试处理器...")
            self.processor.stop()
            self.processor = None
    
    def cleanup_test_environment(self):
        """清理测试环境"""
        self.stop_test_processor()
        
        if self.test_dir and self.test_dir.exists():
            print(f"清理测试目录: {self.test_dir}")
            shutil.rmtree(self.test_dir)
    
    def run_test(self, test_name: str, test_func):
        """运行单个测试"""
        print(f"\n运行测试: {test_name}")
        print("-" * 40)
        
        start_time = time.time()
        try:
            test_func()
            duration = time.time() - start_time
            result = {
                'name': test_name,
                'status': 'PASS',
                'duration': duration,
                'error': None
            }
            print(f"✓ {test_name} - 通过 ({duration:.3f}s)")
        except Exception as e:
            duration = time.time() - start_time
            result = {
                'name': test_name,
                'status': 'FAIL',
                'duration': duration,
                'error': str(e)
            }
            print(f"✗ {test_name} - 失败: {e} ({duration:.3f}s)")
        
        self.test_results.append(result)
    
    def test_basic_operations(self):
        """测试基本操作"""
        client = SyncClient(str(self.config_path))
        
        try:
            # 测试插入
            result = client.insert('test_users', {
                'username': 'test_user_1',
                'email': 'test1@example.com',
                'created_at': time.time()
            })
            assert result.success, f"插入失败: {result.error}"
            assert result.data['inserted_id'] > 0, "插入ID无效"
            
            # 测试查询
            result = client.select('test_users', where={'username': 'test_user_1'})
            assert result.success, f"查询失败: {result.error}"
            assert len(result.data) == 1, "查询结果数量错误"
            assert result.data[0]['username'] == 'test_user_1', "查询结果错误"
            
            # 测试更新
            result = client.update('test_users',
                                 values={'email': 'updated@example.com', 'updated_at': time.time()},
                                 where={'username': 'test_user_1'})
            assert result.success, f"更新失败: {result.error}"
            assert result.data['rows_affected'] == 1, "更新行数错误"
            
            # 验证更新
            result = client.find_one('test_users', where={'username': 'test_user_1'})
            assert result.success, f"验证查询失败: {result.error}"
            assert result.data['email'] == 'updated@example.com', "更新验证失败"
            
            # 测试删除
            result = client.delete('test_users', where={'username': 'test_user_1'})
            assert result.success, f"删除失败: {result.error}"
            assert result.data['rows_affected'] == 1, "删除行数错误"
            
            # 验证删除
            result = client.find_one('test_users', where={'username': 'test_user_1'})
            assert result.success, f"验证查询失败: {result.error}"
            assert result.data is None, "删除验证失败"
            
        finally:
            client.close()
    
    def test_concurrent_operations(self):
        """测试并发操作"""
        import threading
        
        results = []
        errors = []
        
        def worker(worker_id):
            client = SyncClient(str(self.config_path))
            try:
                # 每个worker插入多条记录
                for i in range(5):
                    result = client.insert('test_users', {
                        'username': f'worker_{worker_id}_user_{i}',
                        'email': f'worker{worker_id}user{i}@example.com',
                        'created_at': time.time()
                    })
                    
                    if result.success:
                        results.append(result)
                    else:
                        errors.append(f"Worker {worker_id}: {result.error}")
            except Exception as e:
                errors.append(f"Worker {worker_id} exception: {e}")
            finally:
                client.close()
        
        # 启动多个并发worker
        threads = []
        worker_count = 5
        
        for i in range(worker_count):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        assert len(errors) == 0, f"并发操作出现错误: {errors}"
        assert len(results) == worker_count * 5, f"期望 {worker_count * 5} 个成功结果，实际 {len(results)} 个"
        
        # 验证数据库中的记录数
        client = SyncClient(str(self.config_path))
        try:
            result = client.count('test_users')
            assert result.success, f"计数查询失败: {result.error}"
            assert result.data == worker_count * 5, f"数据库记录数错误: 期望 {worker_count * 5}，实际 {result.data}"
        finally:
            client.close()
    
    def test_error_handling(self):
        """测试错误处理"""
        client = SyncClient(str(self.config_path))
        
        try:
            # 测试查询不存在的表
            result = client.select('non_existent_table')
            assert not result.success, "应该返回失败"
            assert "no such table" in result.error.lower(), f"错误信息不正确: {result.error}"
            
            # 测试插入重复的唯一键
            client.insert('test_users', {
                'username': 'duplicate_user',
                'email': 'duplicate@example.com'
            })
            
            result = client.insert('test_users', {
                'username': 'duplicate_user',  # 重复的用户名
                'email': 'another@example.com'
            })
            assert not result.success, "应该返回失败"
            assert "unique" in result.error.lower(), f"错误信息不正确: {result.error}"
            
            # 测试更新不存在的记录
            result = client.update('test_users',
                                 values={'email': 'new@example.com'},
                                 where={'username': 'non_existent_user'})
            assert result.success, "更新不存在的记录应该成功但影响0行"
            assert result.data['rows_affected'] == 0, "应该影响0行"
            
        finally:
            client.close()
    
    def test_table_wrapper(self):
        """测试表封装器"""
        client = SyncClient(str(self.config_path))
        
        try:
            from syncsys_client import SyncTable
            
            products_table = SyncTable(client, 'test_products')
            
            # 插入产品
            result = products_table.insert({
                'name': 'Test Product',
                'price': 99.99,
                'stock': 100
            })
            assert result.success, f"插入产品失败: {result.error}"
            
            # 查询产品
            result = products_table.find_one(where={'name': 'Test Product'})
            assert result.success, f"查询产品失败: {result.error}"
            assert result.data['name'] == 'Test Product', "产品名称错误"
            assert result.data['price'] == 99.99, "产品价格错误"
            
            # 更新库存
            result = products_table.update(
                values={'stock': 95},
                where={'name': 'Test Product'}
            )
            assert result.success, f"更新库存失败: {result.error}"
            
            # 验证更新
            result = products_table.find_one(where={'name': 'Test Product'})
            assert result.success, f"验证查询失败: {result.error}"
            assert result.data['stock'] == 95, "库存更新错误"
            
        finally:
            client.close()
    
    def test_database_wrapper(self):
        """测试数据库封装器"""
        with SyncDatabase(str(self.config_path)) as db:
            users = db.table('test_users')
            products = db.table('test_products')
            
            # 测试用户表操作
            result = users.insert({
                'username': 'db_wrapper_user',
                'email': 'dbwrapper@example.com',
                'created_at': time.time()
            })
            assert result.success, f"用户插入失败: {result.error}"
            
            # 测试产品表操作
            result = products.insert({
                'name': 'DB Wrapper Product',
                'price': 199.99,
                'stock': 50
            })
            assert result.success, f"产品插入失败: {result.error}"
            
            # 验证数据
            result = users.exists(where={'username': 'db_wrapper_user'})
            assert result.success and result.data, "用户不存在"
            
            result = products.count()
            assert result.success and result.data > 0, "产品计数错误"
    
    def test_performance(self):
        """测试性能"""
        client = SyncClient(str(self.config_path))
        
        try:
            # 测试批量插入性能
            start_time = time.time()
            insert_count = 50
            
            for i in range(insert_count):
                result = client.insert('test_users', {
                    'username': f'perf_user_{i}',
                    'email': f'perf{i}@example.com',
                    'created_at': time.time()
                })
                assert result.success, f"性能测试插入失败: {result.error}"
            
            insert_duration = time.time() - start_time
            insert_rate = insert_count / insert_duration
            
            print(f"插入性能: {insert_count} 条记录，耗时 {insert_duration:.2f} 秒，速率 {insert_rate:.1f} 条/秒")
            
            # 测试查询性能
            start_time = time.time()
            query_count = 20
            
            for i in range(query_count):
                result = client.select('test_users', where={'username': f'perf_user_{i}'})
                assert result.success, f"性能测试查询失败: {result.error}"
            
            query_duration = time.time() - start_time
            query_rate = query_count / query_duration
            
            print(f"查询性能: {query_count} 次查询，耗时 {query_duration:.2f} 秒，速率 {query_rate:.1f} 次/秒")
            
            # 性能断言
            assert insert_rate > 5, f"插入速率过低: {insert_rate:.1f} 条/秒"
            assert query_rate > 10, f"查询速率过低: {query_rate:.1f} 次/秒"
            
        finally:
            client.close()
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("SyncSys 系统功能测试")
        print("=" * 60)
        
        try:
            # 设置测试环境
            self.setup_test_environment()
            self.start_test_processor()
            
            # 运行测试
            self.run_test("基本操作测试", self.test_basic_operations)
            self.run_test("并发操作测试", self.test_concurrent_operations)
            self.run_test("错误处理测试", self.test_error_handling)
            self.run_test("表封装器测试", self.test_table_wrapper)
            self.run_test("数据库封装器测试", self.test_database_wrapper)
            self.run_test("性能测试", self.test_performance)
            
            # 输出测试结果
            self.print_test_summary()
            
        finally:
            self.cleanup_test_environment()
    
    def print_test_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("测试结果摘要")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = total_tests - passed_tests
        total_duration = sum(r['duration'] for r in self.test_results)
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"总耗时: {total_duration:.3f} 秒")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n失败的测试:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"  ✗ {result['name']}: {result['error']}")
        
        print("\n详细结果:")
        for result in self.test_results:
            status_symbol = "✓" if result['status'] == 'PASS' else "✗"
            print(f"  {status_symbol} {result['name']} - {result['duration']:.3f}s")
        
        print("=" * 60)
        
        if failed_tests == 0:
            print("🎉 所有测试通过！")
        else:
            print(f"⚠️  {failed_tests} 个测试失败")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='SyncSys 系统功能测试')
    parser.add_argument('--config', '-c', help='使用指定的配置文件')
    
    args = parser.parse_args()
    
    tester = SystemTester(args.config)
    tester.run_all_tests()

if __name__ == "__main__":
    main()