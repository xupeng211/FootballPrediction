#!/usr/bin/env python3
"""
修复关键的lint错误
"""

import re
from pathlib import Path


def fix_test_retry_enhanced():
    """修复test_retry_enhanced.py中的语法错误"""
    file_path = Path("tests/unit/utils/test_retry_enhanced.py")

    if not file_path.exists():
        return False

    content = file_path.read_text(encoding="utf-8")

    # 修复注释的装饰器语法错误
    # 将 @# retry_with_backoff( 替换为简单的函数调用
    content = re.sub(
        r"        @# retry_with_backoff\(\s*\n(?:            [^\n]*\n)*?        \)",
        "        # retry_with_backoff call removed\n",
        content,
        flags=re.MULTILINE,
    )

    # 修复函数定义前的语法错误
    content = re.sub(r"\n        \n        def (test_\w+)", r"\n\n    def \1", content)

    # 修复缺失的类方法缩进
    content = re.sub(r"(\n    def test_\w+)", r"\n    def test_\w+", content)

    file_path.write_text(content, encoding="utf-8")
    return True


def fix_test_monitoring_coverage():
    """修复test_monitoring_coverage.py中的语法错误"""
    file_path = Path("tests/unit/api/tests/unit/api/test_monitoring_coverage.py")

    if not file_path.exists():
        return False

    content = file_path.read_text(encoding="utf-8")

    lines = content.split("\n")
    fixed_lines = []
    in_imports = True

    for line in lines:
        stripped = line.strip()

        # 跳过空行和注释
        if not stripped or stripped.startswith("#"):
            if stripped and in_imports:
                # 遇到注释，结束导入部分
                in_imports = False
            fixed_lines.append(line)
            continue

        # 修复缩进问题
        if (
            line.startswith("    ")
            and in_imports
            and not stripped.startswith("import")
            and not stripped.startswith("from")
        ):
            # 这行不应该有缩进
            line = stripped

        # 检查是否是导入语句
        if stripped.startswith("import") or stripped.startswith("from"):
            # 确保没有缩进
            if line.startswith("    "):
                line = stripped
            fixed_lines.append(line)
        elif in_imports:
            # 第一个非导入行，结束导入部分
            in_imports = False
            fixed_lines.append("")
            fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    fixed_content = "\n".join(fixed_lines)
    file_path.write_text(fixed_content, encoding="utf-8")
    return True


def remove_unused_imports_in_try_blocks():
    """移除try块中的未使用导入"""
    # 这些文件中的try块导入实际上在代码中使用了，只是ruff没有正确识别
    # 我们保留这些导入，因为它们在条件代码块中使用
    pass


def main():
    """主函数"""
    print("修复关键的lint错误...")

    # 修复test_retry_enhanced.py
    if fix_test_retry_enhanced():
        print("  ✓ 修复了 tests/unit/utils/test_retry_enhanced.py")

    # 修复test_monitoring_coverage.py
    if fix_test_monitoring_coverage():
        print("  ✓ 修复了 tests/unit/api/tests/unit/api/test_monitoring_coverage.py")

    print("\n✅ 关键错误修复完成！")


if __name__ == "__main__":
    main()
