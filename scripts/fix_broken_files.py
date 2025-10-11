#!/usr/bin/env python3
"""
修复被破坏的文件
Fix files broken by import organization script
"""

import re
from pathlib import Path


def fix_file_syntax(file_path: Path) -> bool:
    """修复单个文件的语法错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        return False

    original_content = content

    # 1. 移除函数/类中间的import语句
    # 找到所有被错误放置的import语句
    lines = content.splitlines()
    new_lines = []
    i = 0

    # 收集所有的import语句
    top_imports = []
    in_function_or_class = False
    indent_level = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 检查是否是函数或类定义
        if (
            stripped.startswith("def ")
            or stripped.startswith("class ")
            or stripped.startswith("async def ")
        ):
            in_function_or_class = True
            indent_level = len(line) - len(stripped)
        elif (
            in_function_or_class
            and stripped
            and not line.startswith(" " * (indent_level + 1))
        ):
            # 检查是否退出了函数/类
            if len(line) - len(stripped) <= indent_level:
                in_function_or_class = False

        # 如果在函数/类内部且是import语句，跳过
        if in_function_or_class and (
            stripped.startswith("import ") or stripped.startswith("from ")
        ):
            # 记录这个import以便后续添加到文件顶部
            top_imports.append(line)
            i += 1
            continue

        # 处理语法错误：未闭合的括号
        if stripped.startswith("from ") and i > 0:
            # 检查前面是否有未闭合的函数调用
            prev_lines = new_lines[-10:] if new_lines else []
            for prev_line in reversed(prev_lines):
                prev_stripped = prev_line.strip()
                if prev_stripped.endswith(","):
                    # 找到了未闭合的调用，需要添加闭合括号
                    if "(" in prev_line:
                        # 在括号后添加)
                        new_lines[-1] = prev_line.rstrip() + ")"
                    break
                elif prev_stripped and not prev_line.startswith(" "):
                    break

        new_lines.append(line)
        i += 1

    # 2. 将收集的import添加到文件顶部
    if top_imports:
        # 找到第一个非import、非注释、非空行的位置
        insert_pos = 0
        for j, line in enumerate(new_lines):
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith("#")
                and not stripped.startswith('"""')
                and not stripped.startswith("'''")
            ):
                if not (stripped.startswith("import ") or stripped.startswith("from ")):
                    insert_pos = j
                    break

        # 在该位置插入imports
        # 按类型分组
        stdlib_imports = []
        thirdparty_imports = []
        local_imports = []

        for imp in top_imports:
            imp_stripped = imp.strip()
            if imp_stripped.startswith("from ."):
                local_imports.append(imp)
            elif any(
                imp_stripped.startswith(f"import {lib}")
                or imp_stripped.startswith(f"from {lib}")
                for lib in [
                    "os",
                    "sys",
                    "time",
                    "datetime",
                    "json",
                    "logging",
                    "asyncio",
                    "pathlib",
                    "re",
                    "collections",
                    "itertools",
                    "functools",
                    "typing",
                    "uuid",
                    "hashlib",
                    "base64",
                    "urllib",
                    "http",
                    "socket",
                ]
            ):
                stdlib_imports.append(imp)
            elif imp_stripped.startswith("from src") or imp_stripped.startswith(
                "import src"
            ):
                local_imports.append(imp)
            else:
                thirdparty_imports.append(imp)

        # 排序并插入
        all_imports = []
        if stdlib_imports:
            all_imports.extend(sorted(set(stdlib_imports)))
            all_imports.append("")
        if thirdparty_imports:
            all_imports.extend(sorted(set(thirdparty_imports)))
            all_imports.append("")
        if local_imports:
            all_imports.extend(sorted(set(local_imports)))
            all_imports.append("")

        # 插入到合适位置
        final_lines = new_lines[:insert_pos] + all_imports + new_lines[insert_pos:]
    else:
        final_lines = new_lines

    # 3. 修复其他常见语法错误
    content = "\n".join(final_lines)

    # 修复未闭合的括号（简单情况）
    # 查找类似:   value=xxx,
    #              from yyy import zzz
    content = re.sub(r",\s*\n\s*from\s+\S+\s+import\s+\S+", ",", content)

    # 修复except块前有import的情况
    content = re.sub(
        r"(\s*)try:\s*\n\s*from\s+(\S+)\s+import\s+(\S+)",
        r"\1# Import moved to top\n\1try:",
        content,
    )

    # 写回文件
    if content != original_content:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ 修复 {file_path}")
            return True
        except Exception as e:
            print(f"写入文件失败 {file_path}: {e}")
            return False

    return False


def main():
    """主函数"""
    print("🔧 修复被破坏的文件...")

    src_path = Path("src")
    fixed_count = 0

    # 查找所有Python文件
    python_files = list(src_path.rglob("*.py"))
    print(f"找到 {len(python_files)} 个Python文件")

    for file_path in python_files:
        # 检查文件是否有语法错误
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            compile(content, str(file_path), "exec")
        except SyntaxError:
            # 有语法错误，尝试修复
            if fix_file_syntax(file_path):
                fixed_count += 1
        except Exception:
            pass

    print(f"\n✅ 完成！修复了 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
