"""
事务生成器使用示例
演示如何使用不同的类和方法生成事务JSON文件
"""

from transaction_builder import (
    TransactionBuilder,
    DataDictHelper,
    FieldManager
)
import json


def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建事务构建器
    builder = TransactionBuilder()
    
    # 添加INSERT操作
    task_data = {
        "task_id": "a6e5f65f-e93b-4621-aeca-3ab8167a0418",
        "task_type": "Others",
        "suggested_colleague": "All",
        "is_finished": "False",
        "sender_name": "Bohan, Zhang",
        "sender_dept": "C/EG-V",
        "sender_mail": "beihaizhang11@cs.com",
        "sender_phone": "13501253304",
        "cc": "",
        "VIN": "LSVCCAF07P2000204",
        "carid": "EA267",
        "car_location": "VLabs",
        "key_location": "Vlabs Key Cabinet",
        "task_status": "rejected",
        "assigned_by": "qinwei@testcompany.com",
        "accepted_by": "",
        "deferred_by": "",
        "finished_by": "",
        "rejected_by": "",
        "reject_reason": "",
        "sent_time": "",
        "request_start_time": "",
        "request_end_time": "",
        "assigned_time": 1652221600,
        "accepted_time": "",
        "finished_time": "",
        "purpose": "",
        "project": "",
        "task_description": "",
        "bg_description": "",
        "effort": "",
        "task_dept": "",
        "additional_comment": ""
    }
    builder.add_insert("tasks", task_data)
    
    # 添加UPDATE操作 - 简化版，只需要task_id和values字典
    builder.add_update("tasks", "a6e5f65f-e93b-4621-aeca-3ab8167a0418", {"task_status": "in_progress"})
    
    # 添加DELETE操作 - 简化版，只需要task_id
    builder.add_delete("tasks_staff", "task-001")
    
    # 生成事务
    transaction = builder.build_transaction("request-001", "client-001")
    print(json.dumps(transaction, indent=2, ensure_ascii=False))

    # 保存到文件
    builder.save_to_file("example_transaction.json", "request-001", "client-001")
    print("事务已保存到 example_transaction.json")
    
    # 演示高级API的使用
    print("\n=== 高级API示例 ===")
    
    # 创建带client_id的构建器
    high_level_builder = TransactionBuilder(client_id="client-001")
    
    # 使用高级API
    task_id = "high-level-task-001"
    high_level_builder.create_task({
        "task_id": task_id,
        "task_type": "High Level Test",
        "sender_name": "High Level User",
        "sender_mail": "highlevel@company.com"
    }).update_task_status(
        task_id=task_id,
        status="assigned",
        updated_by="manager@company.com"
    ).assign_staff(
        task_id=task_id,
        staff_email="worker@company.com"
    )
    
    # 使用高级API保存文件
    high_level_builder.save_transaction_file("high_level_transaction.json", "high-level-request")
    print("高级API事务已保存到 high_level_transaction.json")
    
    # 使用配置路径保存文件
    config_path = high_level_builder.save_to_config_path(request_id="config-example")
    print(f"使用配置路径保存文件到: {config_path}")

# def example_with_helpers():
#     """使用助手类的示例"""
#     print("\n=== 使用助手类示例 ===")
    
#     builder = UnifiedTransactionBuilder()
    
#     # 使用DataDictHelper构建数据
#     insert_data = DataDictHelper.build_insert_data(
#         task_id="task-002",
#         task_type="Maintenance",
#         sender_name="Li Si",
#         sender_email="lisi@company.com",
#         task_status="pending"
#     )
#     builder.add_insert("tasks", insert_data)
    
#     # 使用FieldManager构建更新字段
#     status_fields = FieldManager.status_update(
#         status="accepted",
#         updated_by="manager@company.com"
#     )
#     builder.add_update("tasks", "task-002", status_fields)
    
#     # 生成事务
#     transaction = builder.build_transaction("req-002", "client-002")
#     print(json.dumps(transaction, indent=2, ensure_ascii=False))


# def example_high_level_api():
#     """高级API使用示例"""
#     print("\n=== 高级API使用示例 ===")
    
#     # 创建事务生成器
#     generator = TransactionGenerator("client-003")
    
#     # 链式调用创建复杂事务
#     generator.create_task({
#         "task_type": "Testing",
#         "sender_name": "Wang Wu",
#         "sender_email": "wangwu@company.com",
#         "VIN": "TEST123456789",
#         "car_location": "Lab A"
#     }).update_task_status(
#         task_id="auto-generated-id",  # 会被自动生成的ID替换
#         status="assigned",
#         updated_by="manager@company.com"
#     ).assign_staff(
#         task_id="auto-generated-id",
#         staff_email="staff1@company.com"
#     ).assign_staff(
#         task_id="auto-generated-id",
#         staff_email="staff2@company.com"
#     )
    
#     # 生成JSON字符串
#     json_string = generator.generate_json_string("req-003")
#     print(json_string)
    
#     # 保存到文件
#     generator.save_to_file("example_transaction.json", "req-003")
#     print("事务已保存到 example_transaction.json")


# def example_flexible_updates():
#     """灵活更新示例"""
#     print("\n=== 灵活更新示例 ===")
    
#     builder = UnifiedTransactionBuilder()
    
#     # 场景1: 只更新状态
#     builder.add_update("tasks", "task-001", {"task_status": "finished"})
    
#     # 场景2: 更新多个字段
#     builder.add_update("tasks", "task-002", {
#         "task_status": "rejected",
#         "rejected_by": "admin@company.com",
#         "reject_reason": "资源不足"
#     })
    
#     # 场景3: 更新时间相关字段
#     import time
#     current_time = int(time.time())
#     builder.add_update("tasks", "task-003", {
#         "accepted_time": current_time,
#         "accepted_by": "worker@company.com"
#     })
    
#     # 场景4: 使用复杂删除条件
#     builder.add_delete_with_conditions("tasks_staff", {
#         "task_id": "task-001",
#         "staff_email": "specific@company.com"
#     })
    
#     transaction = builder.build_transaction("flexible-req", "client-004")
#     print(json.dumps(transaction, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    example_basic_usage()
#    example_with_helpers()
#    example_high_level_api()
#    example_flexible_updates() 