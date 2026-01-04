# SyncSys事务生成器

这个模块提供了一套完整的工具来生成符合SyncSys系统要求的事务JSON文件。

## 核心特性

- **统一接口**: 一个类提供两个层次的API，满足不同使用场景
- **简化操作**: 基于task_id的简化操作，符合系统实际使用场景
- **灵活更新**: UPDATE操作支持任意字段组合，只需传入values字典
- **简单删除**: DELETE操作只需要task_id，适用于大多数场景
- **复杂条件支持**: 提供复杂WHERE条件的删除操作
- **业务封装**: 高级API封装了常见的业务逻辑
- **配置文件支持**: 通过config.json配置文件输出路径
- **链式调用**: 支持流畅的API调用方式
- **类型安全**: 使用Python类型提示确保代码质量
- **易于扩展**: 模块化设计，便于添加新功能

## 主要类

### TransactionBuilder
统一的事务构建器，提供两个层次的API：
1. **底层API**：灵活的数据库操作方法（add_insert, add_update, add_delete）
2. **高级API**：面向业务的便捷方法（create_task, update_task_status, assign_staff）

### DataDictHelper
数据字典助手，帮助构建标准化的数据结构。

### FieldManager
字段管理器，提供常见的字段组合模板。

## 快速开始

### 底层API使用示例

```python
from transaction_generator import TransactionBuilder

# 创建构建器
builder = TransactionBuilder()

# 添加INSERT操作
builder.add_insert("tasks", {
    "task_id": "task-001",
    "task_type": "Others",
    "sender_name": "张三",
    "task_status": "pending"
})

# 添加UPDATE操作 - 简化版，只需要task_id和values字典
builder.add_update("tasks", "task-001", {"task_status": "finished"})

# 添加DELETE操作 - 简化版，只需要task_id
builder.add_delete("tasks_staff", "task-001")

# 生成事务
transaction = builder.build_transaction("req-001", "client-001")
```

### 高级API使用示例

```python
from transaction_generator import TransactionBuilder

# 创建构建器并设置client_id
builder = TransactionBuilder(client_id="client-001")

# 链式调用高级API
task_id = "my-task-001"
builder.create_task({
    "task_id": task_id,
    "task_type": "Testing",
    "sender_name": "李四"
}).update_task_status(
    task_id=task_id,
    status="assigned"
).assign_staff(
    task_id=task_id, 
    staff_email="worker@company.com"
)

# 生成JSON文件
builder.save_transaction_file("transaction.json")

# 使用配置路径保存文件
config_path = builder.save_to_config_path(request_id="example-001")
print(f"文件已保存到: {config_path}")
```

## 配置文件

在 `transaction_generator/config.json` 中可以配置文件输出路径：

```json
{
  "output_path": "../shared_folder/requests/",
  "file_prefix": "transaction_",
  "file_extension": ".json"
}
```

使用配置路径保存文件：

```python
from transaction_generator import TransactionBuilder

builder = TransactionBuilder(client_id="client-001")
builder.create_task({
    "task_type": "Testing",
    "sender_name": "测试用户"
})

# 使用配置文件中的路径保存，自动生成文件名
file_path = builder.save_to_config_path()
print(f"文件已保存到: {file_path}")

# 或者指定文件名
file_path = builder.save_to_config_path(filename="custom_transaction.json")
```

### 复杂删除示例

```python
from transaction_generator import TransactionBuilder

builder = TransactionBuilder()

# 简单删除 - 只需要task_id
builder.add_delete("tasks_staff", "task-001")

# 复杂删除 - 支持多个条件
builder.add_delete_with_conditions("tasks_staff", {
    "task_id": "task-001",
    "staff_email": "specific@company.com"
})

# 高级API的复杂删除
builder = TransactionBuilder(client_id="client-001")
builder.remove_staff("task-001")  # 删除所有员工
builder.remove_specific_staff("task-001", "worker@company.com")  # 删除特定员工
```

## 运行示例

```bash
python examples.py
```

查看更多使用示例和详细说明。 