#!/usr/bin/env python3
"""
Week 3: 字符串字面量修复工具
专门处理unterminated string literal错误
"""

import os
import re
from pathlib import Path

class StringLiteralFixer:
    def __init__(self):
        self.fixed_files = []
        self.failed_files = []

    def fix_file(self, file_path: str) -> bool:
        """修复单个文件的字符串字面量错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            fixed_lines = []

            for line in lines:
                # 跳过错误消息行
                if 'unterminated string literal' in line:
                    continue

                # 修复引号不匹配
                quote_count = line.count('"')
                if quote_count % 2 == 1:
                    # 奇数个引号，需要添加闭合引号
                    if line.strip().endswith(','):
                        line = line.rstrip() + '",'
                    else:
                        line = line.rstrip() + '"'

                # 修复三引号字符串
                if '"""' in line:
                    triple_quote_count = line.count('"""')
                    if triple_quote_count % 2 == 1 and not line.strip().endswith('"""'):
                        line = line.rstrip() + '"""'

                fixed_lines.append(line)

            fixed_content = '\n'.join(fixed_lines)

            # 验证修复结果
            try:
                compile(fixed_content, file_path, 'exec')
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"✅ {file_path}: 字符串修复成功")
                self.fixed_files.append(file_path)
                return True
            except SyntaxError:
                print(f"❌ {file_path}: 仍有其他语法错误")
                self.failed_files.append(file_path)
                return False

        except Exception as e:
            print(f"❌ {file_path}: 处理异常 - {e}")
            self.failed_files.append(file_path)
            return False

    def fix_directory(self, directory: str) -> None:
        """修复目录下的所有Python文件"""
        python_files = list(Path(directory).rglob("*.py"))

        print("🔧 开始修复字符串字面量错误")
        print(f"📁 目标目录: {directory}")
        print(f"📂 发现 {len(python_files)} 个Python文件")
        print("=" * 60)

        for file_path in python_files:
            self.fix_file(str(file_path))

        self.print_summary()

    def print_summary(self) -> None:
        """打印修复摘要"""
        print("=" * 60)
        print("📊 字符串字面量修复摘要")
        print("=" * 60)
        print(f"✅ 修复成功: {len(self.fixed_files)} 个文件")
        print(f"❌ 修复失败: {len(self.failed_files)} 个文件")

        total_files = len(self.fixed_files) + len(self.failed_files)
        if total_files > 0:
            success_rate = len(self.fixed_files) / total_files * 100
            print(f"📈 修复成功率: {success_rate:.1f}%")

        print("=" * 60)

def main():
    import sys

    fixer = StringLiteralFixer()

    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "src"

    if not os.path.exists(directory):
        print(f"❌ 目录不存在: {directory}")
        return

    fixer.fix_directory(directory)

if __name__ == "__main__":
    main()