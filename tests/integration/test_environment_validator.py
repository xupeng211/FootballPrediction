#!/usr/bin/env python3
"""
测试环境验证工具
验证Python环境和基础功能是否正常
"""

import sys
import importlib
import subprocess
from pathlib import Path

def test_python_environment():
    """测试Python基础环境"""
    print("🐍 Python环境验证...")
    print(f"   Python版本: {sys.version}")
    print(f"   Python路径: {sys.executable}")

    # 检查基础库
    基础库 = ['os', 'sys', 'json', 'pathlib', 'datetime']
    for lib in 基础库:
        try:
            importlib.import_module(lib)
            print(f"   ✅ {lib}")
        except ImportError as e:
            print(f"   ❌ {lib}: {e}")

def test_core_dependencies():
    """测试核心依赖"""
    print("\n📦 核心依赖验证...")

    依赖列表 = [
        ('pydantic', '2.3.0'),
        ('fastapi', None),
        ('sqlalchemy', None),
        ('redis', None),
    ]

    for 依赖名, 最低版本 in 依赖列表:
        try:
            模块 = importlib.import_module(依赖名)
            版本 = getattr(模块, '__version__', 'unknown')
            print(f"   ✅ {依赖名}: v{版本}")

            if 最低版本 and 版本 != 'unknown':
                try:
                    from packaging import version as pkg_version
                    if pkg_version.parse(版本) < pkg_version.parse(最低版本):
                        print(f"   ⚠️  版本过低，需要 >={最低版本}")
                except ImportError:
                    print(f"   ⚠️  无法验证版本要求")

        except ImportError as e:
            print(f"   ❌ {依赖名}: {e}")

def test_project_structure():
    """测试项目结构"""
    print("\n📁 项目结构验证...")

    关键目录 = ['src', 'tests', 'scripts', '.github']
    关键文件 = ['pyproject.toml', 'pytest.ini', 'CLAUDE.md']

    for 目录 in 关键目录:
        if Path(目录).exists():
            print(f"   ✅ {目录}/ 目录存在")
        else:
            print(f"   ❌ {目录}/ 目录缺失")

    for 文件 in 关键文件:
        if Path(文件).exists():
            print(f"   ✅ {文件} 文件存在")
        else:
            print(f"   ❌ {文件} 文件缺失")

def test_basic_functionality():
    """测试基础功能"""
    print("\n🧪 基础功能验证...")

    # 测试基础Python功能
    try:
        # 字符串操作
        text = "Hello, World!"
        assert text.upper() == "HELLO, WORLD!"
        print("   ✅ 字符串操作")

        # 数据结构
        data = {"key": "value", "list": [1, 2, 3]}
        assert data["key"] == "value"
        assert len(data["list"]) == 3
        print("   ✅ 数据结构操作")

        # 文件操作
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name

        with open(temp_path, 'r') as f:
            content = f.read()

        import os
        os.unlink(temp_path)
        assert content == "test content"
        print("   ✅ 文件操作")

    except Exception as e:
        print(f"   ❌ 基础功能测试失败: {e}")

def test_import_issues():
    """测试导入问题"""
    print("\n🔍 导入问题诊断...")

    # 测试pytest相关问题
    try:
        import pytest
        print("   ✅ pytest导入成功")
    except Exception as e:
        print(f"   ❌ pytest导入失败: {e}")
        print("   💡 建议: 使用Docker环境或重新创建虚拟环境")

    # 测试其他工具
    工具列表 = ['ruff', 'mypy', 'bandit']
    for 工具 in 工具列表:
        try:
            result = subprocess.run([工具, '--version'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"   ✅ {工具}: {result.stdout.strip()}")
            else:
                print(f"   ⚠️  {工具}: 命令执行失败")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print(f"   ❌ {工具}: 未安装或不可用")

def main():
    """主函数"""
    print("🔧 测试环境完整验证工具")
    print("=" * 50)

    test_python_environment()
    test_core_dependencies()
    test_project_structure()
    test_basic_functionality()
    test_import_issues()

    print("\n" + "=" * 50)
    print("🎯 验证完成")
    print("💡 如果发现❌标记，请参考建议进行修复")

if __name__ == "__main__":
    main()