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
        
        logging.info(f"[邮件初始化] OUTLOOK_AVAILABLE={OUTLOOK_AVAILABLE}")
        logging.info(f"[邮件初始化] _is_email_enabled()={self._is_email_enabled()}")
        logging.info(f"[邮件初始化] sender_email={self.sender_email}")
        
        self.enabled = OUTLOOK_AVAILABLE and self._is_email_enabled()
        
        if self.enabled:
            logging.info("✓✓✓ [邮件初始化] 邮件功能已启用")
        else:
            logging.warning("✗✗✗ [邮件初始化] 邮件功能已禁用：Outlook不可用或配置禁用")
    
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
            logging.info(f"[邮件检查] request_id={request_id}: 邮件功能未启用")
            return False
        
        logging.info(f"[邮件检查] 开始检查 request_id={request_id}")
        
        # 检查是否是batch_import请求
        if 'batch_import' not in request_id:
            logging.info(f"[邮件检查] request_id不包含'batch_import': {request_id}")
            return False
        
        logging.info(f"[邮件检查] ✓ request_id包含'batch_import'")
        
        # 检查是否是TRANSACTION操作
        operation = request_data.get('operation')
        if operation != 'TRANSACTION':
            logging.info(f"[邮件检查] operation不是TRANSACTION: {operation}")
            return False
        
        logging.info(f"[邮件检查] ✓ operation是TRANSACTION")
        
        # 检查metadata中是否有to_list
        metadata = request_data.get('metadata', {})
        to_list = metadata.get('to_list', '')
        
        if not metadata:
            logging.warning(f"[邮件检查] ✗ 缺少metadata字段")
            return False
        
        logging.info(f"[邮件检查] metadata存在: {list(metadata.keys())}")
        
        if not to_list or not to_list.strip():
            logging.warning(f"[邮件检查] ✗ metadata中没有有效的to_list")
            return False
        
        logging.info(f"[邮件检查] ✓ to_list存在: {to_list}")
        
        # 检查是否包含UPDATE操作到tickets表
        operations = request_data.get('data', {}).get('operations', [])
        logging.info(f"[邮件检查] 检查operations: 共{len(operations)}个操作")
        
        has_ticket_update = False
        for i, operation in enumerate(operations):
            op_type = operation.get('type')
            op_table = operation.get('table')
            logging.info(f"[邮件检查] 操作{i+1}: type={op_type}, table={op_table}")
            
            if op_type == 'UPDATE' and op_table == 'tickets':
                has_ticket_update = True
                logging.info(f"[邮件检查] ✓ 找到tickets表的UPDATE操作")
                break
        
        if not has_ticket_update:
            logging.info(f"[邮件检查] ✗ 没有找到tickets表的UPDATE操作")
            return False
        
        logging.info(f"[邮件检查] ✓✓✓ 满足所有邮件发送条件！")
        return True
    
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
        short_text = ticket_data.get('short_text', '')
        
        if short_text:
            return f"Ticket Update Notification: {problem_no} - {short_text}"
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
        
        # 获取更新者信息
        metadata = request_data.get('metadata', {})
        username = metadata.get('username', 'System')
        
        # 生成HTML邮件正文
        html_body = f"""
        <html>
        <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; font-size: 14px; line-height: 1.6;">
            <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #007bff; margin-bottom: 20px;">KPM System Ticket Update Notification</h2>
                
                <p>Dear Team,</p>
                
                <p>A ticket has been updated in the system. Please review the details below:</p>
                
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
        html_body += f"""
                <div style="background-color: #e9ecef; border: 1px solid #ced4da; border-radius: 5px; padding: 15px; margin: 20px 0;">
                    <h4 style="color: #495057; margin-top: 0;">Update Metadata</h4>
                    <p><strong>Updated by:</strong> {username}</p>
                    <p><strong>Update time:</strong> {metadata.get('generated_at', 'N/A')}</p>
                    <p><strong>Hostname:</strong> {metadata.get('hostname', 'N/A')}</p>
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
        problem_no = ticket_data.get('problem_no', 'unknown')
        
        if not self.enabled:
            logging.warning(f"[邮件发送-{problem_no}] 邮件功能未启用，跳过发送")
            return False
        
        outlook = None
        try:
            # 获取metadata中的邮件列表
            metadata = request_data.get('metadata', {})
            to_list_str = metadata.get('to_list', '')
            cc_list_str = metadata.get('cc_list', '')
            
            logging.info(f"[邮件发送-{problem_no}] to_list_str='{to_list_str}'")
            logging.info(f"[邮件发送-{problem_no}] cc_list_str='{cc_list_str}'")
            
            # 解析邮件列表
            to_emails = self.parse_email_list(to_list_str)
            cc_emails = self.parse_email_list(cc_list_str)
            
            logging.info(f"[邮件发送-{problem_no}] 解析后to_emails={to_emails}")
            logging.info(f"[邮件发送-{problem_no}] 解析后cc_emails={cc_emails}")
            
            if not to_emails:
                logging.warning(f"[邮件发送-{problem_no}] metadata中没有有效的to_list，跳过发送")
                return False
            
            # 创建Outlook应用
            logging.info(f"[邮件发送-{problem_no}] 正在创建Outlook应用...")
            outlook = self.create_outlook_application()
            logging.info(f"[邮件发送-{problem_no}] Outlook应用创建成功")
            
            mail = outlook.CreateItem(0)  # 0 = olMailItem
            logging.info(f"[邮件发送-{problem_no}] 邮件对象创建成功")
            
            # 设置发件人
            mail.SentOnBehalfOfName = self.sender_email
            logging.info(f"[邮件发送-{problem_no}] 发件人: {self.sender_email}")
            
            # 设置收件人（分号分隔）
            mail.To = ';'.join(to_emails)
            logging.info(f"[邮件发送-{problem_no}] 收件人: {mail.To}")
            
            # 设置抄送人（如果有）
            if cc_emails:
                mail.CC = ';'.join(cc_emails)
                logging.info(f"[邮件发送-{problem_no}] 抄送人: {mail.CC}")
            
            # 设置主题
            subject = self.generate_email_subject(ticket_data, request_data)
            mail.Subject = subject
            logging.info(f"[邮件发送-{problem_no}] 主题: {subject}")
            
            # 设置邮件正文
            mail.HTMLBody = self.generate_email_body(ticket_data, request_data)
            mail.BodyFormat = 2  # 2 = olFormatHTML
            logging.info(f"[邮件发送-{problem_no}] 邮件正文已设置")
            
            # 发送邮件
            logging.info(f"[邮件发送-{problem_no}] 正在发送邮件...")
            mail.Send()
            logging.info(f"[邮件发送-{problem_no}] ✓✓✓ 邮件发送成功！")
            
            logging.info(f"邮件发送成功：problem_no={problem_no}, "
                        f"to={to_emails}, cc={cc_emails}")
            
            return True
            
        except Exception as e:
            logging.error(f"[邮件发送-{problem_no}] ✗✗✗ 发送邮件失败: {e}", exc_info=True)
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
        request_id = request_data.get('request_id', 'unknown')
        logging.info(f"[邮件发送] ======== 开始处理邮件发送 request_id={request_id} ========")
        
        if not self.should_send_email(request_data):
            logging.info(f"[邮件发送] 不满足邮件发送条件，跳过")
            return True
        
        try:
            # 提取problem_no列表
            problem_numbers = self.extract_problem_numbers(request_data)
            logging.info(f"[邮件发送] 提取到的problem_no列表: {problem_numbers}")
            
            if not problem_numbers:
                logging.warning("[邮件发送] 未找到problem_no，跳过邮件发送")
                return True
            
            success_count = 0
            total_count = len(problem_numbers)
            
            # 为每个problem_no发送邮件
            for problem_no in problem_numbers:
                logging.info(f"[邮件发送] 正在处理 problem_no={problem_no}")
                
                # 获取票据数据
                ticket_data = self.get_ticket_data(problem_no)
                if not ticket_data:
                    logging.warning(f"[邮件发送] 未找到problem_no {problem_no} 的票据数据")
                    continue
                
                logging.info(f"[邮件发送] 票据数据获取成功，准备发送邮件...")
                
                # 发送邮件
                if self.send_notification_email(ticket_data, request_data):
                    success_count += 1
                    logging.info(f"[邮件发送] ✓ problem_no {problem_no} 邮件发送成功")
                else:
                    logging.error(f"[邮件发送] ✗ problem_no {problem_no} 邮件发送失败")
            
            logging.info(f"[邮件发送] ======== 邮件发送完成：成功 {success_count}/{total_count} ========")
            return success_count > 0 or total_count == 0
            
        except Exception as e:
            logging.error(f"[邮件发送] 处理batch_import请求时出错: {e}", exc_info=True)
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
