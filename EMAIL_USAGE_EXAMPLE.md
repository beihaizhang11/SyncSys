# 邮件模块使用示例

## 📧 基本使用

### 1. 创建符合新格式的请求

```python
import json
import time

# 创建batch_import请求
request = {
    "request_id": f"USER123_batch_import_{int(time.time())}_abc123",
    "client_id": "CLIENT_HOSTNAME",
    "operation": "TRANSACTION",
    "table": "",
    "data": {
        "operations": [
            {
                "type": "UPDATE",
                "table": "tickets",
                "data": {
                    "values": {
                        "status": "In Progress",
                        "comments": "Updated via batch import"
                    },
                    "where": {
                        "problem_no": "10521211"
                    }
                }
            }
        ]
    },
    "timestamp": time.time(),
    "metadata": {
        "username": "USER123",
        "hostname": "CLIENT_HOSTNAME",
        "to_list": "manager@company.com;team-lead@company.com",  # 必填
        "cc_list": "supervisor@company.com;admin@company.com",   # 可选
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
}

# 保存为JSON文件
with open('request.json', 'w', encoding='utf-8') as f:
    json.dump(request, f, ensure_ascii=False, indent=2)
```

---

## 📨 邮件收件人配置

### 单个收件人
```json
"metadata": {
    "to_list": "user@company.com",
    "cc_list": ""
}
```

### 多个收件人
```json
"metadata": {
    "to_list": "user1@company.com;user2@company.com;user3@company.com",
    "cc_list": "manager@company.com;supervisor@company.com"
}
```

### 仅To，无CC
```json
"metadata": {
    "to_list": "user@company.com",
    "cc_list": ""
}
```

### 包含空格（自动去除）
```json
"metadata": {
    "to_list": " user1@company.com ; user2@company.com ; user3@company.com ",
    "cc_list": " manager@company.com "
}
```
**解析结果**: `['user1@company.com', 'user2@company.com', 'user3@company.com']`

---

## 🔧 在代码中使用

### 示例 1: 直接使用邮件发送器

```python
from email_notification import TicketEmailSender
from syncsys_core import DatabaseManager, ConfigManager

# 初始化
config = ConfigManager('config.json')
db_manager = DatabaseManager(config.get('database.path'))
email_sender = TicketEmailSender(db_manager, config)

# 准备请求数据
request_data = {
    "request_id": "USER_batch_import_12345_xyz",
    "client_id": "CLIENT01",
    "operation": "TRANSACTION",
    "data": {
        "operations": [
            {
                "type": "UPDATE",
                "table": "tickets",
                "data": {
                    "values": {"status": "Resolved"},
                    "where": {"problem_no": "10521211"}
                }
            }
        ]
    },
    "timestamp": 1754890751.0,
    "metadata": {
        "username": "John.Doe",
        "hostname": "WORKSTATION01",
        "to_list": "team@company.com",
        "cc_list": "manager@company.com",
        "generated_at": "2025-01-04T10:30:00"
    }
}

# 检查是否应该发送邮件
if email_sender.should_send_email(request_data):
    print("✓ 满足邮件发送条件")
    
    # 处理请求并发送邮件
    result = email_sender.process_batch_import_request(request_data)
    if result:
        print("✓ 邮件发送成功")
    else:
        print("✗ 邮件发送失败")
else:
    print("✗ 不满足邮件发送条件")
```

---

### 示例 2: 在SyncProcessor中自动处理

邮件发送已集成到 `SyncProcessor` 中，会自动处理：

```python
from syncsys_core import SyncProcessor

# 启动处理器
processor = SyncProcessor('config.json')
processor.start()

# 处理器会自动：
# 1. 监控请求文件
# 2. 执行数据库操作
# 3. 检查是否需要发送邮件
# 4. 发送邮件通知
# 5. 写入响应文件
```

---

## ⚙️ 配置文件设置

### config.json
```json
{
  "email": {
    "enabled": true,
    "sender": "system@company.com",
    "batch_import_notifications": true,
    "smtp_timeout": 30
  },
  "database": {
    "path": "C:/path/to/database.db"
  },
  "shared_folder": {
    "requests": "C:/path/to/requests",
    "responses": "C:/path/to/responses"
  }
}
```

### 配置说明
- `email.enabled`: 是否启用邮件功能（true/false）
- `email.sender`: 发件人邮箱地址
- `email.batch_import_notifications`: 是否发送批量导入通知
- `email.smtp_timeout`: SMTP超时时间（秒）

---

## 📋 完整工作流程示例

```python
import json
import time
from pathlib import Path

# 1. 准备票据更新请求
def create_batch_import_request(problem_no, updates, recipients, cc_recipients=None):
    """
    创建batch_import请求
    
    Args:
        problem_no: 问题编号
        updates: 更新的字段字典
        recipients: 收件人列表 ['email1', 'email2']
        cc_recipients: 抄送人列表（可选）
    """
    request = {
        "request_id": f"SYSTEM_batch_import_{int(time.time())}_{problem_no}",
        "client_id": "BATCH_PROCESSOR",
        "operation": "TRANSACTION",
        "table": "",
        "data": {
            "operations": [
                {
                    "type": "UPDATE",
                    "table": "tickets",
                    "data": {
                        "values": updates,
                        "where": {"problem_no": problem_no}
                    }
                }
            ]
        },
        "timestamp": time.time(),
        "metadata": {
            "username": "SYSTEM",
            "hostname": "BATCH_SERVER",
            "to_list": ";".join(recipients),
            "cc_list": ";".join(cc_recipients) if cc_recipients else "",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
    }
    return request

# 2. 使用示例
if __name__ == '__main__':
    # 创建请求
    request = create_batch_import_request(
        problem_no="10521211",
        updates={
            "status": "In Progress",
            "priority": "High",
            "comments": "Updated by automated system"
        },
        recipients=[
            "engineer1@company.com",
            "engineer2@company.com"
        ],
        cc_recipients=[
            "manager@company.com",
            "supervisor@company.com"
        ]
    )
    
    # 3. 保存到requests文件夹
    requests_folder = Path("C:/Develop/kpm-system/requests")
    request_file = requests_folder / f"{request['client_id']}_{request['request_id']}.json"
    
    with open(request_file, 'w', encoding='utf-8') as f:
        json.dump(request, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 请求已创建: {request_file}")
    print(f"  Problem No: {request['data']['operations'][0]['data']['where']['problem_no']}")
    print(f"  收件人: {request['metadata']['to_list']}")
    print(f"  抄送人: {request['metadata']['cc_list']}")
    print(f"\n等待处理器处理...")
```

---

## 🎯 最佳实践

### 1. 邮件地址验证
```python
def validate_email(email: str) -> bool:
    """简单的邮箱验证"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# 使用
emails = "user1@company.com;user2@company.com"
valid_emails = [e for e in emails.split(';') if validate_email(e.strip())]
```

### 2. 批量更新多个票据
```python
def create_multi_ticket_request(problem_numbers, updates, recipients):
    """为多个票据创建更新请求"""
    operations = []
    for problem_no in problem_numbers:
        operations.append({
            "type": "UPDATE",
            "table": "tickets",
            "data": {
                "values": updates,
                "where": {"problem_no": problem_no}
            }
        })
    
    request = {
        "request_id": f"BULK_batch_import_{int(time.time())}",
        "client_id": "BULK_PROCESSOR",
        "operation": "TRANSACTION",
        "table": "",
        "data": {"operations": operations},
        "timestamp": time.time(),
        "metadata": {
            "username": "BULK_SYSTEM",
            "hostname": "SERVER01",
            "to_list": ";".join(recipients),
            "cc_list": "",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
    }
    return request

# 使用
request = create_multi_ticket_request(
    problem_numbers=["10521211", "10521212", "10521213"],
    updates={"status": "Reviewed"},
    recipients=["team@company.com"]
)
```

### 3. 错误处理
```python
try:
    # 处理batch_import请求
    result = email_sender.process_batch_import_request(request_data)
    if not result:
        print("⚠️ 邮件发送失败，请检查日志")
except Exception as e:
    print(f"❌ 处理失败: {e}")
    # 记录错误日志
    logging.error(f"处理batch_import请求时出错: {e}")
```

---

## 🚨 常见问题

### Q1: 邮件没有发送？
**检查清单**:
- ✅ config.json中`email.enabled`为true
- ✅ request_id包含`batch_import`
- ✅ operation为`TRANSACTION`
- ✅ metadata中有非空的`to_list`
- ✅ 至少有一个对tickets表的UPDATE操作
- ✅ Outlook已安装并可用

### Q2: 如何只发送给一个人？
```json
"metadata": {
    "to_list": "single-recipient@company.com",
    "cc_list": ""
}
```

### Q3: 如何不发送CC？
```json
"metadata": {
    "to_list": "recipient@company.com",
    "cc_list": ""  // 留空或省略
}
```

### Q4: 支持的邮件地址格式？
- ✅ `user@company.com`
- ✅ `user.name@company.com`
- ✅ `user+tag@company.com`
- ✅ `user@sub.company.com`

---

## 📚 相关文档

- [邮件模块修改说明](EMAIL_MODULE_CHANGES.md)
- [代码修改对比](CODE_COMPARISON.md)
- [系统README](README.md)

---

**最后更新**: 2025-01-04
