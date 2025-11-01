#!/usr/bin/env python3
"""
修复关键的类型安全问题
"""

import re
import os
from pathlib import Path


def fix_type_annotations(file_path):
    """修复常见的类型注解问题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, f"Error reading file: {e}"

    original_content = content
    changes_made = []

    # 修复1: __all__ 类型注解
    def fix_all_annotation(text):
        # __all__ = [module] → __all__: list[str] = [module]
        pattern = r"__all__\s*=\s*\[(.*?)\]"

        def replacement(m):
            return f"__all__: list[str] = [{m.group(1)}]"

        return re.sub(pattern, replacement, text, flags=re.DOTALL)

    new_content = fix_all_annotation(content)
    if new_content != content:
        changes_made.append("Fixed __all__ type annotation")

    # 修复2: 简单的返回类型问题
    def fix_return_types(text):
        # 修复常见的 None 返回类型问题
        fixes = [
            # def method() -> datetime: return None → def method() -> Optional[datetime]: return None
            (
                r"(def\s+\w+\([^)]*\)\s*->\s*datetime[^:]*:)(\s*return\s+None)",
                r"\1 | None\2",
            ),
            # def method() -> str: return None → def method() -> Optional[str]: return None
            (
                r"(def\s+\w+\([^)]*\)\s*->\s*str[^:]*:)(\s*return\s+None)",
                r"\1 | None\2",
            ),
            # def method() -> dict: return None → def method() -> Optional[dict]: return None
            (
                r"(def\s+\w+\([^)]*\)\s*->\s*dict[^:]*:)(\s*return\s+None)",
                r"\1 | None\2",
            ),
        ]

        for pattern, replacement in fixes:
            text = re.sub(pattern, replacement, text)
        return text

    new_content = fix_return_types(new_content)
    if new_content != content:
        changes_made.append("Fixed Optional return types")

    # 修复3: 简单的参数类型问题
    def fix_param_types(text):
        # 添加 Optional 类型到可能为 None 的参数
        # 这种修复比较复杂，暂时跳过
        return text

    new_content = fix_param_types(new_content)

    if new_content != original_content:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True, f"Fixed: {'; '.join(changes_made)}"
        except Exception as e:
            return False, f"Error writing file: {e}"
    else:
        return False, "No changes needed"


def fix_critical_files():
    """修复最关键的文件"""
    critical_files = [
        "src/services/processing/processors/odds/__init__.py",
        "src/services/processing/processors/features/__init__.py",
        "src/utils/time_utils.py",
        "src/core/di.py",
    ]

    fixed_count = 0
    failed_count = 0

    for file_path in critical_files:
        if os.path.exists(file_path):
            print(f"🔧 修复: {file_path}")
            success, message = fix_type_annotations(file_path)
            if success:
                fixed_count += 1
                print(f"   ✅ {message}")
            else:
                failed_count += 1
                print(f"   ❌ {message}")
        else:
            print(f"⚠️  文件不存在: {file_path}")

    print("\n📊 修复结果:")
    print(f"✅ 成功修复: {fixed_count} 个文件")
    print(f"❌ 修复失败: {failed_count} 个文件")


def main():
    """主函数"""
    print("🔧 开始修复关键类型安全问题...")

    # 修复关键文件
    fix_critical_files()


if __name__ == "__main__":
    main()
