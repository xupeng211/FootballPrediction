#!/usr/bin/env python3
"""
快速修复最常见的 MyPy 错误
"""

import re
import subprocess
from pathlib import Path


def fix_file(file_path: str):
    """修复单个文件的常见 MyPy 错误"""
    path = Path(file_path)

    if not path.exists():
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # 1. 添加缺失的导入
        imports_to_add = []

        # 检查 logging
        if "logging.getLogger" in content and "import logging" not in content:
            imports_to_add.append("import logging")

        # 检查 os
        if re.search(r"\bos\.", content) and "import os" not in content:
            imports_to_add.append("import os")

        # 检查 datetime
        if (
            "datetime.now()" in content
            and "from datetime import" not in content
            and "import datetime" not in content
        ):
            imports_to_add.append("from datetime import datetime")

        # 检查 typing
        typing_needed = []
        for typ in ["Dict", "List", "Optional", "Any", "Union"]:
            if (
                re.search(rf"\b{typ}\b", content)
                and f"from typing import {typ}" not in content
            ):
                typing_needed.append(typ)

        if typing_needed:
            imports_to_add.append(f'from typing import {", ".join(typing_needed)}')

        # 2. 添加导入
        if imports_to_add:
            lines = content.split("\n")
            # 找到合适的位置插入导入
            insert_idx = 0
            for i, line in enumerate(lines):
                if (
                    line.strip()
                    and not line.startswith("#")
                    and not line.startswith('"""')
                    and not line.startswith("'''")
                ):
                    insert_idx = i
                    break

            for imp in imports_to_add:
                lines.insert(insert_idx, imp)
                insert_idx += 1

            content = "\n".join(lines)

        # 3. 修复变量类型注解
        lines = content.split("\n")
        for i, line in enumerate(lines):
            # result = {"error": []} -> result: Dict[str, List] = {"error": []}
            if re.match(r"^(\s+)(\w+) = \{", line) and ":" not in line.split("=")[0]:
                if "Dict" in content or "Any" in content:
                    lines[i] = re.sub(
                        r"^(\s+)(\w+) = \{", r"\1\2: Dict[str, Any] = {", line
                    )

            # result = [] -> result: List[Any] = []
            if re.match(r"^(\s+)(\w+) = \[\]$", line) and ":" not in line.split("=")[0]:
                if "List" in content or "Any" in content:
                    lines[i] = re.sub(
                        r"^(\s+)(\w+) = \[\]$", r"\1\2: List[Any] = []", line
                    )

        content = "\n".join(lines)

        # 4. 写回文件
        if content != original:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ 修复: {file_path}")
            return True

    except Exception as e:
        print(f"❌ 错误: {file_path} - {e}")

    return False


def main():
    """主函数"""
    print("🔧 快速修复 MyPy 错误...")

    # 需要修复的文件列表（根据错误统计）
    files_to_fix = [
        "src/data/quality/data_quality_monitor.py",
        "src/data/quality/prometheus.py",
        "src/utils/time_utils.py",
        "src/data/storage/lake.py",
        "src/cqrs/handlers.py",
        "src/services/processing/processors/match_processor.py",
        "src/facades/facades.py",
        "src/events/types.py",
    ]

    fixed = 0
    for file_path in files_to_fix:
        if fix_file(file_path):
            fixed += 1

    print(f"\n✨ 完成！修复了 {fixed} 个文件")

    # 验证编译
    print("\n🔍 验证修复结果...")
    for file_path in files_to_fix[:3]:  # 验证前3个
        if Path(file_path).exists():
            result = subprocess.run(
                ["python", "-m", "py_compile", file_path], capture_output=True
            )
            if result.returncode == 0:
                print(f"✅ {file_path} 编译成功")
            else:
                print(f"❌ {file_path} 仍有错误")

    # 统计剩余错误
    print("\n📊 统计剩余错误...")
    result = subprocess.run(["mypy", "src/"], capture_output=True, text=True)
    error_count = result.stdout.count("error:")
    print(f"当前 MyPy 错误数: {error_count}")


if __name__ == "__main__":
    main()
