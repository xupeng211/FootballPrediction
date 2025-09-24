#!/usr/bin/env python3
"""
依赖管理脚本 / Dependency Management Script

用于统一依赖管理策略，自动生成锁定文件。
Used to unify dependency management strategy and automatically generate lock files.
"""

import os
import subprocess
import sys
from datetime import datetime


def run_command(command, cwd=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout.strip(), None
    except subprocess.CalledProcessError as e:
        return None, f"Command failed: {e.cmd}\nError: {e.stderr}"


def update_requirements_lock():
    """更新requirements.lock文件"""
    print("🔄 更新 requirements.lock...")
    
    # 检查pip-tools是否已安装
    stdout, stderr = run_command("pip list | grep pip-tools")
    if stderr:
        print("⚠️  pip-tools未安装，正在安装...")
        stdout, stderr = run_command("pip install pip-tools")
        if stderr:
            print(f"❌ 安装pip-tools失败: {stderr}")
            return False
        print("✅ pip-tools安装成功")
    
    # 生成requirements.lock
    stdout, stderr = run_command("pip-compile --output-file=requirements.lock requirements.txt")
    if stderr:
        print(f"❌ 生成requirements.lock失败: {stderr}")
        return False
    
    print("✅ requirements.lock更新成功")
    return True


def update_requirements_dev_lock():
    """更新requirements-dev.lock文件"""
    print("🔄 更新 requirements-dev.lock...")
    
    # 生成requirements-dev.lock
    stdout, stderr = run_command("pip-compile --output-file=requirements-dev.lock requirements-dev.txt")
    if stderr:
        print(f"❌ 生成requirements-dev.lock失败: {stderr}")
        return False
    
    print("✅ requirements-dev.lock更新成功")
    return True


def sync_dependencies():
    """同步依赖到当前环境"""
    print("🔄 同步依赖到当前环境...")
    
    # 安装生产依赖
    stdout, stderr = run_command("pip-sync requirements.lock")
    if stderr:
        print(f"❌ 同步生产依赖失败: {stderr}")
        return False
    
    # 安装开发依赖
    stdout, stderr = run_command("pip-sync requirements-dev.lock")
    if stderr:
        print(f"❌ 同步开发依赖失败: {stderr}")
        return False
    
    print("✅ 依赖同步成功")
    return True


def main():
    """主函数"""
    print("🚀 开始统一依赖管理策略...")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    print(f"📁 工作目录: {project_root}")
    print()
    
    # 更新锁定文件
    if not update_requirements_lock():
        sys.exit(1)
    
    if not update_requirements_dev_lock():
        sys.exit(1)
    
    print()
    print("✅ 依赖管理策略统一完成!")
    print(f"⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("📝 下一步建议:")
    print("   1. 检查生成的锁定文件是否符合预期")
    print("   2. 运行 'pip-sync requirements.lock requirements-dev.lock' 同步环境")
    print("   3. 运行测试确保依赖更新未破坏功能")


if __name__ == "__main__":
    main()