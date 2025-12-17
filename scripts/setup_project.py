#!/usr/bin/env python3
"""
项目结构初始化脚本
为CI/CD环境提供所需的基本目录结构
"""

import os
from pathlib import Path


def create_required_directories():
    """创建项目所需的基本目录结构"""

    # CI/CD需要的基本目录
    required_dirs = [
        "logs",
        "data",
        "models",
        "config",
        "temp",
        ".pytest_cache",
        ".mypy_cache",
    ]

    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建目录: {dir_path}")

    return True


def main():
    """主函数"""
    print("🚀 初始化项目结构...")

    try:
        if create_required_directories():
            print("✅ 项目结构初始化完成")
            return True
        else:
            print("❌ 项目结构初始化失败")
            return False
    except Exception as e:
        print(f"❌ 项目结构初始化异常: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
