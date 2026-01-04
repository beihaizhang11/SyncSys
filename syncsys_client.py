import json
import os
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from syncsys_core import ConfigManager, FileMonitor, generate_client_id, generate_request_id
import logging

@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    data: Optional[Union[List[Dict], Dict]] = None
    error: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: Optional[float] = None

class SyncClient:
    """同步客户端 - 主机使用"""
    
    def __init__(self, config_path: str = "config.json", client_id: Optional[str] = None):
        self.config = ConfigManager(config_path)
        self.client_id = client_id or generate_client_id()
        
        # 文件夹路径
        self.request_folder = Path(self.config.get('shared_folder.requests'))
        self.response_folder = Path(self.config.get('shared_folder.responses'))
        
        # 确保文件夹存在
        self.request_folder.mkdir(parents=True, exist_ok=True)
        self.response_folder.mkdir(parents=True, exist_ok=True)
        
        # 配置参数
        self.poll_interval = self.config.get('client.poll_interval', 0.2)
        self.request_timeout = self.config.get('client.request_timeout', 30)
        self.retry_attempts = self.config.get('client.retry_attempts', 3)
        self.retry_delay = self.config.get('client.retry_delay', 1)
        
        # 响应监控器
        self.response_monitor = FileMonitor(str(self.response_folder), self.poll_interval)
        self._pending_requests = {}
        self._response_events = {}
        self._monitor_started = False
        self._lock = threading.Lock()
        
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=getattr(logging, self.config.get('logging.level', 'INFO')),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def _start_response_monitor(self):
        """启动响应监控器"""
        if not self._monitor_started:
            self.response_monitor.start_monitoring(self._handle_response_file)
            self._monitor_started = True
    
    def _handle_response_file(self, file_path: Path):
        """处理响应文件"""
        try:
            # 检查是否是本客户端的响应文件
            if not file_path.name.startswith(f"{self.client_id}_"):
                return
            
            # 读取响应文件
            with open(file_path, 'r', encoding='utf-8') as f:
                response_data = json.load(f)
            
            request_id = response_data.get('request_id')
            if request_id in self._response_events:
                with self._lock:
                    self._pending_requests[request_id] = response_data
                    self._response_events[request_id].set()
            
            # 删除响应文件
            file_path.unlink()
            
        except Exception as e:
            logging.error(f"处理响应文件 {file_path} 时出错: {e}")
    
    def _send_request(self, operation: str, table: str, data: Dict[str, Any]) -> str:
        """发送请求"""
        request_id = generate_request_id()
        
        request_data = {
            'request_id': request_id,
            'client_id': self.client_id,
            'operation': operation,
            'table': table,
            'data': data,
            'timestamp': time.time()
        }
        
        # 创建响应事件
        with self._lock:
            self._response_events[request_id] = threading.Event()
        
        # 写入请求文件
        request_file = self.request_folder / f"{self.client_id}_{request_id}.json"
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, ensure_ascii=False, indent=2)
        
        return request_id
    
    def _wait_for_response(self, request_id: str) -> QueryResult:
        """等待响应"""
        self._start_response_monitor()
        
        # 等待响应
        event = self._response_events.get(request_id)
        if not event:
            return QueryResult(success=False, error="请求事件不存在")
        
        if event.wait(timeout=self.request_timeout):
            # 获取响应数据
            with self._lock:
                response_data = self._pending_requests.pop(request_id, None)
                self._response_events.pop(request_id, None)
            
            if response_data:
                result = response_data['result']
                if result['status'] == 'SUCCESS':
                    return QueryResult(
                        success=True,
                        data=result.get('data'),
                        request_id=request_id,
                        timestamp=result.get('timestamp')
                    )
                else:
                    return QueryResult(
                        success=False,
                        error=result.get('error', '未知错误'),
                        request_id=request_id,
                        timestamp=result.get('timestamp')
                    )
            else:
                return QueryResult(success=False, error="响应数据丢失")
        else:
            # 超时清理
            with self._lock:
                self._response_events.pop(request_id, None)
            return QueryResult(success=False, error="请求超时")
    
    def _execute_with_retry(self, operation: str, table: str, data: Dict[str, Any]) -> QueryResult:
        """带重试的执行"""
        last_error = None
        
        for attempt in range(self.retry_attempts):
            try:
                request_id = self._send_request(operation, table, data)
                result = self._wait_for_response(request_id)
                
                if result.success:
                    return result
                
                last_error = result.error
                
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                    
            except Exception as e:
                last_error = str(e)
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
        
        return QueryResult(success=False, error=f"重试 {self.retry_attempts} 次后失败: {last_error}")
    
    # 数据库操作方法
    
    def select(self, table: str, where: Optional[Dict[str, Any]] = None, 
               columns: Optional[List[str]] = None, limit: Optional[int] = None,
               order_by: Optional[str] = None) -> QueryResult:
        """查询数据"""
        data = {}
        if where:
            data['where'] = where
        if columns:
            data['columns'] = columns
        if limit:
            data['limit'] = limit
        if order_by:
            data['order_by'] = order_by
        
        return self._execute_with_retry('SELECT', table, data)
    
    def insert(self, table: str, values: Dict[str, Any]) -> QueryResult:
        """插入数据"""
        data = {'values': values}
        return self._execute_with_retry('INSERT', table, data)
    
    def update(self, table: str, values: Dict[str, Any], 
               where: Dict[str, Any]) -> QueryResult:
        """更新数据"""
        data = {
            'values': values,
            'where': where
        }
        return self._execute_with_retry('UPDATE', table, data)
    
    def delete(self, table: str, where: Dict[str, Any]) -> QueryResult:
        """删除数据"""
        data = {'where': where}
        return self._execute_with_retry('DELETE', table, data)
    
    # 便捷方法
    
    def find_one(self, table: str, where: Optional[Dict[str, Any]] = None, order_by: Optional[str] = None) -> QueryResult:
        """查询单条记录"""
        result = self.select(table, where, limit=1, order_by=order_by)
        if result.success and result.data:
            result.data = result.data[0] if result.data else None
        return result
    
    def find_all(self, table: str, where: Optional[Dict[str, Any]] = None) -> QueryResult:
        """查询所有记录"""
        return self.select(table, where)
    
    def count(self, table: str, where: Optional[Dict[str, Any]] = None) -> QueryResult:
        """计数"""
        result = self.select(table, where)
        if result.success:
            result.data = len(result.data) if result.data else 0
        return result
    
    def exists(self, table: str, where: Dict[str, Any]) -> QueryResult:
        """检查记录是否存在"""
        result = self.find_one(table, where)
        if result.success:
            result.data = result.data is not None
        return result
    
    def execute_sql(self, sql: str, params: Optional[tuple] = None) -> QueryResult:
        """执行原生SQL查询"""
        data = {
            'sql': sql
        }
        if params:
            data['params'] = list(params)
        
        return self._execute_with_retry('SQL', '', data)
    
    def close(self):
        """关闭客户端"""
        if self._monitor_started:
            self.response_monitor.stop_monitoring()
            self._monitor_started = False

class SyncTable:
    """表操作封装类"""
    
    def __init__(self, client: SyncClient, table_name: str):
        self.client = client
        self.table_name = table_name
    
    def select(self, where: Optional[Dict[str, Any]] = None, 
               columns: Optional[List[str]] = None, limit: Optional[int] = None,
               order_by: Optional[str] = None) -> QueryResult:
        return self.client.select(self.table_name, where, columns, limit, order_by)
    
    def insert(self, values: Dict[str, Any]) -> QueryResult:
        return self.client.insert(self.table_name, values)
    
    def update(self, values: Dict[str, Any], where: Dict[str, Any]) -> QueryResult:
        return self.client.update(self.table_name, values, where)
    
    def delete(self, where: Dict[str, Any]) -> QueryResult:
        return self.client.delete(self.table_name, where)
    
    def find_one(self, where: Optional[Dict[str, Any]] = None, order_by: Optional[str] = None) -> QueryResult:
        return self.client.find_one(self.table_name, where, order_by=order_by)
    
    def find_all(self, where: Optional[Dict[str, Any]] = None) -> QueryResult:
        return self.client.find_all(self.table_name, where)
    
    def count(self, where: Optional[Dict[str, Any]] = None) -> QueryResult:
        return self.client.count(self.table_name, where)
    
    def exists(self, where: Dict[str, Any]) -> QueryResult:
        return self.client.exists(self.table_name, where)
    
    def execute_sql(self, sql: str, params: Optional[tuple] = None) -> QueryResult:
        """执行原生SQL查询"""
        return self.client.execute_sql(sql, params)

class SyncDatabase:
    """数据库操作封装类"""
    
    def __init__(self, config_path: str = "config.json", client_id: Optional[str] = None):
        self.client = SyncClient(config_path, client_id)
        self._tables = {}
    
    def table(self, table_name: str) -> SyncTable:
        """获取表操作对象"""
        if table_name not in self._tables:
            self._tables[table_name] = SyncTable(self.client, table_name)
        return self._tables[table_name]
    
    def execute_sql(self, sql: str, params: Optional[tuple] = None) -> QueryResult:
        """执行原生SQL查询"""
        return self.client.execute_sql(sql, params)
    
    def close(self):
        """关闭数据库连接"""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# 使用示例
if __name__ == "__main__":
    # 基本使用
    client = SyncClient()
    
    # 插入数据
    result = client.insert('users', {
        'name': '张三',
        'age': 25,
        'email': 'zhangsan@example.com'
    })
    
    if result.success:
        print(f"插入成功: {result.data}")
    else:
        print(f"插入失败: {result.error}")
    
    # 查询数据
    result = client.select('users', where={'name': '张三'})
    if result.success:
        print(f"查询结果: {result.data}")
    
    # 使用表封装
    users_table = SyncTable(client, 'users')
    result = users_table.find_all()
    if result.success:
        print(f"所有用户: {result.data}")
    
    # 使用数据库封装
    with SyncDatabase() as db:
        users = db.table('users')
        result = users.insert({'name': '李四', 'age': 30})
        if result.success:
            print("插入成功")
    
    client.close()