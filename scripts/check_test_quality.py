#!/usr/bin/env python3
"""
测试质量检查脚本
Test Quality Check Script

自动化验证测试代码是否符合最佳实践。

使用方法：
python scripts/check_test_quality.py [test_file_or_directory]

检查项目：
- 测试命名约定
- Mock使用规范
- 断言精确性
- 文档字符串
- 测试复杂度
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import argparse


class TestQualityChecker:
    """测试质量检查器"""

    def __init__(self):
        self.issues = []
        self.stats = {
            "files_checked": 0,
            "tests_found": 0,
            "issues_found": 0,
            "warnings": 0,
            "errors": 0,
        }
        self.rules = {
            "naming": self.check_naming_convention,
            "mocks": self.check_mock_usage,
            "assertions": self.check_assertions,
            "documentation": self.check_documentation,
            "complexity": self.check_test_complexity,
        }

    def check_file(self, file_path: Path) -> List[Dict]:
        """检查单个文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content)
        except Exception as e:
            return [
                {
                    "type": "error",
                    "file": str(file_path),
                    "line": 1,
                    "message": f"Failed to parse file: {e}",
                }
            ]

        issues = []
        functions = []

        # 提取所有函数
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append((node.name, node.lineno, node))

        # 应用所有规则
        for rule_name, rule_func in self.rules.items():
            rule_issues = rule_func(file_path, content, functions)
            issues.extend(rule_issues)

        self.stats["files_checked"] += 1
        self.stats["tests_found"] += len(functions)

        return issues

    def check_naming_convention(
        self, file_path: Path, content: str, functions: List
    ) -> List[Dict]:
        """检查命名约定"""
        issues = []

        # 检查测试函数命名
        for func_name, line_no, _ in functions:
            if not func_name.startswith("test_"):
                continue

            # 检查命名格式：test_[功能]_[场景]_[期望]
            if func_name.count("_") < 2:
                issues.append(
                    {
                        "type": "warning",
                        "rule": "naming",
                        "file": str(file_path),
                        "line": line_no,
                        "message": f"Test function '{func_name}' should follow format: test_[feature]_[scenario]_[expected]",
                    }
                )

            # 检查是否有意义的动词
            if any(
                keyword in func_name
                for keyword in ["test1", "test_a", "test_example", "test_it"]
            ):
                issues.append(
                    {
                        "type": "warning",
                        "rule": "naming",
                        "file": str(file_path),
                        "line": line_no,
                        "message": f"Test function '{func_name}' should have a descriptive name",
                    }
                )

            # 检查是否包含期望结果
            if not any(
                keyword in func_name
                for keyword in ["returns", "raises", "is", "are", "should"]
            ):
                issues.append(
                    {
                        "type": "info",
                        "rule": "naming",
                        "file": str(file_path),
                        "line": line_no,
                        "message": f"Test function '{func_name}' should include expected result (e.g., 'returns_201', 'raises_ValueError')",
                    }
                )

        return issues

    def check_mock_usage(
        self, file_path: Path, content: str, functions: List
    ) -> List[Dict]:
        """检查Mock使用"""
        issues = []
        lines = content.split("\n")

        # 检查是否使用了全局mock
        for i, line in enumerate(lines, 1):
            if "sys.modules[" in line and "Mock" in line:
                issues.append(
                    {
                        "type": "error",
                        "rule": "mocks",
                        "file": str(file_path),
                        "line": i,
                        "message": "Avoid global mocking with sys.modules. Use @patch decorator instead",
                    }
                )

            # 检查patch使用
            if re.search(r"@patch\(.*\).*$", line):
                # 检查patch路径是否精确
                match = re.search(r'@patch\([\'"]([^\'\"]+)[\'"]\)', line)
                if match:
                    patch_target = match.group(1)
                    if patch_target.endswith(".Mock") or patch_target.endswith(".mock"):
                        issues.append(
                            {
                                "type": "warning",
                                "rule": "mocks",
                                "file": str(file_path),
                                "line": i,
                                "message": f"Patch target '{patch_target}' seems too generic. Be more specific",
                            }
                        )

        return issues

    def check_assertions(
        self, file_path: Path, content: str, functions: List
    ) -> List[Dict]:
        """检查断言精确性"""
        issues = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # 检查模糊的状态码断言
            if "assert" in line and "status_code" in line:
                # 查找 in [200, 201, 202] 模式
                if re.search(r"status_code\s+in\s+\[", line):
                    issues.append(
                        {
                            "type": "error",
                            "rule": "assertions",
                            "file": str(file_path),
                            "line": i,
                            "message": "Use exact status code assertion instead of range",
                        }
                    )

            # 检查是否有断言消息
            if (
                line.strip().startswith("assert ")
                and "f'Expected" not in line
                and 'f"Expected' not in line
            ):
                # 但跳过简单的断言
                if not re.search(
                    r"assert\s+(True|False|None|is\s+None|is\s+not\s+None)\s*$", line
                ):
                    issues.append(
                        {
                            "type": "warning",
                            "rule": "assertions",
                            "file": str(file_path),
                            "line": i,
                            "message": "Consider adding assertion message for better debugging",
                        }
                    )

            # 检查是否验证了响应结构
            if "response.json()" in line and "assert" not in line:
                issues.append(
                    {
                        "type": "info",
                        "rule": "assertions",
                        "file": str(file_path),
                        "line": i,
                        "message": "Consider asserting on response.json() structure",
                    }
                )

        return issues

    def check_documentation(
        self, file_path: Path, content: str, functions: List
    ) -> List[Dict]:
        """检查文档字符串"""
        issues = []

        for func_name, line_no, func_node in functions:
            if not func_name.startswith("test_"):
                continue

            # 检查是否有docstring
            if not ast.get_docstring(func_node):
                issues.append(
                    {
                        "type": "info",
                        "rule": "documentation",
                        "file": str(file_path),
                        "line": line_no,
                        "message": f"Test function '{func_name}' should have a docstring",
                    }
                )
            else:
                # 检查docstring质量
                docstring = ast.get_docstring(func_node) or ""
                doc_lines = docstring.split("\n")

                # 第一行应该是简短描述
                if len(doc_lines[0]) > 100:
                    issues.append(
                        {
                            "type": "warning",
                            "rule": "documentation",
                            "file": str(file_path),
                            "line": line_no,
                            "message": "First line of docstring should be brief (< 100 chars)",
                        }
                    )

                # 检查是否包含测试目的说明
                if "测试" not in docstring and "test" not in docstring.lower():
                    issues.append(
                        {
                            "type": "info",
                            "rule": "documentation",
                            "file": str(file_path),
                            "line": line_no,
                            "message": "Docstring should describe the test purpose",
                        }
                    )

        return issues

    def check_test_complexity(
        self, file_path: Path, content: str, functions: List
    ) -> List[Dict]:
        """检查测试复杂度"""
        issues = []

        for func_name, line_no, func_node in functions:
            if not func_name.startswith("test_"):
                continue

            # 计算复杂度（简化版）
            complexity = 0
            for node in ast.walk(func_node):
                if isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                    complexity += 1
                elif isinstance(node, ast.Assert):
                    complexity += 0.5

            if complexity > 5:
                issues.append(
                    {
                        "type": "warning",
                        "rule": "complexity",
                        "file": str(file_path),
                        "line": line_no,
                        "message": f"Test function '{func_name}' is too complex (score: {complexity}). Consider splitting.",
                    }
                )

            # 检查函数长度
            if func_node.end_lineno:
                lines = func_node.end_lineno - func_node.lineno
                if lines > 30:
                    issues.append(
                        {
                            "type": "info",
                            "rule": "complexity",
                            "file": str(file_path),
                            "line": line_no,
                            "message": f"Test function '{func_name}' is too long ({lines} lines). Consider splitting.",
                        }
                    )

        return issues

    def check_directory(self, directory: Path) -> List[Dict]:
        """检查目录中的所有测试文件"""
        issues = []

        # 查找所有测试文件
        test_files = []
        for pattern in ["test_*.py", "*_test.py"]:
            test_files.extend(directory.rglob(pattern))

        # 排除一些目录
        exclude_dirs = {".git", "__pycache__", ".venv", "node_modules", "build", "dist"}
        test_files = [
            f
            for f in test_files
            if not any(exclude in str(f) for exclude in exclude_dirs)
        ]

        for test_file in test_files:
            file_issues = self.check_file(test_file)
            issues.extend(file_issues)

        return issues

    def print_report(self, issues: List[Dict]):
        """打印检查报告"""
        # 更新统计
        for issue in issues:
            self.stats["issues_found"] += 1
            if issue["type"] == "error":
                self.stats["errors"] += 1
            elif issue["type"] == "warning":
                self.stats["warnings"] += 1

        # 按类型分组
        by_type = {"error": [], "warning": [], "info": []}
        for issue in issues:
            by_type[issue["type"]].append(issue)

        # 打印报告
        print("\n" + "=" * 60)
        print("🔍 测试质量检查报告")
        print("=" * 60)

        # 统计信息
        print("\n📊 统计信息:")
        print(f"  - 检查文件数: {self.stats['files_checked']}")
        print(f"  - 发现测试数: {self.stats['tests_found']}")
        print(f"  - 问题总数: {self.stats['issues_found']}")
        print(f"    - 错误: {self.stats['errors']}")
        print(f"    - 警告: {self.stats['warnings']}")
        print(
            f"    - 信息: {self.stats['issues_found'] - self.stats['errors'] - self.stats['warnings']}"
        )

        # 详细问题
        if issues:
            print("\n⚠️ 发现的问题:")

            # 错误
            if by_type["error"]:
                print("\n❌ 错误:")
                for issue in by_type["error"][:10]:  # 限制显示数量
                    print(f"  {issue['file']}:{issue['line']}")
                    print(f"    {issue['message']}")
                if len(by_type["error"]) > 10:
                    print(f"  ... 还有 {len(by_type['error']) - 10} 个错误")

            # 警告
            if by_type["warning"]:
                print("\n⚠️ 警告:")
                for issue in by_type["warning"][:10]:
                    print(f"  {issue['file']}:{issue['line']}")
                    print(f"    {issue['message']}")
                if len(by_type["warning"]) > 10:
                    print(f"  ... 还有 {len(by_type['warning']) - 10} 个警告")

            # 信息
            if by_type["info"]:
                print("\nℹ️ 建议:")
                for issue in by_type["info"][:5]:
                    print(f"  {issue['file']}:{issue['line']}")
                    print(f"    {issue['message']}")
                if len(by_type["info"]) > 5:
                    print(f"  ... 还有 {len(by_type['info']) - 5} 个建议")
        else:
            print("\n✅ 太棒了！没有发现质量问题。")

        # 质量评分
        print("\n📈 质量评分:")
        if self.stats["issues_found"] == 0:
            score = 100
        else:
            # 简单的评分算法
            error_penalty = self.stats["errors"] * 10
            warning_penalty = self.stats["warnings"] * 3
            info_penalty = (
                self.stats["issues_found"]
                - self.stats["errors"]
                - self.stats["warnings"]
            )
            score = max(0, 100 - error_penalty - warning_penalty - info_penalty)

        print(f"  总分: {score}/100")

        if score >= 90:
            print("  🏆 优秀！测试质量很高。")
        elif score >= 80:
            print("  👍 良好！还有一些改进空间。")
        elif score >= 70:
            print("  👌 一般，建议尽快修复问题。")
        else:
            print("  👎 需要改进，请优先修复错误。")

        print("\n" + "=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="检查测试代码质量")
    parser.add_argument(
        "path", nargs="?", default="tests", help="要检查的文件或目录路径（默认：tests）"
    )
    parser.add_argument(
        "--rules",
        nargs="*",
        choices=["naming", "mocks", "assertions", "documentation", "complexity"],
        help="只检查指定的规则",
    )
    parser.add_argument(
        "--output", choices=["text", "json"], default="text", help="输出格式"
    )

    args = parser.parse_args()

    checker = TestQualityChecker()

    # 如果指定了特定规则，只运行这些规则
    if args.rules:
        selected_rules = {k: v for k, v in checker.rules.items() if k in args.rules}
        checker.rules = selected_rules

    path = Path(args.path)

    if path.is_file():
        issues = checker.check_file(path)
    else:
        issues = checker.check_directory(path)

    if args.output == "json":
        import json

        print(json.dumps({"stats": checker.stats, "issues": issues}, indent=2))
    else:
        checker.print_report(issues)

    # 返回适当的退出码
    if checker.stats["errors"] > 0:
        sys.exit(1)
    elif checker.stats["warnings"] > 5:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
