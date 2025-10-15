#!/usr/bin/env python3
"""
快速质量修复脚本
Quick Quality Fix Script

专注于修复关键的代码质量问题
"""

import re
from pathlib import Path


def fix_specific_files():
    """修复特定的文件"""
    critical_files = [
        "src/adapters/football.py",
        "src/api/predictions/router.py",
        "src/api/schemas.py",
        "src/utils/dict_utils.py",
    ]

    print("🔧 修复关键文件...")

    for file_path in critical_files:
        path = Path(file_path)
        if not path.exists():
            continue

        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()

            original = content

            # 修复常见的类型注解错误
            content = re.sub(
                r"-> List\[Dict\[str, Any\]:", "-> List[Dict[str, Any]]:", content
            )

            content = re.sub(
                r"-> Optional\[Dict\[str, Any\]:",
                "-> Optional[Dict[str, Any]]:",
                content,
            )

            content = re.sub(
                r"-> Optional\[PredictionRequest\]:",
                "-> Optional[PredictionRequest]:",
                content,
            )

            content = re.sub(r"-> Optional\[str\]:", "-> Optional[str]:", content)

            content = re.sub(r"-> Dict\[str, Any\]:", "-> Dict[str, Any]:", content)

            if content != original:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  ✅ 修复了 {file_path}")

        except Exception as e:
            print(f"  ❌ {file_path}: {e}")


def add_missing_imports():
    """添加缺失的导入"""
    print("\n🔧 添加缺失的导入...")

    # 修复需要ClassVar的文件
    files_to_fix = ["tests/unit/utils/test_config_comprehensive.py"]

    for file_path in files_to_fix:
        path = Path(file_path)
        if not path.exists():
            continue

        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()

            if "ClassVar" in content and "from typing import" in content:
                content = re.sub(
                    r"from typing import (.*)",
                    r"from typing import \1, ClassVar",
                    content,
                )

                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  ✅ 添加ClassVar导入到 {file_path}")

        except Exception as e:
            print(f"  ❌ {file_path}: {e}")


def run_quality_checks():
    """运行质量检查"""
    print("\n🔍 运行质量检查...")

    import subprocess

    # 1. ruff检查
    print("\n  运行ruff检查...")
    try:
        result = subprocess.run(
            ["python", "-m", "ruff", "check", "src/utils/dict_utils.py", "--no-fix"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("    ✅ ruff检查通过")
        else:
            print("    ⚠️ ruff发现问题")
    except Exception as e:
        print(f"    ❌ ruff检查失败: {e}")

    # 2. 测试检查
    print("\n  运行基础测试...")
    try:
        result = subprocess.run(
            [
                "python",
                "-m",
                "pytest",
                "tests/unit/utils/test_dict_utils_basic.py",
                "-q",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("    ✅ 基础测试通过")
        else:
            print("    ⚠️ 测试失败")
    except Exception as e:
        print(f"    ❌ 测试运行失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("           快速质量修复工具")
    print("=" * 60)

    fix_specific_files()
    add_missing_imports()
    run_quality_checks()

    print("\n" + "=" * 60)
    print("✅ 快速修复完成！")
    print("\n💡 下一步：")
    print("1. 运行 'python -m pytest tests/unit/utils/test_dict_utils*.py'")
    print("2. 运行 'python -m mypy src/utils/dict_utils.py'")
    print("3. 运行 'python -m ruff format src/'")
    print("=" * 60)


if __name__ == "__main__":
    main()
