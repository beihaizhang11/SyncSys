#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SyncSys 事务响应时间测试脚本
基于事务模板测试完整的请求-响应时间
"""

import json
import time
import uuid
import random
from pathlib import Path
from datetime import datetime
import copy


class TransactionResponseTimer:
    """事务响应时间测试器"""
    
    def __init__(self):
        """初始化测试器"""
        # 配置路径
        self.requests_folder = Path("shared_folder/requests")
        self.responses_folder = Path("shared_folder/responses")
        
        # 确保文件夹存在
        self.requests_folder.mkdir(parents=True, exist_ok=True)
        self.responses_folder.mkdir(parents=True, exist_ok=True)
        
        # 生成客户端ID
        self.client_id = f"txn_test_{int(time.time())}"
        
        # 加载模板
        self.templates = self._load_templates()
        
        # 测试数据生成器
        self.test_counter = 0
        
    def _load_templates(self):
        """加载事务模板"""
        templates = []
        template_files = [
            "transaction_sample0.json",
            "transaction_sample1.json", 
            "transaction_sample2.json",
            "transaction_sample3.json"
        ]
        
        for template_file in template_files:
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                    templates.append(template)
                    print(f"✓ 加载模板: {template_file}")
            except FileNotFoundError:
                print(f"✗ 模板文件不存在: {template_file}")
        
        if not templates:
            raise FileNotFoundError("没有找到任何模板文件")
        
        return templates
    
    def _generate_unique_task_id(self):
        """生成唯一的task_id"""
        return str(uuid.uuid4())
    
    def _generate_unique_email(self):
        """生成唯一的邮箱地址"""
        names = ["alice", "bob", "charlie", "diana", "edward", "fiona", "george", "helen"]
        domains = ["company.com", "test.org", "example.net", "demo.co"]
        timestamp = int(time.time())
        name = random.choice(names)
        domain = random.choice(domains)
        return f"{name}_{timestamp}_{random.randint(1000,9999)}@{domain}"
    
    def _generate_test_request(self, template_index=None):
        """基于模板生成测试请求"""
        self.test_counter += 1
        
        # 选择模板
        if template_index is None:
            template = random.choice(self.templates)
        else:
            template = self.templates[template_index % len(self.templates)]
        
        # 深拷贝模板
        request = copy.deepcopy(template)
        
        # 生成唯一的请求ID和客户端ID
        request["request_id"] = f"txn_test_{self.test_counter}_{int(time.time())}"
        request["client_id"] = self.client_id
        request["timestamp"] = time.time()
        
        # 存储生成的task_id映射，用于保持操作间的一致性
        task_id_mapping = {}
        
        # 处理每个操作，确保数据唯一性
        for operation in request["data"]["operations"]:
            if operation["type"] == "INSERT" and operation["table"] == "tasks":
                # 为tasks表生成唯一数据
                values = operation["data"]["values"]
                
                # 保存原始task_id用于映射
                original_task_id = values.get("task_id")
                new_task_id = self._generate_unique_task_id()
                task_id_mapping[original_task_id] = new_task_id
                
                # 更新字段
                values["task_id"] = new_task_id
                values["sender_mail"] = self._generate_unique_email()
                values["sender_phone"] = f"135{random.randint(10000000, 99999999)}"
                values["carid"] = f"TEST{random.randint(100, 999)}"
                values["assigned_time"] = int(time.time())
                
                # 添加时间戳到名称确保唯一性
                if "sender_name" in values:
                    values["sender_name"] = f"测试用户_{self.test_counter}_{random.randint(1000,9999)}"
                
            elif operation["type"] == "INSERT" and operation["table"] == "tasks_staff":
                # 为tasks_staff表生成唯一数据
                values = operation["data"]["values"]
                
                # 更新task_id引用
                original_task_id = values.get("task_id")
                if original_task_id in task_id_mapping:
                    values["task_id"] = task_id_mapping[original_task_id]
                else:
                    # 如果没有映射，使用现有的task_id（可能引用已存在的任务）
                    pass
                
                # 生成唯一邮箱
                values["staff_email"] = self._generate_unique_email()
                values["staff_time"] = int(time.time())
                
            elif operation["type"] == "UPDATE":
                # 更新操作中的task_id引用
                where_clause = operation["data"].get("where", {})
                if "task_id" in where_clause:
                    original_task_id = where_clause["task_id"]
                    if original_task_id in task_id_mapping:
                        where_clause["task_id"] = task_id_mapping[original_task_id]
                
                # 更新时间戳
                values = operation["data"].get("values", {})
                if "assigned_time" in values:
                    values["assigned_time"] = int(time.time())
                
            elif operation["type"] == "DELETE":
                # 删除操作中的task_id引用
                where_clause = operation["data"].get("where", {})
                if "task_id" in where_clause:
                    original_task_id = where_clause["task_id"]
                    if original_task_id in task_id_mapping:
                        where_clause["task_id"] = task_id_mapping[original_task_id]
        
        return request
    
    def send_request(self, request):
        """发送请求"""
        request_file = self.requests_folder / f"{request['client_id']}_{request['request_id']}.json"
        
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request, f, ensure_ascii=False, indent=2)
        
        return request_file
    
    def wait_for_response(self, request_id, timeout=30):
        """等待响应"""
        response_file = self.responses_folder / f"{self.client_id}_{request_id}.json"
        
        start_wait = time.time()
        while time.time() - start_wait < timeout:
            if response_file.exists():
                try:
                    with open(response_file, 'r', encoding='utf-8') as f:
                        response = json.load(f)
                    return response
                except (json.JSONDecodeError, IOError):
                    # 文件可能还在写入中，继续等待
                    time.sleep(0.01)
            else:
                time.sleep(0.01)
        
        return None
    
    def test_single_transaction(self, template_index=None):
        """测试单个事务的响应时间"""
        template_name = f"模板{template_index}" if template_index is not None else "随机模板"
        print(f"测试事务 ({template_name})...")
        
        # 生成请求
        request = self._generate_test_request(template_index)
        request_id = request['request_id']
        operations_count = len(request['data']['operations'])
        
        print(f"  请求ID: {request_id}")
        print(f"  操作数量: {operations_count}")
        
        # 记录开始时间
        start_time = time.time()
        
        # 发送请求
        request_file = self.send_request(request)
        print(f"  发送请求: {request_file.name}")
        
        # 等待响应
        response = self.wait_for_response(request_id)
        
        # 记录结束时间
        end_time = time.time()
        
        if response:
            response_time = end_time - start_time
            print(f"  ✓ 收到响应: {response_time:.3f}秒")
            print(f"  状态: {response['result']['status']}")
            
            # 显示事务详情
            if response['result']['status'] == 'SUCCESS':
                result_data = response['result']['data']
                if 'operations_count' in result_data:
                    print(f"  成功操作: {result_data['operations_count']}")
                if 'total_affected_rows' in result_data:
                    print(f"  影响行数: {result_data['total_affected_rows']}")
            else:
                print(f"  错误: {response['result'].get('error', '未知错误')}")
            
            # 清理响应文件
            response_file = self.responses_folder / f"{self.client_id}_{request_id}.json"
            try:
                response_file.unlink()
            except:
                pass
            
            return response_time, response['result']['status']
        else:
            print(f"  ✗ 响应超时 (>30秒)")
            return None, "TIMEOUT"
    
    def test_all_templates(self):
        """测试所有模板"""
        print(f"\n测试所有模板 (共{len(self.templates)}个)...")
        print("=" * 50)
        
        results = []
        for i in range(len(self.templates)):
            print(f"\n模板 {i}:")
            response_time, status = self.test_single_transaction(i)
            if response_time:
                results.append(response_time)
        
        if results:
            print(f"\n所有模板测试结果:")
            print(f"  平均响应时间: {sum(results)/len(results):.3f}秒")
            print(f"  最快响应时间: {min(results):.3f}秒")
            print(f"  最慢响应时间: {max(results):.3f}秒")
    
    def test_batch_transactions(self, count=10):
        """批量测试事务"""
        print(f"\n批量测试 {count} 个事务...")
        print("=" * 50)
        
        results = []
        success_count = 0
        
        for i in range(count):
            print(f"\n事务 {i+1}/{count}:")
            response_time, status = self.test_single_transaction()
            
            if response_time:
                results.append(response_time)
                if status == "SUCCESS":
                    success_count += 1
        
        if results:
            total_time = sum(results)
            avg_time = total_time / len(results)
            
            print(f"\n批量测试结果:")
            print(f"  成功事务: {success_count}/{count}")
            print(f"  平均响应时间: {avg_time:.3f}秒")
            print(f"  最快响应时间: {min(results):.3f}秒")
            print(f"  最慢响应时间: {max(results):.3f}秒")
            print(f"  总耗时: {total_time:.3f}秒")
            print(f"  平均吞吐量: {len(results)/total_time:.2f} 事务/秒")
        else:
            print("所有事务都超时了!")


def main():
    """主函数"""
    print("SyncSys 事务响应时间测试")
    print("=" * 50)
    
    try:
        # 创建测试器
        tester = TransactionResponseTimer()
        print(f"客户端ID: {tester.client_id}")
        print(f"加载了 {len(tester.templates)} 个模板")
        
        # 检查处理器是否运行
        print(f"\n请确保 SyncSys 处理器正在运行 (start_processor.py)")
        input("按 Enter 键开始测试...")
        
        # 测试单个事务
        print("\n1. 单个事务测试:")
        tester.test_single_transaction()
        
        # 测试所有模板
        print("\n2. 所有模板测试:")
        tester.test_all_templates()
        
        # 批量测试
        print("\n3. 批量事务测试:")
        tester.test_batch_transactions(5)
        
        print("\n测试完成!")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 