#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SyncSys 快速事务测试
简单快速的事务响应时间测试
"""

import json
import time
import uuid
import random
from pathlib import Path
import copy


def quick_transaction_test():
    """快速事务测试"""
    print("SyncSys 快速事务响应时间测试")
    print("=" * 40)
    
    # 配置路径
    requests_folder = Path("shared_folder/requests")
    responses_folder = Path("shared_folder/responses")
    
    # 确保文件夹存在
    requests_folder.mkdir(parents=True, exist_ok=True)
    responses_folder.mkdir(parents=True, exist_ok=True)
    
    # 尝试加载第一个模板
    template_file = "transaction_sample0.json"
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            template = json.load(f)
        print(f"✓ 加载模板: {template_file}")
    except FileNotFoundError:
        print(f"✗ 找不到模板文件: {template_file}")
        return
    
    # 生成测试ID
    client_id = f"quick_txn_{int(time.time())}"
    request_id = f"quick_test_{int(time.time())}"
    
    # 深拷贝模板并生成唯一数据
    request = copy.deepcopy(template)
    request["request_id"] = request_id
    request["client_id"] = client_id
    request["timestamp"] = time.time()
    
    # 生成唯一数据，避免重复
    new_task_id = str(uuid.uuid4())
    test_time = int(time.time())
    test_suffix = random.randint(1000, 9999)
    
    # 更新所有操作中的数据
    for operation in request["data"]["operations"]:
        if operation["type"] == "INSERT" and operation["table"] == "tasks":
            values = operation["data"]["values"]
            values["task_id"] = new_task_id
            values["sender_mail"] = f"test_{test_time}_{test_suffix}@quicktest.com"
            values["sender_phone"] = f"135{random.randint(10000000, 99999999)}"
            values["carid"] = f"QUICK{test_suffix}"
            values["assigned_time"] = test_time
            values["sender_name"] = f"快速测试用户_{test_suffix}"
            
        elif operation["type"] == "INSERT" and operation["table"] == "tasks_staff":
            values = operation["data"]["values"]
            values["task_id"] = new_task_id
            values["staff_email"] = f"staff_{test_time}_{random.randint(1000,9999)}@quicktest.com"
            values["staff_time"] = test_time
            
        elif operation["type"] == "UPDATE":
            where_clause = operation["data"].get("where", {})
            if "task_id" in where_clause:
                where_clause["task_id"] = new_task_id
            values = operation["data"].get("values", {})
            if "assigned_time" in values:
                values["assigned_time"] = test_time
                
        elif operation["type"] == "DELETE":
            where_clause = operation["data"].get("where", {})
            if "task_id" in where_clause:
                where_clause["task_id"] = new_task_id
    
    print(f"客户端ID: {client_id}")
    print(f"请求ID: {request_id}")
    print(f"事务操作数: {len(request['data']['operations'])}")
    print("发送事务请求...")
    
    # 记录开始时间
    start_time = time.time()
    
    # 发送请求
    request_file = requests_folder / f"{client_id}_{request_id}.json"
    with open(request_file, 'w', encoding='utf-8') as f:
        json.dump(request, f, ensure_ascii=False, indent=2)
    
    print(f"请求文件已创建: {request_file.name}")
    
    # 等待响应
    response_file = responses_folder / f"{client_id}_{request_id}.json"
    print("等待响应...")
    
    response = None
    timeout = 30  # 30秒超时
    start_wait = time.time()
    
    while time.time() - start_wait < timeout:
        if response_file.exists():
            try:
                with open(response_file, 'r', encoding='utf-8') as f:
                    response = json.load(f)
                break
            except (json.JSONDecodeError, IOError):
                # 文件可能还在写入中
                time.sleep(0.01)
        else:
            time.sleep(0.01)
    
    # 计算响应时间
    end_time = time.time()
    response_time = end_time - start_time
    
    # 输出结果
    if response:
        print(f"\n✓ 收到响应!")
        print(f"响应时间: {response_time:.3f}秒")
        print(f"状态: {response['result']['status']}")
        
        if response['result']['status'] == 'SUCCESS':
            print("✓ 事务处理成功")
            result_data = response['result']['data']
            if 'operations_count' in result_data:
                print(f"成功执行操作数: {result_data['operations_count']}")
            if 'total_affected_rows' in result_data:
                print(f"总影响行数: {result_data['total_affected_rows']}")
        else:
            print("✗ 事务处理失败")
            print(f"错误: {response['result'].get('error', '未知错误')}")
        
        # 清理响应文件
        try:
            response_file.unlink()
        except:
            pass
    else:
        print(f"\n✗ 响应超时 ({timeout}秒)")
        print("请检查 SyncSys 处理器是否正在运行")
    
    print("\n测试完成!")


if __name__ == "__main__":
    quick_transaction_test() 