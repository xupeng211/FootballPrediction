#!/usr/bin/env python3
"""
增强的语法修复工具
修复正则表达式错误，支持更多修复模式
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime


class EnhancedSyntaxFixer:
    """增强的语法修复器"""

    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path.cwd() / src_dir
        self.fixed_files = []
        self.failed_files = []
        self.total_fixes = 0
        self.fix_patterns = [
            # 修复模式列表
            (r'^(\s*""\s*([^"]*)""\s*)$', lambda m: f'"""\n{m.group(2).strip()}\n"""'),
            (
                r'^(\s*"\'\s*([^\']*)\'\s*)$',
                lambda m: f"'''\n{m.group(2).strip()}\n'''",
            ),
            (r"__all__\s*=\s*\[\)", "__all__ = ["),
            (r"\{\s*([^}]+)\s*,\s*\)", r"{\1}"),
            (r"\[\s*([^\]]+)\s*,\s*\]", r"[\1]"),
            (r"(\w+)\s*\(\s*([^)]*)\s*\)\s*\)", r"\1(\2)"),
            (r"from\s+([^\s]+)\s+import\s+([^\n:]+)\s*:\s*$", r"from \1 import \2"),
            (r"except\s*\(([^)]+)\)\s*:\s*$", r"except (\1):"),
            (r"except\s*([^\s:]+)\s*:\s*$", r"except \1:"),
            (r"class\s+(\w+)\s*\(\s*([^)]*)\s*\)\s*:\s*$", r"class \1(\2):"),
            (
                r"def\s+(\w+)\s*\(\s*([^)]*)\s*\)(?:\s*->\s*([^:]+))?\s*:\s*$",
                r"def \1(\2) -> \3:",
            ),
            (r"return\s*\{\s*$", "return {"),
            (r"return\s*\[\s*$", "return ["),
            (r"(\w+)\s*\.\s*(\w+)\s*:\s*$", r"\1.\2"),
            (r"if\s+([^\n:]+)\s*:\s*$", r"if \1:"),
            (r"elif\s+([^\n:]+)\s*:\s*$", r"elif \1:"),
            (r"else\s*:\s*$", r"else:"),
            (r"for\s+([^\n:]+)\s*:\s*$", r"for \1:"),
            (r"while\s+([^\n:]+)\s*:\s*$", r"while \1:"),
            (r"try\s*:\s*$", r"try:"),
            (r"finally\s*:\s*$", r"finally:"),
            (r"@(\w+)\s*\(\s*([^)]*)\s*\)\s*:\s*$", r"@\1(\2)\n"),
            (r'""\s*([^"]*)""\s*$', r'"""\n\1"""'),
            (r"'\s*([^']*)'\s*$", r"'''\n\1'''"),
        ]

    def fix_file_content(self, content: str) -> Tuple[str, List[str]]:
        """修复文件内容"""
        fixes_applied = []

        lines = content.split("\n")
        fixed_lines = []

        for i, line in enumerate(lines):
            original_line = line
            line = line.rstrip()

            # 应用修复模式
            for pattern, replacement in self.fix_patterns:
                try:
                    if callable(replacement):
                        # 处理可调用替换
                        match = re.match(pattern, line)
                        if match:
                            line = replacement(match)
                            fixes_applied.append(
                                f"Line {i+1}: {original_line} → {line}"
                            )
                    else:
                        # 处理字符串替换
                        new_line = re.sub(pattern, replacement, line)
                        if new_line != line:
                            fixes_applied.append(f"Line {i+1}: {line} → {new_line}")
                            line = new_line
                except re.error as e:
                    # 记录错误但继续
                    fixes_applied.append(f"Line {i+1}: Regex error: {e}")

            # 特殊处理：确保类和函数定义后有空行和缩进
            if line.strip().startswith(("class ", "def ")) and ":" in line:
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if (
                        next_line.strip()
                        and not next_line.startswith("    ")
                        and not next_line.startswith("\t")
                    ):
                        # 下一行需要缩进
                        lines[i + 1] = "    " + next_line

            fixed_lines.append(line)

        fixed_content = "\n".join(fixed_lines)

        # 确保文件以换行符结尾
        if fixed_content and not fixed_content.endswith("\n"):
            fixed_content += "\n"

        # 移除连续的空行
        fixed_content = re.sub(r"\n\s*\n\s*\n", "\n\n", fixed_content)

        return fixed_content, fixes_applied

    def fix_file(self, file_path: Path) -> bool:
        """修复单个文件"""
        try:
            # 跳过某些目录
            skip_dirs = ["__pycache__", ".git", "migrations", "archive"]
            if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                return False

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # 跳过二进制文件或空文件
            if not content or "\x00" in content:
                return False

            # 应用修复
            fixed_content, fixes = self.fix_file_content(content)

            # 保存修复后的文件
            if fixed_content != content:
                # 创建备份（可选）
                backup_path = file_path.with_suffix(".py.bak")
                if not backup_path.exists():
                    with open(backup_path, "w", encoding="utf-8") as f:
                        f.write(content)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)

                self.fixed_files.append(str(file_path.relative_to(Path.cwd())))
                self.total_fixes += len(fixes)
                print(
                    f"✅ 修复 {file_path.relative_to(Path.cwd())} ({len(fixes)} 处修复)"
                )
                return True

        except Exception as e:
            print(f"❌ 修复失败 {file_path}: {e}")
            self.failed_files.append(str(file_path.relative_to(Path.cwd())))

        return False

    def scan_and_fix(
        self, max_files: int = 50, target_dirs: Optional[List[str]] = None
    ) -> dict:
        """扫描并修复文件"""
        print("🔧 开始增强的语法修复...")
        print(f"最大文件数: {max_files}")

        # 查找所有Python文件
        python_files = list(self.src_dir.rglob("*.py"))

        # 过滤文件
        if target_dirs:
            python_files = [
                f for f in python_files if any(dir in str(f) for dir in target_dirs)
            ]

        # 跳过某些目录
        skip_patterns = ["__pycache__", ".git", "migrations", "archive", "backup"]
        python_files = [
            f
            for f in python_files
            if not any(pattern in str(f) for pattern in skip_patterns)
        ]

        print(f"找到 {len(python_files)} 个Python文件")

        # 限制文件数量
        files_to_fix = python_files[:max_files]

        print(f"\n开始修复前 {len(files_to_fix)} 个文件...\n")

        # 逐个修复
        for file_path in files_to_fix:
            self.fix_file(file_path)

        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "target_dirs": target_dirs or ["all"],
            "total_files": len(python_files),
            "processed_files": len(files_to_fix),
            "fixed_files": len(self.fixed_files),
            "failed_files": len(self.failed_files),
            "total_fixes": self.total_fixes,
            "fixed_files_list": self.fixed_files[:10],
            "failed_files_list": self.failed_files[:5],
        }

        self.print_report(report)
        return report

    def print_report(self, report: dict):
        """打印修复报告"""
        print("\n" + "=" * 60)
        print("📋 增强的语法修复报告")
        print("=" * 60)

        print("\n📊 统计:")
        print(f"  - 目标目录: {', '.join(report['target_dirs'])}")
        print(f"  - 总文件数: {report['total_files']}")
        print(f"  - 处理文件数: {report['processed_files']}")
        print(f"  - 成功修复: {report['fixed_files']}")
        print(f"  - 修复失败: {report['failed_files']}")
        print(f"  - 总修复数: {report['total_fixes']}")

        if report["fixed_files_list"]:
            print("\n✅ 已修复的部分文件:")
            for file_path in report["fixed_files_list"]:
                print(f"  - {file_path}")

        if report["failed_files_list"]:
            print("\n❌ 修复失败的部分文件:")
            for file_path in report["failed_files_list"]:
                print(f"  - {file_path}")

        # 计算修复率
        if report["processed_files"] > 0:
            fix_rate = (report["fixed_files"] / report["processed_files"]) * 100
            print(f"\n📊 修复率: {fix_rate:.1f}%")

        # 保存报告
        import json

        report_file = Path("enhanced_fix_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="增强的Python语法修复工具")
    parser.add_argument("--max-files", type=int, default=50, help="最大修复文件数")
    parser.add_argument(
        "--target", nargs="*", default=["database", "models"], help="目标目录"
    )

    args = parser.parse_args()

    fixer = EnhancedSyntaxFixer()
    fixer.scan_and_fix(args.max_files, args.target)

    print("\n下一步:")
    print("1. 运行测试: python -m pytest tests/unit/ -x --tb=short")
    print(
        "2. 继续修复: python scripts/enhanced_fix.py --max-files 50 --target api services"
    )


if __name__ == "__main__":
    main()
