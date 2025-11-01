#!/usr/bin/env python3
"""
自动清理和排序 Python 文件的 import 语句
功能：
1. 移除未使用的 import (F401)
2. 按 PEP 8 标准排序 import 语句
3. 生成详细的修复报告
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
import subprocess


class ImportCleaner:
    """Import 清理器"""

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.fixed_files = []
        self.errors = []
        self.stats = {
            "total_files": 0,
            "fixed_files": 0,
            "unused_imports_removed": 0,
            "imports_reordered": 0,
            "errors": 0,
        }

    def get_python_files(self, directory: str) -> List[Path]:
        """获取目录中的所有 Python 文件"""
        try:
            path = Path(directory)
            return [f for f in path.rglob("*.py") if not f.name.startswith(".")]
        except Exception as e:
            print(f"❌ 错误：无法读取目录 {directory}: {e}")
            return []

    def get_unused_imports(self, file_path: Path) -> List[str]:
        """使用 ruff 检测未使用的 import"""
        try:
            result = subprocess.run(
                ["ruff", "check", str(file_path), "--select=F401", "--no-fix"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            unused_imports = []
            for line in result.stdout.split("\n"):
                if "F401" in line and "`" in line:
                    # 提取 import 名称，例如: `os` is unused
                    match = re.search(r"`([^`]+)`.*unused", line)
                    if match:
                        unused_imports.append(match.group(1))

            return unused_imports
        except Exception as e:
            print(f"⚠️ 警告：无法检查 {file_path}: {e}")
            return []

    def parse_imports(self, content: str) -> Tuple[List[ast.Import], List[ast.ImportFrom]]:
        """解析 AST 获取所有 import 语句"""
        try:
            tree = ast.parse(content)
            imports = []
            from_imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.append(node)
                elif isinstance(node, ast.ImportFrom):
                    from_imports.append(node)

            return imports, from_imports
        except SyntaxError:
            return [], []

    def remove_unused_imports(self, content: str, unused_imports: List[str]) -> str:
        """移除未使用的 import"""
        lines = content.split("\n")
        new_lines = []

        for line in lines:
            should_remove = False
            for unused in unused_imports:
                # 检查是否包含未使用的 import
                if f"import {unused}" in line or f"from {unused}" in line:
                    should_remove = True
                    break

            if not should_remove:
                new_lines.append(line)

        return "\n".join(new_lines)

    def reorder_imports(self, content: str) -> str:
        """按 PEP 8 标准重新排序 import 语句"""
        lines = content.split("\n")
        import_lines = []
        other_lines = []
        in_import_section = True

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                import_lines.append(line)
            elif stripped == "" and import_lines:
                import_lines.append(line)
            elif import_lines and not stripped.startswith(("import ", "from ")) and stripped != "":
                in_import_section = False

            if not in_import_section or not stripped.startswith(("import ", "from ")):
                if stripped != "" or not import_lines:
                    other_lines.append(line)

        # 分组和排序 import 语句
        stdlib_imports = []
        third_party_imports = []
        local_imports = []

        for line in import_lines:
            if line.strip() == "":
                continue

            if line.startswith("from ."):
                local_imports.append(line)
            elif line.startswith("from "):
                module = line.split()[1]
                if module in [
                    "os",
                    "sys",
                    "json",
                    "datetime",
                    "pathlib",
                    "re",
                    "ast",
                    "typing",
                    "collections",
                    "itertools",
                    "functools",
                    "enum",
                ]:
                    stdlib_imports.append(line)
                else:
                    third_party_imports.append(line)
            elif line.startswith("import "):
                modules = line.split()[1].split(",")
                for module in modules:
                    module = module.strip()
                    if module in [
                        "os",
                        "sys",
                        "json",
                        "datetime",
                        "pathlib",
                        "re",
                        "ast",
                        "typing",
                        "collections",
                        "itertools",
                        "functools",
                        "enum",
                    ]:
                        stdlib_imports.append(f"import {module}")
                    else:
                        third_party_imports.append(f"import {module}")
            else:
                other_lines.append(line)

        # 去重并排序
        stdlib_imports = sorted(list(set(stdlib_imports)))
        third_party_imports = sorted(list(set(third_party_imports)))
        local_imports = sorted(list(set(local_imports)))

        # 重新组合
        ordered_imports = []
        if stdlib_imports:
            ordered_imports.extend(stdlib_imports)
            ordered_imports.append("")

        if third_party_imports:
            ordered_imports.extend(third_party_imports)
            ordered_imports.append("")

        if local_imports:
            ordered_imports.extend(local_imports)
            ordered_imports.append("")

        return "\n".join(ordered_imports + other_lines)

    def fix_file(self, file_path: Path) -> bool:
        """修复单个文件的 import 问题"""
        try:
            # 读取文件内容
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # 获取未使用的 import
            unused_imports = self.get_unused_imports(file_path)

            # 移除未使用的 import
            if unused_imports:
                content = self.remove_unused_imports(content, unused_imports)
                self.stats["unused_imports_removed"] += len(unused_imports)

            # 重新排序 import
            reordered_content = self.reorder_imports(content)
            if reordered_content != content:
                content = reordered_content
                self.stats["imports_reordered"] += 1

            # 如果有改动，写回文件
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                self.fixed_files.append(str(file_path))
                self.stats["fixed_files"] += 1
                return True

            return False

        except Exception as e:
            self.errors.append(f"处理 {file_path} 时出错: {e}")
            self.stats["errors"] += 1
            return False

    def process_directory(self, directory: str) -> Dict:
        """处理目录中的所有 Python 文件"""
        python_files = self.get_python_files(directory)
        self.stats["total_files"] = len(python_files)

        print(f"🔍 开始处理 {len(python_files)} 个 Python 文件...")

        for file_path in python_files:
            if self.fix_file(file_path):
                print(f"✅ 已修复: {file_path}")

        return self.stats

    def generate_report(self, output_file: str) -> None:
        """生成修复报告"""
        report = f"""# 📊 Import 清理报告 (IMPORT_CLEANUP_REPORT)

**清理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**清理工具**: scripts/cleanup_imports.py
**清理范围**: {self.root_dir}

## 📈 清理统计

### 总体统计
- **处理文件总数**: {self.stats['total_files']} 个
- **已修复文件数**: {self.stats['fixed_files']} 个
- **修复成功率**: {(self.stats['fixed_files'] / max(self.stats['total_files'], 1)) * 100:.1f}%

### 详细统计
- **移除未使用 import**: {self.stats['unused_imports_removed']} 个
- **重新排序 import**: {self.stats['imports_reordered']} 个文件
- **处理错误**: {self.stats['errors']} 个

## 📋 已修复文件列表

### 修复的文件 ({len(self.fixed_files)} 个)
"""

        if self.fixed_files:
            for file_path in self.fixed_files:
                report += f"- `{file_path}`\n"
        else:
            report += "无文件需要修复\n"

        if self.errors:
            report += "\n## ⚠️ 处理错误\n\n"
            for error in self.errors:
                report += f"- {error}\n"

        report += f"""

## 🎯 清理效果

- **F401 错误减少**: {self.stats['unused_imports_removed']} 个未使用 import 被移除
- **代码整洁性**: import 语句按 PEP 8 标准重新排序
- **维护性**: 提高了代码的可读性和维护性

## 🔧 使用方法

```bash
# 清理整个项目
python scripts/cleanup_imports.py

# 清理特定目录
python scripts/cleanup_imports.py src/services

# 查看帮助
python scripts/cleanup_imports.py --help
```

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**工具版本**: 1.0
"""

        # 确保报告目录存在
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"📄 报告已生成: {output_file}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="自动清理和排序 Python import 语句")
    parser.add_argument("directory", nargs="?", default=".", help="要清理的目录 (默认: 当前目录)")
    parser.add_argument(
        "--report",
        default="docs/_reports/IMPORT_CLEANUP_REPORT.md",
        help="报告输出路径 (默认: docs/_reports/IMPORT_CLEANUP_REPORT.md)",
    )

    args = parser.parse_args()

    # 确保目录存在
    if not os.path.exists(args.directory):
        print(f"❌ 错误：目录 {args.directory} 不存在")
        sys.exit(1)

    print(f"🧹 开始清理 {args.directory} 中的 import 语句...")

    # 创建清理器并处理
    cleaner = ImportCleaner(args.directory)
    stats = cleaner.process_directory(args.directory)

    # 生成报告
    cleaner.generate_report(args.report)

    # 输出总结
    print("\n✅ 清理完成！")
    print(f"📊 处理文件: {stats['total_files']} 个")
    print(f"🔧 修复文件: {stats['fixed_files']} 个")
    print(f"🗑️ 移除未使用 import: {stats['unused_imports_removed']} 个")
    print(f"📋 重新排序 import: {stats['imports_reordered']} 个")
    print(f"❌ 错误: {stats['errors']} 个")


if __name__ == "__main__":
    main()
