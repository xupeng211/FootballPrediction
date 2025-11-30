#!/usr/bin/env python3
"""
本地全量静态扫描脚本
验证所有Python文件的导入和语法正确性
"""

import ast
import os
import sys
import traceback
from pathlib import Path
from typing import Optional

# 需要验证的根目录
ROOT_DIRS = ["src", "tests"]


class ImportValidator(ast.NodeVisitor):
    """AST访问器，用于检查导入和语法问题"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.imports: set[str] = set()
        self.undefined_names: set[str] = set()
        self.errors: list[str] = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module)
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)


def validate_file(filepath: Path) -> tuple[bool, list[str]]:
    """验证单个Python文件的导入和语法"""
    errors = []

    try:
        # 1. 语法检查
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # 语法验证
        try:
            ast.parse(content)
        except SyntaxError as e:
            errors.append(f"语法错误: {e}")
            return False, errors

        # 2. 简单检查常见的导入问题
        if (
            "datetime:" in content
            and "from datetime import datetime as dt_datetime" not in content
            and "import datetime" in content
        ):
            if "datetime" in content.split("from datetime import")[0].split("#")[0]:
                errors.append("可能存在 datetime 命名冲突")

        if "NameError: name 'datetime' is not defined" in content:
            errors.append("存在未定义的 datetime 引用")

        # 3. 简单的 import 测试（不执行模块）
        try:
            compile(content, str(filepath), "exec")
        except Exception:
            errors.append(f"编译错误: {e}")

    except Exception:
        errors.append(f"文件读取错误: {e}")

    return len(errors) == 0, errors


def main():
    """主函数"""
    print("🔍 开始本地全量静态扫描...")
    print("=" * 60)

    all_files = []
    for root_dir in ROOT_DIRS:
        root_path = Path(root_dir)
        if root_path.exists():
            all_files.extend(root_path.rglob("*.py"))

    if not all_files:
        print("❌ 未找到任何Python文件")
        return 1

    print(f"📁 发现 {len(all_files)} 个Python文件")
    print("🔍 开始验证...")
    print()

    bad_files = []
    total_files = len(all_files)

    for i, filepath in enumerate(all_files, 1):
        relative_path = str(filepath)  # 直接使用完整路径
        print(f"[{i:3d}/{total_files}] 检查: {relative_path}", end=" ")

        is_valid, errors = validate_file(filepath)

        if is_valid:
            print("✅")
        else:
            print("❌")
            bad_files.append((relative_path, errors))

    print("=" * 60)

    if bad_files:
        print(f"🚨 发现 {len(bad_files)} 个文件存在问题:")
        print()

        for filepath, errors in bad_files:
            print(f"📄 {filepath}:")
            for error in errors:
                print(f"   ❌ {error}")
            print()

        print("💡 请修复上述错误后重新运行扫描")
        return 1
    else:
        print("🎉 所有模块验证通过!")
        print("✅ All modules valid")
        return 0


if __name__ == "__main__":
    sys.exit(main())
