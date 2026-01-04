import sqlite3
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from syncsys_core import ConfigManager
import logging

class DatabaseInitializer:
    """数据库初始化器"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = ConfigManager(config_path)
        self.db_path = self.config.get('database.path')
        self.backup_path = self.config.get('database.backup_path')
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if self.backup_path:
            os.makedirs(self.backup_path, exist_ok=True)
    
    def create_table(self, table_name: str, columns: Dict[str, str], 
                     primary_key: str = None, indexes: List[str] = None):
        """创建表
        
        Args:
            table_name: 表名
            columns: 列定义 {'column_name': 'column_type'}
            primary_key: 主键列名
            indexes: 需要创建索引的列名列表
        """
        with sqlite3.connect(self.db_path) as conn:
            # 构建列定义
            column_defs = []
            for col_name, col_type in columns.items():
                col_def = f"{col_name} {col_type}"
                if primary_key and col_name == primary_key:
                    col_def += " PRIMARY KEY"
                column_defs.append(col_def)
            
            # 创建表
            sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)})"
            conn.execute(sql)
            
            # 创建索引
            if indexes:
                for index_col in indexes:
                    if index_col in columns:
                        index_name = f"idx_{table_name}_{index_col}"
                        index_sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({index_col})"
                        conn.execute(index_sql)
            
            conn.commit()
            logging.info(f"表 {table_name} 创建成功")
    
    def create_tables_from_schema(self, schema_file: str):
        """从schema文件创建表"""
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        for table_name, table_def in schema.get('tables', {}).items():
            self.create_table(
                table_name=table_name,
                columns=table_def.get('columns', {}),
                primary_key=table_def.get('primary_key'),
                indexes=table_def.get('indexes', [])
            )
    
    def backup_database(self, backup_name: str = None):
        """备份数据库"""
        if not backup_name:
            from datetime import datetime
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        backup_file = Path(self.backup_path) / backup_name
        
        # 复制数据库文件
        import shutil
        shutil.copy2(self.db_path, backup_file)
        
        logging.info(f"数据库备份完成: {backup_file}")
        return str(backup_file)
    
    def restore_database(self, backup_file: str):
        """恢复数据库"""
        import shutil
        shutil.copy2(backup_file, self.db_path)
        logging.info(f"数据库恢复完成: {backup_file}")
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """获取表信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # 获取索引信息
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()
            
            # 获取记录数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            return {
                'columns': [
                    {
                        'name': col[1],
                        'type': col[2],
                        'not_null': bool(col[3]),
                        'default': col[4],
                        'primary_key': bool(col[5])
                    } for col in columns
                ],
                'indexes': [idx[1] for idx in indexes],
                'row_count': row_count
            }
    
    def list_tables(self) -> List[str]:
        """列出所有表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            return [row[0] for row in cursor.fetchall()]
    
    def drop_table(self, table_name: str):
        """删除表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()
            logging.info(f"表 {table_name} 删除成功")
    
    def vacuum_database(self):
        """压缩数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("VACUUM")
            logging.info("数据库压缩完成")
    
    def get_database_size(self) -> int:
        """获取数据库文件大小（字节）"""
        return os.path.getsize(self.db_path)
    
    def execute_sql(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行自定义SQL"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            if sql.strip().upper().startswith('SELECT'):
                return [dict(row) for row in cursor.fetchall()]
            else:
                conn.commit()
                return [{'rows_affected': cursor.rowcount}]

class DatabaseMonitor:
    """数据库监控器"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = ConfigManager(config_path)
        self.db_path = self.config.get('database.path')
    
    def get_connection_count(self) -> int:
        """获取连接数（SQLite单连接，返回1或0）"""
        try:
            with sqlite3.connect(self.db_path, timeout=1) as conn:
                return 1
        except:
            return 0
    
    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 获取所有表的统计信息
            tables_stats = {}
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]
                tables_stats[table] = {'row_count': row_count}
            
            # 获取数据库页面信息
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            return {
                'tables': tables_stats,
                'page_count': page_count,
                'page_size': page_size,
                'database_size': page_count * page_size,
                'file_size': os.path.getsize(self.db_path)
            }
    
    def check_integrity(self) -> bool:
        """检查数据库完整性"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]
                return result == 'ok'
        except:
            return False

def create_sample_schema():
    """创建示例schema文件"""
    schema = {
        "tables": {
            "users": {
                "columns": {
                    "id": "INTEGER",
                    "username": "TEXT NOT NULL UNIQUE",
                    "email": "TEXT NOT NULL UNIQUE",
                    "password_hash": "TEXT NOT NULL",
                    "created_at": "REAL NOT NULL",
                    "updated_at": "REAL",
                    "is_active": "INTEGER DEFAULT 1"
                },
                "primary_key": "id",
                "indexes": ["username", "email", "created_at"]
            },
            "products": {
                "columns": {
                    "id": "INTEGER",
                    "name": "TEXT NOT NULL",
                    "description": "TEXT",
                    "price": "REAL NOT NULL",
                    "stock": "INTEGER DEFAULT 0",
                    "category_id": "INTEGER",
                    "created_at": "REAL NOT NULL",
                    "updated_at": "REAL"
                },
                "primary_key": "id",
                "indexes": ["name", "category_id", "price"]
            },
            "orders": {
                "columns": {
                    "id": "INTEGER",
                    "user_id": "INTEGER NOT NULL",
                    "total_amount": "REAL NOT NULL",
                    "status": "TEXT DEFAULT 'pending'",
                    "created_at": "REAL NOT NULL",
                    "updated_at": "REAL"
                },
                "primary_key": "id",
                "indexes": ["user_id", "status", "created_at"]
            },
            "order_items": {
                "columns": {
                    "id": "INTEGER",
                    "order_id": "INTEGER NOT NULL",
                    "product_id": "INTEGER NOT NULL",
                    "quantity": "INTEGER NOT NULL",
                    "price": "REAL NOT NULL"
                },
                "primary_key": "id",
                "indexes": ["order_id", "product_id"]
            }
        }
    }
    
    with open('schema.json', 'w', encoding='utf-8') as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)
    
    print("示例schema文件已创建: schema.json")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库管理工具')
    parser.add_argument('--init', action='store_true', help='初始化数据库')
    parser.add_argument('--schema', type=str, help='从schema文件创建表')
    parser.add_argument('--backup', type=str, nargs='?', const='', help='备份数据库')
    parser.add_argument('--restore', type=str, help='恢复数据库')
    parser.add_argument('--info', type=str, help='获取表信息')
    parser.add_argument('--list', action='store_true', help='列出所有表')
    parser.add_argument('--stats', action='store_true', help='获取数据库统计信息')
    parser.add_argument('--vacuum', action='store_true', help='压缩数据库')
    parser.add_argument('--check', action='store_true', help='检查数据库完整性')
    parser.add_argument('--create-schema', action='store_true', help='创建示例schema文件')
    
    args = parser.parse_args()
    
    if args.create_schema:
        create_sample_schema()
    elif args.init or args.schema or args.backup is not None or args.restore or args.info or args.list or args.stats or args.vacuum or args.check:
        db_init = DatabaseInitializer()
        
        if args.init:
            print("数据库初始化完成")
        
        if args.schema:
            db_init.create_tables_from_schema(args.schema)
            print(f"从 {args.schema} 创建表完成")
        
        if args.backup is not None:
            backup_file = db_init.backup_database(args.backup if args.backup else None)
            print(f"数据库备份完成: {backup_file}")
        
        if args.restore:
            db_init.restore_database(args.restore)
            print(f"数据库恢复完成")
        
        if args.info:
            info = db_init.get_table_info(args.info)
            print(f"表 {args.info} 信息:")
            print(json.dumps(info, ensure_ascii=False, indent=2))
        
        if args.list:
            tables = db_init.list_tables()
            print("数据库表列表:")
            for table in tables:
                print(f"  - {table}")
        
        if args.stats:
            monitor = DatabaseMonitor()
            stats = monitor.get_database_stats()
            print("数据库统计信息:")
            print(json.dumps(stats, ensure_ascii=False, indent=2))
        
        if args.vacuum:
            db_init.vacuum_database()
            print("数据库压缩完成")
        
        if args.check:
            monitor = DatabaseMonitor()
            is_ok = monitor.check_integrity()
            print(f"数据库完整性检查: {'通过' if is_ok else '失败'}")
    else:
        parser.print_help()