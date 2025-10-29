#!/usr/bin/env python3
"""
改进的语法修复工具
解决路径问题，优化修复逻辑
"""

import os
import re
from pathlib import Path
from typing import List, Tuple
from datetime import datetime


class ImprovedSyntaxFixer:
    """改进的语法修复器"""

    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path.cwd() / src_dir  # 使用绝对路径
        self.fixed_files = []
        self.failed_files = []
        self.total_fixes = 0

    def fix_all_patterns(self, content: str) -> Tuple[str, int]:
        """应用所有修复模式"""
        original = content
        fixes = 0

        # 1. 修复 __all__ = [) 的问题
        if "__all__ = [)" in content:
            content = content.replace("__all__ = [)", "__all__ = [")
            fixes += 1

        # 2. 修复字典和列表的括号问题
        # 查找 {"key": value,) 的模式
        content = re.sub(r"\{([^}]+),\s*\)", r"{\1}", content)
        # 查找 [item,) 的模式
        content = re.sub(r"\[([^\]]+),\s*\]", r"[\1]", content)

        # 3. 修复缺少的冒号
        # 类定义
        content = re.sub(r"(class\s+\w+\([^)]*\))\s*\n", r"\1:\n", content)
        # 函数定义
        content = re.sub(r"(def\s+\w+\([^)]*\)(?:\s*->\s*[^:]+)?)\s*\n", r"\1:\n", content)
        # try/except/finally
        content = re.sub(
            r"\b(try|except|finally|else|elif|if|for|while|with)\b\s*([^\n:])",
            r"\1:\2",
            content,
        )

        # 4. 修复文档字符串
        content = re.sub(r'""""([^"]*)""', r'"""\n\1"""', content)
        content = re.sub(r"''''([^']*)''", r"'''\n\1'''", content)

        # 5. 修复 @abstractmethodasync 问题
        content = content.replace("@abstractmethodasync", "@abstractmethod\nasync")

        # 6. 修复缺少闭合的括号（简单情况）
        lines = content.split("\n")
        for i, line in enumerate(lines):
            # 检查未闭合的圆括号
            open_parens = line.count("(") - line.count(")")
            if open_parens > 0 and not line.strip().startswith("#"):
                line = line + ")" * open_parens
                lines[i] = line
                fixes += 1

        content = "\n".join(lines)

        # 7. 修复 return 语句中的问题
        content = re.sub(r"return\s*\{([^}]+),\s*\)", r"return {\1}", content)
        content = re.sub(r"return\s*\[([^\]]+),\s*\]", r"return [\1]", content)

        # 8. 修复缩进问题（基本修复）
        lines = content.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                # 确保基本缩进正确
                if any(stripped.startswith(kw) for kw in ["except", "elif:", "else:", "finally:"]):
                    if not line.startswith("    ") and not line.startswith("\t"):
                        lines[i] = "    " + line

        content = "\n".join(lines)

        # 计算总修复数
        if content != original:
            fixes = content.count("\n") - original.count("\n")  # 简单估算
            if fixes < 1:
                fixes = 1

        return content, fixes

    def fix_file(self, file_path: Path) -> bool:
        """修复单个文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 应用修复
            fixed_content, fixes = self.fix_all_patterns(content)

            # 保存修复后的文件
            if fixed_content != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)

                self.fixed_files.append(str(file_path.relative_to(Path.cwd())))
                self.total_fixes += fixes
                print(f"✅ 修复 {file_path.relative_to(Path.cwd())} ({fixes} 处)")
                return True
            else:
                return False

        except Exception as e:
            print(f"❌ 修复失败 {file_path}: {e}")
            self.failed_files.append(str(file_path.relative_to(Path.cwd())))
            return False

    def scan_and_fix(self, max_files: int = 100) -> dict:
        """扫描并修复文件"""
        print("🔧 开始扫描和修复...")
        print(f"源码目录: {self.src_dir}")
        print(f"最大文件数: {max_files}")

        # 查找所有Python文件
        python_files = list(self.src_dir.rglob("*.py"))
        print(f"找到 {len(python_files)} 个Python文件")

        # 优先修复核心模块
        priority_patterns = [
            "api/**/*.py",
            "services/**/*.py",
            "database/**/*.py",
            "adapters/**/*.py",
            "core/**/*.py",
        ]

        # 收集优先文件
        priority_files = []
        for pattern in priority_patterns:
            priority_files.extend(list(self.src_dir.glob(pattern)))

        # 去重并添加其他文件
        all_files = priority_files + [f for f in python_files if f not in priority_files]

        # 限制文件数量
        files_to_fix = all_files[:max_files]

        print(f"\n开始修复前 {len(files_to_fix)} 个文件...\n")

        # 逐个修复
        for file_path in files_to_fix:
            if file_path.exists():
                self.fix_file(file_path)

        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(python_files),
            "processed_files": len(files_to_fix),
            "fixed_files": len(self.fixed_files),
            "failed_files": len(self.failed_files),
            "total_fixes": self.total_fixes,
            "fixed_files_list": self.fixed_files[:10],
            "failed_files_list": self.failed_files[:10],
        }

        self.print_report(report)
        return report

    def print_report(self, report: dict):
        """打印修复报告"""
        print("\n" + "=" * 60)
        print("📋 改进的语法修复报告")
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

        report_file = Path("improved_fix_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="改进的Python语法修复工具")
    parser.add_argument("--src", default="src", help="源代码目录")
    parser.add_argument("--max-files", type=int, default=100, help="最大修复文件数")

    args = parser.parse_args()

    fixer = ImprovedSyntaxFixer(args.src)
    fixer.scan_and_fix(args.max_files)

    print("\n下一步:")
    print("1. 运行测试: python -m pytest tests/unit/ -x --tb=short")
    print("2. 继续修复: python scripts/improved_fix.py --max-files 100")


if __name__ == "__main__":
    main()
