#!/usr/bin/env python3
"""
修复剩余的语法错误，特别是未匹配的括号问题
"""

import re
from pathlib import Path


def fix_bracket_issues(content: str) -> str:
    """修复括号匹配问题"""

    # 修复常见的括号不匹配问题
    patterns = [
        # 修复 [] 不匹配
        (r"\[\s*\]", "[]"),
        (r'\[\s*["\']([^"\']*)["\']\s*\]', r'["\1"]'),
        (r"\[\s*([^\]]+)\s*\]", r"[\1]"),
        # 修复 "][" 模式
        (r'"\]\["', '""'),
        # 修复尾随的 ]
        (r"(\])\s*$", r"\1"),
        # 修复不匹配的括号组合
        (r'\]\s*\["', '""'),
        (r"\]\s*\'[", '""'),
        # 修复 try/except 块中的语法问题
        (r"except\s*:\s*$", "except:\n        pass"),
        (r'except\s*:\s*["\'][^"\']*["\']\s*$', "except:\n        pass"),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    return content


def fix_remaining_syntax_errors(file_path: Path) -> bool:
    """修复文件中剩余的语法错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 应用括号修复
        content = fix_bracket_issues(content)

        # 修复特定的问题文件
        if "test_tasks_maintenance_tasks.py" in str(file_path):
            # 专门处理这个文件的特定问题
            content = re.sub(
                r'\[\s*["\'][^"\']*["\']\s*\]\s*as\s*mock_[^:]*:\s*[^:]*:\s*[^:]*:',
                "mock_db.return_value = Mock()",
                content,
            )

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed remaining syntax errors in: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """主函数"""
    print("修复剩余的语法错误...")

    # 优先处理 auto_generated 目录
    auto_gen_dir = Path("tests/auto_generated")
    if auto_gen_dir.exists():
        fixed_count = 0
        for py_file in auto_gen_dir.rglob("*.py"):
            if fix_remaining_syntax_errors(py_file):
                fixed_count += 1
        print(f"在 auto_generated 中修复了 {fixed_count} 个文件")

    print("剩余语法错误修复完成！")


if __name__ == "__main__":
    main()
