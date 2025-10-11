#!/usr/bin/env python3
"""
批量修复 logger 未定义错误
"""

import os
import re
from pathlib import Path
from typing import List, Set


def fix_logger_in_file(file_path: Path) -> bool:
    """修复单个文件中的 logger 未定义错误"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # 检查是否已经导入了 logging
    has_logging_import = "import logging" in content or "from logging import" in content

    # 检查是否已经定义了 logger
    has_logger_def = "logger = logging.getLogger" in content or "logger =" in content

    # 如果有 logger 未定义的错误
    if 'Name "logger" is not defined' in content or re.search(r"\blogger\b", content):
        if not has_logging_import:
            # 添加 logging 导入
            lines = content.split("\n")

            # 找到合适的位置插入导入
            import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    import_idx = i + 1
                elif line.strip() == "" and import_idx > 0:
                    break

            # 插入 logging 导入
            lines.insert(import_idx, "import logging")
            content = "\n".join(lines)

        if not has_logger_def:
            # 在类或模块开始处添加 logger 定义
            lines = content.split("\n")

            # 如果是类文件
            if "class " in content:
                # 找到第一个类
                class_idx = None
                for i, line in enumerate(lines):
                    if line.startswith("class "):
                        class_idx = i
                        break

                if class_idx is not None:
                    # 在类的第一个方法前添加 logger
                    method_idx = class_idx + 1
                    while method_idx < len(lines) and (
                        lines[method_idx].startswith('"""')
                        or lines[method_idx].strip() == ""
                        or lines[method_idx].strip().startswith("#")
                    ):
                        method_idx += 1

                    if method_idx < len(lines) and (
                        "def " in lines[method_idx] or "async def " in lines[method_idx]
                    ):
                        # 在方法前添加 logger
                        indent = "    "
                        lines.insert(
                            method_idx, f"{indent}logger = logging.getLogger(__name__)"
                        )
                        content = "\n".join(lines)
            else:
                # 模块级别 logger
                # 在第一个函数或类定义前添加
                def_idx = 0
                for i, line in enumerate(lines):
                    if (
                        line.startswith("def ")
                        or line.startswith("async def ")
                        or line.startswith("class ")
                    ):
                        def_idx = i
                        break

                if def_idx > 0:
                    lines.insert(def_idx, "logger = logging.getLogger(__name__)")
                    content = "\n".join(lines)
                else:
                    # 添加到文件末尾
                    lines.append("\nlogger = logging.getLogger(__name__)")
                    content = "\n".join(lines)

    # 如果内容有修改，写回文件
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    return False


def main():
    """主函数"""
    print("🔧 开始修复 logger 未定义错误\n")

    # 从 MyPy 输出中获取需要修复的文件
    result = os.popen(
        'mypy src 2>&1 | grep "logger" | grep "not defined" | cut -d: -f1 | sort -u'
    ).read()
    error_files = [line.strip() for line in result.split("\n") if line.strip()]

    print(f"找到 {len(error_files)} 个需要修复的文件")

    fixed_count = 0
    for file_path in error_files:
        if os.path.exists(file_path):
            print(f"📝 修复文件: {file_path}")
            if fix_logger_in_file(Path(file_path)):
                print("   ✅ 已修复")
                fixed_count += 1
            else:
                print("   ⚪ 无需修复")
        else:
            print(f"   ❌ 文件不存在: {file_path}")

    print(f"\n✅ 完成！共修复了 {fixed_count} 个文件")

    # 验证修复效果
    print("\n🔍 验证修复效果...")
    result = (
        os.popen('mypy src 2>&1 | grep "logger" | grep "not defined" | wc -l')
        .read()
        .strip()
    )
    remaining = int(result) if result else 0

    if remaining == 0:
        print("\n🎉 所有 logger 错误都已修复！")
    else:
        print(f"\n⚠️  还有 {remaining} 个 logger 错误需要手动修复")


if __name__ == "__main__":
    main()
