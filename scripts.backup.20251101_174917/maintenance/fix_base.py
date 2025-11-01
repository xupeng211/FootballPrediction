#!/usr/bin/env python3
"""修复base.py文件的语法错误"""

import re
from pathlib import Path


def fix_base_py():
    file_path = Path("src/database/base.py")

    if not file_path.exists():
        print(f"文件不存在: {file_path}")
        return

    content = file_path.read_text(encoding="utf-8")

    # 修复模式
    fixes = [
        # 修复函数定义格式
        (r"def update_from_dict\(\) ->  :\s*\n\s*self,", "def update_from_dict(self,"),
        (
            r"exclude_fields: set \| None = None\s*\)\s*-> None:",
            "exclude_fields: set | None = None) -> None:",
        ),
        # 修复docstring格式
        (
            r'"""从字典更新模型实例"""\s*\n\s*Args:',
            '"""从字典更新模型实例\n\n        Args:',
        ),
        (r"default = \{\}\s*\n\s*for:key,", "default = {}\n        for key,"),
        (
            r"if:key in valid_fields and key not in exclude_fields:",
            "if key in valid_fields and key not in exclude_fields:",
        ),
        (
            r"setattr\(self, key, value\)\s*\n\s*\}\s*\n\s*def __repr__\(self\) -> str:",
            "setattr(self, key, value)\n\n    def __repr__(self) -> str:",
        ),
        # 修复return语句
        (
            r'return:\s*f"<{self\.__class_\.__name__\}\(id={self\.id\)>',
            'return f"<{self.__class__.__name__}(id={self.id})>"',
        ),
    ]

    original_content = content
    fix_count = 0

    for pattern, replacement in fixes:
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        if new_content != content:
            matches = re.findall(pattern, content)
            fix_count += len(matches) if matches else 1
            content = new_content

    # 修复其他常见问题
    content = re.sub(r"if:exclude_fields", "if exclude_fields", content)
    content = re.sub(r"for:column", "for column", content)
    content = re.sub(r"if:column_name", "if column_name", content)
    content = re.sub(r"if:isinstance", "if isinstance", content)
    content = re.sub(r"return:\s*\n", "return ", content)
    content = re.sub(r"for:column in", "for column in", content)

    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        print(f"✅ 修复了 {file_path}，应用了 {fix_count} 个修复")
    else:
        print(f"⚪ 文件 {file_path} 无需修复")


if __name__ == "__main__":
    fix_base_py()
