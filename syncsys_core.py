import json
import sqlite3
import os
import time
import uuid
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import hashlib

# watchdog导入 - 用于高效文件监控
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

@dataclass
class SyncRequest:
    """同步请求数据结构"""
    request_id: str
    client_id: str
    operation: str  # SELECT, INSERT, UPDATE, DELETE
    table: str
    data: Dict[str, Any]
    timestamp: float
    
class ConfigManager:
    """配置管理器"""
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件 {self.config_path} 不存在")
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def get(self, key: str, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

class DatabaseManager:
    """数据库管理器"""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
        self._lock = threading.Lock()
    
    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT UNIQUE,
                    client_id TEXT,
                    operation TEXT,
                    table_name TEXT,
                    timestamp REAL,
                    status TEXT,
                    error_message TEXT
                )
            ''')
            conn.commit()
    
    def execute_request(self, request: SyncRequest) -> Dict[str, Any]:
        """执行数据库请求"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    result = self._execute_operation(cursor, request)
                    
                    # 记录操作日志
                    cursor.execute('''
                        INSERT OR REPLACE INTO sync_log 
                        (request_id, client_id, operation, table_name, timestamp, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (request.request_id, request.client_id, request.operation, 
                          request.table, request.timestamp, 'SUCCESS'))
                    
                    conn.commit()
                    return {
                        'status': 'SUCCESS',
                        'data': result,
                        'timestamp': time.time()
                    }
                    
            except Exception as e:
                # 记录错误日志
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO sync_log 
                        (request_id, client_id, operation, table_name, timestamp, status, error_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (request.request_id, request.client_id, request.operation, 
                          request.table, request.timestamp, 'ERROR', str(e)))
                    conn.commit()
                
                return {
                    'status': 'ERROR',
                    'error': str(e),
                    'timestamp': time.time()
                }
    
    def _execute_operation(self, cursor, request: SyncRequest):
        """执行具体的数据库操作"""
        if request.operation == 'SELECT':
            return self._execute_select(cursor, request)
        elif request.operation == 'INSERT':
            return self._execute_insert(cursor, request)
        elif request.operation == 'UPDATE':
            return self._execute_update(cursor, request)
        elif request.operation == 'DELETE':
            return self._execute_delete(cursor, request)
        elif request.operation == 'SQL':
            return self._execute_sql(cursor, request)
        elif request.operation == 'TRANSACTION':
            return self._execute_transaction(cursor, request)
        else:
            raise ValueError(f"不支持的操作类型: {request.operation}")
    
    def _execute_select(self, cursor, request: SyncRequest):
        """执行SELECT操作"""
        # 处理列选择
        columns = "*"
        if 'columns' in request.data and request.data['columns']:
            if isinstance(request.data['columns'], list):
                columns = ', '.join(request.data['columns'])
            else:
                columns = str(request.data['columns'])
        
        where_clause = ""
        params = []
        
        if 'where' in request.data:
            conditions = []
            for key, value in request.data['where'].items():
                conditions.append(f"{key} = ?")
                params.append(value)
            where_clause = f" WHERE {' AND '.join(conditions)}"
        
        # 处理排序
        order_clause = ""
        if 'order_by' in request.data:
            order_clause = f" ORDER BY {request.data['order_by']}"
        
        limit_clause = ""
        if 'limit' in request.data:
            limit_clause = f" LIMIT {request.data['limit']}"
        
        sql = f"SELECT {columns} FROM {request.table}{where_clause}{order_clause}{limit_clause}"
        cursor.execute(sql, params)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def _execute_insert(self, cursor, request: SyncRequest):
        """执行INSERT操作"""
        if 'values' not in request.data:
            raise ValueError("INSERT操作缺少values字段")
        
        values = request.data['values']
        columns = list(values.keys())
        placeholders = ', '.join(['?' for _ in columns])
        
        sql = f"INSERT INTO {request.table} ({', '.join(columns)}) VALUES ({placeholders})"
        cursor.execute(sql, list(values.values()))
        
        return {'inserted_id': cursor.lastrowid, 'rows_affected': cursor.rowcount}
    
    def _execute_update(self, cursor, request: SyncRequest):
        """执行UPDATE操作"""
        if 'values' not in request.data or 'where' not in request.data:
            raise ValueError("UPDATE操作缺少values或where字段")
        
        values = request.data['values']
        where_conditions = request.data['where']
        
        set_clause = ', '.join([f"{key} = ?" for key in values.keys()])
        where_clause = ' AND '.join([f"{key} = ?" for key in where_conditions.keys()])
        
        sql = f"UPDATE {request.table} SET {set_clause} WHERE {where_clause}"
        params = list(values.values()) + list(where_conditions.values())
        
        cursor.execute(sql, params)
        return {'rows_affected': cursor.rowcount}
    
    def _execute_delete(self, cursor, request: SyncRequest):
        """执行DELETE操作"""
        if 'where' not in request.data:
            raise ValueError("DELETE操作缺少where字段")
        
        where_conditions = request.data['where']
        where_clause = ' AND '.join([f"{key} = ?" for key in where_conditions.keys()])
        
        sql = f"DELETE FROM {request.table} WHERE {where_clause}"
        cursor.execute(sql, list(where_conditions.values()))
        
        return {'rows_affected': cursor.rowcount}
    
    def _execute_sql(self, cursor, request: SyncRequest):
        """执行自定义SQL操作"""
        if 'sql' not in request.data:
            raise ValueError("SQL操作缺少sql字段")
        
        sql = request.data['sql']
        params = request.data.get('params', [])
        
        cursor.execute(sql, params)
        
        # 判断是否为查询操作
        if sql.strip().upper().startswith('SELECT'):
            return [dict(row) for row in cursor.fetchall()]
        else:
            return {'rows_affected': cursor.rowcount, 'lastrowid': cursor.lastrowid}
    
    def _execute_transaction(self, cursor, request: SyncRequest):
        """执行事务操作"""
        if 'operations' not in request.data:
            raise ValueError("TRANSACTION操作缺少operations字段")
        
        operations = request.data['operations']
        if not isinstance(operations, list) or not operations:
            raise ValueError("operations必须是非空列表")
        
        results = []
        total_affected_rows = 0
        
        try:
            # 开始事务
            cursor.execute("BEGIN TRANSACTION")
            
            # 执行每个操作
            for i, operation in enumerate(operations):
                if not isinstance(operation, dict):
                    raise ValueError(f"操作 {i+1} 必须是字典格式")
                
                # 验证操作格式
                if 'type' not in operation or 'table' not in operation or 'data' not in operation:
                    raise ValueError(f"操作 {i+1} 缺少必要字段: type, table, data")
                
                op_type = operation['type']
                op_table = operation['table']
                op_data = operation['data']
                
                # 创建临时请求对象
                temp_request = SyncRequest(
                    request_id=f"{request.request_id}_op_{i+1}",
                    client_id=request.client_id,
                    operation=op_type,
                    table=op_table,
                    data=op_data,
                    timestamp=request.timestamp
                )
                
                # 执行单个操作
                if op_type == 'UPDATE':
                    result = self._execute_update(cursor, temp_request)
                elif op_type == 'DELETE':
                    result = self._execute_delete(cursor, temp_request)
                elif op_type == 'INSERT':
                    result = self._execute_insert(cursor, temp_request)
                elif op_type == 'SELECT':
                    result = self._execute_select(cursor, temp_request)
                else:
                    raise ValueError(f"事务中不支持的操作类型: {op_type}")
                
                # 记录SQL和结果
                sql_info = {
                    'operation_index': i + 1,
                    'type': op_type,
                    'table': op_table,
                    'result': result
                }
                
                # 累计影响的行数
                if isinstance(result, dict) and 'rows_affected' in result:
                    total_affected_rows += result['rows_affected']
                
                results.append(sql_info)
            
            # 提交事务
            cursor.execute("COMMIT")
            
            return {
                'transaction_success': True,
                'operations_count': len(operations),
                'total_affected_rows': total_affected_rows,
                'results': results
            }
            
        except Exception as e:
            # 回滚事务
            try:
                cursor.execute("ROLLBACK")
            except:
                pass  # 如果回滚失败，可能事务已经被回滚
            
            raise ValueError(f"事务执行失败: {str(e)}")

class _WatchdogFileHandler(FileSystemEventHandler):
    """watchdog文件事件处理器"""
    
    def __init__(self, callback, processed_files, executor, lock):
        self.callback = callback
        self.processed_files = processed_files
        self.executor = executor
        self.lock = lock
        
    def on_created(self, event):
        """文件创建时触发"""
        if not event.is_directory and event.src_path.endswith('.json'):
            self._handle_file_event(event.src_path)
    
    def on_modified(self, event):
        """文件修改时触发"""
        if not event.is_directory and event.src_path.endswith('.json'):
            self._handle_file_event(event.src_path)
    
    def _handle_file_event(self, file_path_str: str):
        """处理文件事件"""
        file_path = Path(file_path_str)
        filename = file_path.name
        
        with self.lock:
            if filename in self.processed_files:
                return
            self.processed_files.add(filename)
        
        # 确保文件写入完成
        if self._wait_for_file_complete(file_path):
            self.executor.submit(self._safe_callback, file_path)
    
    def _wait_for_file_complete(self, file_path: Path, max_wait: float = 2.0, check_interval: float = 0.1) -> bool:
        """等待文件写入完成"""
        start_time = time.time()
        last_size = -1
        
        while time.time() - start_time < max_wait:
            try:
                if not file_path.exists():
                    time.sleep(check_interval)
                    continue
                
                current_size = file_path.stat().st_size
                if current_size == last_size and current_size > 0:
                    # 尝试读取文件验证完整性
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            json.load(f)
                        return True
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # 文件还没有完全写入，继续等待
                        time.sleep(check_interval)
                        continue
                
                last_size = current_size
                time.sleep(check_interval)
                
            except (OSError, IOError):
                time.sleep(check_interval)
                continue
        
        return False
    
    def _safe_callback(self, file_path: Path):
        """安全执行回调函数"""
        try:
            self.callback(file_path)
        except Exception as e:
            logging.error(f"处理文件 {file_path} 时出错: {e}")


class FileMonitor:
    """文件监控器 - 优先使用watchdog，备用轮询"""
    def __init__(self, folder_path: str, poll_interval: float = 0.1):
        self.folder_path = Path(folder_path)
        self.poll_interval = poll_interval
        self._ensure_folder_exists()
        self._processed_files = set()
        self._running = False
        self._thread = None
        self._observer = None
        self._use_watchdog = WATCHDOG_AVAILABLE
        self._executor = ThreadPoolExecutor(max_workers=5)
        self._lock = threading.Lock()
        
        if self._use_watchdog:
            logging.info("使用watchdog进行文件监控")
        else:
            logging.info("watchdog不可用，使用轮询机制")
    
    def _ensure_folder_exists(self):
        """确保监控文件夹存在"""
        self.folder_path.mkdir(parents=True, exist_ok=True)
    
    def start_monitoring(self, callback):
        """开始监控文件夹"""
        if self._running:
            return
        
        self._running = True
        
        # 先处理已存在的文件
        self._process_existing_files(callback)
        
        if self._use_watchdog:
            self._start_watchdog_monitoring(callback)
        else:
            self._start_polling_monitoring(callback)
    
    def _start_watchdog_monitoring(self, callback):
        """启动watchdog监控"""
        try:
            event_handler = _WatchdogFileHandler(
                callback, self._processed_files, self._executor, self._lock
            )
            self._observer = Observer()
            self._observer.schedule(event_handler, str(self.folder_path), recursive=False)
            self._observer.start()
            logging.info(f"开始watchdog监控文件夹: {self.folder_path}")
        except Exception as e:
            logging.error(f"启动watchdog监控失败: {e}")
            logging.info("切换到轮询机制")
            self._use_watchdog = False
            self._start_polling_monitoring(callback)
    
    def _start_polling_monitoring(self, callback):
        """启动轮询监控"""
        self._thread = threading.Thread(target=self._monitor_loop, args=(callback,))
        self._thread.daemon = True
        self._thread.start()
        logging.info(f"开始轮询监控文件夹: {self.folder_path}")
    
    def stop_monitoring(self):
        """停止监控"""
        if not self._running:
            return
        
        self._running = False
        
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        
        if self._thread:
            self._thread.join()
            self._thread = None
        
        self._executor.shutdown(wait=True)
        logging.info("文件监控已停止")
    
    def _process_existing_files(self, callback):
        """处理已存在的文件"""
        if not self.folder_path.exists():
            return
        
        for file_path in self.folder_path.glob("*.json"):
            filename = file_path.name
            with self._lock:
                if filename not in self._processed_files:
                    self._processed_files.add(filename)
                    self._executor.submit(self._safe_callback, file_path, callback)
    
    def _monitor_loop(self, callback):
        """监控循环（轮询模式）"""
        while self._running:
            try:
                self._check_new_files(callback)
                time.sleep(self.poll_interval)
            except Exception as e:
                logging.error(f"文件监控错误: {e}")
                time.sleep(1)
    
    def _check_new_files(self, callback):
        """检查新文件（轮询模式）"""
        if not self.folder_path.exists():
            return
        
        for file_path in self.folder_path.glob("*.json"):
            with self._lock:
                if file_path.name not in self._processed_files:
                    self._processed_files.add(file_path.name)
                    self._executor.submit(self._safe_callback, file_path, callback)
    
    def _safe_callback(self, file_path: Path, callback):
        """安全执行回调函数"""
        try:
            callback(file_path)
        except Exception as e:
            logging.error(f"处理文件 {file_path} 时出错: {e}")

class SyncProcessor:
    """同步处理器 - 处理设备使用"""
    def __init__(self, config_path: str = "config.json"):
        self.config = ConfigManager(config_path)
        self.db_manager = DatabaseManager(self.config.get('database.path'))
        self.request_monitor = FileMonitor(
            self.config.get('shared_folder.requests'),
            self.config.get('processor.poll_interval', 0.1)
        )
        self.response_folder = Path(self.config.get('shared_folder.responses'))
        self.response_folder.mkdir(parents=True, exist_ok=True)
        
        self.executor = ThreadPoolExecutor(
            max_workers=self.config.get('processor.max_concurrent_requests', 10)
        )
        
        # 初始化邮件发送器
        self.email_sender = None
        self._init_email_sender()
        
        self._setup_logging()
    
    def _init_email_sender(self):
        """初始化邮件发送器"""
        try:
            from email_notification import get_email_sender
            self.email_sender = get_email_sender(self.db_manager, self.config)
            logging.info("邮件发送器初始化成功")
        except ImportError as e:
            logging.warning(f"邮件模块不可用: {e}")
            self.email_sender = None
        except Exception as e:
            logging.error(f"初始化邮件发送器失败: {e}")
            self.email_sender = None
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=getattr(logging, self.config.get('logging.level', 'INFO')),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.get('logging.file', 'syncsys.log')),
                logging.StreamHandler()
            ]
        )
    
    def start(self):
        """启动处理器"""
        logging.info("启动同步处理器...")
        self.request_monitor.start_monitoring(self._process_request_file)
        logging.info("同步处理器已启动")
    
    def stop(self):
        """停止处理器"""
        logging.info("停止同步处理器...")
        self.request_monitor.stop_monitoring()
        self.executor.shutdown(wait=True)
        logging.info("同步处理器已停止")
    
    def _process_request_file(self, file_path: Path):
        """处理请求文件"""
        self.executor.submit(self._handle_request, file_path)
    
    def _handle_request(self, file_path: Path):
        """处理单个请求"""
        request_data = None
        try:
            # 读取请求文件
            with open(file_path, 'r', encoding='utf-8') as f:
                request_data = json.load(f)
            
            # 创建请求对象
            request = SyncRequest(
                request_id=request_data['request_id'],
                client_id=request_data['client_id'],
                operation=request_data['operation'],
                table=request_data['table'],
                data=request_data['data'],
                timestamp=request_data['timestamp']
            )
            
            # 执行数据库操作
            result = self.db_manager.execute_request(request)
            
            logging.info(f"[处理器] 数据库操作状态: {result.get('status')}")
            logging.info(f"[处理器] email_sender存在: {self.email_sender is not None}")
            
            # 检查是否需要发送邮件（仅在数据库操作成功时）
            if result.get('status') == 'SUCCESS':
                logging.info(f"[处理器] 数据库操作成功，检查是否需要发送邮件...")
                
                if not self.email_sender:
                    logging.warning(f"[处理器] email_sender未初始化，跳过邮件发送")
                elif self.email_sender.should_send_email(request_data):
                    logging.info(f"[处理器] 满足邮件发送条件，开始发送邮件...")
                    try:
                        self.email_sender.process_batch_import_request(request_data)
                        logging.info(f"[处理器] 已处理batch_import邮件发送: {request.request_id}")
                    except Exception as email_error:
                        logging.error(f"[处理器] 发送batch_import邮件时出错: {email_error}", exc_info=True)
                        # 邮件发送失败不影响主流程
                else:
                    logging.info(f"[处理器] 不满足邮件发送条件")
            else:
                logging.warning(f"[处理器] 数据库操作失败，不发送邮件")
            
            # 写入响应文件
            response_data = {
                'request_id': request.request_id,
                'client_id': request.client_id,
                'result': result,
                'processed_at': time.time()
            }
            
            response_file = self.response_folder / f"{request.client_id}_{request.request_id}.json"
            with open(response_file, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, ensure_ascii=False, indent=2)
            
            # 删除请求文件
            file_path.unlink()
            
            logging.info(f"处理请求 {request.request_id} 完成")
            
        except Exception as e:
            logging.error(f"处理请求文件 {file_path} 时出错: {e}")
            # 创建错误响应
            try:
                if request_data is None:
                    # 如果无法读取请求数据，使用文件名作为ID
                    request_id = file_path.stem
                    client_id = 'unknown'
                else:
                    request_id = request_data.get('request_id', 'unknown')
                    client_id = request_data.get('client_id', 'unknown')
                
                error_response = {
                    'request_id': request_id,
                    'client_id': client_id,
                    'result': {
                        'status': 'ERROR',
                        'error': str(e),
                        'timestamp': time.time()
                    },
                    'processed_at': time.time()
                }
                
                response_file = self.response_folder / f"{client_id}_{request_id}.json"
                with open(response_file, 'w', encoding='utf-8') as f:
                    json.dump(error_response, f, ensure_ascii=False, indent=2)
                    
                # 删除请求文件（错误情况下也要删除，避免重复处理）
                if file_path.exists():
                    file_path.unlink()
                    
            except Exception as response_error:
                logging.error(f"创建错误响应时出错: {response_error}")
                # 即使创建错误响应失败，也要尝试删除请求文件
                try:
                    if file_path.exists():
                        file_path.unlink()
                except:
                    pass

def generate_client_id() -> str:
    """生成客户端ID"""
    return hashlib.md5(f"{os.getenv('COMPUTERNAME', 'unknown')}_{time.time()}".encode()).hexdigest()[:16]

def generate_request_id() -> str:
    """生成请求ID"""
    return str(uuid.uuid4())

if __name__ == "__main__":
    # 处理器启动示例
    processor = SyncProcessor()
    try:
        processor.start()
        print("处理器已启动，按 Ctrl+C 停止...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        processor.stop()
        print("处理器已停止")