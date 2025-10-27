#!/usr/bin/env python3
"""
目标模块修复工具
专门修复 database/, adapters/, monitoring/ 模块
"""

import os
import re
from pathlib import Path
from typing import List, Tuple
from datetime import datetime


class TargetedSyntaxFixer:
    """目标模块语法修复器"""

    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path.cwd() / src_dir
        self.fixed_files = []
        self.failed_files = []
        self.total_fixes = 0

    def fix_complex_patterns(self, content: str) -> Tuple[str, int]:
        """修复复杂的语法错误模式"""
        original = content
        fixes = 0

        # 1. 修复 return 语句格式
        lines = content.split("\n")
        for i, line in enumerate(lines):
            # 修复 return: { 这样的格式
            if "return:" in line and "{" in line and "}" not in line:
                # 查找下一行是否包含 }
                if i + 1 < len(lines) and "}" in lines[i + 1]:
                    # 合并两行
                    line = line.replace("return:", "return")
                    lines[i] = line
                    lines[i + 1] = "    " + lines[i + 1].strip()
                    fixes += 1

        content = "\n".join(lines)

        # 2. 修复函数调用格式
        content = re.sub(r"(\w+)\s*\(\s*([^)]+)\s*\)\s*\)", r"\1(\2)", content)

        # 3. 修复 if 语句
        content = re.sub(r"if\s*([^:]+)\s*:\s*\n\s*([^\n])", r"if \1:\n    \2", content)

        # 4. 修复字典格式
        content = re.sub(r"\{\s*([^}]+)\s*:\s*\n\s*", r"{\1: ", content)

        # 5. 修复方法调用中的多余冒号
        content = re.sub(r"(\.\w+)\s*:\s*\n", r"\1\n", content)

        # 6. 修复类定义
        content = re.sub(
            r'class\s+(\w+)\s*\([^)]*\)\s*:\s*\n\s*"""',
            r'class \1(\1):\n    """',
            content,
        )

        # 7. 修复导入语句
        content = re.sub(
            r"from\s+([^\s]+)\s+import\s+([^\n:]+)\s*:\s*\n",
            r"from \1 import \2\n",
            content,
        )

        # 8. 修复异常处理
        content = re.sub(
            r"except\s*\([^)]+\)\s*:\s*\n\s*([^\n])", r"except (\1):\n    \2", content
        )

        # 计算修复数
        if content != original:
            fixes = 1

        return content, fixes

    def fix_file(self, file_path: Path) -> bool:
        """修复单个文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 应用基础修复
            content = self.fix_basic_patterns(content)

            # 应用复杂修复
            fixed_content, fixes = self.fix_complex_patterns(content)

            # 保存修复后的文件
            if fixed_content != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)

                self.fixed_files.append(str(file_path.relative_to(Path.cwd())))
                self.total_fixes += fixes
                print(f"✅ 修复 {file_path.relative_to(Path.cwd())}")
                return True
            else:
                return False

        except Exception as e:
            print(f"❌ 修复失败 {file_path}: {e}")
            self.failed_files.append(str(file_path.relative_to(Path.cwd())))
            return False

    def fix_basic_patterns(self, content: str) -> str:
        """基础修复模式"""
        # 1. 修复 __all__ 问题
        content = content.replace("__all__ = [)", "__all__ = [")

        # 2. 修复缺少的冒号
        content = re.sub(r"(class\s+\w+\([^)]*\))\s*\n", r"\1:\n", content)
        content = re.sub(r"(def\s+\w+\([^)]*\))\s*\n", r"\1:\n", content)

        # 3. 修复文档字符串
        content = re.sub(r'""""([^"]*)""', r'"""\n\1"""', content)

        # 4. 修复括号
        content = re.sub(r"\{([^}]+),\s*\)", r"{\1}", content)
        content = re.sub(r"\[([^\]]+),\s*\]", r"[\1]", content)

        return content

    def scan_and_fix_target_modules(self) -> dict:
        """扫描并修复目标模块"""
        print("🎯 开始修复目标模块...")

        # 目标模块
        target_modules = [
            "database/**/*.py",
            "adapters/**/*.py",
            "monitoring/**/*.py",
            "cache/**/*.py",
            "collectors/**/*.py",
            "tasks/**/*.py",
        ]

        all_files = []
        for pattern in target_modules:
            files = list(self.src_dir.glob(pattern))
            all_files.extend(files)

        # 去重
        all_files = list(set(all_files))
        print(f"找到 {len(all_files)} 个目标模块文件")

        # 逐个修复
        for file_path in all_files:
            if file_path.exists():
                self.fix_file(file_path)

        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "target_modules": target_modules,
            "total_files": len(all_files),
            "fixed_files": len(self.fixed_files),
            "failed_files": len(self.failed_files),
            "total_fixes": self.total_fixes,
            "fixed_files_list": self.fixed_files[:20],
            "failed_files_list": self.failed_files[:10],
        }

        self.print_report(report)
        return report

    def print_report(self, report: dict):
        """打印修复报告"""
        print("\n" + "=" * 60)
        print("📋 目标模块修复报告")
        print("=" * 60)

        print("\n📊 统计:")
        print(f"  - 目标模块: {', '.join(report['target_modules'])}")
        print(f"  - 总文件数: {report['total_files']}")
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

        # 保存报告
        import json

        report_file = Path("targeted_fix_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")


def main():
    """主函数"""
    fixer = TargetedSyntaxFixer()
    fixer.scan_and_fix_target_modules()

    print("\n下一步:")
    print("1. 运行测试: python -m pytest tests/unit/ -x --tb=short")
    print("2. 继续修复: python scripts/improved_fix.py --max-files 100")


if __name__ == "__main__":
    main()
