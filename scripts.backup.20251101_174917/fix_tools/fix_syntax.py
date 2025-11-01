#!/usr/bin/env python3
"""
智能语法修复器 - 专注于最常见且可修复的语法错误模式
"""

import re
from pathlib import Path
from typing import List


class SmartSyntaxFixer:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.fixes_applied = []

    def fix_common_patterns(self, content: str) -> str:
        """修复最常见的语法错误模式"""

        # 模式1: 字典中缺少冒号
        content = self.fix_missing_colons(content)

        # 模式2: 括号不匹配 (简单情况)
        content = self.fix_bracket_mismatches(content)

        # 模式3: 引号不匹配
        content = self.fix_quote_mismatches(content)

        # 模式4: 缺少逗号
        content = self.fix_missing_commas(content)

        # 模式5: 函数/类定义缺少冒号
        content = self.fix_missing_definition_colons(content)

        return content

    def fix_missing_colons(self, content: str) -> str:
        """修复字典中缺少的冒号"""
        # 匹配模式: "key" "value" -> "key": "value"
        pattern = r'("[^"]+")\s+([^"}\],]+?)(?=[,}\]])'

        def replacer(match):
            key, value = match.groups()
            # 确保value不是数字或已有冒号
            if not value.strip().isdigit() and ":" not in value:
                self.fixes_applied.append(f"Added colon between {key} and {value}")
                return f"{key}: {value}"
            return match.group(0)

        return re.sub(pattern, replacer, content)

    def fix_bracket_mismatches(self, content: str) -> str:
        """修复简单的括号不匹配"""
        # 修复: {"key": [value)} -> {"key": "value"}
        content = re.sub(r'\{("[^"]+":)\s*\[([^\]]+)\)', r'{\1 "\2"}', content)
        # 修复: ["value"] -> "value" (在某些上下文中)
        content = re.sub(r'\[("[^"]+")\]', r"\1", content)

        return content

    def fix_quote_mismatches(self, content: str) -> str:
        """修复引号问题"""
        # 修复: {key: "value"} -> {"key": "value"}
        content = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*):", r'{"\1":', content)
        # 修复: [value] -> "value" (简单字符串)
        content = re.sub(r"\[([a-zA-Z_][a-zA-Z0-9_]*)\]", r'"\1"', content)

        return content

    def fix_missing_commas(self, content: str) -> str:
        """修复缺少的逗号"""
        # 在字典项之间添加逗号
        content = re.sub(r'("[^"]+":\s*[^,}]+?)(\s*"[^"]+":)', r"\1,\2", content)

        return content

    def fix_missing_definition_colons(self, content: str) -> str:
        """修复函数/类定义缺少的冒号"""
        lines = content.split("\n")
        fixed_lines = []

        for line in lines:
            # 检查是否是函数/类定义且缺少冒号
            if re.match(r"\s*(def\s+\w+\([^)]*\)|class\s+\w+[^:]*)\s*$", line):
                if not line.rstrip().endswith(":"):
                    line += ":"
                    self.fixes_applied.append("Added colon to function/class definition")
            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def apply_fixes(self) -> bool:
        """应用修复并保存文件"""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()

            fixed_content = self.fix_common_patterns(content)

            if fixed_content != content:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)
                return True
            return False
        except Exception as e:
            print(f"Error fixing {self.file_path}: {e}")
            return False


def fix_files_in_batch(directory: str, max_files: int = 10) -> List[str]:
    """批量修复文件"""
    dir_path = Path(directory)
    fixed_files = []

    for i, file_path in enumerate(dir_path.rglob("*.py")):
        if i >= max_files:
            break

        print(f"🔧 修复 {file_path.relative_to(dir_path)}...")
        fixer = SmartSyntaxFixer(file_path)
        if fixer.apply_fixes():
            fixed_files.append(str(file_path.relative_to(dir_path)))
            print(f"  ✅ 修复成功: {', '.join(fixer.fixes_applied)}")
        else:
            print("  ⏭️  无需修复或修复失败")

    return fixed_files


if __name__ == "__main__":
    import sys

    directory = sys.argv[1] if len(sys.argv) > 1 else "tests/unit"
    max_files = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    print(f"🔧 开始智能语法修复，最多处理 {max_files} 个文件...")
    fixed = fix_files_in_batch(directory, max_files)
    print(f"✅ 修复完成，成功修复 {len(fixed)} 个文件")
