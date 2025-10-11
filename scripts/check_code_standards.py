#!/usr/bin/env python3
"""
检查代码规范 - 命名规范和类型注解
"""

import ast
import re
from pathlib import Path
from typing import List, Tuple, Dict
from collections import defaultdict


class CodeStandardsChecker(ast.NodeVisitor):
    """代码规范检查器"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.issues = []
        self.stats = {
            "functions": 0,
            "functions_with_types": 0,
            "functions_with_docstrings": 0,
            "classes": 0,
            "classes_with_docstrings": 0,
            "variables": 0,
            "constants": 0,
        }

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """访问函数定义"""
        self.stats["functions"] += 1

        # 检查命名规范
        if not re.match(r"^[a-z_][a-z0-9_]*$", node.name):
            self.issues.append(
                {
                    "line": node.lineno,
                    "type": "function_name",
                    "message": f"函数名 '{node.name}' 应使用snake_case命名",
                    "severity": "warning",
                }
            )

        # 检查类型注解
        has_return_type = node.returns is not None
        has_arg_types = all(arg.annotation is not None for arg in node.args.args)

        if has_return_type or has_arg_types:
            self.stats["functions_with_types"] += 1
        else:
            self.issues.append(
                {
                    "line": node.lineno,
                    "type": "type_annotation",
                    "message": f"函数 '{node.name}' 缺少类型注解",
                    "severity": "info",
                }
            )

        # 检查文档字符串
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            self.stats["functions_with_docstrings"] += 1

        # 检查参数默认值
        for arg in node.args.defaults:
            if isinstance(arg, ast.Name) and arg.id == "None":
                # 检查对应的参数是否有Optional类型注解
                idx = node.args.defaults.index(arg)
                arg_idx = len(node.args.args) - len(node.args.defaults) + idx
                if arg_idx < len(node.args.args):
                    param = node.args.args[arg_idx]
                    if param.annotation:
                        # 简单检查是否包含Optional
                        if not (
                            "Optional" in ast.dump(param.annotation)
                            or "Union" in ast.dump(param.annotation)
                            or param.annotation is None
                        ):
                            self.issues.append(
                                {
                                    "line": node.lineno,
                                    "type": "optional_type",
                                    "message": f"参数 '{param.arg}' 默认值为None，应使用Optional类型",
                                    "severity": "info",
                                }
                            )

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """访问异步函数定义"""
        # 与普通函数相同的处理
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """访问类定义"""
        self.stats["classes"] += 1

        # 检查命名规范（PascalCase）
        if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
            self.issues.append(
                {
                    "line": node.lineno,
                    "type": "class_name",
                    "message": f"类名 '{node.name}' 应使用PascalCase命名",
                    "severity": "warning",
                }
            )

        # 检查文档字符串
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            self.stats["classes_with_docstrings"] += 1

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        """访问变量名"""
        if isinstance(node.ctx, ast.Store):
            self.stats["variables"] += 1

            # 检查常量命名（大写）
            if node.id.isupper():
                self.stats["constants"] += 1
            # 检查变量命名（snake_case）
            elif not re.match(r"^[a-z_][a-z0-9_]*$", node.id):
                # 跳过一些常见的例外
                exceptions = ["_", "__name__", "__main__", "__doc__", "__file__"]
                if node.id not in exceptions:
                    self.issues.append(
                        {
                            "line": node.lineno,
                            "type": "variable_name",
                            "message": f"变量名 '{node.id}' 应使用snake_case命名",
                            "severity": "info",
                        }
                    )

        self.generic_visit(node)


def check_file(file_path: Path) -> Dict:
    """检查单个文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        checker = CodeStandardsChecker(file_path)
        checker.visit(tree)

        # 计算覆盖率
        functions_coverage = (
            checker.stats["functions_with_types"] / max(checker.stats["functions"], 1)
        ) * 100
        doc_coverage = (
            (
                checker.stats["functions_with_docstrings"]
                + checker.stats["classes_with_docstrings"]
            )
            / max(checker.stats["functions"] + checker.stats["classes"], 1)
            * 100
        )

        return {
            "file": file_path,
            "stats": checker.stats,
            "issues": checker.issues,
            "coverage": {"types": functions_coverage, "docs": doc_coverage},
        }
    except Exception as e:
        return {
            "file": file_path,
            "error": str(e),
            "stats": {},
            "issues": [],
            "coverage": {"types": 0, "docs": 0},
        }


def main():
    """主函数"""
    print("=" * 80)
    print("🔍 代码规范检查")
    print("=" * 80)

    src_path = Path("src")
    python_files = list(src_path.rglob("*.py"))

    # 过滤掉测试文件和__init__.py
    python_files = [
        f
        for f in python_files
        if not f.name.startswith("test_")
        and f.name != "__init__.py"
        and "__pycache__" not in str(f)
    ]

    print(f"\n📊 检查 {len(python_files)} 个Python文件...")

    all_issues = defaultdict(list)
    total_stats = {
        "functions": 0,
        "functions_with_types": 0,
        "functions_with_docstrings": 0,
        "classes": 0,
        "classes_with_docstrings": 0,
    }

    # 检查每个文件
    for file_path in python_files[:50]:  # 只检查前50个文件
        result = check_file(file_path)

        if "error" in result:
            print(f"  ❌ {file_path}: {result['error']}")
            continue

        # 收集统计信息
        for key in total_stats:
            total_stats[key] += result["stats"].get(key, 0)

        # 收集问题
        for issue in result["issues"]:
            issue["file"] = file_path  # 添加文件路径
            all_issues[issue["type"]].append(issue)

        # 显示覆盖率低的文件
        if result["coverage"]["types"] < 50:
            rel_path = str(result["file"]).replace("src/", "")
            print(f"  ⚠️  {rel_path}: 类型注解覆盖率 {result['coverage']['types']:.1f}%")

    # 计算总体覆盖率
    type_coverage = (
        total_stats["functions_with_types"] / max(total_stats["functions"], 1)
    ) * 100
    doc_coverage = (
        (
            total_stats["functions_with_docstrings"]
            + total_stats["classes_with_docstrings"]
        )
        / max(total_stats["functions"] + total_stats["classes"], 1)
        * 100
    )

    print("\n" + "=" * 80)
    print("📈 总体统计")
    print("=" * 80)

    print("\n函数统计:")
    print(f"  总数: {total_stats['functions']}")
    print(f"  有类型注解: {total_stats['functions_with_types']} ({type_coverage:.1f}%)")
    print(f"  有文档字符串: {total_stats['functions_with_docstrings']}")

    print("\n类统计:")
    print(f"  总数: {total_stats['classes']}")
    print(f"  有文档字符串: {total_stats['classes_with_docstrings']}")

    print(f"\n文档覆盖率: {doc_coverage:.1f}%")

    print("\n" + "=" * 80)
    print("🔧 主要问题")
    print("=" * 80)

    for issue_type, issues in all_issues.items():
        if issues:
            print(f"\n{issue_type.replace('_', ' ').title()} ({len(issues)} 个):")
            # 只显示前5个
            for issue in issues[:5]:
                rel_path = str(issue["file"]).replace("src/", "")
                print(f"  - {rel_path}:{issue['line']} - {issue['message']}")
            if len(issues) > 5:
                print(f"  ... 还有 {len(issues) - 5} 个")

    # 生成建议
    print("\n" + "=" * 80)
    print("💡 改进建议")
    print("=" * 80)

    print("\n1. 类型注解改进:")
    if type_coverage < 70:
        print("   - 为函数添加参数和返回值类型注解")
        print("   - 使用 typing 模块中的类型（Optional, Union, List等）")
        print("   - 使用 Python 3.11+ 的新联合类型语法 (int | str)")

    print("\n2. 文档改进:")
    if doc_coverage < 70:
        print("   - 为公共函数和类添加文档字符串")
        print("   - 使用 Google 或 NumPy 风格的文档")
        print("   - 包含参数、返回值和异常说明")

    print("\n3. 命名规范:")
    print("   - 函数和变量使用 snake_case")
    print("   - 类使用 PascalCase")
    print("   - 常量使用 UPPER_CASE")

    print("\n4. 运行命令:")
    print("   - make lint: 运行 ruff 检查")
    print("   - make mypy-check: 运行类型检查")
    print("   - make fmt: 格式化代码")


if __name__ == "__main__":
    main()
