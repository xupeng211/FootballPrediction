#!/usr/bin/env python3
"""
自动替换print为logger的脚本
"""

import re
import os
from pathlib import Path
from typing import List, Tuple, Dict


def replace_print_in_file(file_path: Path) -> Tuple[int, List[str]]:
    """替换单个文件中的print语句"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # 如果编码问题，跳过
        return 0, []

    # 检查是否已经导入logger
    has_logging = "import logging" in content or "from logging import" in content
    logger_name = None

    if has_logging:
        # 查找logger实例名称
        logger_match = re.search(r"(\w+)\s*=\s*logging\.getLogger", content)
        if logger_match:
            logger_name = logger_match.group(1)

    changes = []
    lines = content.split("\n")
    new_lines = []
    modified = False

    for i, line in enumerate(lines, 1):
        # 跳过注释中的print
        if line.strip().startswith("#"):
            new_lines.append(line)
            continue

        # 查找print语句（排除pprint和已有logger调用）
        print_pattern = r"(?:[^\w]|^)\bprint\s*\("
        if re.search(print_pattern, line):
            # 匹配print调用
            print_match = re.search(r"print\s*\((.*?)\)", line)
            if print_match:
                # 检查是否是logger调用（避免修改已有的logger.info等）
                if "logger." not in line and "pprint" not in line:
                    print_content = print_match.group(1)

                    # 如果还没有logger，添加导入
                    if not has_logging:
                        # 在文件开头添加logging导入
                        if not new_lines or i < 20:
                            new_lines.insert(0, "import logging")
                            new_lines.insert(1, "logger = logging.getLogger(__name__)")
                            new_lines.insert(2, "")
                            has_logging = True
                            logger_name = "logger"
                            modified = True

                    # 转换为logger调用
                    # 简单判断：如果是f-string，使用info；如果是字符串字面量，也使用info
                    if 'f"' in print_content or "f'" in print_content:
                        # f-string格式
                        new_line = line.replace(
                            f"print({print_content})",
                            f'{logger_name or "logger"}.info({print_content})',
                        )
                    else:
                        # 普通字符串或其他
                        new_line = line.replace(
                            f"print({print_content})",
                            f'{logger_name or "logger"}.info({print_content})',
                        )

                    new_lines.append(new_line)
                    changes.append(f"Line {i}: {line.strip()} → {new_line.strip()}")
                    modified = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))

    return len(changes), changes


def main():
    """主函数"""
    src_dir = Path("src")
    total_changes = 0
    files_modified = 0

    print("🔄 开始替换print为logger...")
    print()

    # 遍历所有Python文件
    py_files = list(src_dir.rglob("*.py"))

    for py_file in py_files:
        # 跳过__pycache__
        if "__pycache__" in str(py_file):
            continue

        # 跳过刚创建的简化模块
        if "mod.py" in py_file.name and "services/audit_service_mod.py" != str(py_file):
            continue

        count, changes = replace_print_in_file(py_file)
        if count > 0:
            files_modified += 1
            total_changes += count
            print(f"✅ {py_file}: {count}处修改")
            for change in changes[:3]:  # 只显示前3个
                print(f"   {change}")
            if len(changes) > 3:
                print(f"   ... 还有{len(changes) - 3}处修改")
            print()

    print("📊 总结:")
    print(f"  - 修改文件数: {files_modified}")
    print(f"  - 总替换数: {total_changes}")
    print()
    print("✅ 完成！")

    if total_changes > 0:
        print("\n建议运行以下命令检查:")
        print("  make lint")
        print("  make test-quick")


if __name__ == "__main__":
    main()
