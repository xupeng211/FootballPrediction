#!/usr/bin/env python3
"""
🔧 全面语法错误修复工具
Phase G最终阶段 - 解决项目中所有剩余的语法错误

基于前面成功的isinstance修复经验，扩展修复范围到所有语法问题
"""

import ast
import re
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import json

@dataclass
class FixResult:
    """修复结果数据结构"""
    file_path: str
    original_error: Optional[str]
    fix_applied: Optional[str]
    success: bool
    fix_count: int

class ComprehensiveSyntaxFixer:
    """全面语法错误修复器"""

    def __init__(self):
        self.fix_results = []
        self.fix_statistics = {
            'total_files': 0,
            'successful_fixes': 0,
            'failed_fixes': 0,
            'total_fixes_applied': 0,
            'error_types_found': {}
        }
        self.fix_patterns = {
            'isinstance': self._fix_isinstance_errors,
            'unclosed_brackets': self._fix_unclosed_brackets,
            'missing_colons': self._fix_missing_colons,
            'indentation': self._fix_indentation_errors,
            'unclosed_strings': self._fix_unclosed_strings,
            'invalid_f_string': self._fix_f_string_errors,
            'import_errors': self._fix_import_errors,
            'syntax_cleaner': self._clean_syntax_errors
        }

    def fix_project_syntax(self, source_dir: str = "src") -> Dict:
        """修复整个项目的语法错误"""
        print("🔧 启动全面语法错误修复...")
        print("=" * 60)

        source_path = Path(source_dir)
        if not source_path.exists():
            print(f"❌ 目录不存在: {source_dir}")
            return self.fix_statistics

        # 获取所有Python文件
        python_files = list(source_path.rglob("*.py"))
        self.fix_statistics['total_files'] = len(python_files)
        print(f"📂 发现 {len(python_files)} 个Python文件")

        # 批量处理文件
        batch_size = 50
        for i in range(0, len(python_files), batch_size):
            batch = python_files[i:i+batch_size]
            print(f"\n🔄 处理批次 {i//batch_size + 1}/{(len(python_files)-1)//batch_size + 1} ({len(batch)} 个文件)")

            for file_path in batch:
                if self._should_skip_file(file_path):
                    continue

                result = self._fix_file_syntax(file_path)
                self.fix_results.append(result)
                self._update_statistics(result)

        # 生成修复报告
        self._generate_fix_report()

        return self.fix_statistics

    def _should_skip_file(self, file_path: Path) -> bool:
        """判断是否应该跳过文件"""
        skip_patterns = [
            "__pycache__",
            ".pytest_cache",
            "htmlcov",
            ".coverage",
            "site-packages",
            ".git",
            "migrations/versions",  # 跳过数据库迁移版本文件
            "venv",
            "env"
        ]

        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)

    def _fix_file_syntax(self, file_path: Path) -> FixResult:
        """修复单个文件的语法错误"""
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # 尝试解析原始内容
            try:
                ast.parse(original_content)
                return FixResult(str(file_path), None, None, True, 0)
            except SyntaxError as e:
                original_error = str(e)

            # 应用修复模式
            fixed_content = original_content
            fixes_applied = 0
            last_fix = None

            for fix_name, fix_function in self.fix_patterns.items():
                try:
                    new_content, fix_count = fix_function(fixed_content)
                    if fix_count > 0:
                        fixed_content = new_content
                        fixes_applied += fix_count
                        last_fix = fix_name

                        # 记录错误类型
                        if fix_name not in self.fix_statistics['error_types_found']:
                            self.fix_statistics['error_types_found'][fix_name] = 0
                        self.fix_statistics['error_types_found'][fix_name] += 1

                except Exception as e:
                    print(f"   ⚠️ {fix_name} 修复失败 {file_path.name}: {e}")
                    continue

            # 验证修复结果
            try:
                ast.parse(fixed_content)
                # 写入修复后的内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)

                print(f"   ✅ {file_path.name} - 修复成功 ({fixes_applied}处修复, {last_fix})")
                return FixResult(str(file_path), original_error, last_fix, True, fixes_applied)

            except SyntaxError as e:
                print(f"   ❌ {file_path.name} - 修复失败: {e}")
                return FixResult(str(file_path), original_error, None, False, fixes_applied)

        except Exception as e:
            print(f"   ❌ {file_path.name} - 处理异常: {e}")
            return FixResult(str(file_path), str(e), None, False, 0)

    def _fix_isinstance_errors(self, content: str) -> Tuple[str, int]:
        """修复isinstance语法错误"""
        fixes = 0
        fixed_content = content

        # 模式1: isinstance(x, (type1, type2, type3)) -> isinstance(x, (type1, type2))
        pattern1 = r'\bisinstance\s*\(\s*([^,]+),\s*\(\s*([^)]+)\s*\)\s*\)'
        def fix_isinstance_triple(match):
            nonlocal fixes
            obj = match.group(1).strip()
            types_str = match.group(2).strip()
            types = [t.strip() for t in types_str.split(',') if t.strip()]
            if len(types) > 2:
                types = types[:2]
                fixes += 1
            return f"isinstance({obj}, ({', '.join(types)}))"

        fixed_content = re.sub(pattern1, fix_isinstance_triple, fixed_content, flags=re.MULTILINE)

        # 模式2: isinstance(x, type1, type2) -> isinstance(x, (type1, type2))
        pattern2 = r'\bisinstance\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)'
        def fix_isinstance_double(match):
            nonlocal fixes
            obj = match.group(1).strip()
            type1 = match.group(2).strip()
            type2 = match.group(3).strip()
            fixes += 1
            return f"isinstance({obj}, ({type1}, {type2}))"

        fixed_content = re.sub(pattern2, fix_isinstance_double, fixed_content, flags=re.MULTILINE)

        return fixed_content, fixes

    def _fix_unclosed_brackets(self, content: str) -> Tuple[str, int]:
        """修复未闭合的括号"""
        fixes = 0
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 检查括号平衡
            open_count = line.count('(') + line.count('[') + line.count('{')
            close_count = line.count(')') + line.count(']') + line.count('}')

            if open_count > close_count:
                # 在行末添加缺失的闭合括号
                missing = open_count - close_count
                # 根据上下文添加合适的闭合括号
                if '(' in line and line.count('(') > line.count(')'):
                    line += ')' * missing
                elif '[' in line and line.count('[') > line.count(']'):
                    line += ']' * missing
                elif '{' in line and line.count('{') > line.count('}'):
                    line += '}' * missing
                fixes += missing

            fixed_lines.append(line)

        return '\n'.join(fixed_lines), fixes

    def _fix_missing_colons(self, content: str) -> Tuple[str, int]:
        """修复缺少的冒号"""
        fixes = 0
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)
                continue

            # 检查常见的需要冒号的语句
            needs_colon_patterns = [
                (r'^\s*if\s+.*', 'if'),
                (r'^\s*elif\s+.*', 'elif'),
                (r'^\s*else\b', 'else'),
                (r'^\s*for\s+.*', 'for'),
                (r'^\s*while\s+.*', 'while'),
                (r'^\s*def\s+.*\(', 'def'),
                (r'^\s*class\s+.*', 'class'),
                (r'^\s*try\s*$', 'try'),
                (r'^\s*except\s+', 'except'),
                (r'^\s*finally\s*$', 'finally'),
                (r'^\s*with\s+', 'with')
            ]

            for pattern, keyword in needs_colon_patterns:
                if re.match(pattern, stripped) and not stripped.endswith(':'):
                    line += ':'
                    fixes += 1
                    break

            fixed_lines.append(line)

        return '\n'.join(fixed_lines), fixes

    def _fix_indentation_errors(self, content: str) -> Tuple[str, int]:
        """修复缩进错误"""
        fixes = 0
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 移除行尾空白
            original_line = line
            line = line.rstrip()

            # 修复混合缩进（制表符和空格混用）
            if '\t' in line and line.strip():
                # 将制表符替换为4个空格
                line = line.replace('\t', '    ')
                fixes += 1

            # 检查明显的缩进问题
            if line.strip() and not line.startswith(' ') and not line.startswith('#'):
                # 可能需要缩进的行（在if、for、def等之后）
                if original_line != line:
                    fixes += 1

            fixed_lines.append(line)

        return '\n'.join(fixed_lines), fixes

    def _fix_unclosed_strings(self, content: str) -> Tuple[str, int]:
        """修复未闭合的字符串"""
        fixes = 0
        lines = content.split('\n')
        fixed_lines = []

        in_string = False
        string_char = None

        for line in lines:
            i = 0
            while i < len(line):
                char = line[i]

                if not in_string:
                    if char in ['"', "'"]:
                        in_string = True
                        string_char = char
                else:
                    if char == string_char:
                        # 检查是否是转义字符
                        if i > 0 and line[i-1] != '\\':
                            in_string = False
                            string_char = None

                i += 1

            # 如果行结束时字符串未闭合，添加闭合
            if in_string:
                line += string_char
                fixes += 1
                in_string = False
                string_char = None

            fixed_lines.append(line)

        return '\n'.join(fixed_lines), fixes

    def _fix_f_string_errors(self, content: str) -> Tuple[str, int]:
        """修复f-string语法错误"""
        fixes = 0

        # 修复空表达式错误
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:

            # 查找f-string模式
            fstring_pattern = r'f["\']([^"\']*)\{([^}]*)\}([^"\']*)["\']'
            def fix_fstring(match):
                nonlocal fixes
                prefix = match.group(1)
                expr = match.group(2)
                suffix = match.group(3)

                # 如果表达式为空，使用占位符
                if not expr.strip():
                    expr = "'empty'"
                    fixes += 1

                return f'f"{prefix}{{{expr}}}{suffix}"'

            line = re.sub(fstring_pattern, fix_fstring, line)
            fixed_lines.append(line)

        return '\n'.join(fixed_lines), fixes

    def _fix_import_errors(self, content: str) -> Tuple[str, int]:
        """修复导入语句错误"""
        fixes = 0
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            stripped = line.strip()

            # 修复重复的import
            if stripped.startswith('import ') and stripped.count('import ') > 1:
                # 提取第一个import
                parts = stripped.split('import ', 2)
                if len(parts) >= 2:
                    line = f"import {parts[1]}"
                    fixes += 1

            # 修复from ... import 语句
            if stripped.startswith('from ') and ' import ' not in stripped:
                # 如果缺少import，添加基本的import
                if '.' in stripped:
                    module = stripped.split(' ', 1)[1]
                    line = f"from {module} import *"
                    fixes += 1

            fixed_lines.append(line)

        return '\n'.join(fixed_lines), fixes

    def _clean_syntax_errors(self, content: str) -> Tuple[str, int]:
        """清理其他语法错误"""
        fixes = 0
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            original_line = line

            # 移除重复的空行
            if not line.strip() and i > 0 and not lines[i-1].strip():
                continue

            # 清理行首多余空格（保持4的倍数）
            if line.strip() and not line.startswith('#'):
                leading_spaces = len(line) - len(line.lstrip(' '))
                if leading_spaces % 4 != 0 and leading_spaces > 0:
                    # 调整到最近的4的倍数
                    new_spaces = (leading_spaces // 4) * 4
                    line = ' ' * new_spaces + line.lstrip()
                    fixes += 1

            # 修复明显的语法错误
            line = self._fix_obvious_syntax_errors(line)
            if line != original_line:
                fixes += 1

            fixed_lines.append(line)

        return '\n'.join(fixed_lines), fixes

    def _fix_obvious_syntax_errors(self, line: str) -> str:
        """修复明显的语法错误"""
        # 修复常见的模式错误
        fixes = [
            (r'(\w+)\s*\(\s*\)\s*\.', r'\1().'),  # 方法调用后的点
            (r',\s*,', r','),                   # 重复逗号
            (r'\.\s*\.', r'.'),                 # 重复点
            (r'\s*=\s*=\s*', r'=='),            # 赋值运算符
        ]

        for pattern, replacement in fixes:
            line = re.sub(pattern, replacement, line)

        return line

    def _update_statistics(self, result: FixResult):
        """更新统计信息"""
        if result.success:
            self.fix_statistics['successful_fixes'] += 1
            self.fix_statistics['total_fixes_applied'] += result.fix_count
        else:
            self.fix_statistics['failed_fixes'] += 1

    def _generate_fix_report(self):
        """生成修复报告"""
        print("\n" + "=" * 60)
        print("📊 全面语法修复结果报告")
        print("=" * 60)

        stats = self.fix_statistics
        print("📁 文件处理:")
        print(f"   总文件数: {stats['total_files']}")
        print(f"   修复成功: {stats['successful_fixes']}")
        print(f"   修复失败: {stats['failed_fixes']}")
        print(f"   成功率: {stats['successful_fixes']/stats['total_files']*100:.1f}%")

        print("\n🔧 修复统计:")
        print(f"   总修复数: {stats['total_fixes_applied']}")
        print(f"   平均每文件: {stats['total_fixes_applied']/max(1, stats['successful_fixes']):.1f}")

        print("\n📋 错误类型分布:")
        for error_type, count in stats['error_types_found'].items():
            print(f"   {error_type}: {count} 次")

        # 显示修复失败的文件
        failed_files = [r for r in self.fix_results if not r.success]
        if failed_files:
            print(f"\n❌ 修复失败的文件 ({len(failed_files)}个):")
            for result in failed_files[:10]:  # 只显示前10个
                print(f"   - {Path(result.file_path).name}: {result.original_error[:80]}...")

        # 保存详细报告
        report_data = {
            'timestamp': str(Path.cwd()),
            'statistics': stats,
            'successful_files': [r.file_path for r in self.fix_results if r.success],
            'failed_files': [{'path': r.file_path, 'error': r.original_error} for r in self.fix_results if not r.success],
            'error_types': stats['error_types_found']
        }

        with open('comprehensive_syntax_fix_report.json', 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print("\n📄 详细报告已保存: comprehensive_syntax_fix_report.json")

def main():
    """主函数"""
    print("🚀 启动全面语法错误修复工具")
    print("基于Phase G成功经验的扩展语法修复")

    fixer = ComprehensiveSyntaxFixer()

    # 修复src目录
    print("\n📂 修复 src/ 目录...")
    src_stats = fixer.fix_project_syntax("src")

    # 修复scripts目录
    print("\n📂 修复 scripts/ 目录...")
    scripts_stats = fixer.fix_project_syntax("scripts")

    # 合并统计
    total_stats = {
        'total_files': src_stats['total_files'] + scripts_stats['total_files'],
        'successful_fixes': src_stats['successful_fixes'] + scripts_stats['successful_fixes'],
        'failed_fixes': src_stats['failed_fixes'] + scripts_stats['failed_fixes'],
        'total_fixes_applied': src_stats['total_fixes_applied'] + scripts_stats['total_fixes_applied'],
        'error_types_found': {**src_stats['error_types_found'], **scripts_stats['error_types_found']}
    }

    print("\n🎉 全面语法修复完成!")
    print(f"   总处理文件: {total_stats['total_files']}")
    print(f"   成功修复: {total_stats['successful_fixes']}")
    print(f"   总修复数: {total_stats['total_fixes_applied']}")
    print(f"   整体成功率: {total_stats['successful_fixes']/total_stats['total_files']*100:.1f}%")

    print("\n🎯 下一步建议:")
    if total_stats['successful_fixes'] > 0:
        print("   ✅ 语法修复完成，现在可以运行Phase G工具")
        print("   📋 建议: python3 scripts/intelligent_test_gap_analyzer.py")
    else:
        print("   ⚠️ 未发现可修复的语法错误")
        print("   📋 建议: 检查其他类型的代码问题")

    return total_stats

if __name__ == "__main__":
    main()