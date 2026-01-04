# 代码修改对比

## 📊 关键方法修改对比

### 1. 类初始化部分

#### ❌ 修改前
```python
class TicketEmailSender:
    """票据邮件发送器"""
    
    # 预定义的assignee邮箱映射
    ASSIGNEE_EMAILS = {
        "Adlkofer, Thomas": "thomas.adlkofer@audi.com.cn",
        "Yang Xie": "yang.xie@audi.com.cn", 
        "Xu, Fangchao": "fangchao.xu@audi.com.cn",
        "Wang, Zhuwei": "zhuwei.wang@audi.com.cn",
        "Yanan Wang": "yanan.wang@audi.com.cn",
        "Yudong Zhao": "yudong.zhao@audi.com.cn",
        "Han, Yinuo": "extern.yinuo.han@audi.com.cn"
    }
    
    def __init__(self, db_manager, config_manager=None):
        self.db_manager = db_manager
        self.config = config_manager
        self.sender_email = "bohan.zhang1@audi.com.cn"  # 硬编码
        self.enabled = OUTLOOK_AVAILABLE and self._is_email_enabled()
```

#### ✅ 修改后
```python
class TicketEmailSender:
    """票据邮件发送器"""
    
    def __init__(self, db_manager, config_manager=None):
        self.db_manager = db_manager
        self.config = config_manager
        self.sender_email = self._get_sender_email()  # 从配置读取
        self.enabled = OUTLOOK_AVAILABLE and self._is_email_enabled()
    
    def _get_sender_email(self) -> str:
        """获取发件人邮箱"""
        if self.config:
            return self.config.get('email.sender', 'bohan.zhang1@audi.com.cn')
        return 'bohan.zhang1@audi.com.cn'
```

---

### 2. should_send_email() 方法

#### ❌ 修改前
```python
def should_send_email(self, request_data: Dict[str, Any]) -> bool:
    if not self.enabled:
        return False
    
    request_id = request_data.get('request_id', '')
    if 'batch_import' not in request_id:
        return False
    
    if request_data.get('operation') != 'TRANSACTION':
        return False
    
    # 检查是否包含UPDATE操作到tickets表
    operations = request_data.get('data', {}).get('operations', [])
    for operation in operations:
        if (operation.get('type') == 'UPDATE' and 
            operation.get('table') == 'tickets'):
            return True
    
    return False
```

#### ✅ 修改后
```python
def should_send_email(self, request_data: Dict[str, Any]) -> bool:
    if not self.enabled:
        return False
    
    request_id = request_data.get('request_id', '')
    if 'batch_import' not in request_id:
        return False
    
    if request_data.get('operation') != 'TRANSACTION':
        return False
    
    # 新增：检查metadata中是否有to_list
    metadata = request_data.get('metadata', {})
    to_list = metadata.get('to_list', '')
    if not to_list or not to_list.strip():
        logging.debug("metadata中没有to_list，跳过邮件发送")
        return False
    
    # 检查是否包含UPDATE操作到tickets表
    operations = request_data.get('data', {}).get('operations', [])
    for operation in operations:
        if (operation.get('type') == 'UPDATE' and 
            operation.get('table') == 'tickets'):
            return True
    
    return False
```

**修改说明**: 新增了对 `metadata.to_list` 的检查，确保有收件人才发送邮件。

---

### 3. 邮箱处理方法

#### ❌ 修改前
```python
def get_assignee_email(self, assignee: str) -> Optional[str]:
    """
    获取assignee的邮箱地址
    """
    if not assignee:
        return None
    
    # 直接匹配
    if assignee in self.ASSIGNEE_EMAILS:
        return self.ASSIGNEE_EMAILS[assignee]
    
    # 模糊匹配（根据姓名关键词）
    assignee_lower = assignee.lower()
    for name, email in self.ASSIGNEE_EMAILS.items():
        if any(part.lower() in assignee_lower for part in name.split() if len(part) > 2):
            logging.info(f"模糊匹配assignee: {assignee} -> {name} ({email})")
            return email
    
    logging.warning(f"未找到assignee {assignee} 的邮箱地址")
    return None
```

#### ✅ 修改后
```python
def parse_email_list(self, email_string: str) -> List[str]:
    """
    解析邮件列表字符串（分号分隔）
    
    Args:
        email_string: 邮件列表字符串，如 "1@1.com;2@2.com"
        
    Returns:
        List[str]: 邮箱地址列表
    """
    if not email_string:
        return []
    
    # 分号分隔，去除空格和空字符串
    emails = [email.strip() for email in email_string.split(';')]
    emails = [email for email in emails if email]
    
    return emails
```

**修改说明**: 完全重写，从查找预定义邮箱改为解析邮件列表字符串。

---

### 4. send_notification_email() 方法

#### ❌ 修改前
```python
def send_notification_email(self, ticket_data: Dict[str, Any], 
                          request_data: Dict[str, Any]) -> bool:
    outlook = None
    try:
        # 获取assignee邮箱
        assignee = ticket_data.get('assignee')
        assignee_email = self.get_assignee_email(assignee)
        
        if not assignee_email:
            logging.warning(f"无法获取assignee {assignee} 的邮箱地址，跳过发送")
            return False
        
        # 创建Outlook应用
        outlook = self.create_outlook_application()
        mail = outlook.CreateItem(0)
        
        # 设置发件人
        mail.SentOnBehalfOfName = self.sender_email
        
        # 设置收件人
        mail.To = assignee_email  # 单个收件人
        
        # 设置主题和正文
        mail.Subject = self.generate_email_subject(ticket_data, request_data)
        mail.HTMLBody = self.generate_email_body(ticket_data, request_data)
        mail.BodyFormat = 2
        
        mail.Send()
        
        logging.info(f"邮件发送成功：problem_no={ticket_data.get('problem_no')}, "
                    f"assignee={assignee}, email={assignee_email}")
        
        return True
    except Exception as e:
        logging.error(f"发送邮件失败: {e}")
        return False
```

#### ✅ 修改后
```python
def send_notification_email(self, ticket_data: Dict[str, Any], 
                          request_data: Dict[str, Any]) -> bool:
    outlook = None
    try:
        # 获取metadata中的邮件列表
        metadata = request_data.get('metadata', {})
        to_list_str = metadata.get('to_list', '')
        cc_list_str = metadata.get('cc_list', '')
        
        # 解析邮件列表
        to_emails = self.parse_email_list(to_list_str)
        cc_emails = self.parse_email_list(cc_list_str)
        
        if not to_emails:
            logging.warning("metadata中没有有效的to_list，跳过发送")
            return False
        
        # 创建Outlook应用
        outlook = self.create_outlook_application()
        mail = outlook.CreateItem(0)
        
        # 设置发件人
        mail.SentOnBehalfOfName = self.sender_email
        
        # 设置收件人（分号分隔）- 支持多人
        mail.To = ';'.join(to_emails)
        
        # 设置抄送人（如果有）- 支持多人
        if cc_emails:
            mail.CC = ';'.join(cc_emails)
        
        # 设置主题和正文
        mail.Subject = self.generate_email_subject(ticket_data, request_data)
        mail.HTMLBody = self.generate_email_body(ticket_data, request_data)
        mail.BodyFormat = 2
        
        mail.Send()
        
        logging.info(f"邮件发送成功：problem_no={ticket_data.get('problem_no')}, "
                    f"to={to_emails}, cc={cc_emails}")
        
        return True
    except Exception as e:
        logging.error(f"发送邮件失败: {e}")
        return False
```

**修改说明**: 
- 从 metadata 读取收件人和抄送人
- 支持多个收件人和抄送人
- 移除了 assignee 相关逻辑

---

### 5. process_batch_import_request() 方法

#### ❌ 修改前
```python
def process_batch_import_request(self, request_data: Dict[str, Any]) -> bool:
    # ...省略前面部分...
    
    for problem_no in problem_numbers:
        ticket_data = self.get_ticket_data(problem_no)
        if not ticket_data:
            logging.warning(f"未找到problem_no {problem_no} 的票据数据")
            continue
        
        # 检查是否有assignee
        assignee = ticket_data.get('assignee')
        if not assignee:
            logging.info(f"problem_no {problem_no} 没有assignee，跳过邮件发送")
            continue  # 没有assignee就不发送
        
        # 发送邮件
        if self.send_notification_email(ticket_data, request_data):
            success_count += 1
```

#### ✅ 修改后
```python
def process_batch_import_request(self, request_data: Dict[str, Any]) -> bool:
    # ...省略前面部分...
    
    for problem_no in problem_numbers:
        ticket_data = self.get_ticket_data(problem_no)
        if not ticket_data:
            logging.warning(f"未找到problem_no {problem_no} 的票据数据")
            continue
        
        # 发送邮件（移除了assignee检查）
        if self.send_notification_email(ticket_data, request_data):
            success_count += 1
```

**修改说明**: 移除了对 assignee 字段的检查，只要票据存在就发送邮件。

---

### 6. 邮件正文模板

#### ❌ 修改前
```python
html_body = f"""
<p>Dear {ticket_data.get('assignee', 'Team Member')},</p>
<p>A ticket assigned to you has been updated in the system.</p>

<!-- 元数据部分 -->
<p><strong>Updated by:</strong> {metadata.get('kmp_username', 'System')}</p>
<p><strong>Update time:</strong> {import_info.get('timestamp', 'N/A')}</p>
<p><strong>Source:</strong> {import_info.get('source', 'N/A')}</p>
<p><strong>Action:</strong> {import_info.get('user_action', 'N/A')}</p>
"""
```

#### ✅ 修改后
```python
username = metadata.get('username', 'System')

html_body = f"""
<p>Dear Team,</p>
<p>A ticket has been updated in the system.</p>

<!-- 元数据部分 -->
<p><strong>Updated by:</strong> {username}</p>
<p><strong>Update time:</strong> {metadata.get('generated_at', 'N/A')}</p>
<p><strong>Hostname:</strong> {metadata.get('hostname', 'N/A')}</p>
"""
```

**修改说明**: 
- 问候语改为通用的 "Dear Team"
- 使用新的 metadata 字段（username, generated_at, hostname）

---

## 📈 修改统计

| 类型 | 数量 |
|------|------|
| 删除的方法 | 1 (`get_assignee_email`) |
| 新增的方法 | 2 (`_get_sender_email`, `parse_email_list`) |
| 修改的方法 | 4 (`should_send_email`, `send_notification_email`, `process_batch_import_request`, `generate_email_body`) |
| 删除的类变量 | 1 (`ASSIGNEE_EMAILS`) |
| 删除的代码行 | ~50 行 |
| 新增的代码行 | ~30 行 |

---

## 🎯 核心改进

1. **灵活性提升**: 收件人不再受预定义列表限制
2. **支持多人**: 同时支持多个收件人和抄送人
3. **配置驱动**: 发件人邮箱从配置文件读取
4. **更通用**: 不依赖业务特定字段（assignee）
5. **易维护**: 无需在代码中维护邮箱映射

---

**生成时间**: 2025-01-04
