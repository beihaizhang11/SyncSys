"""
事务生成器 - 用于生成SyncSys系统的事务JSON文件
支持INSERT、UPDATE、DELETE操作，所有操作都使用字典传输数据
"""

import json
import time
import uuid
import os
from typing import Dict, List, Any, Optional


class TransactionOperationBuilder:
    """操作构建器 - 生成标准化的操作结构"""
    
    @staticmethod
    def create_insert_operation(table: str, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建INSERT操作
        
        Args:
            table: 表名
            data_dict: 要插入的数据字典
        
        Returns:
            INSERT操作字典
        """
        return {
            "type": "INSERT",
            "table": table,
            "data": {"values": data_dict}
        }
    
    @staticmethod
    def create_update_operation(table: str, task_id: str, values_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建UPDATE操作 - 简化版，只需要task_id和要更新的字段
        
        Args:
            table: 表名
            task_id: 任务ID
            values_dict: 要更新的字段字典
        
        Returns:
            UPDATE操作字典
        """
        return {
            "type": "UPDATE",
            "table": table,
            "data": {
                "values": values_dict,
                "where": {"task_id": task_id}
            }
        }
    
    @staticmethod
    def create_delete_operation(table: str, task_id: str) -> Dict[str, Any]:
        """
        创建DELETE操作 - 简化版，只需要task_id
        
        Args:
            table: 表名
            task_id: 任务ID
        
        Returns:
            DELETE操作字典
        """
        return {
            "type": "DELETE",
            "table": table,
            "data": {"where": {"task_id": task_id}}
        }


class TransactionBuilder:
    """
    事务构建器 - 统一的事务生成器
    
    提供两个层次的API：
    1. 底层API：灵活的数据库操作方法（add_insert, add_update, add_delete）
    2. 高级API：面向业务的便捷方法（create_task, update_task_status, assign_staff）
    """
    
    def __init__(self, client_id: Optional[str] = None):
        """
        初始化事务构建器
        
        Args:
            client_id: 客户端ID，如果提供则可以使用高级API方法
        """
        self.operations: List[Dict[str, Any]] = []
        self.client_id = client_id
    
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 如果配置文件不存在，返回默认配置
            return {
                "output_path": "../shared_folder/requests/",
                "file_prefix": "transaction_",
                "file_extension": ".json"
            }
    
    # ===============================================
    # 底层API：灵活的数据库操作方法
    # ===============================================
    
    def add_insert(self, table: str, data_dict: Dict[str, Any]) -> 'TransactionBuilder':
        """
        INSERT操作 - 传入完整的数据字典
        
        Args:
            table: 表名
            data_dict: 包含所有字段的数据字典
        """
        operation = TransactionOperationBuilder.create_insert_operation(table, data_dict)
        self.operations.append(operation)
        return self
    
    def add_update(self, table: str, task_id: str, values_dict: Dict[str, Any]) -> 'TransactionBuilder':
        """
        UPDATE操作 - 简化版，只需要task_id和要更新的字段
        
        Args:
            table: 表名
            task_id: 任务ID（作为WHERE条件）
            values_dict: 要更新的字段字典
        """
        operation = TransactionOperationBuilder.create_update_operation(table, task_id, values_dict)
        self.operations.append(operation)
        return self
    
    def add_delete(self, table: str, task_id: str) -> 'TransactionBuilder':
        """
        DELETE操作 - 简化版，只需要task_id
        
        Args:
            table: 表名
            task_id: 任务ID（作为WHERE条件）
        """
        operation = TransactionOperationBuilder.create_delete_operation(table, task_id)
        self.operations.append(operation)
        return self
    
    def add_delete_with_conditions(self, table: str, where_conditions: Dict[str, Any]) -> 'TransactionBuilder':
        """
        DELETE操作 - 支持复杂的where条件
        
        Args:
            table: 表名
            where_conditions: WHERE条件字典
        """
        operation = {
            "type": "DELETE",
            "table": table,
            "data": {"where": where_conditions}
        }
        self.operations.append(operation)
        return self
    
    def build_transaction(self, request_id: str, client_id: str, timestamp: Optional[int] = None) -> Dict[str, Any]:
        """
        构建完整的事务JSON
        
        Args:
            request_id: 请求ID
            client_id: 客户端ID
            timestamp: 时间戳，如果不提供则使用当前时间
        
        Returns:
            完整的事务JSON字典
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        return {
            "request_id": request_id,
            "client_id": client_id,
            "operation": "TRANSACTION",
            "table": "",
            "data": {"operations": self.operations},
            "timestamp": timestamp
        }
    
    def clear(self) -> 'TransactionBuilder':
        """清空所有操作"""
        self.operations.clear()
        return self
    
    def get_operations_count(self) -> int:
        """获取操作数量"""
        return len(self.operations)
    

    
    def save_to_file(self, filepath: str, request_id: str, client_id: Optional[str] = None, timestamp: Optional[int] = None) -> None:
        """保存到文件"""
        if client_id is None:
            client_id = self.client_id
        if client_id is None:
            raise ValueError("client_id必须提供，可以在初始化时设置或调用时传入")
        json_content = self.generate_json_string(request_id, client_id, timestamp)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json_content)
    
    # ===============================================
    # 高级API：面向业务的便捷方法
    # ===============================================
    
    def create_task(self, task_data: Dict[str, Any]) -> 'TransactionBuilder':
        """
        创建任务 - 高级API
        
        Args:
            task_data: 任务数据字典，如果不包含task_id会自动生成
        """
        if "task_id" not in task_data:
            task_data["task_id"] = str(uuid.uuid4())
        
        self.add_insert("tasks", task_data)
        return self
    
    def update_task_status(self, task_id: str, status: str, updated_by: Optional[str] = None) -> 'TransactionBuilder':
        """
        更新任务状态 - 高级API
        
        Args:
            task_id: 任务ID
            status: 新状态
            updated_by: 更新者
        """
        status_fields = FieldManager.status_update(status, updated_by, int(time.time()))
        self.add_update("tasks", task_id, status_fields)
        return self
    
    def assign_staff(self, task_id: str, staff_email: str, staff_time: Optional[int] = None) -> 'TransactionBuilder':
        """
        分配员工 - 高级API
        
        Args:
            task_id: 任务ID
            staff_email: 员工邮箱
            staff_time: 分配时间，不提供则使用当前时间
        """
        if staff_time is None:
            staff_time = int(time.time())
        
        staff_data = DataDictHelper.build_insert_data(
            task_id=task_id,
            staff_email=staff_email,
            staff_time=staff_time
        )
        self.add_insert("tasks_staff", staff_data)
        return self
    
    def remove_staff(self, task_id: str) -> 'TransactionBuilder':
        """
        移除员工 - 删除该任务的所有员工记录 - 高级API
        
        Args:
            task_id: 任务ID
        """
        self.add_delete("tasks_staff", task_id)
        return self
    
    def remove_specific_staff(self, task_id: str, staff_email: str) -> 'TransactionBuilder':
        """
        移除特定员工 - 删除该任务的指定员工记录 - 高级API
        
        Args:
            task_id: 任务ID
            staff_email: 员工邮箱
        """
        self.add_delete_with_conditions("tasks_staff", {
            "task_id": task_id,
            "staff_email": staff_email
        })
        return self
    
    def generate_transaction(self, request_id: Optional[str] = None, client_id: Optional[str] = None) -> Dict[str, Any]:
        """
        生成事务JSON
        
        Args:
            request_id: 请求ID，不提供则自动生成
            client_id: 客户端ID，不提供则使用初始化时的值
        """
        if request_id is None:
            request_id = f"transaction-{int(time.time())}-{str(uuid.uuid4())[:8]}"
        
        if client_id is None:
            client_id = self.client_id
        if client_id is None:
            raise ValueError("client_id必须提供，可以在初始化时设置或调用时传入")
        
        return self.build_transaction(request_id, client_id)
    
    def generate_json_string(self, request_id: Optional[str] = None, client_id: Optional[str] = None, timestamp: Optional[int] = None, indent: int = 2) -> str:
        """
        生成JSON字符串
        
        Args:
            request_id: 请求ID，不提供则自动生成
            client_id: 客户端ID，不提供则使用初始化时的值
            timestamp: 时间戳，不提供则使用当前时间
            indent: JSON缩进
        """
        if client_id is None:
            client_id = self.client_id
        if client_id is None:
            raise ValueError("client_id必须提供，可以在初始化时设置或调用时传入")
        
        transaction = self.generate_transaction(request_id, client_id)
        return json.dumps(transaction, indent=indent, ensure_ascii=False)
    
    def save_transaction_file(self, filepath: str, request_id: Optional[str] = None) -> None:
        """
        保存事务到文件 - 高级API（需要client_id已在初始化时设置）
        
        Args:
            filepath: 文件路径
            request_id: 请求ID，不提供则自动生成
        """
        if self.client_id is None:
            raise ValueError("使用此方法需要在初始化时设置client_id")
        
        json_content = self.generate_json_string(request_id)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json_content)
    
    def save_to_config_path(self, filename: Optional[str] = None, request_id: Optional[str] = None) -> str:
        """
        使用配置文件中的路径保存事务文件
        
        Args:
            filename: 文件名，不提供则自动生成
            request_id: 请求ID，不提供则自动生成
            
        Returns:
            保存的文件完整路径
        """
        if self.client_id is None:
            raise ValueError("使用此方法需要在初始化时设置client_id")
        
        config = self.load_config()
        output_path = config.get("output_path", "../shared_folder/requests/")
        file_prefix = config.get("file_prefix", "transaction_")
        file_extension = config.get("file_extension", ".json")
        
        if filename is None:
            if request_id is None:
                request_id = f"{int(time.time())}-{str(uuid.uuid4())[:8]}"
            filename = f"{file_prefix}{request_id}{file_extension}"
        
        # 确保输出目录存在
        full_output_path = os.path.join(os.path.dirname(__file__), output_path)
        os.makedirs(full_output_path, exist_ok=True)
        
        # 完整文件路径
        full_filepath = os.path.join(full_output_path, filename)
        
        # 保存文件
        json_content = self.generate_json_string(request_id)
        with open(full_filepath, 'w', encoding='utf-8') as f:
            f.write(json_content)
        
        return full_filepath
    
    def reset(self) -> 'TransactionBuilder':
        """重置构建器"""
        self.clear()
        return self


class DataDictHelper:
    """数据字典助手 - 帮助构建数据字典"""
    
    @staticmethod
    def build_insert_data(**kwargs) -> Dict[str, Any]:
        """
        构建INSERT操作的数据字典
        
        Args:
            **kwargs: 任意字段键值对
        
        Returns:
            过滤掉None值的字典
        """
        return {k: v for k, v in kwargs.items() if v is not None}
    
    @staticmethod
    def build_where_conditions(**where_conditions) -> Dict[str, Any]:
        """
        构建WHERE条件字典
        
        Args:
            **where_conditions: WHERE条件键值对
        
        Returns:
            过滤掉None值的WHERE条件字典
        """
        return {k: v for k, v in where_conditions.items() if v is not None}


class FieldManager:
    """字段管理器 - 管理不同业务场景的字段组合"""
    
    @staticmethod
    def status_update(status: str, updated_by: Optional[str] = None, update_time: Optional[int] = None) -> Dict[str, Any]:
        """
        状态更新字段组合
        
        Args:
            status: 任务状态
            updated_by: 更新者
            update_time: 更新时间
        
        Returns:
            状态更新字段字典
        """
        fields: Dict[str, Any] = {"task_status": status}
        if updated_by:
            fields["assigned_by"] = updated_by
        if update_time:
            fields["assigned_time"] = update_time
        return fields
    
    @staticmethod
    def acceptance_update(accepted_by: str, accepted_time: Optional[int] = None) -> Dict[str, Any]:
        """
        接受任务字段组合
        
        Args:
            accepted_by: 接受者
            accepted_time: 接受时间
        
        Returns:
            接受任务字段字典
        """
        fields: Dict[str, Any] = {"accepted_by": accepted_by}
        if accepted_time:
            fields["accepted_time"] = accepted_time
        return fields
    
    @staticmethod
    def completion_update(finished_by: str, finished_time: Optional[int] = None) -> Dict[str, Any]:
        """
        完成任务字段组合
        
        Args:
            finished_by: 完成者
            finished_time: 完成时间
        
        Returns:
            完成任务字段字典
        """
        fields: Dict[str, Any] = {"finished_by": finished_by, "task_status": "finished"}
        if finished_time:
            fields["finished_time"] = finished_time
        return fields
    
    @staticmethod
    def rejection_update(rejected_by: str, reject_reason: str, rejected_time: Optional[int] = None) -> Dict[str, Any]:
        """
        拒绝任务字段组合
        
        Args:
            rejected_by: 拒绝者
            reject_reason: 拒绝原因
            rejected_time: 拒绝时间
        
        Returns:
            拒绝任务字段字典
        """
        fields: Dict[str, Any] = {
            "rejected_by": rejected_by,
            "reject_reason": reject_reason,
            "task_status": "rejected"
        }
        if rejected_time:
            fields["rejected_time"] = rejected_time
        return fields