#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试邮件模块的修改
"""

import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)

# 模拟数据库管理器
class MockDBManager:
    def __init__(self):
        self.db_path = "mock.db"

# 模拟配置管理器
class MockConfigManager:
    def __init__(self):
        self.config = {
            'email': {
                'enabled': True,
                'sender': 'test@audi.com.cn'
            }
        }
    
    def get(self, key, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

def test_email_module():
    """测试邮件模块"""
    print("=" * 60)
    print("邮件模块测试")
    print("=" * 60)
    
    # 读取测试请求
    with open('test_request.json', 'r', encoding='utf-8') as f:
        test_request = json.load(f)
    
    print("\n1. 测试请求数据:")
    print(f"   Request ID: {test_request.get('request_id')}")
    print(f"   Operation: {test_request.get('operation')}")
    
    metadata = test_request.get('metadata', {})
    print(f"\n2. Metadata信息:")
    print(f"   Username: {metadata.get('username')}")
    print(f"   Hostname: {metadata.get('hostname')}")
    print(f"   To List: {metadata.get('to_list')}")
    print(f"   CC List: {metadata.get('cc_list')}")
    
    # 测试邮件列表解析
    from email_notification import TicketEmailSender
    
    db_manager = MockDBManager()
    config_manager = MockConfigManager()
    
    # 注意：这里会因为没有win32com而导致邮件功能禁用，这是正常的
    sender = TicketEmailSender(db_manager, config_manager)
    
    print(f"\n3. 邮件发送器状态:")
    print(f"   Enabled: {sender.enabled}")
    print(f"   Sender Email: {sender.sender_email}")
    
    # 测试邮件列表解析
    to_list = metadata.get('to_list', '')
    cc_list = metadata.get('cc_list', '')
    
    to_emails = sender.parse_email_list(to_list)
    cc_emails = sender.parse_email_list(cc_list)
    
    print(f"\n4. 解析后的邮件列表:")
    print(f"   To Emails: {to_emails}")
    print(f"   CC Emails: {cc_emails}")
    
    # 测试是否应该发送邮件
    should_send = sender.should_send_email(test_request)
    print(f"\n5. 是否应该发送邮件: {should_send}")
    
    # 提取problem_no
    problem_numbers = sender.extract_problem_numbers(test_request)
    print(f"\n6. 提取的Problem Numbers: {problem_numbers}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    # 显示新旧版本对比
    print("\n【修改总结】:")
    print("✓ 移除了预定义的ASSIGNEE_EMAILS映射")
    print("✓ 添加了parse_email_list()方法来解析分号分隔的邮件列表")
    print("✓ 修改了should_send_email()检查metadata中的to_list")
    print("✓ 修改了send_notification_email()从metadata获取to_list和cc_list")
    print("✓ 支持多个收件人和抄送人")
    print("✓ 更新了邮件正文模板，不再依赖assignee字段")
    print("✓ 使用metadata中的username和generated_at作为更新者信息")

if __name__ == '__main__':
    test_email_module()
