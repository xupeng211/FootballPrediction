#!/usr/bin/env python3
"""
最终修复 MyPy 类型错误
"""

import re
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).parent.parent


def main():
    print("🔧 最终修复 MyPy 类型错误")
    print("=" * 50)

    # 使用 sed 进行快速修复
    fixes = [
        # 修复泛型类型
        ("s/\\bDict\\b/Dict[str, Any]/g", "修复 Dict 泛型"),
        ("s/\\bdict\\b/dict[str, Any]/g", "修复 dict 泛型"),
        ("s/\\bList\\b/List[Any]/g", "修复 List 泛型"),
        ("s/\\bType\\b/Type[Any]/g", "修复 Type 泛型"),
        # 添加类型导入
        ("s/from typing import/from typing import Any, /g", "添加 Any 导入"),
    ]

    for pattern, desc in fixes:
        print(f"\n📝 {desc}...")
        cmd = f"find src -name '*.py' -not -name '__init__.py' -exec sed -i '{pattern}' {{}} +"
        subprocess.run(cmd, shell=True)

    # 运行 type-check 验证
    print("\n🔍 验证修复效果...")
    result = subprocess.run(["make", "type-check"], capture_output=True, text=True)

    # 统计剩余错误
    errors = result.stdout.count("error:")
    warnings = result.stdout.count("warning:")

    print("\n📊 结果统计:")
    print(f"  • 错误数: {errors}")
    print(f"  • 警告数: {warnings}")

    if errors == 0:
        print("\n✅ 核心模块类型检查通过！")
        return 0
    else:
        print(f"\n⚠️  还有 {errors} 个错误需要处理")

        # 导出错误到文件
        with open("mypy_errors.log", "w") as f:
            f.write(result.stdout)
        print("📄 错误详情已保存到 mypy_errors.log")

        return 1


if __name__ == "__main__":
    sys.exit(main())
