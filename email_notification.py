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
        """
        初始化邮件发送器
        
        Args:
            db_manager: 数据库管理器实例
            config_manager: 配置管理器实例（可选）
        """
        self.db_manager = db_manager
        self.config = config_manager
        
        # 邮件配置
        self.sender_email = "bohan.zhang1@audi.com.cn"
        self.enabled = OUTLOOK_AVAILABLE and self._is_email_enabled()
        
        if not self.enabled:
            logging.warning("邮件功能已禁用：Outlook不可用或配置禁用")
    
    def _is_email_enabled(self) -> bool:
        """检查邮件功能是否启用"""
        if self.config:
            return self.config.get('email.enabled', True)
        return True
    
    def should_send_email(self, request_data: Dict[str, Any]) -> bool:
        """
        判断是否应该发送邮件
        
        Args:
            request_data: 请求数据
            
        Returns:
            bool: 是否应该发送邮件
        """
        if not self.enabled:
            return False
        
        # 检查是否是batch_import请求
        request_id = request_data.get('request_id', '')
        if 'batch_import' not in request_id:
            return False
        
        # 检查是否是TRANSACTION操作
        if request_data.get('operation') != 'TRANSACTION':
            return False
        
        # 检查是否包含UPDATE操作到tickets表
        operations = request_data.get('data', {}).get('operations', [])
        for operation in operations:
            if (operation.get('type') == 'UPDATE' and 
                operation.get('table') == 'tickets'):
                return True
        
        return False
    
    def extract_problem_numbers(self, request_data: Dict[str, Any]) -> List[str]:
        """
        从请求数据中提取problem_no
        
        Args:
            request_data: 请求数据
            
        Returns:
            List[str]: problem_no列表
        """
        problem_numbers = []
        operations = request_data.get('data', {}).get('operations', [])
        
        for operation in operations:
            if (operation.get('type') == 'UPDATE' and 
                operation.get('table') == 'tickets'):
                where_clause = operation.get('data', {}).get('where', {})
                problem_no = where_clause.get('problem_no')
                if problem_no:
                    problem_numbers.append(str(problem_no))
        
        return problem_numbers
    
    def get_ticket_data(self, problem_no: str) -> Optional[Dict[str, Any]]:
        """
        从数据库获取票据数据
        
        Args:
            problem_no: 问题编号
            
        Returns:
            Optional[Dict]: 票据数据，如果不存在则返回None
        """
        try:
            import sqlite3
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT * FROM tickets WHERE problem_no = ?",
                    (problem_no,)
                )
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                else:
                    logging.warning(f"未找到problem_no为{problem_no}的票据")
                    return None
                    
        except Exception as e:
            logging.error(f"查询票据数据时出错: {e}")
            return None
    
    def get_assignee_email(self, assignee: str) -> Optional[str]:
        """
        获取assignee的邮箱地址
        
        Args:
            assignee: 指派人姓名
            
        Returns:
            Optional[str]: 邮箱地址，如果未找到则返回None
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
    
    def generate_email_subject(self, ticket_data: Dict[str, Any], 
                             request_data: Dict[str, Any]) -> str:
        """
        生成邮件主题
        
        Args:
            ticket_data: 票据数据
            request_data: 请求数据
            
        Returns:
            str: 邮件主题
        """
        problem_no = ticket_data.get('problem_no', 'Unknown')
        ticket_title = ticket_data.get('title', '')
        
        if ticket_title:
            return f"Ticket Update Notification: {problem_no} - {ticket_title}"
        else:
            return f"Ticket Update Notification: {problem_no}"
    
    def generate_email_body(self, ticket_data: Dict[str, Any], 
                          request_data: Dict[str, Any]) -> str:
        """
        生成邮件正文（HTML格式）
        
        Args:
            ticket_data: 票据数据
            request_data: 请求数据
            
        Returns:
            str: HTML格式的邮件正文
        """
        # 获取更新信息
        metadata = request_data.get('metadata', {})
        import_info = metadata.get('import_info', {})
        updated_fields = import_info.get('updated_fields', [])
        
        # 获取操作中的更新值
        operations = request_data.get('data', {}).get('operations', [])
        updated_values = {}
        for operation in operations:
            if (operation.get('type') == 'UPDATE' and 
                operation.get('table') == 'tickets'):
                updated_values.update(operation.get('data', {}).get('values', {}))
        
        # 生成HTML邮件正文
        html_body = f"""
        <html>
        <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; font-size: 14px; line-height: 1.6;">
            <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #007bff; margin-bottom: 20px;">KPM System Ticket Update Notification</h2>
                
                <p>Dear {ticket_data.get('assignee', 'Team Member')},</p>
                
                <p>A ticket assigned to you has been updated in the system. Please review the details below:</p>
                
                <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 20px; margin: 20px 0;">
                    <h3 style="color: #495057; margin-top: 0;">Ticket Information</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; font-weight: bold; width: 150px;">Problem No:</td>
                            <td style="padding: 8px;">{ticket_data.get('problem_no', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Source:</td>
                            <td style="padding: 8px;">{ticket_data.get('source', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Project:</td>
                            <td style="padding: 8px;">{ticket_data.get('konzernprojekt', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">short_text:</td>
                            <td style="padding: 8px;">{ticket_data.get('short_text', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">P-Status:</td>
                            <td style="padding: 8px;">{ticket_data.get('p_status', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">FB-Status:</td>
                            <td style="padding: 8px;">{ticket_data.get('fb_status', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Shipper:</td>
                            <td style="padding: 8px;">{ticket_data.get('shipper', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Recipient:</td>
                            <td style="padding: 8px;">{ticket_data.get('recipient', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Processing Type:</td>
                            <td style="padding: 8px;">{ticket_data.get('bearbeitungs_auftragsart', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Software:</td>
                            <td style="padding: 8px;">{ticket_data.get('sw', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Hardware:</td>
                            <td style="padding: 8px;">{ticket_data.get('hw', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">E-Project:</td>
                            <td style="padding: 8px;">{ticket_data.get('e_projekt', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Assignee:</td>
                            <td style="padding: 8px;">{ticket_data.get('assignee', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Priority:</td>
                            <td style="padding: 8px;">{ticket_data.get('priority', 'N/A')}</td>
                        </tr>
                        <tr style="background-color: #ffffff;">
                            <td style="padding: 8px; font-weight: bold;">Status:</td>
                            <td style="padding: 8px;">{ticket_data.get('status', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Rating:</td>
                            <td style="padding: 8px;">{ticket_data.get('rating', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Created Date:</td>
                            <td style="padding: 8px;">{ticket_data.get('created_at', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Update Date:</td>
                            <td style="padding: 8px;">{ticket_data.get('updated_at', 'N/A')}</td>
                        </tr>
        """
        
        # 添加评论字段（如果存在）
        if ticket_data.get('comments'):
            html_body += f"""
                        <tr style="background-color: #ffffff;">
                            <td style="padding: 8px; font-weight: bold;">Comments:</td>
                            <td style="padding: 8px;">{ticket_data.get('comments', 'N/A')}</td>
                        </tr>
            """
        
        html_body += """
                    </table>
                </div>
        """
        
        # 添加更新信息
        if updated_fields or updated_values:
            html_body += """
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 20px; margin: 20px 0;">
                    <h3 style="color: #856404; margin-top: 0;">Update Details</h3>
            """
            
            if updated_fields:
                html_body += f"""
                    <p><strong>Updated Fields:</strong> {', '.join(updated_fields)}</p>
                """
            
            if updated_values:
                html_body += """
                    <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                """
                for field, value in updated_values.items():
                    html_body += f"""
                        <tr>
                            <td style="padding: 5px; font-weight: bold; width: 150px;">{field.title()}:</td>
                            <td style="padding: 5px;">{value}</td>
                        </tr>
                    """
                html_body += "</table>"
            
            html_body += "</div>"
        
        # 添加更新元数据
        if metadata:
            html_body += f"""
                <div style="background-color: #e9ecef; border: 1px solid #ced4da; border-radius: 5px; padding: 15px; margin: 20px 0;">
                    <h4 style="color: #495057; margin-top: 0;">Update Metadata</h4>
                    <p><strong>Updated by:</strong> {metadata.get('kmp_username', 'System')}</p>
                    <p><strong>Update time:</strong> {import_info.get('timestamp', 'N/A')}</p>
                    <p><strong>Source:</strong> {import_info.get('source', 'N/A')}</p>
                    <p><strong>Action:</strong> {import_info.get('user_action', 'N/A')}</p>
                </div>
            """
        
        # 结尾
        html_body += """
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
                    <p>Please review the updated ticket and take any necessary actions.</p>
                    <p>If you have any questions, please contact the system administrator.</p>
                    
                    <p style="margin-top: 20px;">
                        Best regards,<br>
                        <strong>SyncSys Notification System (AUDI Central Workshop)</strong>
                    </p>
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-left: 3px solid #007bff; font-size: 12px; color: #6c757d;">
                    <p style="margin: 0;"><strong>Note:</strong> This is an automated notification from the SyncSys system. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def send_notification_email(self, ticket_data: Dict[str, Any], 
                              request_data: Dict[str, Any]) -> bool:
        """
        发送通知邮件
        
        Args:
            ticket_data: 票据数据
            request_data: 请求数据
            
        Returns:
            bool: 发送是否成功
        """
        if not self.enabled:
            logging.warning("邮件功能未启用，跳过发送")
            return False
        
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
            mail = outlook.CreateItem(0)  # 0 = olMailItem
            
            # 设置发件人
            mail.SentOnBehalfOfName = self.sender_email
            
            # 设置收件人
            mail.To = assignee_email
            
            # 设置主题
            mail.Subject = self.generate_email_subject(ticket_data, request_data)
            
            # 设置邮件正文
            mail.HTMLBody = self.generate_email_body(ticket_data, request_data)
            mail.BodyFormat = 2  # 2 = olFormatHTML
            
            # 发送邮件
            mail.Send()
            
            logging.info(f"邮件发送成功：problem_no={ticket_data.get('problem_no')}, "
                        f"assignee={assignee}, email={assignee_email}")
            
            return True
            
        except Exception as e:
            logging.error(f"发送邮件失败: {e}")
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
            logging.debug("不需要发送邮件")
            return True
        
        try:
            # 提取problem_no列表
            problem_numbers = self.extract_problem_numbers(request_data)
            if not problem_numbers:
                logging.warning("未找到problem_no，跳过邮件发送")
                return True
            
            success_count = 0
            total_count = len(problem_numbers)
            
            # 为每个problem_no发送邮件
            for problem_no in problem_numbers:
                # 获取票据数据
                ticket_data = self.get_ticket_data(problem_no)
                if not ticket_data:
                    logging.warning(f"未找到problem_no {problem_no} 的票据数据")
                    continue
                
                # 检查是否有assignee
                assignee = ticket_data.get('assignee')
                if not assignee:
                    logging.info(f"problem_no {problem_no} 没有assignee，跳过邮件发送")
                    continue
                
                # 发送邮件
                if self.send_notification_email(ticket_data, request_data):
                    success_count += 1
                else:
                    logging.error(f"发送problem_no {problem_no} 的邮件失败")
            
            logging.info(f"batch_import邮件发送完成：成功 {success_count}/{total_count}")
            return success_count > 0 or total_count == 0
            
        except Exception as e:
            logging.error(f"处理batch_import请求时出错: {e}")
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
