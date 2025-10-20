#!/usr/bin/env python3
"""
修复所有测试错误的脚本
"""

import os
import re
from pathlib import Path


def fix_test_file(file_path: Path) -> bool:
    """修复单个测试文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # 1. 修复缺失的sys导入
        if "sys.modules" in content and "import sys" not in content:
            # 在第一个导入后添加sys导入
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    lines.insert(i + 1, "import sys")
                    break
            content = "\n".join(lines)

        # 2. 修复重复的Mock导入
        content = re.sub(
            r"# Mock module [^\n]+\nfrom unittest\.mock import Mock, patch\nsys\.modules\[\'[^\']+\'\] = Mock\(\n(?=.*# Mock module)",
            "",
            content,
        )

        # 3. 修复语法错误 - 删除孤立的except块
        content = re.sub(
            r"\n\s+except Exception:\s*\n\s+pytest\.skip\([^)]+\)\n",
            "\n        pass  # Skipped\n",
            content,
        )

        # 4. 修复缺失的IMPORT_MODULE变量
        if "IMPORT_MODULE" in content and "IMPORT_MODULE =" not in content:
            content = content.replace(
                "except ImportError:\n    IMPORT_SUCCESS = False",
                "except ImportError:\n    IMPORT_SUCCESS = False\n    IMPORT_MODULE = None",
            )

        # 5. 修复文件末尾缺少换行
        if content and not content.endswith("\n"):
            content += "\n"

        # 写回文件
        if content != original:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """主函数"""
    Path("tests/unit")

    # 找出所有有错误的文件

    # 先运行一次pytest找出错误
    print("🔍 查找有错误的测试文件...")

    # 根据已知的错误文件列表
    known_error_files = [
        "tests/unit/adapters/registry_test.py",
        "tests/unit/core/config_di_test.py",
        "tests/unit/core/di_test.py",
        "tests/unit/data/collectors/scores_collector_test.py",
        "tests/unit/database/test_sql_compatibility.py",
        "tests/unit/services/processing/caching/processing_cache_test.py",
        "tests/unit/utils/test_string_utils_comprehensive.py",
        "tests/unit/utils/test_validators_comprehensive.py",
        "tests/unit/utils/test_tasks_imports.py",
        "tests/unit/utils/test_coverage_boost.py",
        "tests/unit/utils/test_metrics_collector_fixed.py",
        "tests/unit/utils/test_simple_functional.py",
        "tests/unit/utils/test_metrics_collector.py",
        "tests/unit/utils/test_backup_tasks.py",
        "tests/unit/utils/test_data_collection_tasks.py",
        "tests/unit/utils/test_connection_fixed.py",
    ]

    fixed_count = 0
    for file_path in known_error_files:
        full_path = Path(file_path)
        if full_path.exists():
            print(f"修复: {file_path}")
            if fix_test_file(full_path):
                print("  ✅ 已修复")
                fixed_count += 1
            else:
                print("  ⚪ 无需修复")

    print(f"\n✨ 总共修复了 {fixed_count} 个文件")

    # 验证修复
    print("\n🧪 验证修复效果...")
    import subprocess

    result = subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "tests/unit/adapters/registry_test.py",
            "tests/unit/core/di_test.py",
            "-q",
        ],
        capture_output=True,
        text=True,
    )

    if "ERROR" not in result.stdout:
        print("✅ 修复成功！")
    else:
        print("❌ 仍有错误需要手动处理")
        print(result.stdout[:500])


if __name__ == "__main__":
    main()
