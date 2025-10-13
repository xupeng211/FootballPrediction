#!/usr/bin/env python3
"""
查找超过50行的函数
"""

import ast
from pathlib import Path
from typing import List, Tuple


def analyze_function_lengths(file_path: Path) -> List[Tuple[str, int, int]]:
    """分析文件中的函数长度"""
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
        except Exception:
            return []

    functions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 计算函数行数
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line
            lines = end_line - start_line + 1

            if lines > 50:
                functions.append((node.name, lines, start_line))

    return functions


def main():
    """主函数"""
    print("=" * 80)
    print("🔍 查找超过50行的函数")
    print("=" * 80)

    long_functions = []
    src_path = Path("src")

    for py_file in src_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        functions = analyze_function_lengths(py_file)
        for func_name, lines, line_num in functions:
            long_functions.append((str(py_file), func_name, lines, line_num))

    # 按行数排序
    long_functions.sort(key=lambda x: x[2], reverse=True)

    print(f"\n找到 {len(long_functions)} 个超过50行的函数:\n")

    for file_path, func_name, lines, line_num in long_functions[:20]:  # 只显示前20个
        rel_path = file_path.replace("src/", "")
        print(f"  {lines:3d} 行 - {rel_path}:{func_name} (第{line_num}行)")

    if len(long_functions) > 20:
        print(f"\n... 还有 {len(long_functions) - 20} 个长函数")

    # 统计最需要重构的文件
    print("\n📊 最需要重构的文件:")
    file_count = {}
    for file_path, _, _, _ in long_functions:
        file_count[file_path] = file_count.get(file_path, 0) + 1

    for file_path, count in sorted(
        file_count.items(), key=lambda x: x[1], reverse=True
    )[:10]:
        rel_path = file_path.replace("src/", "")
        print(f"  {count} 个长函数 - {rel_path}")

    # 生成报告
    if long_functions:
        print("\n📝 生成重构建议...")
        with open("long_functions_report.txt", "w", encoding="utf-8") as f:
            f.write("超过50行的函数列表\n")
            f.write("=" * 80 + "\n\n")

            for file_path, func_name, lines, line_num in long_functions:
                rel_path = file_path.replace("src/", "")
                f.write(f"{lines:3d} 行 - {rel_path}:{func_name} (第{line_num}行)\n")

        print("  ✅ 报告已保存到: long_functions_report.txt")


if __name__ == "__main__":
    main()
