#!/usr/bin/env python3
"""
精确修复关键的语法错误
"""

import re
import os
from pathlib import Path


def fix_critical_syntax_errors(file_path):
    """修复关键的语法错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, f"Error reading file: {e}"

    original_content = content
    changes_made = []

    # 修复字典语法错误
    # {"key": value,) → {"key": value}
    content = re.sub(r'\{"([^}"]+),\s*\}', r"{\1}", content)
    if content != original_content:
        changes_made.append("Fixed dictionary syntax")

    # 修复方法定义中的缺失冒号
    # def method(self) -> str"" pass → def method(self) -> str:\n    """docstring"""\n    pass
    content = re.sub(
        r'def (\w+)\(self[^)]*\) -> ([^:]+):\s*""([^"]*)"" pass',
        lambda m: f'def {m.group(1)}(self) -> {m.group(2)}:\n    """{m.group(3)}"""\n    pass',
        content,
    )
    if content != original_content:
        changes_made.append("Fixed method definitions")

    # 修复缺失的冒号在类定义中
    content = re.sub(
        r'def (\w+)\([^)]*\) -> ([^:\n]+)\s*\n\s*"""',
        lambda m: f'def {m.group(1)}(... ) -> {m.group(2)}:\n    """',
        content,
    )

    # 修复 __all__ 语法
    content = re.sub(r"__all__\s*=\s*\[\)", "__all__ = []", content)
    if content != original_content:
        changes_made.append("Fixed __all__ syntax")

    # 修复重复的return语句
    content = re.sub(r"return\s*\{[^}]*\}\s*return\s*\{", "return {", content)
    if content != original_content:
        changes_made.append("Fixed duplicate return statements")

    # 修复装饰器语法
    content = re.sub(r"@abstractmethodasync def", "@abstractmethod\n    async def", content)
    if content != original_content:
        changes_made.append("Fixed decorator syntax")

    if content != original_content:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, f"Fixed: {'; '.join(changes_made)}"
        except Exception as e:
            return False, f"Error writing file: {e}"
    else:
        return False, "No changes needed"


def main():
    """主函数"""
    print("🔧 开始修复关键语法错误...")

    src_dir = "/home/user/projects/FootballPrediction/src"

    # 首先修复已知的问题文件
    critical_files = [
        "src/adapters/base.py",
        "src/adapters/__init__.py",
    ]

    fixed_files = []
    failed_files = []

    for file_path in critical_files:
        full_path = os.path.join(src_dir, file_path)
        if os.path.exists(full_path):
            success, message = fix_critical_syntax_errors(full_path)
            if success:
                fixed_files.append((file_path, message))
                print(f"✅ Fixed: {file_path} - {message}")
            else:
                if "No changes needed" not in message:
                    failed_files.append((file_path, message))
                    print(f"❌ Failed: {file_path} - {message}")

    print("\n📊 修复结果:")
    print(f"✅ 成功修复: {len(fixed_files)} 个文件")
    print(f"❌ 修复失败: {len(failed_files)} 个文件")


if __name__ == "__main__":
    main()
