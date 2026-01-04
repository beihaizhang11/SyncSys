#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送调试工具
用于诊断邮件发送问题
"""

import json
import logging
import sys

# 设置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

print("=" * 80)
print("邮件发送调试工具")
print("=" * 80)

# 1. 检查win32com
print("\n1. 检查win32com模块...")
try:
    import win32com.client as win32
    print("   ✓ win32com.client 可用")
    OUTLOOK_AVAILABLE = True
except ImportError as e:
    print(f"   ✗ win32com.client 不可用: {e}")
    OUTLOOK_AVAILABLE = False

# 2. 检查配置文件
print("\n2. 检查配置文件...")
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    print("   ✓ config.json 读取成功")
    
    email_config = config.get('email', {})
    print(f"   - email.enabled: {email_config.get('enabled', 'NOT SET')}")
    print(f"   - email.sender: {email_config.get('sender', 'NOT SET')}")
    
    db_path = config.get('database', {}).get('path', 'NOT SET')
    print(f"   - database.path: {db_path}")
except Exception as e:
    print(f"   ✗ 读取配置文件失败: {e}")
    email_config = {}
    db_path = None

# 3. 检查测试请求文件
print("\n3. 检查测试请求文件...")
try:
    with open('test_request.json', 'r', encoding='utf-8') as f:
        test_request = json.load(f)
    print("   ✓ test_request.json 读取成功")
    
    request_id = test_request.get('request_id', '')
    operation = test_request.get('operation', '')
    metadata = test_request.get('metadata', {})
    
    print(f"   - request_id: {request_id}")
    print(f"   - operation: {operation}")
    print(f"   - metadata keys: {list(metadata.keys())}")
    print(f"   - to_list: {metadata.get('to_list', 'NOT SET')}")
    print(f"   - cc_list: {metadata.get('cc_list', 'NOT SET')}")
    
    # 检查operations
    operations = test_request.get('data', {}).get('operations', [])
    print(f"   - operations count: {len(operations)}")
    for i, op in enumerate(operations):
        print(f"     操作{i+1}: type={op.get('type')}, table={op.get('table')}")
        
except Exception as e:
    print(f"   ✗ 读取测试请求文件失败: {e}")
    test_request = None

# 4. 初始化数据库管理器
print("\n4. 初始化数据库管理器...")
if db_path:
    try:
        from syncsys_core import DatabaseManager
        db_manager = DatabaseManager(db_path)
        print(f"   ✓ DatabaseManager 初始化成功")
    except Exception as e:
        print(f"   ✗ DatabaseManager 初始化失败: {e}")
        db_manager = None
else:
    print("   ✗ 数据库路径未配置")
    db_manager = None

# 5. 初始化邮件发送器
print("\n5. 初始化邮件发送器...")
if db_manager:
    try:
        from syncsys_core import ConfigManager
        from email_notification import TicketEmailSender
        
        config_manager = ConfigManager('config.json')
        email_sender = TicketEmailSender(db_manager, config_manager)
        
        print(f"   ✓ TicketEmailSender 初始化成功")
        print(f"   - enabled: {email_sender.enabled}")
        print(f"   - sender_email: {email_sender.sender_email}")
    except Exception as e:
        print(f"   ✗ TicketEmailSender 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        email_sender = None
else:
    print("   ✗ 数据库管理器未初始化，跳过")
    email_sender = None

# 6. 测试邮件发送条件
print("\n6. 测试邮件发送条件...")
if email_sender and test_request:
    try:
        should_send = email_sender.should_send_email(test_request)
        print(f"   - should_send_email() 返回: {should_send}")
    except Exception as e:
        print(f"   ✗ 检查发送条件失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print("   ✗ 邮件发送器或测试请求未准备好")

# 7. 尝试创建Outlook应用（如果win32com可用）
print("\n7. 测试Outlook连接...")
if OUTLOOK_AVAILABLE:
    try:
        import pythoncom
        pythoncom.CoInitialize()
        outlook = win32.Dispatch('outlook.application')
        print("   ✓ Outlook应用创建成功")
        print(f"   - Outlook版本: {outlook.Version if hasattr(outlook, 'Version') else 'Unknown'}")
        
        # 测试创建邮件对象
        mail = outlook.CreateItem(0)
        print("   ✓ 邮件对象创建成功")
        
        # 清理
        del mail
        del outlook
        pythoncom.CoUninitialize()
    except Exception as e:
        print(f"   ✗ Outlook连接失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print("   ✗ win32com不可用，跳过Outlook测试")

# 8. 提取problem_no并检查数据库
print("\n8. 测试数据库查询...")
if email_sender and test_request and db_manager:
    try:
        problem_numbers = email_sender.extract_problem_numbers(test_request)
        print(f"   - 提取的problem_no: {problem_numbers}")
        
        if problem_numbers:
            for problem_no in problem_numbers:
                ticket_data = email_sender.get_ticket_data(problem_no)
                if ticket_data:
                    print(f"   ✓ 找到票据数据: problem_no={problem_no}")
                    print(f"     - short_text: {ticket_data.get('short_text', 'N/A')}")
                    print(f"     - status: {ticket_data.get('status', 'N/A')}")
                else:
                    print(f"   ✗ 未找到票据数据: problem_no={problem_no}")
    except Exception as e:
        print(f"   ✗ 数据库查询失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print("   ✗ 邮件发送器或数据库管理器未准备好")

# 总结
print("\n" + "=" * 80)
print("诊断总结")
print("=" * 80)

checks = {
    "win32com可用": OUTLOOK_AVAILABLE,
    "配置文件读取": email_config is not None,
    "测试请求准备": test_request is not None,
    "数据库管理器": db_manager is not None,
    "邮件发送器": email_sender is not None,
    "邮件功能启用": email_sender.enabled if email_sender else False,
}

for check_name, check_result in checks.items():
    status = "✓" if check_result else "✗"
    print(f"{status} {check_name}")

print("\n如果所有检查都通过但仍然无法发送邮件，请：")
print("1. 检查日志文件 syncsys.log")
print("2. 确认request_id包含'batch_import'")
print("3. 确认metadata中有to_list")
print("4. 确认包含对tickets表的UPDATE操作")
print("5. 确认Outlook已安装并正确配置")

print("\n" + "=" * 80)
