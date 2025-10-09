#!/usr/bin/env python3
"""
修复star import (F403/F405) 错误的脚本
"""

import os
import re
from pathlib import Path


def fix_star_imports(filepath):
    """修复单个文件的star import"""
    print(f"检查: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 修复相对导入中的star import
        # 例如: from .module import * -> from .module import specific_name1, specific_name2
        lines = content.split("\n")
        new_lines = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # 查找star import
            if line.startswith("from ") and line.endswith(" import *"):
                # 获取模块路径
                module_path = line.replace("from ", "").replace(" import *", "")

                # 查找下一行的__all__定义
                all_names = []
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if next_line.startswith("__all__"):
                        # 提取__all__中的名称
                        all_match = re.search(
                            r"__all__\s*=\s*\[(.*?)\]", next_line, re.DOTALL
                        )
                        if all_match:
                            all_content = all_match.group(1)
                            # 提取双引号或单引号中的名称
                            names = re.findall(r'["\']([^"\']+)["\']', all_content)
                            all_names = [n.strip() for n in names if n.strip()]
                        break
                    j += 1

                # 如果找到了名称列表，替换star import
                if all_names:
                    # 限制导入数量，如果太多则保持star import但添加__all__
                    if len(all_names) <= 10:
                        new_line = f"from {module_path} import {', '.join(all_names)}"
                        new_lines.append(new_line)
                        # 跳过__all__定义（如果有）
                        if j < len(lines) and lines[j].strip().startswith("__all__"):
                            # 保持__all__但移除已导入的名称
                            remaining = [n for n in all_names if n not in all_names]
                            if remaining:
                                all_str = ", ".join(f'"{n}"' for n in remaining)
                                new_lines.append(f"__all__ = [{all_str}]")
                            i = j + 1
                        else:
                            i += 1
                    else:
                        # 如果太多名称，保持star import但添加__all__（如果还没有）
                        new_lines.append(line)
                        if j >= len(lines) or not lines[j].strip().startswith(
                            "__all__"
                        ):
                            all_str = ", ".join(f'"{n}"' for n in all_names)
                            new_lines.append(f"__all__ = [{all_str}]")
                            i = j + 1
                        else:
                            i += 1
                else:
                    # 无法确定导入名称，添加type: ignore注释
                    new_line = line + "  # type: ignore"
                    new_lines.append(new_line)
                    i += 1
            else:
                new_lines.append(lines[i])
                i += 1

        content = "\n".join(new_lines)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  ✅ 修复了 {filepath}")
            return True
        else:
            print(f"  - 无需修复 {filepath}")
            return False

    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


def main():
    """主函数"""
    import subprocess

    # 获取所有有F403/F405错误的文件
    result = subprocess.run(
        ["ruff", "check", "--select=F403,F405", "--output-format=concise"],
        capture_output=True,
        text=True,
    )

    files = set()
    for line in result.stdout.split("\n"):
        if line:
            filepath = line.split(":")[0]
            if os.path.exists(filepath):
                files.add(filepath)

    print(f"找到 {len(files)} 个需要修复的文件")
    print("=" * 60)

    fixed_count = 0
    for filepath in sorted(files):
        if fix_star_imports(filepath):
            fixed_count += 1

    print("=" * 60)
    print(f"✅ 修复了 {fixed_count} 个文件")

    # 验证修复结果
    print("\n验证修复结果...")
    result = subprocess.run(
        ["ruff", "check", "--select=F403,F405"], capture_output=True, text=True
    )

    remaining = len(result.stdout.split("\n")) if result.stdout.strip() else 0
    print(f"剩余 {remaining} 个F403/F405错误")


if __name__ == "__main__":
    main()
