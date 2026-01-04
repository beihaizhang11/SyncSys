#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SyncSys 性能计时器
用于测量各个步骤的详细执行时间
"""

import time
import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field
from contextlib import contextmanager


@dataclass
class TimingResult:
    """计时结果"""
    step_name: str
    start_time: float
    end_time: float
    duration: float
    success: bool = True
    error_message: str = ""
    
    def __post_init__(self):
        if self.duration == 0:
            self.duration = self.end_time - self.start_time


class PerformanceTimer:
    """性能计时器"""
    
    def __init__(self):
        """初始化计时器"""
        self.results: List[TimingResult] = []
        self.start_time = None
        self.current_step = None
        
    def start_timing(self, step_name: str = "总计时"):
        """开始总计时"""
        self.start_time = time.time()
        self.current_step = step_name
        self.results.clear()
        
    @contextmanager
    def time_step(self, step_name: str):
        """计时上下文管理器"""
        start = time.time()
        success = True
        error_msg = ""
        
        try:
            yield
        except Exception as e:
            success = False
            error_msg = str(e)
            raise
        finally:
            end = time.time()
            result = TimingResult(
                step_name=step_name,
                start_time=start,
                end_time=end,
                duration=end - start,
                success=success,
                error_message=error_msg
            )
            self.results.append(result)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取计时摘要"""
        if not self.results:
            return {}
        
        total_time = sum(r.duration for r in self.results)
        successful_steps = [r for r in self.results if r.success]
        failed_steps = [r for r in self.results if not r.success]
        
        summary = {
            "total_steps": len(self.results),
            "successful_steps": len(successful_steps),
            "failed_steps": len(failed_steps),
            "total_time": total_time,
            "step_details": []
        }
        
        for result in self.results:
            step_detail = {
                "step_name": result.step_name,
                "duration": result.duration,
                "percentage": (result.duration / total_time * 100) if total_time > 0 else 0,
                "success": result.success,
                "error_message": result.error_message
            }
            summary["step_details"].append(step_detail)
        
        return summary
    
    def print_summary(self):
        """打印计时摘要"""
        summary = self.get_summary()
        
        if not summary:
            print("没有计时数据")
            return
        
        print("\n" + "=" * 60)
        print("性能分析报告")
        print("=" * 60)
        print(f"总步骤数: {summary['total_steps']}")
        print(f"成功步骤: {summary['successful_steps']}")
        print(f"失败步骤: {summary['failed_steps']}")
        print(f"总耗时: {summary['total_time']:.4f}秒")
        print("\n详细步骤分析:")
        print("-" * 60)
        
        for detail in summary["step_details"]:
            status = "✓" if detail["success"] else "✗"
            print(f"{status} {detail['step_name']:<25} {detail['duration']:.4f}秒 ({detail['percentage']:.1f}%)")
            if not detail["success"] and detail["error_message"]:
                print(f"    错误: {detail['error_message']}")
        
        print("-" * 60)


class DatabasePerformanceAnalyzer:
    """数据库性能分析器"""
    
    def __init__(self, db_manager):
        """初始化分析器"""
        self.db_manager = db_manager
        self.timer = PerformanceTimer()
    
    def analyze_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个请求的性能"""
        from syncsys_core import SyncRequest
        
        self.timer.start_timing("请求处理")
        
        try:
            # 步骤1: 解析请求数据
            with self.timer.time_step("1. 解析请求数据"):
                request = SyncRequest(
                    request_id=request_data['request_id'],
                    client_id=request_data['client_id'],
                    operation=request_data['operation'],
                    table=request_data['table'],
                    data=request_data['data'],
                    timestamp=request_data['timestamp']
                )
            
            # 步骤2: 数据库连接准备
            with self.timer.time_step("2. 数据库连接准备"):
                # 这里模拟连接准备时间
                time.sleep(0.001)  # 1ms模拟
            
            # 步骤3: 执行数据库操作
            with self.timer.time_step("3. 执行数据库操作"):
                result = self.db_manager.execute_request(request)
            
            # 步骤4: 结果处理
            with self.timer.time_step("4. 结果处理"):
                response_data = {
                    'request_id': request.request_id,
                    'client_id': request.client_id,
                    'result': result,
                    'processed_at': time.time()
                }
            
            return response_data
            
        except Exception as e:
            print(f"分析过程中发生错误: {e}")
            return {
                'request_id': request_data.get('request_id', 'unknown'),
                'client_id': request_data.get('client_id', 'unknown'),
                'result': {'status': 'ERROR', 'error': str(e)},
                'processed_at': time.time()
            }


class FileOperationTimer:
    """文件操作计时器"""
    
    def __init__(self):
        """初始化文件操作计时器"""
        self.timer = PerformanceTimer()
    
    def time_file_read(self, file_path: Path) -> Dict[str, Any]:
        """计时文件读取操作"""
        self.timer.start_timing("文件读取")
        
        data = None
        try:
            with self.timer.time_step("1. 文件存在性检查"):
                exists = file_path.exists()
                if not exists:
                    raise FileNotFoundError(f"文件不存在: {file_path}")
            
            with self.timer.time_step("2. 文件大小获取"):
                file_size = file_path.stat().st_size
            
            with self.timer.time_step("3. 文件内容读取"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            with self.timer.time_step("4. JSON解析"):
                data = json.loads(content)
            
            return {
                'success': True,
                'data': data,
                'file_size': file_size,
                'timing_summary': self.timer.get_summary()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timing_summary': self.timer.get_summary()
            }
    
    def time_file_write(self, file_path: Path, data: Dict[str, Any]) -> Dict[str, Any]:
        """计时文件写入操作"""
        self.timer.start_timing("文件写入")
        
        try:
            with self.timer.time_step("1. 目录准备"):
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self.timer.time_step("2. JSON序列化"):
                json_content = json.dumps(data, ensure_ascii=False, indent=2)
            
            with self.timer.time_step("3. 文件写入"):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json_content)
            
            with self.timer.time_step("4. 写入验证"):
                # 验证文件是否正确写入
                written_size = file_path.stat().st_size
                if written_size == 0:
                    raise IOError("文件写入失败，文件大小为0")
            
            return {
                'success': True,
                'written_size': written_size,
                'timing_summary': self.timer.get_summary()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timing_summary': self.timer.get_summary()
            }


def create_performance_report(timings: List[Dict[str, Any]], report_file: str = "performance_report.json"):
    """创建性能报告"""
    report = {
        'generated_at': time.time(),
        'total_tests': len(timings),
        'timings': timings,
        'summary': {
            'avg_total_time': 0,
            'avg_step_times': {},
            'success_rate': 0
        }
    }
    
    if timings:
        # 计算平均时间
        total_times = []
        step_times = {}
        successful_tests = 0
        
        for timing in timings:
            if timing.get('success', False):
                successful_tests += 1
                summary = timing.get('timing_summary', {})
                total_times.append(summary.get('total_time', 0))
                
                for step in summary.get('step_details', []):
                    step_name = step['step_name']
                    if step_name not in step_times:
                        step_times[step_name] = []
                    step_times[step_name].append(step['duration'])
        
        # 计算平均值
        if total_times:
            report['summary']['avg_total_time'] = sum(total_times) / len(total_times)
        
        for step_name, times in step_times.items():
            report['summary']['avg_step_times'][step_name] = sum(times) / len(times)
        
        report['summary']['success_rate'] = successful_tests / len(timings)
    
    # 保存报告
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"性能报告已保存到: {report_file}")
    return report


if __name__ == "__main__":
    # 测试计时器功能
    timer = PerformanceTimer()
    timer.start_timing("测试计时")
    
    with timer.time_step("步骤1: 模拟操作"):
        time.sleep(0.1)
    
    with timer.time_step("步骤2: 另一个操作"):
        time.sleep(0.05)
    
    timer.print_summary() 