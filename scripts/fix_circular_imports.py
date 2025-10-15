#!/usr/bin/env python3
"""
修复循环导入问题
Fix Circular Import Issues
"""

import os
from pathlib import Path

def fix_services_init():
    """修复 services/__init__.py"""
    print("🔧 修复 services/__init__.py 循环导入...")

    init_file = Path("src/services/__init__.py")
    if init_file.exists():
        content = """# Services module
# Core services are imported on demand to avoid circular imports

__all__ = [
    # Services will be added here as needed
]
"""
        init_file.write_text(content)
        print("  ✅ services/__init__.py 已简化")

def fix_src_init():
    """修复 src/__init__.py"""
    print("\n🔧 修复 src/__init__.py...")

    init_file = Path("src/__init__.py")
    if init_file.exists():
        content = """# Football Prediction System
# Core modules are imported on demand

__version__ = "1.0.0"
__author__ = "Football Prediction Team"

# Minimal imports only
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type hints only, no runtime imports
    from . import services
    from . import api
    from . import core
    from . import database
    from . import cache
    from . import adapters
"""
        init_file.write_text(content)
        print("  ✅ src/__init__.py 已更新")

def test_import(module_path: str, item_name: str = None) -> bool:
    """测试导入"""
    try:
        if item_name:
            cmd = f'python -c "from {module_path} import {item_name}"'
        else:
            cmd = f'python -c "import {module_path}"'

        result = os.system(cmd + " 2>/dev/null")
        return result == 0
    except:
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("           修复循环导入问题")
    print("=" * 60)

    # 修复循环导入
    fix_services_init()
    fix_src_init()

    # 测试关键导入
    print("\n🔍 测试关键模块导入...")

    tests = [
        ("src.database.connection", "DatabaseManager"),
        ("src.core.logging", "get_logger"),
        ("src.utils.dict_utils", None),
    ]

    success = 0
    for module, item in tests:
        if test_import(module, item):
            name = f"{module}.{item}" if item else module
            print(f"  ✅ {name}")
            success += 1
        else:
            name = f"{module}.{item}" if item else module
            print(f"  ❌ {name}")

    print(f"\n✅ 成功: {success}/{len(tests)}")

    if success >= 2:
        print("\n📊 可以运行基础测试了！")
        print("尝试: pytest tests/unit/utils/test_dict_utils.py -v")

if __name__ == "__main__":
    main()