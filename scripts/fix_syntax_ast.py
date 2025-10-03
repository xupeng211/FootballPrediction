#!/usr/bin/env python3
"""
AST 驱动的 Python 语法修复工具

专门修复 tests/unit 模块中的语法错误：
- 括号不匹配
- 引号缺失
- 逗号缺失
- 其他常见语法问题

使用方法：
python scripts/fix_syntax_ast.py [directory] [--max-files N] [--report FILE]
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set, Dict, Any
import argparse
import json
from datetime import datetime

class ASTSyntaxFixer:
    def __init__(self, directory: str, max_files: int = 50):
        self.directory = Path(directory)
        self.max_files = max_files
        self.fixed_files = set()
        self.unfixed_files = set()
        self.total_fixes = 0
        self.repair_stats = {
            'bracket_mismatch': 0,
            'missing_quotes': 0,
            'missing_commas': 0,
            'other_fixes': 0
        }

    def fix_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """使用 AST 修复单个文件的语法错误"""
        fixes = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            self.unfixed_files.add(str(file_path))
            return False, [f"Error reading file: {e}"]

        # 尝试解析 AST
        try:
            ast.parse(original_content)
            # 如果能成功解析，文件没有语法错误
            return True, ["No syntax errors found"]
        except SyntaxError as e:
            # 有语法错误，尝试修复
            fixed_content = self.fix_syntax_errors(original_content, e)

            if fixed_content == original_content:
                # 无法修复
                self.unfixed_files.add(str(file_path))
                return False, ["Could not fix syntax errors automatically"]

            # 验证修复后的代码
            try:
                ast.parse(fixed_content)
                # 修复成功，保存文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                self.fixed_files.add(str(file_path))
                return True, fixes
            except SyntaxError:
                # 修复失败，保持原样
                self.unfixed_files.add(str(file_path))
                return False, ["Fixed code still has syntax errors"]
        except Exception as e:
            self.unfixed_files.add(str(file_path))
            return False, [f"Unexpected error: {e}"]

    def fix_syntax_errors(self, content: str, error: SyntaxError) -> str:
        """基于语法错误类型进行修复"""
        lines = content.split('\n')
        error_line = error.lineno - 1 if error.lineno else 0

        if error_line >= len(lines):
            return content

        fixed_content = content

        # 根据错误信息选择修复策略
        error_msg = str(error).lower()

        if 'bracket' in error_msg or 'parenthesis' in error_msg or 'brace' in error_msg:
            fixed_content = self.fix_bracket_mismatch(content, error)
            self.repair_stats['bracket_mismatch'] += 1
        elif 'eol while scanning string literal' in error_msg:
            fixed_content = self.fix_missing_quotes(content, error)
            self.repair_stats['missing_quotes'] += 1
        elif 'invalid syntax' in error_msg and 'comma' in error_msg:
            fixed_content = self.fix_missing_commas(content, error)
            self.repair_stats['missing_commas'] += 1
        else:
            # 尝试通用修复
            fixed_content = self.fix_general_syntax(content, error)
            self.repair_stats['other_fixes'] += 1

        return fixed_content

    def fix_bracket_mismatch(self, content: str, error: SyntaxError) -> str:
        """修复括号不匹配问题"""
        lines = content.split('\n')
        if not error.lineno or error.lineno > len(lines):
            return content

        line_idx = error.lineno - 1
        line = lines[line_idx]

        # 检查常见的括号不匹配模式
        patterns = [
            # 模式 1: 缺少关闭括号
            (r'(\{[^}]*$)', r'\1}'),
            (r'(\[[^\]]*$)', r'\1]'),
            (r'(\([^)]*$)', r'\1)'),

            # 模式 2: 括号类型不匹配
            (r'(\{[^}]*)\]', r'\1}'),
            (r'(\[[^\]]*)\}', r'\1]'),
            (r'(\([^)]*)\]', r'\1)'),

            # 模式 3: 多余的关闭括号
            (r'(\})\s*([^{}]*$)', r'\2'),
            (r'(\])\s*([^\[\]]*$)', r'\2'),
            (r'(\))\s*([^()]*$)', r'\2'),
        ]

        fixed_line = line
        for pattern, replacement in patterns:
            if re.search(pattern, line):
                fixed_line = re.sub(pattern, replacement, line)
                break

        if fixed_line != line:
            lines[line_idx] = fixed_line
            return '\n'.join(lines)

        return content

    def fix_missing_quotes(self, content: str, error: SyntaxError) -> str:
        """修复缺失引号的问题"""
        lines = content.split('\n')
        if not error.lineno or error.lineno > len(lines):
            return content

        line_idx = error.lineno - 1
        line = lines[line_idx]

        # 模式：字典中缺少引号的键或值
        patterns = [
            # 模式 1: 字典键缺少引号
            (r'(\{\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3'),
            # 模式 2: 字符串值缺少引号
            (r'(:\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*[,\}])', r'\1"\2"\3'),
        ]

        fixed_line = line
        for pattern, replacement in patterns:
            if re.search(pattern, line):
                fixed_line = re.sub(pattern, replacement, line)
                break

        if fixed_line != line:
            lines[line_idx] = fixed_line
            return '\n'.join(lines)

        return content

    def fix_missing_commas(self, content: str, error: SyntaxError) -> str:
        """修复缺失逗号的问题"""
        lines = content.split('\n')
        if not error.lineno or error.lineno > len(lines):
            return content

        line_idx = error.lineno - 1
        line = lines[line_idx]

        # 模式：字典或列表元素间缺少逗号
        patterns = [
            # 字典项之间缺少逗号
            (r'("[^"]*":\s*[^,}]+)(\s*"[^"]*":)', r'\1,\2'),
            # 列表元素之间缺少逗号
            (r'([^,\[\]]+)(\s*[^,\[\]]+)(?=[^\]]*\])', r'\1,\2'),
        ]

        fixed_line = line
        for pattern, replacement in patterns:
            if re.search(pattern, line):
                fixed_line = re.sub(pattern, replacement, line)
                break

        if fixed_line != line:
            lines[line_idx] = fixed_line
            return '\n'.join(lines)

        return content

    def fix_general_syntax(self, content: str, error: SyntaxError) -> str:
        """通用语法修复"""
        lines = content.split('\n')
        if not error.lineno or error.lineno > len(lines):
            return content

        line_idx = error.lineno - 1
        line = lines[line_idx]

        # 通用修复模式
        patterns = [
            # 修复函数定义缺少冒号
            (r'(def\s+\w+\([^)]*\))\s*$', r'\1:'),
            # 修复类定义缺少冒号
            (r'(class\s+\w+\([^)]*\))\s*$', r'\1:'),
            # 修复 if 语句缺少冒号
            (r'(if\s+[^:]+)\s*$', r'\1:'),
            # 修复 for/while 语句缺少冒号
            (r'(for\s+[^:]+)\s*$', r'\1:'),
            (r'(while\s+[^:]+)\s*$', r'\1:'),
        ]

        fixed_line = line
        for pattern, replacement in patterns:
            if re.search(pattern, line):
                fixed_line = re.sub(pattern, replacement, line)
                break

        if fixed_line != line:
            lines[line_idx] = fixed_line
            return '\n'.join(lines)

        return content

    def get_problematic_files(self) -> List[Path]:
        """获取有语法错误的文件列表"""
        problematic_files = []

        for file_path in self.directory.rglob('*.py'):
            if len(problematic_files) >= self.max_files:
                break

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except (SyntaxError, Exception):
                problematic_files.append(file_path)

        return problematic_files

    def process_batch(self) -> Dict[str, Any]:
        """处理一批文件"""
        problematic_files = self.get_problematic_files()
        print(f"🔍 发现 {len(problematic_files)} 个有语法问题的文件")

        batch_results = {
            'processed_files': len(problematic_files),
            'fixed_files': 0,
            'unfixed_files': 0,
            'repair_stats': self.repair_stats.copy(),
            'batch_details': []
        }

        for i, file_path in enumerate(problematic_files[:self.max_files]):
            print(f"📄 [{i+1}/{min(len(problematic_files), self.max_files)}] 处理 {file_path.relative_to(self.directory)}...")

            success, fixes = self.fix_file(file_path)

            if success:
                batch_results['fixed_files'] += 1
                batch_results['batch_details'].append({
                    'file': str(file_path.relative_to(self.directory)),
                    'status': 'fixed',
                    'fixes': fixes
                })
                print(f"  ✅ 修复成功")
            else:
                batch_results['unfixed_files'] += 1
                batch_results['batch_details'].append({
                    'file': str(file_path.relative_to(self.directory)),
                    'status': 'unfixed',
                    'fixes': fixes
                })
                print(f"  ❌ 修复失败: {fixes[0] if fixes else 'Unknown error'}")

        return batch_results

    def generate_unfixed_report(self, report_file: str):
        """生成无法修复文件的报告"""
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# 🚫 无法修复的文件报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**处理目录**: {self.directory}\n")
            f.write(f"**无法修复文件数**: {len(self.unfixed_files)}\n\n")

            if self.unfixed_files:
                f.write("## 📋 无法修复的文件列表\n\n")
                for file_path in sorted(self.unfixed_files):
                    f.write(f"- `{file_path}`\n")

            f.write(f"\n## 📊 修复统计\n\n")
            f.write(f"- **总修复次数**: {sum(self.repair_stats.values())}\n")
            for fix_type, count in self.repair_stats.items():
                f.write(f"- **{fix_type}**: {count} 次\n")

def main():
    parser = argparse.ArgumentParser(description='AST 驱动的 Python 语法修复工具')
    parser.add_argument('directory', nargs='?', default='tests/unit', help='要修复的目录')
    parser.add_argument('--max-files', type=int, default=30, help='每批处理的文件数')
    parser.add_argument('--report', help='报告文件路径')
    parser.add_argument('--unfixed-report', default='docs/_reports/UNFIXED_FILES.md', help='无法修复文件报告')

    args = parser.parse_args()

    fixer = ASTSyntaxFixer(args.directory, args.max_files)

    print(f"🔧 开始修复 {args.directory} 中的语法错误...")
    print(f"📊 每批处理最多 {args.max_files} 个文件")

    batch_results = fixer.process_batch()

    print(f"\n🎯 批次修复结果:")
    print(f"📊 处理文件: {batch_results['processed_files']}")
    print(f"✅ 修复成功: {batch_results['fixed_files']}")
    print(f"❌ 修复失败: {batch_results['unfixed_files']}")

    print(f"\n🔧 修复统计:")
    for fix_type, count in batch_results['repair_stats'].items():
        print(f"- {fix_type}: {count}")

    # 生成报告
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(batch_results, f, indent=2, ensure_ascii=False)
        print(f"\n📄 批次报告已保存到: {args.report}")

    # 生成无法修复文件报告
    if fixer.unfixed_files:
        fixer.generate_unfixed_report(args.unfixed_report)
        print(f"📄 无法修复文件报告已保存到: {args.unfixed_report}")

if __name__ == "__main__":
    main()