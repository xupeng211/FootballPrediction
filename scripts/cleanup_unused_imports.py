#!/usr/bin/env python3
"""
未使用导入清理工具
Unused Imports Cleanup Tool

自动检测和移除未使用的导入语句，支持安全清理。
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Set, Tuple

import subprocess


class UnusedImportsCleaner:
    """未使用导入清理器"""

    def __init__(self, source_dir: str = "src"):
        self.source_dir = Path(source_dir)
        self.python_files = []
        self.cleanup_results = {}

    def find_python_files(self) -> List[Path]:
        """查找所有Python文件"""
        python_files = []
        for file_path in self.source_dir.rglob("*.py"):
            if not any(skip in str(file_path) for skip in [
                "__pycache__",
                ".git",
                ".pytest_cache",
                "venv",
                ".venv"
            ]):
                python_files.append(file_path)
        return python_files

    def get_unused_imports_ruff(self, file_path: Path) -> List[str]:
        """使用ruff获取未使用的导入"""
        try:
            # 运行ruff检查
            result = subprocess.run(
                ["ruff", "check", str(file_path), "--select=F401", "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return []  # 没有未使用的导入

            # 解析JSON输出
            import json
            try:
                issues = json.loads(result.stdout)
                unused_imports = []
                for issue in issues:
                    if issue.get("code") == "F401":
                        unused_imports.append(issue.get("message", ""))
                return unused_imports
            except json.JSONDecodeError:
                # 如果JSON解析失败，使用简单的文本解析
                unused_imports = []
                for line in result.stdout.split('\n'):
                    if 'F401' in line and 'imported but unused' in line:
                        # 提取导入名称
                        match = re.search(r'`([^`]+)` imported but unused', line)
                        if match:
                            unused_imports.append(match.group(1))
                return unused_imports

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            print(f"警告: 无法检查文件 {file_path}")
            return []

    def extract_import_info(self, file_path: Path) -> Tuple[List[ast.Import], List[ast.ImportFrom]]:
        """提取文件中的导入信息"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            imports = []
            imports_from = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.append(node)
                elif isinstance(node, ast.ImportFrom):
                    imports_from.append(node)

            return imports, imports_from

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"警告: 无法解析文件 {file_path}: {e}")
            return [], []

    def remove_unused_imports(self, file_path: Path, unused_names: Set[str]) -> bool:
        """移除未使用的导入"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            imports, imports_from = self.extract_import_info(file_path)
            lines_to_remove = set()

            # 检查导入语句
            for imp in imports + imports_from:
                for alias in imp.names:
                    name = alias.asname if alias.asname else alias.name
                    if name in unused_names:
                        # 标记要删除的行
                        line_num = imp.lineno - 1  # 转换为0基索引
                        if 0 <= line_num < len(lines):
                            lines_to_remove.add(line_num)

            # 检查多行导入
            for imp in imports_from:
                if imp.lineno in [line + 1 for line in lines_to_remove]:
                    # 如果是from导入，检查是否所有名称都未使用
                    all_unused = all(
                        (alias.asname if alias.asname else alias.name) in unused_names
                        for alias in imp.names
                    )
                    if all_unused:
                        line_num = imp.lineno - 1
                        if 0 <= line_num < len(lines):
                            lines_to_remove.add(line_num)

            # 移除标记的行
            new_lines = [
                line for i, line in enumerate(lines)
                if i not in lines_to_remove
            ]

            # 清理多余的空行
            cleaned_lines = []
            prev_empty = False
            for line in new_lines:
                is_empty = line.strip() == ""
                if not (is_empty and prev_empty):
                    cleaned_lines.append(line)
                prev_empty = is_empty

            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)

            return len(lines_to_remove) > 0

        except Exception as e:
            print(f"错误: 清理文件 {file_path} 失败: {e}")
            return False

    def analyze_unused_imports(self, file_path: Path) -> dict:
        """分析文件的未使用导入"""
        unused_imports = self.get_unused_imports_ruff(file_path)

        if not unused_imports:
            return {"unused_count": 0, "unused_names": [], "safe_to_remove": []}

        # 提取导入名称
        unused_names = set()
        for import_msg in unused_imports:
            # 从ruff消息中提取名称
            match = re.search(r'`([^`]+)`', import_msg)
            if match:
                name = match.group(1)
                # 处理模块导入的情况
                if '.' in name and not name.endswith('.*'):
                    unused_names.add(name.split('.')[-1])
                else:
                    unused_names.add(name)

        # 识别可以安全移除的导入
        safe_to_remove = []
        dangerous_to_remove = []

        for name in unused_names:
            # 检查是否是可能的副作用导入
            dangerous_patterns = [
                'settings', 'config', 'models', 'signals', 'apps',
                'admin', 'urlpatterns', 'wsgi', 'asgi'
            ]
            if any(pattern in name.lower() for pattern in dangerous_patterns):
                dangerous_to_remove.append(name)
            else:
                safe_to_remove.append(name)

        return {
            "unused_count": len(unused_names),
            "unused_names": list(unused_names),
            "safe_to_remove": safe_to_remove,
            "dangerous_to_remove": dangerous_to_remove
        }

    def cleanup_file(self, file_path: Path, dry_run: bool = True) -> dict:
        """清理单个文件"""
        print(f"\n处理文件: {file_path}")

        analysis = self.analyze_unused_imports(file_path)

        if analysis["unused_count"] == 0:
            print("  ✅ 没有发现未使用的导入")
            return {"cleaned": False, "removed_count": 0}

        print(f"  📊 发现 {analysis['unused_count']} 个未使用的导入:")
        for name in analysis["unused_names"]:
            marker = "⚠️" if name in analysis["dangerous_to_remove"] else "✅"
            print(f"    {marker} {name}")

        if analysis["dangerous_to_remove"]:
            print(f"  ⚠️ {len(analysis['dangerous_to_remove'])} 个可能有副作用的导入，跳过清理")
            safe_names = set(analysis["safe_to_remove"])
        else:
            safe_names = set(analysis["unused_names"])

        if not safe_names:
            print("  ℹ️ 没有可以安全移除的导入")
            return {"cleaned": False, "removed_count": 0}

        if dry_run:
            print(f"  🧪 预计将移除 {len(safe_names)} 个导入")
            return {"cleaned": False, "removed_count": len(safe_names), "dry_run": True}

        # 实际清理
        success = self.remove_unused_imports(file_path, safe_names)
        if success:
            print(f"  ✅ 成功移除 {len(safe_names)} 个未使用的导入")
            return {"cleaned": True, "removed_count": len(safe_names)}
        else:
            print("  ❌ 清理失败")
            return {"cleaned": False, "removed_count": 0}

    def cleanup_all_files(self, dry_run: bool = True) -> dict:
        """清理所有文件"""
        print("🧹 开始清理未使用的导入...")
        print(f"📁 搜索目录: {self.source_dir}")

        python_files = self.find_python_files()
        print(f"📄 找到 {len(python_files)} 个Python文件")

        if not python_files:
            print("❌ 没有找到Python文件")
            return {"total_files": 0, "cleaned_files": 0, "total_removed": 0}

        total_removed = 0
        cleaned_files = 0

        for file_path in python_files:
            result = self.cleanup_file(file_path, dry_run)
            if result.get("cleaned", False):
                cleaned_files += 1
                total_removed += result.get("removed_count", 0)

        summary = {
            "total_files": len(python_files),
            "cleaned_files": cleaned_files,
            "total_removed": total_removed,
            "dry_run": dry_run
        }

        print(f"\n{'='*60}")
        print(f"📊 清理完成 ({'预览模式' if dry_run else '实际清理'})")
        print(f"{'='*60}")
        print(f"📁 处理文件数: {summary['total_files']}")
        print(f"🧹 清理文件数: {summary['cleaned_files']}")
        print(f"🗑️ 移除导入数: {summary['total_removed']}")

        if dry_run and summary['total_removed'] > 0:
            print(f"\n💡 要实际执行清理，请使用 --no-dry-run 参数")

        return summary


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="清理未使用的导入")
    parser.add_argument(
        "--source-dir",
        default="src",
        help="源代码目录 (默认: src)"
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="实际执行清理 (默认为预览模式)"
    )
    parser.add_argument(
        "--file",
        help="只处理指定文件"
    )

    args = parser.parse_args()

    cleaner = UnusedImportsCleaner(args.source_dir)

    if args.file:
        # 处理单个文件
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            return

        result = cleaner.cleanup_file(file_path, dry_run=not args.no_dry_run)
        print(f"\n结果: {'清理成功' if result.get('cleaned') else '无需清理'}")
    else:
        # 处理所有文件
        summary = cleaner.cleanup_all_files(dry_run=not args.no_dry_run)

        if not args.no_dry_run and summary['total_removed'] > 0:
            print(f"\n✅ 清理完成！建议运行代码检查确认清理结果:")
            print(f"   ruff check {args.source_dir}/")
            print(f"   python -m py_compile {args.source_dir}/")


if __name__ == "__main__":
    main()