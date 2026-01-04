#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SyncSys 详细性能测试脚本
测量文件读取、数据库操作、文件写入等各个步骤的详细时间
"""

import json
import time
import uuid
import random
import copy
from pathlib import Path
from typing import Dict, List, Any

from test_tools.performance_timer import (
    PerformanceTimer, 
    DatabasePerformanceAnalyzer, 
    FileOperationTimer,
    create_performance_report
)
from syncsys_core import DatabaseManager, SyncRequest


class DetailedPerformanceTester:
    """ 详细性能测试器 """
    
    def __init__(self):
        """初始化测试器"""
        # 路径配置
        self.requests_folder = Path("shared_folder/requests")
        self.responses_folder = Path("shared_folder/responses")
        
        # 确保文件夹存在
        self.requests_folder.mkdir(parents=True, exist_ok=True)
        self.responses_folder.mkdir(parents=True, exist_ok=True)
        
        # 初始化组件
        self.db_manager = DatabaseManager("WorkshopTasks1.db")
        self.db_analyzer = DatabasePerformanceAnalyzer(self.db_manager)
        self.file_timer = FileOperationTimer()
        self.main_timer = PerformanceTimer()
        
        # 生成客户端ID
        self.client_id = f"perf_test_{int(time.time())}"
        
        # 加载模板
        self.templates = self._load_templates()
        
        # 测试结果存储
        self.test_results = []
        
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
    
    def _generate_unique_request(self, template_index=0):
        """生成唯一请求数据"""
        template = self.templates[template_index % len(self.templates)]
        request = copy.deepcopy(template)
        
        # 生成唯一标识
        request_id = f"perf_test_{int(time.time())}_{random.randint(1000, 9999)}"
        request["request_id"] = request_id
        request["client_id"] = self.client_id
        request["timestamp"] = time.time()
        
        # 生成唯一数据
        new_task_id = str(uuid.uuid4())
        test_time = int(time.time())
        test_suffix = random.randint(1000, 9999)
        
        # 更新操作数据
        for operation in request["data"]["operations"]:
            if operation["type"] == "INSERT" and operation["table"] == "tasks":
                values = operation["data"]["values"]
                values["task_id"] = new_task_id
                values["sender_mail"] = f"perf_{test_time}_{test_suffix}@test.com"
                values["sender_phone"] = f"135{random.randint(10000000, 99999999)}"
                values["carid"] = f"PERF{test_suffix}"
                values["assigned_time"] = test_time
                values["sender_name"] = f"性能测试用户_{test_suffix}"
                
            elif operation["type"] == "INSERT" and operation["table"] == "tasks_staff":
                values = operation["data"]["values"]
                values["task_id"] = new_task_id
                values["staff_email"] = f"staff_{test_time}_{random.randint(1000,9999)}@test.com"
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
        
        return request
    
    def test_end_to_end_performance(self, template_index=0):
        """测试端到端性能"""
        print(f"\n开始端到端性能测试 (模板 {template_index})...")
        
        # 重置主计时器
        self.main_timer.start_timing("端到端流程")
        
        test_result = {
            'template_index': template_index,
            'success': False,
            'total_time': 0,
            'step_times': {},
            'error_message': ''
        }
        
        try:
            # 步骤1: 生成请求数据
            with self.main_timer.time_step("1. 生成请求数据"):
                request_data = self._generate_unique_request(template_index)
                request_id = request_data['request_id']
            
            # 步骤2: 写入请求文件
            request_file = self.requests_folder / f"{self.client_id}_{request_id}.json"
            with self.main_timer.time_step("2. 写入请求文件"):
                file_write_result = self.file_timer.time_file_write(request_file, request_data)
                if not file_write_result['success']:
                    raise Exception(f"请求文件写入失败: {file_write_result['error']}")
            
            # 步骤3: 模拟文件监控检测
            with self.main_timer.time_step("3. 文件监控检测"):
                time.sleep(0.001)  # 模拟监控检测延迟
            
            # 步骤4: 读取请求文件
            with self.main_timer.time_step("4. 读取请求文件"):
                file_read_result = self.file_timer.time_file_read(request_file)
                if not file_read_result['success']:
                    raise Exception(f"请求文件读取失败: {file_read_result['error']}")
                read_request_data = file_read_result['data']
            
            # 步骤5: 数据库操作分析
            with self.main_timer.time_step("5. 数据库操作"):
                db_result = self.db_analyzer.analyze_request(read_request_data)
                if db_result['result']['status'] != 'SUCCESS':
                    raise Exception(f"数据库操作失败: {db_result['result'].get('error', '未知错误')}")
            
            # 步骤6: 写入响应文件
            response_file = self.responses_folder / f"{self.client_id}_{request_id}.json"
            with self.main_timer.time_step("6. 写入响应文件"):
                response_write_result = self.file_timer.time_file_write(response_file, db_result)
                if not response_write_result['success']:
                    raise Exception(f"响应文件写入失败: {response_write_result['error']}")
            
            # 步骤7: 清理文件
            with self.main_timer.time_step("7. 清理文件"):
                try:
                    request_file.unlink()
                    response_file.unlink()
                except:
                    pass
            
            # 记录成功结果
            test_result['success'] = True
            summary = self.main_timer.get_summary()
            test_result['total_time'] = summary['total_time']
            
            # 提取各步骤时间
            for step in summary['step_details']:
                test_result['step_times'][step['step_name']] = step['duration']
            
            # 添加子操作时间
            test_result['file_write_timing'] = file_write_result.get('timing_summary', {})
            test_result['file_read_timing'] = file_read_result.get('timing_summary', {})
            test_result['db_timing'] = self.db_analyzer.timer.get_summary()
            
        except Exception as e:
            test_result['error_message'] = str(e)
            summary = self.main_timer.get_summary()
            test_result['total_time'] = summary.get('total_time', 0)
        
        self.test_results.append(test_result)
        return test_result
    
    def run_batch_tests(self, count=10):
        """运行批量测试"""
        print(f"\n开始批量性能测试 ({count} 次)...")
        print("=" * 60)
        
        for i in range(count):
            template_index = i % len(self.templates)
            print(f"\n测试 {i+1}/{count} (模板 {template_index}):")
            
            result = self.test_end_to_end_performance(template_index)
            
            if result['success']:
                print(f"  ✓ 成功 - 总时间: {result['total_time']:.4f}秒")
                # 显示主要步骤时间
                key_steps = [
                    "2. 写入请求文件",
                    "4. 读取请求文件", 
                    "5. 数据库操作",
                    "6. 写入响应文件"
                ]
                for step in key_steps:
                    if step in result['step_times']:
                        print(f"    {step}: {result['step_times'][step]:.4f}秒")
            else:
                print(f"  ✗ 失败 - {result['error_message']}")
    
    def analyze_results(self):
        """分析测试结果"""
        if not self.test_results:
            print("没有测试结果可分析")
            return
        
        successful_tests = [r for r in self.test_results if r['success']]
        failed_tests = [r for r in self.test_results if not r['success']]
        
        print(f"\n" + "=" * 60)
        print("性能测试结果分析")
        print("=" * 60)
        print(f"总测试数: {len(self.test_results)}")
        print(f"成功测试: {len(successful_tests)}")
        print(f"失败测试: {len(failed_tests)}")
        
        if successful_tests:
            # 计算平均时间
            total_times = [r['total_time'] for r in successful_tests]
            avg_total = sum(total_times) / len(total_times)
            min_total = min(total_times)
            max_total = max(total_times)
            
            print(f"\n总体性能:")
            print(f"  平均总时间: {avg_total:.4f}秒")
            print(f"  最快时间: {min_total:.4f}秒")
            print(f"  最慢时间: {max_total:.4f}秒")
            print(f"  成功率: {len(successful_tests)/len(self.test_results)*100:.1f}%")
            
            # 分析各步骤平均时间
            step_times = {}
            for result in successful_tests:
                for step_name, duration in result['step_times'].items():
                    if step_name not in step_times:
                        step_times[step_name] = []
                    step_times[step_name].append(duration)
            
            print(f"\n各步骤平均时间:")
            for step_name, times in step_times.items():
                avg_time = sum(times) / len(times)
                percentage = (avg_time / avg_total * 100)
                print(f"  {step_name:<25} {avg_time:.4f}秒 ({percentage:.1f}%)")
        
        # 生成详细报告
        report_file = f"performance_report_{int(time.time())}.json"
        create_performance_report(self.test_results, report_file)
    
    def print_detailed_timing(self, result):
        """打印详细计时信息"""
        if not result['success']:
            print(f"测试失败: {result['error_message']}")
            return
        
        print(f"\n详细性能分析:")
        print("-" * 40)
        
        # 主流程时间
        print("主流程:")
        for step_name, duration in result['step_times'].items():
            percentage = (duration / result['total_time'] * 100)
            print(f"  {step_name:<25} {duration:.4f}秒 ({percentage:.1f}%)")
        
        # 文件操作细节
        if 'file_write_timing' in result:
            timing = result['file_write_timing']
            if timing and 'step_details' in timing:
                print(f"\n文件写入细节:")
                for step in timing['step_details']:
                    print(f"  {step['step_name']:<25} {step['duration']:.4f}秒")
        
        if 'file_read_timing' in result:
            timing = result['file_read_timing']
            if timing and 'step_details' in timing:
                print(f"\n文件读取细节:")
                for step in timing['step_details']:
                    print(f"  {step['step_name']:<25} {step['duration']:.4f}秒")
        
        # 数据库操作细节
        if 'db_timing' in result:
            timing = result['db_timing']
            if timing and 'step_details' in timing:
                print(f"\n数据库操作细节:")
                for step in timing['step_details']:
                    print(f"  {step['step_name']:<25} {step['duration']:.4f}秒")


def main():
    """主函数"""
    print("SyncSys 详细性能测试")
    print("=" * 60)
    
    try:
        # 创建测试器
        tester = DetailedPerformanceTester()
        print(f"客户端ID: {tester.client_id}")
        print(f"加载了 {len(tester.templates)} 个模板")
        
        print(f"\n这个测试将详细分析以下步骤的性能:")
        print("1. 生成请求数据")
        print("2. 写入请求文件 (包含目录准备、JSON序列化、文件写入、写入验证)")
        print("3. 文件监控检测")
        print("4. 读取请求文件 (包含文件检查、大小获取、内容读取、JSON解析)")
        print("5. 数据库操作 (包含请求解析、连接准备、SQL执行、结果处理)")
        print("6. 写入响应文件")
        print("7. 清理文件")
        
        input("\n按 Enter 键开始测试...")
        
        # 单次详细测试
        print("\n1. 单次详细测试:")
        result = tester.test_end_to_end_performance(0)
        tester.print_detailed_timing(result)
        
        # 批量测试
        print(f"\n2. 批量性能测试:")
        tester.run_batch_tests(10)
        
        # 分析结果
        tester.analyze_results()
        
        print("\n测试完成!")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 