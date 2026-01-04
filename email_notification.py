#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SyncSys 邮件通知模块
用于在batch_import请求时发送邮件通知
"""

import logging
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import win32com.client as win32
    OUTLOOK_AVAILABLE = True
except ImportError:
    OUTLOOK_AVAILABLE = False
    logging.warning("win32com.client 不可用，邮件功能将被禁用")

class TicketEmailSender:
    """票据邮件发送器"""
    
    def __init__(self, db_manager, config_manager=None):
        """
        初始化邮件发送器
        
        Args:
            db_manager: 数据库管理器实例
            config_manager: 配置管理器实例（可选）
        """
        self.db_manager = db_manager
        self.config = config_manager
        
        # 邮件配置
        self.sender_email = self._get_sender_email()
        self.enabled = OUTLOOK_AVAILABLE and self._is_email_enabled()
        
        if self.enabled:
            logging.info(f"[邮件模块] 已启用 (发件人: {self.sender_email})")
        else:
            logging.warning("[邮件模块] 已禁用 (Outlook不可用或配置禁用)")
    
    def _is_email_enabled(self) -> bool:
        """检查邮件功能是否启用"""
        if self.config:
            return self.config.get('email.enabled', True)
        return True
    
    def _get_sender_email(self) -> str:
        """获取发件人邮箱"""
        if self.config:
            return self.config.get('email.sender', 'bohan.zhang1@audi.com.cn')
        return 'bohan.zhang1@audi.com.cn'
    
    def should_send_email(self, request_data: Dict[str, Any]) -> bool:
        """
        判断是否应该发送邮件
        
        Args:
            request_data: 请求数据
            
        Returns:
            bool: 是否应该发送邮件
        """
        request_id = request_data.get('request_id', '')
        
        # 检查邮件功能是否启用
        if not self.enabled:
            return False
        
        # 检查是否是batch_import请求
        if 'batch_import' not in request_id:
            return False
        
        # 检查是否是TRANSACTION操作
        if request_data.get('operation') != 'TRANSACTION':
            return False
        
        # 检查metadata中是否有to_list
        metadata = request_data.get('metadata', {})
        to_list = metadata.get('to_list', '')
        
        if not metadata or not to_list or not to_list.strip():
            logging.warning(f"[邮件] 跳过发送: metadata中缺少to_list (request_id={request_id})")
            return False
        
        # 统计操作信息
        operations = request_data.get('data', {}).get('operations', [])
        logging.info(f"[邮件] 满足发送条件: {len(operations)}个操作, to={to_list}")
        
        return True
    
    def get_operations_summary(self, request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取操作摘要信息
        
        Args:
            request_data: 请求数据
            
        Returns:
            List[Dict]: 操作摘要列表
        """
        operations = request_data.get('data', {}).get('operations', [])
        summary = []
        
        for i, operation in enumerate(operations):
            op_type = operation.get('type', 'UNKNOWN')
            op_table = operation.get('table', 'UNKNOWN')
            op_data = operation.get('data', {})
            
            summary_item = {
                'index': i + 1,
                'type': op_type,
                'table': op_table,
                'values': op_data.get('values', {}),
                'where': op_data.get('where', {})
            }
            summary.append(summary_item)
        
        return summary
    
    def format_operation_detail(self, operation: Dict[str, Any]) -> str:
        """
        格式化单个操作的详细信息（HTML）
        
        Args:
            operation: 操作信息
            
        Returns:
            str: HTML格式的操作详情
        """
        op_type = operation.get('type', 'UNKNOWN')
        op_table = operation.get('table', 'UNKNOWN')
        op_values = operation.get('values', {})
        op_where = operation.get('where', {})
        
        html = f"""
        <div style="background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 10px 0;">
            <h4 style="color: #007bff; margin-top: 0;">
                操作 #{operation.get('index', '?')}: {op_type} - {op_table}
            </h4>
        """
        
        # 显示更新的值
        if op_values:
            html += """
            <div style="margin: 10px 0;">
                <strong style="color: #495057;">更新的值:</strong>
                <table style="width: 100%; border-collapse: collapse; margin-top: 5px;">
            """
            for key, value in op_values.items():
                # 截断过长的值
                str_value = str(value)
                if len(str_value) > 100:
                    str_value = str_value[:100] + '...'
                html += f"""
                    <tr>
                        <td style="padding: 5px; font-weight: bold; width: 200px; color: #6c757d;">{key}:</td>
                        <td style="padding: 5px; color: #212529;">{str_value}</td>
                    </tr>
                """
            html += "</table></div>"
        
        # 显示条件
        if op_where:
            html += """
            <div style="margin: 10px 0;">
                <strong style="color: #495057;">条件:</strong>
                <table style="width: 100%; border-collapse: collapse; margin-top: 5px;">
            """
            for key, value in op_where.items():
                html += f"""
                    <tr>
                        <td style="padding: 5px; font-weight: bold; width: 200px; color: #6c757d;">{key}:</td>
                        <td style="padding: 5px; color: #212529;">{value}</td>
                    </tr>
                """
            html += "</table></div>"
        
        html += "</div>"
        return html
    
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
    
    def create_outlook_application(self):
        """创建Outlook应用程序实例"""
        try:
            # 在多线程环境中需要初始化COM
            import pythoncom
            pythoncom.CoInitialize()
            
            return win32.Dispatch('outlook.application')
        except Exception as e:
            logging.error(f'无法连接到Outlook: {e}')
            raise
    
    def generate_email_subject(self, request_data: Dict[str, Any]) -> str:
        """
        生成邮件主题
        
        Args:
            request_data: 请求数据
            
        Returns:
            str: 邮件主题
        """
        metadata = request_data.get('metadata', {})
        username = metadata.get('username', 'System')
        
        operations = request_data.get('data', {}).get('operations', [])
        operations_count = len(operations)
        
        # 获取主要操作类型
        operation_types = list(set([op.get('type', 'UNKNOWN') for op in operations]))
        operation_types_str = ', '.join(operation_types)
        
        return f"Batch Import Notification: {operations_count} Operations by {username}"
    
    def generate_email_body(self, request_data: Dict[str, Any]) -> str:
        """
        生成邮件正文（HTML格式）
        
        Args:
            request_data: 请求数据
            
        Returns:
            str: HTML格式的邮件正文
        """
        # 获取元数据
        metadata = request_data.get('metadata', {})
        username = metadata.get('username', 'System')
        hostname = metadata.get('hostname', 'Unknown')
        generated_at = metadata.get('generated_at', 'N/A')
        
        # 获取请求信息
        request_id = request_data.get('request_id', 'Unknown')
        
        # 获取操作摘要
        operations_summary = self.get_operations_summary(request_data)
        operations_count = len(operations_summary)
        
        # 统计操作类型
        operation_types = {}
        for op in operations_summary:
            op_type = op['type']
            operation_types[op_type] = operation_types.get(op_type, 0) + 1
        
        operations_stats = ', '.join([f"{count} {op_type}" for op_type, count in operation_types.items()])
        
        # 生成HTML邮件正文
        html_body = f"""
        <html>
        <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; font-size: 14px; line-height: 1.6;">
            <div style="max-width: 900px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #007bff; margin-bottom: 20px;">🔔 Batch Import Notification</h2>
                
                <p>Dear Team,</p>
                
                <p>A batch import operation has been executed in the system. Please review the details below:</p>
                
                <div style="background-color: #e3f2fd; border-left: 4px solid #007bff; padding: 15px; margin: 20px 0;">
                    <h3 style="color: #0d47a1; margin-top: 0;">📊 Request Summary</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; font-weight: bold; width: 180px; color: #1565c0;">Request ID:</td>
                            <td style="padding: 8px; color: #212529;">{request_id}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #1565c0;">Submitted by:</td>
                            <td style="padding: 8px; color: #212529;">{username}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #1565c0;">Hostname:</td>
                            <td style="padding: 8px; color: #212529;">{hostname}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #1565c0;">Submitted at:</td>
                            <td style="padding: 8px; color: #212529;">{generated_at}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #1565c0;">Total Operations:</td>
                            <td style="padding: 8px; color: #212529;"><strong>{operations_count}</strong> ({operations_stats})</td>
                        </tr>
                    </table>
                </div>
                
                <div style="margin: 30px 0;">
                    <h3 style="color: #495057; border-bottom: 2px solid #007bff; padding-bottom: 10px;">📝 Operations Details</h3>
        """
        
        # 添加每个操作的详细信息
        for operation in operations_summary:
            html_body += self.format_operation_detail(operation)
        
        # 结尾
        html_body += """
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #dee2e6;">
                    <p style="color: #495057;">
                        <strong>📌 Action Required:</strong><br>
                        Please review the operations listed above and verify that all changes are correct. 
                        If you notice any discrepancies, please contact the system administrator immediately.
                    </p>
                    
                    <p style="margin-top: 20px; color: #6c757d;">
                        Best regards,<br>
                        <strong>SyncSys Notification System</strong>
                    </p>
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-left: 3px solid #6c757d; font-size: 12px; color: #6c757d;">
                    <p style="margin: 0;">
                        <strong>ℹ️ Note:</strong> This is an automated notification from the SyncSys system. 
                        Please do not reply to this email. For support, contact your system administrator.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def send_notification_email(self, request_data: Dict[str, Any]) -> bool:
        """
        发送通知邮件
        
        Args:
            request_data: 请求数据
            
        Returns:
            bool: 发送是否成功
        """
        request_id = request_data.get('request_id', 'unknown')
        
        if not self.enabled:
            return False
        
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
                logging.warning(f"[邮件] 跳过发送: 没有有效收件人")
                return False
            
            # 创建Outlook应用并发送
            outlook = self.create_outlook_application()
            mail = outlook.CreateItem(0)
            
            mail.SentOnBehalfOfName = self.sender_email
            mail.To = ';'.join(to_emails)
            if cc_emails:
                mail.CC = ';'.join(cc_emails)
            
            mail.Subject = self.generate_email_subject(request_data)
            mail.HTMLBody = self.generate_email_body(request_data)
            mail.BodyFormat = 2
            
            mail.Send()
            
            # 简化的成功日志
            cc_info = f", cc={len(cc_emails)}人" if cc_emails else ""
            logging.info(f"[邮件] 发送成功: to={len(to_emails)}人{cc_info}")
            
            return True
            
        except Exception as e:
            logging.error(f"[邮件] 发送失败: {e}")
            return False
        finally:
            # 清理COM资源
            try:
                if outlook:
                    del outlook
                import pythoncom
                pythoncom.CoUninitialize()
            except:
                pass
    
    def process_batch_import_request(self, request_data: Dict[str, Any]) -> bool:
        """
        处理batch_import请求，发送相关邮件
        
        Args:
            request_data: 请求数据
            
        Returns:
            bool: 处理是否成功
        """
        if not self.should_send_email(request_data):
            return True
        
        try:
            return self.send_notification_email(request_data)
        except Exception as e:
            logging.error(f"[邮件] 处理失败: {e}")
            return False

# 创建全局邮件发送器实例（延迟初始化）
_email_sender = None

def get_email_sender(db_manager, config_manager=None):
    """获取邮件发送器实例（单例模式）"""
    global _email_sender
    if _email_sender is None:
        _email_sender = TicketEmailSender(db_manager, config_manager)
    return _email_sender

def reset_email_sender():
    """重置邮件发送器实例"""
    global _email_sender
    _email_sender = None
