#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户端使用示例
展示如何在主机上使用SyncSys进行数据库操作
"""

import time
import json
from syncsys_client import SyncClient, SyncDatabase, QueryResult
from typing import Dict, Any

def print_result(operation: str, result: QueryResult):
    """打印操作结果"""
    print(f"\n{operation}:")
    if result.success:
        print(f"  ✓ 成功: {result.data}")
        if result.timestamp:
            print(f"  时间戳: {result.timestamp}")
    else:
        print(f"  ✗ 失败: {result.error}")
    print("-" * 40)

def basic_operations_example():
    """基本操作示例"""
    print("=" * 50)
    print("基本操作示例")
    print("=" * 50)
    
    # 创建客户端
    client = SyncClient()
    print(f"客户端ID: {client.client_id}")
    
    try:
        # 1. 插入数据
        result = client.insert('users', {
            'username': 'john_doe',
            'email': 'john@example.com',
            'password_hash': 'hashed_password_123',
            'created_at': time.time(),
            'is_active': 1
        })
        print_result("插入用户", result)
        
        # 2. 查询数据
        result = client.select('users', where={'username': 'john_doe'})
        print_result("查询用户", result)
        
        # 3. 更新数据
        result = client.update('users', 
                              values={'email': 'john.doe@example.com', 'updated_at': time.time()},
                              where={'username': 'john_doe'})
        print_result("更新用户邮箱", result)
        
        # 4. 查询更新后的数据
        result = client.find_one('users', where={'username': 'john_doe'})
        print_result("查询更新后的用户", result)
        
        # 5. 计数
        result = client.count('users')
        print_result("用户总数", result)
        
        # 6. 检查存在性
        result = client.exists('users', where={'username': 'john_doe'})
        print_result("检查用户是否存在", result)
        
    finally:
        client.close()

def table_wrapper_example():
    """表封装器示例"""
    print("\n" + "=" * 50)
    print("表封装器示例")
    print("=" * 50)
    
    client = SyncClient()
    
    try:
        # 使用表封装器
        from syncsys_client import SyncTable
        users_table = SyncTable(client, 'users')
        
        # 插入多个用户
        users_data = [
            {'username': 'alice', 'email': 'alice@example.com', 'created_at': time.time()},
            {'username': 'bob', 'email': 'bob@example.com', 'created_at': time.time()},
            {'username': 'charlie', 'email': 'charlie@example.com', 'created_at': time.time()}
        ]
        
        for user_data in users_data:
            result = users_table.insert(user_data)
            print_result(f"插入用户 {user_data['username']}", result)
        
        # 查询所有用户
        result = users_table.find_all()
        print_result("查询所有用户", result)
        
        # 删除用户
        result = users_table.delete(where={'username': 'bob'})
        print_result("删除用户 bob", result)
        
    finally:
        client.close()

def database_wrapper_example():
    """数据库封装器示例"""
    print("\n" + "=" * 50)
    print("数据库封装器示例")
    print("=" * 50)
    
    # 使用上下文管理器
    with SyncDatabase() as db:
        users = db.table('users')
        products = db.table('products')
        
        # 添加产品
        product_data = {
            'name': 'iPhone 15',
            'description': '最新款iPhone',
            'price': 999.99,
            'stock': 100,
            'category_id': 1,
            'created_at': time.time()
        }
        
        result = products.insert(product_data)
        print_result("添加产品", result)
        
        # 查询产品
        result = products.find_all()
        print_result("查询所有产品", result)
        
        # 更新库存
        result = products.update(
            values={'stock': 95, 'updated_at': time.time()},
            where={'name': 'iPhone 15'}
        )
        print_result("更新产品库存", result)

def batch_operations_example():
    """批量操作示例"""
    print("\n" + "=" * 50)
    print("批量操作示例")
    print("=" * 50)
    
    client = SyncClient()
    
    try:
        # 批量插入订单
        orders_data = [
            {
                'user_id': 1,
                'total_amount': 999.99,
                'status': 'pending',
                'created_at': time.time()
            },
            {
                'user_id': 2,
                'total_amount': 1999.98,
                'status': 'processing',
                'created_at': time.time()
            },
            {
                'user_id': 1,
                'total_amount': 599.99,
                'status': 'completed',
                'created_at': time.time()
            }
        ]
        
        print("批量插入订单...")
        for i, order_data in enumerate(orders_data, 1):
            result = client.insert('orders', order_data)
            if result.success:
                print(f"  订单 {i} 插入成功")
            else:
                print(f"  订单 {i} 插入失败: {result.error}")
        
        # 查询特定用户的订单
        result = client.select('orders', where={'user_id': 1})
        print_result("查询用户1的订单", result)
        
        # 统计不同状态的订单数量
        for status in ['pending', 'processing', 'completed']:
            result = client.count('orders', where={'status': status})
            print(f"状态为 {status} 的订单数量: {result.data if result.success else '查询失败'}")
        
    finally:
        client.close()

def error_handling_example():
    """错误处理示例"""
    print("\n" + "=" * 50)
    print("错误处理示例")
    print("=" * 50)
    
    client = SyncClient()
    
    try:
        # 尝试查询不存在的表
        result = client.select('non_existent_table')
        print_result("查询不存在的表", result)
        
        # 尝试插入无效数据
        result = client.insert('users', {
            'username': None,  # 假设username不能为空
            'email': 'invalid_email'
        })
        print_result("插入无效数据", result)
        
        # 尝试更新不存在的记录
        result = client.update('users',
                              values={'email': 'new@example.com'},
                              where={'username': 'non_existent_user'})
        print_result("更新不存在的记录", result)
        
    finally:
        client.close()

def performance_test():
    """性能测试示例"""
    print("\n" + "=" * 50)
    print("性能测试示例")
    print("=" * 50)
    
    client = SyncClient()
    
    try:
        # 测试插入性能
        print("测试插入性能...")
        start_time = time.time()
        
        success_count = 0
        total_operations = 10
        
        for i in range(total_operations):
            result = client.insert('users', {
                'username': f'test_user_{i}',
                'email': f'test{i}@example.com',
                'created_at': time.time()
            })
            
            if result.success:
                success_count += 1
            
            if (i + 1) % 5 == 0:
                print(f"  已完成 {i + 1}/{total_operations} 次插入")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n性能测试结果:")
        print(f"  总操作数: {total_operations}")
        print(f"  成功操作数: {success_count}")
        print(f"  总耗时: {duration:.2f} 秒")
        print(f"  平均每次操作耗时: {duration/total_operations:.3f} 秒")
        print(f"  操作成功率: {success_count/total_operations*100:.1f}%")
        
    finally:
        client.close()

def main():
    """主函数"""
    print("SyncSys 客户端使用示例")
    print("请确保处理器已启动并且配置正确")
    
    try:
        # 基本操作示例
        basic_operations_example()
        
        # 表封装器示例
        table_wrapper_example()
        
        # 数据库封装器示例
        database_wrapper_example()
        
        # 批量操作示例
        batch_operations_example()
        
        # 错误处理示例
        error_handling_example()
        
        # 性能测试
        performance_test()
        
        print("\n" + "=" * 50)
        print("所有示例执行完成")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n执行示例时出错: {e}")
        print("请检查:")
        print("1. 处理器是否已启动")
        print("2. 配置文件是否正确")
        print("3. 共享文件夹是否可访问")
        print("4. 数据库是否已初始化")

if __name__ == "__main__":
    main()