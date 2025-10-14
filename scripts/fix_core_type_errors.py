#!/usr/bin/env python3
"""
修复核心模块的 MyPy 类型错误
第一阶段：修复阻塞性错误，确保 pre-push 通过
"""

import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import sys

PROJECT_ROOT = Path(__file__).parent.parent

# 核心模块列表
CORE_MODULES = [
    "src/core",
    "src/services",
    "src/api",
    "src/domain",
    "src/repositories",
    "src/database/repositories",
]

# 错误类型和修复策略
ERROR_FIXES = {
    # 1. 未定义的变量
    "name_defined": {
        "pattern": r"\b_result\b(?!\s*#)",
        "replacement": "result",
        "description": "修复 _result -> result",
    },
    # 2. 属性名错误
    "attr_defined": {
        "patterns": [
            (r"\.stats\b(?!\s*#)", "._stats"),
            (r"\._stats\b(?=\s*#)", ".stats"),
        ],
        "description": "修复 _stats -> stats",
    },
    # 3. 关键字参数错误
    "call-arg": {
        "patterns": [
            (r"_data\s*=", "data="),
            (r"_metadata\s*=", "metadata="),
            (r"_config\s*=", "config="),
        ],
        "description": "修复私有参数名",
    },
    # 4. Optional 类型问题
    "assignment": {
        "pattern": r"(\w+):\s*Optional\[(.+?)\]\s*=\s*None",
        "replacement": r"\1: Optional[\2] | None",
        "description": "修复 Optional 类型默认值",
    },
    # 5. 缺少类型注解
    "no-untyped-def": {
        "pattern": r"def\s+(\w+)\s*\([^)]*\)\s*:\s*$",
        "replacement": r"def \1\2) -> None:",
        "description": "添加 -> None 返回类型",
    },
}

# 文件特定的修复
FILE_FIXES = {
    "src/domain/models/team.py": [
        (r"\b_result\b", "result", "修复 _result -> result"),
        (r"stats\s*=", "stats", "修复 _stats -> stats"),
    ],
    "src/adapters/registry_simple.py": [
        (
            r"name:\s*Optional\[str\]\s*=\s*None",
            "name: str | None = None",
            "修复 Optional 默认值",
        ),
    ],
    "src/cqrs/dto.py": [
        (r"_data\s*=", "data=", "修复 _data -> data"),
    ],
    "src/facades/base.py": [
        (r"\bresult\b", "result", "修复 result -> result"),
    ],
}


def fix_file_errors(file_path: Path) -> Dict[str, int]:
    """修复单个文件的错误"""
    content = file_path.read_text(encoding="utf-8")
    original_content = content
    fixes_applied = {
        "name_defined": 0,
        "attr_defined": 0,
        "call-arg": 0,
        "assignment": 0,
        "no-untyped-def": 0,
    }

    # 应用文件特定修复
    if str(file_path) in FILE_FIXES:
        for pattern, replacement, desc in FILE_FIXES[str(file_path)]:
            old_count = len(re.findall(pattern, content))
            content = re.sub(pattern, replacement, content)
            new_count = len(re.findall(pattern, content))
            fixes_applied["file_specific"] = fixes_applied.get("file_specific", 0) + (
                old_count - new_count
            )

    # 应用通用错误修复
    for error_type, fix_info in ERROR_FIXES.items():
        if error_type == "attr_defined" and "patterns" in fix_info:
            # 特殊处理 attr-defined
            for pattern, replacement in fix_info["patterns"]:
                old_count = len(re.findall(pattern, content))
                content = re.sub(pattern, replacement, content)
                new_count = len(re.findall(pattern, content))
                fixes_applied[error_type] = fixes_applied.get(error_type, 0) + (
                    old_count - new_count
                )
        elif error_type == "call-arg" and "patterns" in fix_info:
            # 特殊处理 call-arg
            for pattern, replacement in fix_info["patterns"]:
                old_count = len(re.findall(pattern, content))
                content = re.sub(pattern, replacement, content)
                new_count = len(re.findall(pattern, content))
                fixes_applied[error_type] = fixes_applied.get(error_type, 0) + (
                    old_count - new_count
                )
        else:
            # 标准处理
            if "pattern" in fix_info:
                old_count = len(re.findall(fix_info["pattern"], content))
                if "replacement" in fix_info:
                    content = re.sub(
                        fix_info["pattern"], fix_info["replacement"], content
                    )
                    new_count = len(re.findall(fix_info["pattern"], content))
                    fixes_applied[error_type] = fixes_applied.get(error_type, 0) + (
                        old_count - new_count
                    )

    # 写回文件
    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        print(f"✓ 修复 {file_path.relative_to(PROJECT_ROOT)}")

    return fixes_applied


def fix_import_errors(file_path: Path) -> int:
    """修复导入错误"""
    content = file_path.read_text(encoding="utf-8")

    # 添加缺少的导入
    imports_to_add = []

    # 检查并添加常用导入
    if "Decimal(" in content and "from decimal import" not in content:
        imports_to_add.append("from decimal import Decimal")

    if "datetime" in content and "from datetime import" not in content:
        imports_to_add.append("from datetime import datetime, date, timedelta")

    if "Optional[" in content and "from typing import Optional" not in content:
        # 检查是否已有 typing 导入
        if "from typing import" in content:
            # 添加到现有导入
            content = re.sub(
                r"from typing import ([^\n]+)",
                lambda m: f"from typing import {m.group(1)}, Optional",
                content,
            )
        else:
            imports_to_add.append("from typing import Optional")

    # 写入导入
    if imports_to_add:
        lines = content.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import "):
                insert_idx = i + 1
            elif line.strip() == "" and insert_idx > 0:
                break

        for imp in reversed(imports_to_add):
            lines.insert(insert_idx, imp)

        content = "\n".join(lines)
        file_path.write_text(content, encoding="utf-8")
        print(f"  ✓ 添加导入到 {file_path.relative_to(PROJECT_ROOT)}")
        return len(imports_to_add)

    return 0


def analyze_ast_for_type_annotations(file_path: Path) -> Dict[str, int]:
    """使用 AST 分析类型注解"""
    content = file_path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(content)
    except:
        return {"functions": 0, "classes": 0, "methods": 0}

    stats = {"functions": 0, "classes": 0, "methods": 0}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            stats["functions"] += 1
            # 检查返回类型注解
            if node.returns:
                stats["with_return_type"] = stats.get("with_return_type", 0) + 1
            else:
                stats["without_return_type"] = stats.get("without_return_type", 0) + 1
        elif isinstance(node, ast.ClassDef):
            stats["classes"] += 1
        elif isinstance(node, ast.AsyncFunctionDef):
            stats["functions"] += 1
            if node.returns:
                stats["with_return_type"] = stats.get("with_return_type", 0) + 1
            else:
                stats["without_return_type"] = stats.get("without_return_type", 0) + 1

    return stats


def main():
    print("🔧 修复核心模块类型错误")
    print("=" * 50)

    total_fixes = {k: 0 for k in ERROR_FIXES.keys()}
    total_files = 0

    # 查找所有核心模块的 Python 文件
    for module in CORE_MODULES:
        module_path = PROJECT_ROOT / module
        if not module_path.exists():
            continue

        for py_file in module_path.glob("**/*.py"):
            # 跳过 __init__.py
            if py_file.name == "__init__.py":
                continue

            print(f"\n📄 处理: {py_file.relative_to(PROJECT_ROOT)}")

            # 分析类型注解状态
            before_stats = analyze_ast_for_type_annotations(py_file)

            # 修复错误
            fixes = fix_file_errors(py_file)

            # 修复导入错误
            fix_import_errors(py_file)

            # 添加 type注解
            add_annotations(py_file)

            # 再次分析
            after_stats = analyze_ast_for_type_annotations(py_file)

            total_files += 1
            for k, v in fixes.items():
                total_fixes[k] += v

            # 打印改进
            if before_stats["without_return_type"] > 0:
                improvement = before_stats["without_return_type"] - after_stats.get(
                    "without_return_type", 0
                )
                if improvement > 0:
                    print(f"  ✓ 添加了 {improvement} 个返回类型注解")

    print("\n" + "=" * 50)
    print("📊 修复统计")
    print("=" * 50)

    for error_type, count in total_fixes.items():
        if count > 0:
            print(f"  • {error_type}: {count} 个")

    print(f"\n📁 处理文件数: {total_files}")

    # 验证修复效果
    print("\n🔍 验证修复效果...")

    # 运行 MyPy 检查
    import subprocess

    cmd = (
        ["mypy"]
        + [str(PROJECT_ROOT / m) for m in CORE_MODULES]
        + ["--no-error-summary", "--show-error-codes"]
    )
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("\n✅ 成功！核心模块类型检查通过！")
        return 0
    else:
        errors = result.stdout.count("error:")
        print(f"\n⚠️  还有 {errors} 个错误需要手动处理")

        # 显示前几个错误
        error_lines = [line for line in result.stdout.split("\n") if "error:" in line][
            :10
        ]
        for error in error_lines:
            print(f"  • {error}")

        return 1


def add_annotations(file_path: Path):
    """为函数添加类型注解"""
    content = file_path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(content)
    except:
        return

    # 需要添加类型注解的函数列表
    functions_to_fix = []

    class TypeAnnotator(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            if not node.returns and not node.name.startswith("_"):
                functions_to_fix.append(node)
            return self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            if not node.returns and not node.name.startswith("_"):
                functions_to_fix.append(node)
            return self.generic_visit(node)

    analyzer = TypeAnnotator()
    analyzer.visit(tree)

    if functions_to_fix:
        lines = content.split("\n")

        for func in sorted(functions_to_fix, key=lambda n: n.lineno):
            line_idx = func.lineno - 1
            if line_idx < len(lines):
                line = lines[line_idx]

                # 添加 -> None 类型注解
                if ":" in line and "->" not in line:
                    lines[line_idx] = line + " -> None:"
                elif line.strip().endswith(":"):
                    lines[line_idx] = line[:-1] + " -> None:"

        content = "\n".join(lines)
        file_path.write_text(content, encoding="utf-8")
        print(f"  ✓ 为 {len(functions_to_fix)} 个函数添加了类型注解")


if __name__ == "__main__":
    sys.exit(main())
