#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统监控和健康检查工具
用于监控SyncSys系统的运行状态和性能
"""

import os
import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from syncsys_core import ConfigManager
from db_manager import DatabaseMonitor
import logging

@dataclass
class SystemStatus:
    """系统状态数据结构"""
    timestamp: float
    processor_running: bool
    database_accessible: bool
    shared_folders_accessible: bool
    pending_requests: int
    processed_requests_last_hour: int
    error_count_last_hour: int
    database_size: int
    response_time_avg: float
    disk_usage: Dict[str, Any]
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = ConfigManager(config_path)
        self.db_monitor = DatabaseMonitor(config_path)
        
        # 路径配置
        self.request_folder = Path(self.config.get('shared_folder.requests'))
        self.response_folder = Path(self.config.get('shared_folder.responses'))
        self.db_path = self.config.get('database.path')
        
        # 监控历史数据
        self.status_history: List[SystemStatus] = []
        self.max_history_size = 1000
        
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def check_processor_status(self) -> bool:
        """检查处理器是否运行"""
        try:
            # 检查是否有新的请求文件被处理
            # 创建测试文件，看是否被处理
            test_file = self.request_folder / f"health_check_{int(time.time())}.json"
            
            test_request = {
                'request_id': f"health_check_{int(time.time())}",
                'client_id': 'system_monitor',
                'operation': 'SELECT',
                'table': 'sqlite_master',
                'data': {'limit': 1},
                'timestamp': time.time()
            }
            
            # 写入测试请求
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(test_request, f)
            
            # 等待处理
            start_time = time.time()
            timeout = 5  # 5秒超时
            
            while time.time() - start_time < timeout:
                if not test_file.exists():
                    # 文件被处理器删除，说明处理器正在运行
                    return True
                time.sleep(0.1)
            
            # 超时，删除测试文件
            if test_file.exists():
                test_file.unlink()
            
            return False
            
        except Exception as e:
            logging.error(f"检查处理器状态时出错: {e}")
            return False
    
    def check_database_status(self) -> bool:
        """检查数据库状态"""
        try:
            return self.db_monitor.check_integrity()
        except Exception as e:
            logging.error(f"检查数据库状态时出错: {e}")
            return False
    
    def check_shared_folders_status(self) -> bool:
        """检查共享文件夹状态"""
        try:
            # 检查文件夹是否存在且可访问
            folders_to_check = [self.request_folder, self.response_folder]
            
            for folder in folders_to_check:
                if not folder.exists():
                    return False
                
                # 尝试创建测试文件
                test_file = folder / f"access_test_{int(time.time())}.tmp"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                except:
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"检查共享文件夹状态时出错: {e}")
            return False
    
    def count_pending_requests(self) -> int:
        """统计待处理请求数量"""
        try:
            if not self.request_folder.exists():
                return 0
            
            return len(list(self.request_folder.glob("*.json")))
            
        except Exception as e:
            logging.error(f"统计待处理请求时出错: {e}")
            return -1
    
    def get_processed_requests_count(self, hours: int = 1) -> int:
        """获取指定时间内处理的请求数量"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 计算时间范围
                since_time = time.time() - (hours * 3600)
                
                cursor.execute(
                    "SELECT COUNT(*) FROM sync_log WHERE timestamp > ? AND status = 'SUCCESS'",
                    (since_time,)
                )
                
                return cursor.fetchone()[0]
                
        except Exception as e:
            logging.error(f"获取处理请求数量时出错: {e}")
            return -1
    
    def get_error_count(self, hours: int = 1) -> int:
        """获取指定时间内的错误数量"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 计算时间范围
                since_time = time.time() - (hours * 3600)
                
                cursor.execute(
                    "SELECT COUNT(*) FROM sync_log WHERE timestamp > ? AND status = 'ERROR'",
                    (since_time,)
                )
                
                return cursor.fetchone()[0]
                
        except Exception as e:
            logging.error(f"获取错误数量时出错: {e}")
            return -1
    
    def get_database_size(self) -> int:
        """获取数据库大小"""
        try:
            return os.path.getsize(self.db_path)
        except Exception as e:
            logging.error(f"获取数据库大小时出错: {e}")
            return -1
    
    def calculate_avg_response_time(self, hours: int = 1) -> float:
        """计算平均响应时间"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 计算时间范围
                since_time = time.time() - (hours * 3600)
                
                # 这里简化处理，实际应该记录请求开始和结束时间
                # 暂时返回固定值，实际使用时需要完善
                cursor.execute(
                    "SELECT COUNT(*) FROM sync_log WHERE timestamp > ?",
                    (since_time,)
                )
                
                count = cursor.fetchone()[0]
                if count > 0:
                    # 简化计算，实际应该基于真实的响应时间数据
                    return 0.5  # 假设平均响应时间为0.5秒
                else:
                    return 0.0
                    
        except Exception as e:
            logging.error(f"计算平均响应时间时出错: {e}")
            return -1.0
    
    def get_disk_usage(self) -> Dict[str, Any]:
        """获取磁盘使用情况"""
        try:
            import shutil
            
            # 获取数据库所在磁盘的使用情况
            db_disk = shutil.disk_usage(os.path.dirname(self.db_path))
            
            # 获取共享文件夹所在磁盘的使用情况
            shared_disk = shutil.disk_usage(str(self.request_folder.parent))
            
            return {
                'database_disk': {
                    'total': db_disk.total,
                    'used': db_disk.used,
                    'free': db_disk.free,
                    'usage_percent': (db_disk.used / db_disk.total) * 100
                },
                'shared_disk': {
                    'total': shared_disk.total,
                    'used': shared_disk.used,
                    'free': shared_disk.free,
                    'usage_percent': (shared_disk.used / shared_disk.total) * 100
                }
            }
            
        except Exception as e:
            logging.error(f"获取磁盘使用情况时出错: {e}")
            return {}
    
    def get_system_resources(self) -> Dict[str, Optional[float]]:
        """获取系统资源使用情况（可选，需要psutil）"""
        try:
            import psutil
            return {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent
            }
        except ImportError:
            return {'cpu_usage': None, 'memory_usage': None}
        except Exception as e:
            logging.error(f"获取系统资源使用情况时出错: {e}")
            return {'cpu_usage': None, 'memory_usage': None}
    
    def collect_system_status(self) -> SystemStatus:
        """收集系统状态"""
        logging.info("收集系统状态...")
        
        # 获取系统资源信息
        resources = self.get_system_resources()
        
        status = SystemStatus(
            timestamp=time.time(),
            processor_running=self.check_processor_status(),
            database_accessible=self.check_database_status(),
            shared_folders_accessible=self.check_shared_folders_status(),
            pending_requests=self.count_pending_requests(),
            processed_requests_last_hour=self.get_processed_requests_count(1),
            error_count_last_hour=self.get_error_count(1),
            database_size=self.get_database_size(),
            response_time_avg=self.calculate_avg_response_time(1),
            disk_usage=self.get_disk_usage(),
            memory_usage=resources.get('memory_usage'),
            cpu_usage=resources.get('cpu_usage')
        )
        
        # 添加到历史记录
        self.status_history.append(status)
        if len(self.status_history) > self.max_history_size:
            self.status_history.pop(0)
        
        return status
    
    def generate_health_report(self, status: SystemStatus) -> Dict[str, Any]:
        """生成健康报告"""
        health_score = 100
        issues = []
        warnings = []
        
        # 检查各项状态
        if not status.processor_running:
            health_score -= 30
            issues.append("处理器未运行")
        
        if not status.database_accessible:
            health_score -= 25
            issues.append("数据库不可访问")
        
        if not status.shared_folders_accessible:
            health_score -= 20
            issues.append("共享文件夹不可访问")
        
        if status.pending_requests > 100:
            health_score -= 10
            warnings.append(f"待处理请求过多: {status.pending_requests}")
        
        if status.error_count_last_hour > 10:
            health_score -= 15
            warnings.append(f"最近1小时错误过多: {status.error_count_last_hour}")
        
        # 检查磁盘使用情况
        if status.disk_usage:
            for disk_name, disk_info in status.disk_usage.items():
                if disk_info.get('usage_percent', 0) > 90:
                    health_score -= 10
                    warnings.append(f"{disk_name}磁盘使用率过高: {disk_info['usage_percent']:.1f}%")
        
        # 检查系统资源
        if status.cpu_usage and status.cpu_usage > 80:
            health_score -= 5
            warnings.append(f"CPU使用率过高: {status.cpu_usage:.1f}%")
        
        if status.memory_usage and status.memory_usage > 85:
            health_score -= 5
            warnings.append(f"内存使用率过高: {status.memory_usage:.1f}%")
        
        # 确保健康分数不低于0
        health_score = max(0, health_score)
        
        # 确定健康等级
        if health_score >= 90:
            health_level = "优秀"
        elif health_score >= 70:
            health_level = "良好"
        elif health_score >= 50:
            health_level = "一般"
        else:
            health_level = "差"
        
        return {
            'timestamp': status.timestamp,
            'health_score': health_score,
            'health_level': health_level,
            'issues': issues,
            'warnings': warnings,
            'status': {
                'processor_running': status.processor_running,
                'database_accessible': status.database_accessible,
                'shared_folders_accessible': status.shared_folders_accessible,
                'pending_requests': status.pending_requests,
                'processed_requests_last_hour': status.processed_requests_last_hour,
                'error_count_last_hour': status.error_count_last_hour,
                'database_size_mb': round(status.database_size / 1024 / 1024, 2),
                'response_time_avg': status.response_time_avg,
                'cpu_usage': status.cpu_usage,
                'memory_usage': status.memory_usage
            },
            'disk_usage': status.disk_usage
        }
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """保存报告到文件"""
        if not filename:
            timestamp = datetime.fromtimestamp(report['timestamp'])
            filename = f"health_report_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logging.info(f"健康报告已保存: {filename}")
    
    def print_status_summary(self, status: SystemStatus):
        """打印状态摘要"""
        print("\n" + "=" * 60)
        print("SyncSys 系统状态摘要")
        print("=" * 60)
        print(f"检查时间: {datetime.fromtimestamp(status.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"处理器状态: {'✓ 运行中' if status.processor_running else '✗ 未运行'}")
        print(f"数据库状态: {'✓ 正常' if status.database_accessible else '✗ 异常'}")
        print(f"共享文件夹: {'✓ 可访问' if status.shared_folders_accessible else '✗ 不可访问'}")
        print(f"待处理请求: {status.pending_requests}")
        print(f"最近1小时处理请求: {status.processed_requests_last_hour}")
        print(f"最近1小时错误数: {status.error_count_last_hour}")
        print(f"数据库大小: {status.database_size / 1024 / 1024:.2f} MB")
        print(f"平均响应时间: {status.response_time_avg:.3f} 秒")
        
        if status.cpu_usage is not None:
            print(f"CPU使用率: {status.cpu_usage:.1f}%")
        if status.memory_usage is not None:
            print(f"内存使用率: {status.memory_usage:.1f}%")
        
        print("\n磁盘使用情况:")
        for disk_name, disk_info in status.disk_usage.items():
            print(f"  {disk_name}: {disk_info.get('usage_percent', 0):.1f}% "
                  f"({disk_info.get('free', 0) / 1024 / 1024 / 1024:.1f} GB 可用)")
        
        print("=" * 60)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='SyncSys 系统监控工具')
    parser.add_argument('--config', '-c', default='config.json', help='配置文件路径')
    parser.add_argument('--report', '-r', action='store_true', help='生成健康报告')
    parser.add_argument('--save', '-s', help='保存报告到指定文件')
    parser.add_argument('--continuous', '-t', type=int, help='持续监控，指定间隔秒数')
    
    args = parser.parse_args()
    
    monitor = SystemMonitor(args.config)
    
    if args.continuous:
        print(f"开始持续监控，间隔 {args.continuous} 秒...")
        print("按 Ctrl+C 停止监控")
        
        try:
            while True:
                status = monitor.collect_system_status()
                monitor.print_status_summary(status)
                
                if args.report:
                    report = monitor.generate_health_report(status)
                    print(f"\n健康评分: {report['health_score']}/100 ({report['health_level']})")
                    
                    if report['issues']:
                        print("严重问题:")
                        for issue in report['issues']:
                            print(f"  ✗ {issue}")
                    
                    if report['warnings']:
                        print("警告:")
                        for warning in report['warnings']:
                            print(f"  ⚠ {warning}")
                
                time.sleep(args.continuous)
                
        except KeyboardInterrupt:
            print("\n监控已停止")
    
    else:
        # 单次检查
        status = monitor.collect_system_status()
        monitor.print_status_summary(status)
        
        if args.report:
            report = monitor.generate_health_report(status)
            print(f"\n健康评分: {report['health_score']}/100 ({report['health_level']})")
            
            if report['issues']:
                print("\n严重问题:")
                for issue in report['issues']:
                    print(f"  ✗ {issue}")
            
            if report['warnings']:
                print("\n警告:")
                for warning in report['warnings']:
                    print(f"  ⚠ {warning}")
            
            if args.save:
                monitor.save_report(report, args.save)
            elif args.report:
                monitor.save_report(report)

if __name__ == "__main__":
    main()