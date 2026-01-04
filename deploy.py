#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署脚本
用于将SyncSys系统部署到生产环境
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Optional

class SyncSysDeployer:
    """SyncSys部署器"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.required_files = [
            'syncsys_core.py',
            'syncsys_client.py',
            'db_manager.py',
            'start_processor.py',
            'system_monitor.py',
            'config.json',
            'schema.json',
            'requirements.txt'
        ]
        
        self.optional_files = [
            'client_example.py',
            'test_system.py',
            'README.md'
        ]
        
        self.batch_files = [
            'start_processor.bat',
            'monitor_system.bat',
            'manage_database.bat'
        ]
    
    def check_source_files(self) -> bool:
        """检查源文件是否完整"""
        print("检查源文件...")
        
        missing_files = []
        for file_name in self.required_files:
            file_path = self.script_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)
        
        if missing_files:
            print(f"❌ 缺少必需文件: {', '.join(missing_files)}")
            return False
        
        print("✅ 所有必需文件都存在")
        return True
    
    def create_deployment_config(self, target_dir: Path, shared_base: str, 
                               db_path: str = None) -> Dict:
        """创建部署配置"""
        print("创建部署配置...")
        
        if db_path is None:
            db_path = str(target_dir / "data" / "syncsys.db")
        
        config = {
            "shared_folder": {
                "requests": os.path.join(shared_base, "requests").replace("\\", "/"),
                "responses": os.path.join(shared_base, "responses").replace("\\", "/")
            },
            "database": {
                "path": db_path.replace("\\", "/"),
                "backup_path": str(target_dir / "backup").replace("\\", "/")
            },
            "processor": {
                "poll_interval": 1.0,
                "max_concurrent_requests": 10,
                "request_timeout": 30,
                "cleanup_interval": 300
            },
            "client": {
                "poll_interval": 0.5,
                "request_timeout": 30,
                "retry_attempts": 3,
                "retry_delay": 1.0
            },
            "logging": {
                "level": "INFO",
                "file": str(target_dir / "logs" / "syncsys.log").replace("\\", "/")
            }
        }
        
        return config
    
    def copy_files(self, target_dir: Path, include_optional: bool = True, 
                   include_batch: bool = True) -> None:
        """复制文件到目标目录"""
        print(f"复制文件到 {target_dir}...")
        
        # 复制必需文件
        for file_name in self.required_files:
            src = self.script_dir / file_name
            dst = target_dir / file_name
            shutil.copy2(src, dst)
            print(f"  ✅ {file_name}")
        
        # 复制可选文件
        if include_optional:
            for file_name in self.optional_files:
                src = self.script_dir / file_name
                if src.exists():
                    dst = target_dir / file_name
                    shutil.copy2(src, dst)
                    print(f"  ✅ {file_name} (可选)")
        
        # 复制批处理文件
        if include_batch and os.name == 'nt':
            for file_name in self.batch_files:
                src = self.script_dir / file_name
                if src.exists():
                    dst = target_dir / file_name
                    shutil.copy2(src, dst)
                    print(f"  ✅ {file_name} (批处理)")
    
    def create_directory_structure(self, target_dir: Path) -> None:
        """创建目录结构"""
        print("创建目录结构...")
        
        directories = [
            target_dir,
            target_dir / "data",
            target_dir / "backup",
            target_dir / "logs",
            target_dir / "client"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"  📁 {directory}")
    
    def create_client_package(self, target_dir: Path) -> None:
        """创建客户端包"""
        print("创建客户端包...")
        
        client_dir = target_dir / "client"
        
        # 复制客户端必需文件
        client_files = ['syncsys_client.py', 'client_example.py']
        
        for file_name in client_files:
            src = self.script_dir / file_name
            if src.exists():
                dst = client_dir / file_name
                shutil.copy2(src, dst)
                print(f"  ✅ client/{file_name}")
        
        # 创建客户端配置模板
        client_config_template = {
            "shared_folder": {
                "requests": "//server/syncsys/requests",
                "responses": "//server/syncsys/responses"
            },
            "client": {
                "poll_interval": 0.5,
                "request_timeout": 30,
                "retry_attempts": 3,
                "retry_delay": 1.0
            },
            "logging": {
                "level": "INFO",
                "file": "syncsys_client.log"
            }
        }
        
        client_config_path = client_dir / "client_config_template.json"
        with open(client_config_path, 'w', encoding='utf-8') as f:
            json.dump(client_config_template, f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ client/client_config_template.json")
        
        # 创建客户端README
        client_readme = """# SyncSys 客户端

## 安装

1. 将此文件夹复制到客户端机器
2. 修改 `client_config_template.json` 为 `config.json`
3. 更新配置中的共享文件夹路径
4. 安装Python依赖（如果需要）

## 使用示例

```python
from syncsys_client import SyncClient

# 创建客户端
client = SyncClient('config.json')

# 插入数据
result = client.insert('users', {
    'username': 'john_doe',
    'email': 'john@example.com'
})

if result.success:
    print(f"插入成功，ID: {result.data['inserted_id']}")
else:
    print(f"插入失败: {result.error}")

# 关闭客户端
client.close()
```

更多示例请参考 `client_example.py`
"""
        
        client_readme_path = client_dir / "README.md"
        with open(client_readme_path, 'w', encoding='utf-8') as f:
            f.write(client_readme)
        
        print(f"  ✅ client/README.md")
    
    def create_startup_scripts(self, target_dir: Path) -> None:
        """创建启动脚本"""
        print("创建启动脚本...")
        
        # Linux/Unix 启动脚本
        if os.name != 'nt':
            startup_script = f"""#!/bin/bash
# SyncSys 处理器启动脚本

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3"
    exit 1
fi

# 启动处理器
echo "启动 SyncSys 处理器..."
python3 start_processor.py --config config.json --daemon

echo "处理器已启动"
"""
            
            script_path = target_dir / "start_syncsys.sh"
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(startup_script)
            
            # 设置执行权限
            os.chmod(script_path, 0o755)
            print(f"  ✅ start_syncsys.sh")
        
        # 创建服务配置文件（systemd）
        if os.name != 'nt':
            service_config = f"""[Unit]
Description=SyncSys Database Synchronization Service
After=network.target

[Service]
Type=simple
User=syncsys
WorkingDirectory={target_dir}
ExecStart=/usr/bin/python3 {target_dir}/start_processor.py --config {target_dir}/config.json --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
            
            service_path = target_dir / "syncsys.service"
            with open(service_path, 'w', encoding='utf-8') as f:
                f.write(service_config)
            
            print(f"  ✅ syncsys.service")
    
    def create_deployment_guide(self, target_dir: Path, shared_base: str) -> None:
        """创建部署指南"""
        print("创建部署指南...")
        
        guide = f"""# SyncSys 部署指南

## 部署信息

- 部署目录: {target_dir}
- 共享文件夹基础路径: {shared_base}
- 配置文件: config.json
- 数据库架构: schema.json

## 部署步骤

### 1. 环境准备

确保系统已安装 Python 3.7+：
```bash
python3 --version
```

### 2. 创建共享文件夹

在文件服务器上创建以下目录结构：
```
{shared_base}/
├── requests/
└── responses/
```

确保所有客户端机器都能访问这些文件夹。

### 3. 初始化数据库

```bash
python3 start_processor.py --config config.json --init-db --schema schema.json
```

### 4. 启动处理器

#### Windows
```cmd
start_processor.bat
```

#### Linux/Unix
```bash
./start_syncsys.sh
```

或者手动启动：
```bash
python3 start_processor.py --config config.json --daemon
```

### 5. 配置客户端

1. 将 `client/` 文件夹复制到客户端机器
2. 重命名 `client_config_template.json` 为 `config.json`
3. 修改配置中的共享文件夹路径
4. 测试连接：
```python
from syncsys_client import SyncClient
client = SyncClient('config.json')
result = client.select('sync_log', limit=1)
print("连接测试:", "成功" if result.success else result.error)
client.close()
```

## 监控和维护

### 系统监控

```bash
# Windows
monitor_system.bat

# Linux/Unix
python3 system_monitor.py --config config.json
```

### 数据库管理

```bash
# Windows
manage_database.bat

# Linux/Unix
python3 db_manager.py --config config.json
```

### 日志查看

日志文件位置：`logs/syncsys.log`

```bash
# 查看最新日志
tail -f logs/syncsys.log

# 查看错误日志
grep ERROR logs/syncsys.log
```

## 性能优化

### 1. 调整轮询间隔

在 `config.json` 中调整：
- `processor.poll_interval`: 处理器轮询间隔
- `client.poll_interval`: 客户端轮询间隔

### 2. 并发设置

- `processor.max_concurrent_requests`: 最大并发请求数

### 3. 数据库优化

```bash
# 数据库清理
python3 db_manager.py --config config.json --vacuum

# 数据库备份
python3 db_manager.py --config config.json --backup
```

## 故障排除

### 常见问题

1. **处理器无法启动**
   - 检查配置文件路径
   - 确认共享文件夹可访问
   - 查看日志文件

2. **客户端连接失败**
   - 检查共享文件夹权限
   - 确认网络连接
   - 验证配置文件

3. **性能问题**
   - 调整轮询间隔
   - 增加并发数
   - 检查磁盘空间

### 系统测试

运行完整的系统测试：
```bash
python3 test_system.py --config config.json
```

## 安全注意事项

1. 确保共享文件夹访问权限正确设置
2. 定期备份数据库
3. 监控系统资源使用情况
4. 及时清理过期的请求和响应文件

## 联系支持

如遇到问题，请检查：
1. 系统日志
2. 配置文件
3. 网络连接
4. 文件权限
"""
        
        guide_path = target_dir / "DEPLOYMENT.md"
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide)
        
        print(f"  ✅ DEPLOYMENT.md")
    
    def deploy(self, target_dir: str, shared_base: str, db_path: str = None,
               include_optional: bool = True, include_batch: bool = True) -> bool:
        """执行部署"""
        print(f"开始部署 SyncSys 到 {target_dir}")
        print("=" * 60)
        
        # 检查源文件
        if not self.check_source_files():
            return False
        
        target_path = Path(target_dir)
        
        try:
            # 创建目录结构
            self.create_directory_structure(target_path)
            
            # 复制文件
            self.copy_files(target_path, include_optional, include_batch)
            
            # 创建部署配置
            config = self.create_deployment_config(target_path, shared_base, db_path)
            config_path = target_path / "config.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"  ✅ config.json")
            
            # 创建客户端包
            self.create_client_package(target_path)
            
            # 创建启动脚本
            self.create_startup_scripts(target_path)
            
            # 创建部署指南
            self.create_deployment_guide(target_path, shared_base)
            
            print("\n" + "=" * 60)
            print("🎉 部署完成！")
            print("=" * 60)
            
            print(f"\n部署目录: {target_path}")
            print(f"配置文件: {target_path / 'config.json'}")
            print(f"客户端包: {target_path / 'client'}")
            print(f"部署指南: {target_path / 'DEPLOYMENT.md'}")
            
            print("\n下一步:")
            print("1. 创建共享文件夹")
            print("2. 初始化数据库")
            print("3. 启动处理器")
            print("4. 配置客户端")
            print("\n详细步骤请参考 DEPLOYMENT.md")
            
            return True
            
        except Exception as e:
            print(f"❌ 部署失败: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='SyncSys 部署工具')
    parser.add_argument('target_dir', help='目标部署目录')
    parser.add_argument('shared_base', help='共享文件夹基础路径 (例如: //server/syncsys)')
    parser.add_argument('--db-path', help='数据库文件路径 (可选)')
    parser.add_argument('--no-optional', action='store_true', help='不包含可选文件')
    parser.add_argument('--no-batch', action='store_true', help='不包含批处理文件')
    
    args = parser.parse_args()
    
    deployer = SyncSysDeployer()
    
    success = deployer.deploy(
        target_dir=args.target_dir,
        shared_base=args.shared_base,
        db_path=args.db_path,
        include_optional=not args.no_optional,
        include_batch=not args.no_batch
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()