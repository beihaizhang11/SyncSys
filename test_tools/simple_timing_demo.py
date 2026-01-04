#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SyncSys 简单计时演示
展示如何使用计时器测量各个步骤的时间
"""

import time
import json
from pathlib import Path
from test_tools.performance_timer import PerformanceTimer, FileOperationTimer


def demo_basic_timing():
    """演示基本计时功能"""
    print("基本计时功能演示")
    print("=" * 40)
    
    timer = PerformanceTimer()
    timer.start_timing("演示流程")
    
    # 步骤1: 数据准备
    with timer.time_step("步骤1: 数据准备"):
        time.sleep(0.05)  # 模拟50ms
        data = {"test": "data", "timestamp": time.time()}
    
    # 步骤2: 数据处理
    with timer.time_step("步骤2: 数据处理"):
        time.sleep(0.1)   # 模拟100ms
        processed_data = json.dumps(data, ensure_ascii=False, indent=2)
    
    # 步骤3: 结果输出
    with timer.time_step("步骤3: 结果输出"):
        time.sleep(0.02)  # 模拟20ms
        print(f"处理完成，数据大小: {len(processed_data)} 字节")
    
    # 打印计时结果
    timer.print_summary()


def demo_file_timing():
    """演示文件操作计时"""
    print("\n文件操作计时演示")
    print("=" * 40)
    
    file_timer = FileOperationTimer()
    
    # 准备测试数据
    test_data = {
        "request_id": "demo_test_123",
        "client_id": "demo_client",
        "operation": "INSERT",
        "table": "test_table",
        "data": {
            "values": {
                "id": 1,
                "name": "测试数据",
                "description": "这是一个演示用的测试数据"
            }
        },
        "timestamp": time.time()
    }
    
    test_file = Path("demo_test.json")
    
    # 测试文件写入
    print("测试文件写入...")
    write_result = file_timer.time_file_write(test_file, test_data)
    
    if write_result['success']:
        print(f"✓ 文件写入成功，大小: {write_result['written_size']} 字节")
        # 打印写入计时
        write_summary = write_result['timing_summary']
        print("\n文件写入步骤时间:")
        for step in write_summary.get('step_details', []):
            print(f"  {step['step_name']:<20} {step['duration']:.4f}秒")
    else:
        print(f"✗ 文件写入失败: {write_result['error']}")
        return
    
    # 测试文件读取
    print(f"\n测试文件读取...")
    read_result = file_timer.time_file_read(test_file)
    
    if read_result['success']:
        print(f"✓ 文件读取成功，大小: {read_result['file_size']} 字节")
        # 打印读取计时
        read_summary = read_result['timing_summary']
        print("\n文件读取步骤时间:")
        for step in read_summary.get('step_details', []):
            print(f"  {step['step_name']:<20} {step['duration']:.4f}秒")
    else:
        print(f"✗ 文件读取失败: {read_result['error']}")
    
    # 清理测试文件
    try:
        test_file.unlink()
        print("\n✓ 清理测试文件完成")
    except:
        pass


def demo_database_timing():
    """演示数据库操作计时"""
    print("\n数据库操作计时演示")
    print("=" * 40)
    
    try:
        from syncsys_core import DatabaseManager
        from test_tools.performance_timer import DatabasePerformanceAnalyzer
        
        # 初始化数据库管理器和分析器
        db_manager = DatabaseManager("WorkshopTasks1.db")
        db_analyzer = DatabasePerformanceAnalyzer(db_manager)
        
        # 准备测试请求
        request_data = {
            "request_id": "timing_demo_123",
            "client_id": "demo_client",
            "operation": "SELECT",
            "table": "tasks",
            "data": {
                "columns": ["task_id", "task_name", "status"],
                "limit": 5
            },
            "timestamp": time.time()
        }
        
        print("执行数据库操作...")
        result = db_analyzer.analyze_request(request_data)
        
        if result['result']['status'] == 'SUCCESS':
            print(f"✓ 数据库操作成功")
            
            # 打印数据库操作计时
            db_summary = db_analyzer.timer.get_summary()
            print("\n数据库操作步骤时间:")
            for step in db_summary.get('step_details', []):
                print(f"  {step['step_name']:<25} {step['duration']:.4f}秒")
            
            # 显示查询结果
            data = result['result']['data']
            if isinstance(data, list):
                print(f"\n查询返回 {len(data)} 条记录")
        else:
            print(f"✗ 数据库操作失败: {result['result'].get('error', '未知错误')}")
    
    except Exception as e:
        print(f"数据库演示出错: {e}")


def demo_custom_timing():
    """演示自定义计时场景"""
    print("\n自定义计时场景演示")
    print("=" * 40)
    
    timer = PerformanceTimer()
    timer.start_timing("自定义场景")
    
    # 模拟复杂的业务流程
    with timer.time_step("初始化"):
        time.sleep(0.01)
    
    with timer.time_step("数据验证"):
        time.sleep(0.03)
    
    with timer.time_step("业务逻辑处理"):
        time.sleep(0.08)
    
    with timer.time_step("结果封装"):
        time.sleep(0.02)
    
    with timer.time_step("日志记录"):
        time.sleep(0.01)
    
    # 获取并分析计时结果
    summary = timer.get_summary()
    
    print(f"总执行时间: {summary['total_time']:.4f}秒")
    print(f"成功步骤: {summary['successful_steps']}/{summary['total_steps']}")
    
    print("\n各步骤时间占比:")
    for step in summary['step_details']:
        print(f"  {step['step_name']:<15} {step['duration']:.4f}秒 ({step['percentage']:.1f}%)")


def main():
    """主演示函数"""
    print("SyncSys 计时器功能演示")
    print("=" * 50)
    print("这个演示将展示如何使用计时器测量各个步骤的执行时间")
    print("包括基本计时、文件操作计时、数据库操作计时等")
    
    input("\n按 Enter 键开始演示...")
    
    # 基本计时演示
    demo_basic_timing()
    
    # 文件操作计时演示
    demo_file_timing()
    
    # 数据库操作计时演示
    demo_database_timing()
    
    # 自定义计时演示
    demo_custom_timing()
    
    print("\n" + "=" * 50)
    print("演示完成！")
    print("\n使用说明:")
    print("1. 使用 PerformanceTimer 进行基本计时")
    print("2. 使用 FileOperationTimer 测量文件操作时间")
    print("3. 使用 DatabasePerformanceAnalyzer 分析数据库性能")
    print("4. 使用 with timer.time_step('步骤名') 包装需要计时的代码")
    print("5. 调用 timer.print_summary() 查看详细报告")


if __name__ == "__main__":
    main() 