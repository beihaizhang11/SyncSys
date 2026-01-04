"""
获取Windows用户显示名称的方法
"""

import os
import subprocess
import getpass


def get_windows_username():
    """
    获取Windows用户的显示名称
    
    Returns:
        str: Windows用户的显示名称
    """
    try:
        # 方法1: 使用whoami命令获取用户信息
        result = subprocess.run(['whoami', '/upn'], 
                              capture_output=True, 
                              text=True, 
                              shell=True)
        
        if result.returncode == 0:
            upn = result.stdout.strip()
            print(f"User Principal Name: {upn}")
        
        # 方法2: 使用net user命令获取当前用户的详细信息
        current_user = getpass.getuser()
        result = subprocess.run(['net', 'user', current_user], 
                              capture_output=True, 
                              text=True, 
                              shell=True)
        
        if result.returncode == 0:
            output = result.stdout
            # 查找Full Name行
            for line in output.split('\n'):
                if 'Full Name' in line or '全名' in line:
                    full_name = line.split(':', 1)[1].strip() if ':' in line else line.strip()
                    if full_name:
                        return full_name
        
        # 方法3: 尝试从环境变量获取
        display_name = os.environ.get('USERNAME', '')
        if display_name:
            return display_name
        
        # 方法4: 使用getpass作为备用
        return getpass.getuser()
        
    except Exception as e:
        print(f"获取用户名时出错: {e}")
        return getpass.getuser()


def get_windows_username_advanced():
    """
    使用Windows API获取用户显示名称（需要安装pywin32）
    
    Returns:
        str: Windows用户的显示名称
    """
    try:
        import win32api
        import win32con
        import win32net
        
        # 获取当前用户名
        username = win32api.GetUserName()
        
        # 尝试获取用户的详细信息
        try:
            user_info = win32net.NetUserGetInfo(None, username, 2)
            full_name = user_info.get('full_name', '')
            if full_name:
                return full_name
        except:
            pass
        
        # 如果上面失败，返回用户名
        return username
        
    except ImportError:
        print("pywin32 模块未安装，使用基本方法...")
        return get_windows_username()
    except Exception as e:
        print(f"获取用户名时出错: {e}")
        return get_windows_username()


def print_user_info():
    """
    打印用户信息
    """
    print("=== Windows 用户信息 ===")
    
    # 基本用户名
    basic_username = getpass.getuser()
    print(f"登录用户名: {basic_username}")
    
    # 尝试获取显示名称
    display_name = get_windows_username()
    print(f"显示名称: {display_name}")
    
    # 尝试高级方法
    advanced_name = get_windows_username_advanced()
    print(f"完整名称: {advanced_name}")
    
    # 环境变量信息
    print("\n=== 环境变量信息 ===")
    env_vars = ['USERNAME', 'USERDOMAIN', 'USERPROFILE', 'COMPUTERNAME']
    for var in env_vars:
        value = os.environ.get(var, '未设置')
        print(f"{var}: {value}")


if __name__ == "__main__":
    print_user_info() 