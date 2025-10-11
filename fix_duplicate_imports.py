#!/usr/bin/env python3
"""
修复重复导入错误（F811）
"""

import os
import re
import subprocess


def fix_duplicate_imports(filepath):
    """修复单个文件中的重复导入"""
    print(f"处理: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        lines = content.split("\n")

        # 记录已经导入的名称
        imported_names = {}
        new_lines = []

        for line in lines:
            stripped = line.strip()

            # 检查是否是导入语句
            if stripped.startswith(("from ", "import ")):
                # 提取导入的名称
                if stripped.startswith("from "):
                    # from x import y, z
                    match = re.match(r"from\s+[^\s]+\s+import\s+(.+)", stripped)
                    if match:
                        imports = match.group(1)
                        # 处理多个导入
                        names = [
                            name.strip().split(" as ")[0] for name in imports.split(",")
                        ]
                        duplicate_found = False

                        for name in names:
                            if name in imported_names:
                                # 找到重复导入
                                duplicate_found = True
                                # 检查是否在 ignore 列表中
                                if name in [
                                    "Dict",
                                    "List",
                                    "Optional",
                                    "Union",
                                    "Tuple",
                                    "Set",
                                    "Any",
                                ]:
                                    # 删除这行
                                    print(f"  删除重复导入: {stripped}")
                                    break
                        else:
                            # 没有重复，保留
                            for name in names:
                                imported_names[name] = line
                            new_lines.append(line)

                        if not duplicate_found:
                            new_lines.append(line)
                else:
                    # import x, y
                    match = re.match(r"import\s+(.+)", stripped)
                    if match:
                        imports = match.group(1)
                        names = [
                            name.strip().split(" as ")[0] for name in imports.split(",")
                        ]
                        duplicate_found = False

                        for name in names:
                            if name in imported_names:
                                duplicate_found = True
                                break
                        else:
                            for name in names:
                                imported_names[name] = line
                            new_lines.append(line)

                        if not duplicate_found:
                            new_lines.append(line)
            else:
                new_lines.append(line)

        content = "\n".join(new_lines)

        # 写回文件
        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print("  ✅ 已修复")
            return True
        else:
            print("  - 无需修复")
            return False

    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


def main():
    """主函数"""
    # 获取所有有 F811 错误的文件
    result = subprocess.run(
        ["ruff", "check", "--select=F811", "--output-format=concise"],
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
        if fix_duplicate_imports(filepath):
            fixed_count += 1

    print("=" * 60)
    print(f"✅ 修复了 {fixed_count} 个文件")

    # 验证修复结果
    print("\n验证修复结果...")
    result = subprocess.run(
        ["ruff", "check", "--select=F811"], capture_output=True, text=True
    )

    remaining = len(result.stdout.split("\n")) if result.stdout.strip() else 0
    print(f"剩余 {remaining} 个 F811 错误")

    if remaining > 0:
        print("\n前 10 个错误:")
        for line in result.stdout.split("\n")[:10]:
            if line:
                print(f"  {line}")


if __name__ == "__main__":
    main()
