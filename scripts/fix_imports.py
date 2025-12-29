#!/usr/bin/env python3
"""
FootballPrediction Import 路径更新脚本
========================================

在目录重构后，自动更新所有 Python 文件中的 import 路径。

处理的路径变化：
- configs.* -> config.*
- database.migrations.* -> database.migrations.* (如已移动)
- src.modeling.* -> src.ml.*
- src.models.* -> src.ml.*

作者：Claude Code
日期：2024-12-29
版本：1.0
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Tuple


class ImportFixer:
    """Import 路径修复器"""

    # 路径映射规则
    PATH_MAPPINGS = {
        # config 相关
        (r"\bfrom configs\s*\.", "from config."):
            re.compile(r"\bfrom configs\s*\."),
        (r"\bimport configs\.", "import config."):
            re.compile(r"\bimport configs\."),

        # modeling -> ml
        (r"\bfrom src\.modeling\b", "from src.ml"):
            re.compile(r"\bfrom src\.modeling\b"),
        (r"\bfrom src\.modeling\.", "from src.ml."):
            re.compile(r"\bfrom src\.modeling\."),

        # models -> ml
        (r"\bfrom src\.models\b", "from src.ml"):
            re.compile(r"\bfrom src\.models\b"),
        (r"\bfrom src\.models\.", "from src.ml."):
            re.compile(r"\bfrom src\.models\."),

        # database 相关（如果从根目录移动到 src/）
        # 注意：这个规则需要谨慎使用，可能需要手动检查
    }

    def __init__(self, project_root: Path, dry_run: bool = True):
        self.project_root = project_root
        self.dry_run = dry_run
        self.fixed_files = []
        self.errors = []

    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        prefix = "[DRY RUN]" if self.dry_run else "[EXECUTE]"
        print(f"{prefix} [{level}] {message}")

    def fix_file_imports(self, filepath: Path) -> int:
        """修复单个文件的 import 路径"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            changes = []

            # 应用所有路径映射规则
            for (pattern, replacement), regex in self.PATH_MAPPINGS.items():
                matches = list(regex.finditer(content))
                if matches:
                    new_content = regex.sub(replacement, content)
                    if new_content != content:
                        changes.extend([
                            f"  {match.group(0)} -> {replacement}"
                            for match in matches
                        ])
                        content = new_content

            if content != original_content:
                if not self.dry_run:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)

                self.fixed_files.append({
                    "path": str(filepath.relative_to(self.project_root)),
                    "changes": changes
                })
                self.log(f"修复: {filepath.relative_to(self.project_root)}")
                for change in changes:
                    self.log(change, "DEBUG")
                return len(changes)

            return 0

        except Exception as e:
            self.errors.append(f"处理失败: {filepath}: {e}")
            self.log(f"处理失败: {e}", "ERROR")
            return 0

    def scan_and_fix(self, exclude_dirs: List[str] = None):
        """扫描并修复所有 Python 文件"""
        if exclude_dirs is None:
            exclude_dirs = [
                ".git",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                "venv",
                ".venv",
                "archive",
                "data",
                "htmlcov",
                ".benchmarks",
            ]

        self.log("开始扫描 Python 文件...")

        py_files = []
        for filepath in self.project_root.rglob("*.py"):
            # 排除特定目录
            if any(
                f"/{exclude}/" in f"{filepath}/" or filepath.is_relative_to(self.project_root / exclude)
                for exclude in exclude_dirs
            ):
                continue

            py_files.append(filepath)

        self.log(f"找到 {len(py_files)} 个 Python 文件")

        total_changes = 0
        for filepath in sorted(py_files):
            changes = self.fix_file_imports(filepath)
            total_changes += changes

        self.log(f"总计修复 {len(self.fixed_files)} 个文件，{total_changes} 处变化")

    def generate_report(self):
        """生成修复报告"""
        report = {
            "dry_run": self.dry_run,
            "fixed_files_count": len(self.fixed_files),
            "errors_count": len(self.errors),
            "fixed_files": self.fixed_files,
            "errors": self.errors
        }

        # 保存报告
        report_path = self.project_root / "logs" / "import_fix_report.json"
        report_path.parent.mkdir(exist_ok=True)
        if not self.dry_run:
            import json
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            self.log(f"报告已保存: {report_path}")

        return report

    def print_summary(self, report: Dict):
        """打印总结"""
        print("\n" + "=" * 60)
        print("Import 路径修复总结")
        print("=" * 60)
        print(f"修复文件数: {report['fixed_files_count']}")
        print(f"错误数: {report['errors_count']}")

        if self.errors:
            print("\n错误详情:")
            for error in self.errors[:10]:  # 只显示前 10 个
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... 还有 {len(self.errors) - 10} 个错误")

        if self.dry_run:
            print("\n⚠️  这是 DRY RUN 模式，没有实际执行任何操作")
            print("   如果确认无误，请运行:")
            print("   python scripts/fix_imports.py --execute")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="FootballPrediction Import 路径更新脚本")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="实际执行操作（默认为 dry-run 模式）"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).parent.parent,
        help="项目根目录（默认自动检测）"
    )

    args = parser.parse_args()

    # 确认项目根目录
    project_root = args.project_root
    if not (project_root / "CLAUDE.md").exists():
        print(f"错误: 无法找到 CLAUDE.md，请确认项目根目录: {project_root}")
        return 1

    print(f"项目根目录: {project_root}")

    # 创建修复器
    fixer = ImportFixer(project_root, dry_run=not args.execute)

    # 执行修复
    fixer.scan_and_fix()

    # 生成报告
    report = fixer.generate_report()
    fixer.print_summary(report)

    return 0


if __name__ == "__main__":
    exit(main())
