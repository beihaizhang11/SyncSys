# SyncSys - 基于共享文件夹的SQLite数据库同步系统

## 系统概述

SyncSys 是一个专为企业网络环境设计的数据库同步系统，通过共享文件夹实现多台主机与中央数据库的同步。系统支持100台主机同时访问，具有高实时性、低耦合、高稳定性的特点。

### 核心特性

- **零服务器架构**: 基于共享文件夹，无需在主机上开放端口或搭建服务器
- **高并发支持**: 支持100台主机同时访问
- **实时同步**: 亚秒级响应时间
- **高可靠性**: 完善的错误处理和重试机制
- **低耦合设计**: 模块化架构，易于扩展和维护
- **零外部依赖**: 仅使用Python标准库（可加入watchdog来提升性能）
- **简单部署**: 配置文件驱动，一键启动

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   主机1 (客户端)  │    │   主机2 (客户端)  │    │   主机N (客户端)  │
│                 │    │                 │    │                 │
│ syncsys_client  │    │ syncsys_client  │    │ syncsys_client  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │              ┌───────┴──────────────────────┘
          │              │
          └──────────────┼─────────────────┐
                         │                 │
                    ┌────▼────┐       ┌────▼────┐
                    │ 请求文件夹 │       │ 响应文件夹 │
                    │requests │       │responses│
                    └────┬────┘       └────▲────┘
                         │                 │
                    ┌────▼─────────────────┴────┐
                    │      处理设备 (服务端)       │
                    │                           │
                    │    syncsys_processor      │
                    │           +               │
                    │      SQLite数据库         │
                    └───────────────────────────┘
```

## 快速开始

### 1. 环境要求

- Python 3.7+
- Windows/Linux/macOS
- 共享网络文件夹访问权限

### 2. 安装部署

```bash
# 克隆或下载项目文件到本地
# 无需安装额外依赖，系统仅使用Python标准库
```

### 3. 配置系统

编辑 `config.json` 文件，设置共享文件夹路径：

```json
{
  "shared_folder": {
    "requests": "//shared-server/syncsys/requests",
    "responses": "//shared-server/syncsys/responses"
  },
  "database": {
    "path": "//shared-server/syncsys/database/main.db"
  }
}
```

### 4. 初始化数据库

在处理设备上运行：

```bash
# 创建数据库表结构
python db_manager.py --create-schema
python start_processor.py --init-db --schema schema.json
```

### 5. 启动处理器

在处理设备上运行：

```bash
python start_processor.py
```

### 6. 客户端使用

在主机上使用客户端：

```python
from syncsys_client import SyncClient

# 创建客户端
client = SyncClient()

# 插入数据
result = client.insert('users', {
    'username': 'john_doe',
    'email': 'john@example.com',
    'created_at': time.time()
})

if result.success:
    print(f"插入成功: {result.data}")
else:
    print(f"插入失败: {result.error}")

# 查询数据
result = client.select('users', where={'username': 'john_doe'})
if result.success:
    print(f"查询结果: {result.data}")

client.close()
```

## 详细使用说明

### 客户端API

#### 基本操作

```python
from syncsys_client import SyncClient

client = SyncClient()

# 查询操作
result = client.select('table_name', where={'column': 'value'}, limit=10)

# 插入操作
result = client.insert('table_name', {'column1': 'value1', 'column2': 'value2'})

# 更新操作
result = client.update('table_name', 
                      values={'column1': 'new_value'}, 
                      where={'id': 1})

# 删除操作
result = client.delete('table_name', where={'id': 1})
```

#### 便捷方法

```python
# 查询单条记录
result = client.find_one('users', where={'username': 'john'})

# 查询所有记录
result = client.find_all('users')

# 计数
result = client.count('users', where={'is_active': 1})

# 检查存在性
result = client.exists('users', where={'email': 'john@example.com'})
```

#### 表封装器

```python
from syncsys_client import SyncTable

users_table = SyncTable(client, 'users')
result = users_table.insert({'username': 'alice', 'email': 'alice@example.com'})
```

#### 数据库封装器

```python
from syncsys_client import SyncDatabase

with SyncDatabase() as db:
    users = db.table('users')
    products = db.table('products')
    
    # 使用表对象进行操作
    result = users.insert({'username': 'bob'})
```

### 数据库管理

#### 创建表

```bash
# 从schema文件创建表
python db_manager.py --schema schema.json

# 列出所有表
python db_manager.py --list

# 获取表信息
python db_manager.py --info users
```

#### 备份和恢复

```bash
# 备份数据库
python db_manager.py --backup

# 恢复数据库
python db_manager.py --restore backup_20231201_120000.db
```

#### 数据库维护

```bash
# 获取数据库统计信息
python db_manager.py --stats

# 检查数据库完整性
python db_manager.py --check

# 压缩数据库
python db_manager.py --vacuum
```

## 配置说明

### config.json 配置项

```json
{
  "shared_folder": {
    "requests": "请求文件夹路径",
    "responses": "响应文件夹路径"
  },
  "database": {
    "path": "数据库文件路径",
    "backup_path": "备份文件夹路径"
  },
  "processor": {
    "poll_interval": 0.1,           // 文件监控间隔(秒)
    "max_concurrent_requests": 10,  // 最大并发请求数
    "request_timeout": 30,          // 请求超时时间(秒)
    "cleanup_interval": 300         // 清理间隔(秒)
  },
  "client": {
    "poll_interval": 0.2,           // 响应监控间隔(秒)
    "request_timeout": 30,          // 请求超时时间(秒)
    "retry_attempts": 3,            // 重试次数
    "retry_delay": 1                // 重试延迟(秒)
  },
  "logging": {
    "level": "INFO",                // 日志级别
    "file": "syncsys.log",          // 日志文件
    "max_size": "10MB",             // 日志文件最大大小
    "backup_count": 5               // 日志备份数量
  }
}
```

## 性能优化

### 1. 文件监控优化

- 调整 `poll_interval` 参数平衡实时性和性能
- 较小的值提供更好的实时性，但消耗更多CPU
- 推荐值：处理器 0.1秒，客户端 0.2秒

### 2. 并发控制

- 调整 `max_concurrent_requests` 控制并发处理数量
- 根据服务器性能和网络带宽调整
- 推荐值：10-50

### 3. 数据库优化

```bash
# 定期压缩数据库
python db_manager.py --vacuum

# 创建适当的索引
# 在schema.json中定义索引
```

### 4. 网络优化

- 使用高速网络连接
- 确保共享文件夹在高性能存储上
- 考虑使用SSD存储

## 故障排除

### 常见问题

1. **客户端连接超时**
   - 检查共享文件夹访问权限
   - 确认处理器正在运行
   - 检查网络连接

2. **数据库锁定错误**
   - 确保只有一个处理器实例运行
   - 检查数据库文件权限

3. **文件权限错误**
   - 确保所有用户对共享文件夹有读写权限
   - 检查文件夹路径是否正确

### 日志分析

```bash
# 查看处理器日志
tail -f syncsys.log

# 查看错误日志
grep ERROR syncsys.log
```

### 调试模式

```bash
# 启用调试日志
python start_processor.py --log-level DEBUG
```

## 安全考虑

1. **文件夹权限**: 确保只有授权用户可以访问共享文件夹
2. **数据加密**: 敏感数据在存储前进行加密
3. **访问控制**: 实现用户认证和授权机制
4. **审计日志**: 记录所有数据库操作

## 扩展开发

### 添加新的数据库操作

1. 在 `syncsys_core.py` 的 `DatabaseManager` 类中添加新方法
2. 在 `syncsys_client.py` 的 `SyncClient` 类中添加对应的客户端方法
3. 更新文档和示例

### 自定义数据处理

```python
class CustomProcessor(SyncProcessor):
    def _handle_request(self, file_path):
        # 自定义请求处理逻辑
        super()._handle_request(file_path)
        # 添加额外处理
```

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 支持

如有问题或建议，请提交 Issue 或联系开发团队。

---

**注意**: 本系统专为企业内网环境设计，不建议在公网环境中使用。