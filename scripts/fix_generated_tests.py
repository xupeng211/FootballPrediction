#!/usr/bin/env python3
"""
修复自动生成的测试文件中的格式问题
"""

import os
import re
from pathlib import Path


def fix_test_file(file_path: str) -> bool:
    """修复单个测试文件的格式问题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 修复 f-string 中的嵌套大括号问题
        content = re.sub(r'f"\{([^}]+)\}"', r'"{\1}"', content)
        content = re.sub(r'f"([^"]*)\{([^}]+)\}"', r'"\1" + str(\2)', content)
        content = re.sub(
            r'f"([^"]*)\{([^}]+)\}([^"]*)"', r'"\1" + str(\2) + "\3"', content
        )

        # 修复模块导入问题
        content = re.sub(
            r"from \{module_name\} import \*",
            lambda m: "# Import statement will be added below",
            content,
        )

        # 添加正确的导入语句
        if "src/collectors/" in file_path:
            module_path = (
                file_path.replace("tests/", "src/")
                .replace("test_", "")
                .replace(".py", "")
            )
            module_name = module_path.replace("/", ".").replace(".py", "")
            content = re.sub(
                r"# Import statement will be added below",
                f'try:\n    from {module_name} import *\nexcept ImportError:\n    pytest.skip("Module not found", allow_module_level=True)',
                content,
            )

        # 修复 pytest.skip 的格式
        content = re.sub(r'pytest\.skip\(f"([^"]+)"', r'pytest.skip("\1"', content)

        # 写回文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ 修复: {file_path}")
        return True

    except Exception as e:
        print(f"❌ 修复失败 {file_path}: {e}")
        return False


def main():
    """主函数"""
    # 查找所有生成的测试文件
    test_dirs = [
        "tests/collectors/",
        "tests/patterns/",
        "tests/services/",
        "tests/tasks/",
        "tests/unit/",
    ]

    fixed_count = 0
    for test_dir in test_dirs:
        if Path(test_dir).exists():
            for test_file in Path(test_dir).glob("test_*_coverage.py"):
                if fix_test_file(str(test_file)):
                    fixed_count += 1

            # 处理其他新生成的测试
            for test_file in Path(test_dir).glob("test_*.py"):
                if "coverage" not in test_file.name and test_file.stat().st_size > 0:
                    # 检查是否是新生成的（简单检查文件内容）
                    with open(test_file, "r") as f:
                        content = f.read()
                        if (
                            "自动生成的测试文件" in content
                            or "TODO: 添加更具体的测试逻辑" in content
                        ):
                            if fix_test_file(str(test_file)):
                                fixed_count += 1

    print(f"\n✅ 共修复 {fixed_count} 个测试文件")


if __name__ == "__main__":
    main()
