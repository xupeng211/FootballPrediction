#!/usr/bin/env python3
"""
批量语法错误修复工具
专门处理括号不匹配、字符串未闭合等常见问题
"""

import os
import re
from pathlib import Path
from typing import List, Tuple
from datetime import datetime


class BatchSyntaxFixer:
    """批量语法修复器"""

    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path(src_dir)
        self.fixed_files = []
        self.failed_files = []
        self.total_fixes = 0

    def fix_bracket_issues(self, content: str) -> Tuple[str, int]:
        """修复括号问题"""
        original = content
        fixes = 0

        # 修复 __all__ = [) 的问题
        content = re.sub(r"__all__\s*=\s*\[\)", "__all__ = [", content)
        if content != original:
            fixes += 1

        # 修复字典和列表的括号问题
        # 查找类似 {"key": value,) 的模式
        content = re.sub(r"(\{[^}]+),\s*\)", r"\1}", content)

        # 查找类似 [item,) 的模式
        content = re.sub(r"(\[[^\]]+),\s*\)", r"\1]", content)

        # 修复函数调用中的括号
        content = re.sub(r"(\w+\([^)]+),\s*\)", r"\1)", content)

        return content, fixes

    def fix_missing_colons(self, content: str) -> Tuple[str, int]:
        """修复缺失的冒号"""
        original = content
        fixes = 0

        # 修复类定义后的冒号
        content = re.sub(r"(class\s+\w+\([^)]*\))\s*\n", r"\1:\n", content)

        # 修复函数定义后的冒号
        content = re.sub(
            r"(def\s+\w+\([^)]*\)(?:\s*->\s*[^:]+)?)\s*\n", r"\1:\n", content
        )

        # 修复 if/for/while/try/except/finally 后的冒号
        keywords = [
            "if",
            "elif",
            "else",
            "for",
            "while",
            "try",
            "except",
            "finally",
            "with",
        ]
        for keyword in keywords:
            pattern = f"({keyword}\\s+[^:\\n]+)\\s*\\n(?=\\s|\\n|$)"
            content = re.sub(pattern, r"\1:\n", content)

        if content != original:
            fixes += 1

        return content, fixes

    def fix_string_quotes(self, content: str) -> Tuple[str, int]:
        """修复字符串引号问题"""
        fixes = 0

        lines = content.split("\n")
        for i, line in enumerate(lines):
            # 修复文档字符串
            if '"""' in line and not line.strip().endswith('"""'):
                # 如果行首有 """ 但行尾没有，添加闭合
                if line.strip().startswith('"""') and '"""' not in line.strip()[3:]:
                    line = line.rstrip() + '"""'
                    fixes += 1

            # 修复单引号字符串
            elif line.count("'") % 2 == 1 and not line.strip().startswith("#"):
                # 如果有奇数个单引号，添加一个
                line = line.rstrip() + "'"
                fixes += 1

            lines[i] = line

        return "\n".join(lines), fixes

    def fix_line_breaks(self, content: str) -> Tuple[str, int]:
        """修复语句换行问题"""
        original = content
        fixes = 0

        # 在某些运算符后添加换行
        operators = ["except", "raise", "return", "yield", "pass", "break", "continue"]

        for op in operators:
            # 修复 pattern: try:something -> try:\n    something
            content = re.sub(f"({op})([^\\n])", "\\1:\\n\\2", content)

        # 修复多个语句在同一行的情况
        content = re.sub(r";\s*([a-zA-Z_])", r";\n\1", content)

        if content != original:
            fixes += 1

        return content, fixes

    def fix_indentation(self, content: str) -> Tuple[str, int]:
        """修复缩进问题"""
        lines = content.split("\n")
        fixed_lines = []
        fixes = 0

        # 基本缩进级别
        base_indent = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 跳过空行和注释
            if not stripped or stripped.startswith("#"):
                fixed_lines.append(line)
                continue

            # 计算当前缩进
            current_indent = len(line) - len(line.lstrip())

            # 检查是否需要缩进（某些关键字后）
            keywords_needing_indent = [
                "except",
                "raise",
                "return",
                "pass",
                "break",
                "continue",
            ]
            for keyword in keywords_needing_indent:
                if stripped.startswith(keyword) and current_indent == base_indent:
                    # 需要缩进
                    line = "    " + line
                    fixes += 1
                    break

            fixed_lines.append(line)

        return "\n".join(fixed_lines), fixes

    def fix_specific_patterns(self, content: str) -> Tuple[str, int]:
        """修复特定的错误模式"""
        original = content
        fixes = 0

        # 修复 @abstractmethodasync 的错误
        content = re.sub(r"@abstractmethodasync", "@abstractmethod\nasync", content)

        # 修复 except 后面的错误
        content = re.sub(
            r"except\s*\(\s*([^)]+)\s*\)([^\\n])", r"except (\1):\n    \2", content
        )

        # 修复字典返回值
        content = re.sub(r"return\s*\{([^}]+),\s*\)", r"return {\1}", content)

        # 修复 if raise 连在一起的情况
        content = re.sub(r"if\s+([^:]+)raise", r"if \1:\n        raise", content)

        if content != original:
            fixes += 1

        return content, fixes

    def fix_file(self, file_path: Path) -> bool:
        """修复单个文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original = content
            total_fixes = 0

            # 应用所有修复
            content, fixes = self.fix_bracket_issues(content)
            total_fixes += fixes

            content, fixes = self.fix_missing_colons(content)
            total_fixes += fixes

            content, fixes = self.fix_string_quotes(content)
            total_fixes += fixes

            content, fixes = self.fix_line_breaks(content)
            total_fixes += fixes

            content, fixes = self.fix_indentation(content)
            total_fixes += fixes

            content, fixes = self.fix_specific_patterns(content)
            total_fixes += fixes

            # 保存修复后的文件
            if content != original:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                self.fixed_files.append(str(file_path))
                self.total_fixes += total_fixes
                print(
                    f"✅ 修复 {file_path.relative_to(Path.cwd())} ({total_fixes} 处修复)"
                )
                return True
            else:
                print(f"ℹ️ 无需修复 {file_path.relative_to(Path.cwd())}")
                return False

        except Exception as e:
            print(f"❌ 修复失败 {file_path}: {e}")
            self.failed_files.append(str(file_path))
            return False

    def fix_multiple_files(
        self, pattern: str = "**/*.py", max_files: int = 100
    ) -> dict:
        """批量修复文件"""
        print("🔧 开始批量修复语法错误...")
        print(f"搜索模式: {pattern}")
        print(f"最大文件数: {max_files}")

        # 查找文件
        files = list(self.src_dir.glob(pattern))

        # 按优先级排序（先修复核心模块）
        priority_dirs = [
            "api",
            "services",
            "database",
            "cache",
            "monitoring",
            "adapters",
        ]

        def get_priority(file_path: Path) -> int:
            for i, dir_name in enumerate(priority_dirs):
                if dir_name in file_path.parts:
                    return i
            return len(priority_dirs)

        files.sort(key=get_priority)

        # 限制文件数量
        files_to_fix = files[:max_files]

        print(f"\n找到 {len(files)} 个文件，修复前 {len(files_to_fix)} 个\n")

        # 逐个修复
        for file_path in files_to_fix:
            self.fix_file(file_path)

        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(files),
            "processed_files": len(files_to_fix),
            "fixed_files": len(self.fixed_files),
            "failed_files": len(self.failed_files),
            "total_fixes": self.total_fixes,
            "fixed_files_list": self.fixed_files[:20],  # 只显示前20个
            "failed_files_list": self.failed_files[:20],
        }

        self.print_report(report)
        return report

    def print_report(self, report: dict):
        """打印修复报告"""
        print("\n" + "=" * 60)
        print("📋 批量语法修复报告")
        print("=" * 60)

        print("\n📊 统计:")
        print(f"  - 总文件数: {report['total_files']}")
        print(f"  - 处理文件数: {report['processed_files']}")
        print(f"  - 成功修复: {report['fixed_files']}")
        print(f"  - 修复失败: {report['failed_files']}")
        print(f"  - 总修复数: {report['total_fixes']}")

        if report["fixed_files_list"]:
            print("\n✅ 已修复的部分文件:")
            for file_path in report["fixed_files_list"]:
                print(f"  - {file_path}")
            if report["fixed_files"] > len(report["fixed_files_list"]):
                print(
                    f"  ... 还有 {report['fixed_files'] - len(report['fixed_files_list'])} 个文件"
                )

        if report["failed_files_list"]:
            print("\n❌ 修复失败的部分文件:")
            for file_path in report["failed_files_list"]:
                print(f"  - {file_path}")
            if report["failed_files"] > len(report["failed_files_list"]):
                print(
                    f"  ... 还有 {report['failed_files'] - len(report['failed_files_list'])} 个文件"
                )

        # 保存报告
        import json

        report_file = Path("batch_syntax_fix_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="批量修复Python语法错误")
    parser.add_argument("--src", default="src", help="源代码目录")
    parser.add_argument("--pattern", default="**/*.py", help="文件匹配模式")
    parser.add_argument("--max-files", type=int, default=100, help="最大修复文件数")

    args = parser.parse_args()

    fixer = BatchSyntaxFixer(args.src)
    fixer.fix_multiple_files(args.pattern, args.max_files)

    print("\n下一步:")
    print("1. 运行测试: python -m pytest tests/unit/ -x --tb=short")
    print("2. 检查覆盖率: python scripts/coverage_monitor.py")
    print("3. 如需继续修复: python scripts/batch_fix_syntax.py --max-files 100")


if __name__ == "__main__":
    main()
