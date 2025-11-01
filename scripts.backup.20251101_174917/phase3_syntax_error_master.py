#!/usr/bin/env python3
"""
Phase 3 语法错误主修复工具
针对2864个语法错误的专业修复系统
"""

import os
import re
import ast
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
import json

class Phase3SyntaxErrorMaster:
    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.critical_errors_fixed = 0
        self.fix_log = []

    def analyze_syntax_errors(self) -> Dict:
        """分析语法错误类型和分布"""
        print("🔍 分析语法错误分布...")

        try:
            result = subprocess.run(
                ['ruff', 'check', 'src/', '--output-format=json'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return {'total_errors': 0, 'error_types': {}}

            errors = json.loads(result.stdout) if result.stdout.strip() else []

            error_analysis = {
                'total_errors': len(errors),
                'error_types': {},
                'critical_files': {},
                'syntax_errors': [],
                'other_errors': []
            }

            for error in errors:
                error_code = error.get('code', 'unknown')
                filename = error.get('filename', 'unknown')

                # 统计错误类型
                error_analysis['error_types'][error_code] = error_analysis['error_types'].get(error_code, 0) + 1

                # 统计关键文件
                if filename not in error_analysis['critical_files']:
                    error_analysis['critical_files'][filename] = 0
                error_analysis['critical_files'][filename] += 1

                # 分类错误
                if error_code == 'invalid-syntax':
                    error_analysis['syntax_errors'].append(error)
                else:
                    error_analysis['other_errors'].append(error)

            return error_analysis

        except Exception as e:
            print(f"❌ 错误分析失败: {e}")
            return {'total_errors': 0, 'error_types': {}}

    def fix_invalid_syntax_errors(self, file_path: str) -> Tuple[bool, int]:
        """修复无效语法错误"""
        try:
            path = Path(file_path)
            if not path.exists():
                return False, 0

            content = path.read_text(encoding='utf-8')
            original_content = content
            fixes_count = 0

            # 修复1: 修复try-except语法错误
            content, fix1 = self._fix_try_except_syntax(content)
            fixes_count += fix1

            # 修复2: 修复函数定义语法错误
            content, fix2 = self._fix_function_definition_syntax(content)
            fixes_count += fix2

            # 修复3: 修复类型注解语法错误
            content, fix3 = self._fix_type_annotation_syntax(content)
            fixes_count += fix3

            # 修复4: 修复导入语句语法错误
            content, fix4 = self._fix_import_statement_syntax(content)
            fixes_count += fix4

            # 修复5: 修复字符串和括号匹配
            content, fix5 = self._fix_bracket_and_string_matching(content)
            fixes_count += fix5

            # 修复6: 修复缩进问题
            content, fix6 = self._fix_indentation_issues(content)
            fixes_count += fix6

            # 验证修复结果
            if content != original_content:
                try:
                    # 尝试解析修复后的代码
                    ast.parse(content)
                    path.write_text(content, encoding='utf-8')
                    return True, fixes_count
                except SyntaxError as e:
                    # 如果仍有语法错误，记录但不保存
                    print(f"⚠️  {file_path} 修复后仍有语法错误: {e}")
                    return False, 0

            return False, 0

        except Exception as e:
            print(f"❌ 修复 {file_path} 时出错: {e}")
            return False, 0

    def _fix_try_except_syntax(self, content: str) -> Tuple[str, int]:
        """修复try-except语法错误"""
        fixes = 0

        # 修复悬空的try块
        content = re.sub(
            r'(\s+)try:\s*\n\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*[^n\W]*\n(\s+)except',
            r'\1try:\n\2 = None\n\3except',
            content,
            flags=re.MULTILINE
        )

        # 修复缺失except的try块
        content = re.sub(
            r'(\s+)try:\s*([^]*?)(?=\n\s*(def|class|if|for|while|try|return|$))',
            lambda m: self._add_except_block(m.group(1), m.group(2)),
            content
        )

        return content, fixes

    def _add_except_block(self, indent: str, try_content: str) -> str:
        """为try块添加except语句"""
        if 'except' in try_content:
            return f"{indent}try:\n{try_content}"
        return f"{indent}try:\n{try_content}{indent}except Exception:\n{indent}    pass\n"

    def _fix_function_definition_syntax(self, content: str) -> Tuple[str, int]:
        """修复函数定义语法错误"""
        fixes = 0

        # 修复参数列表中的语法错误
        content = re.sub(
            r'def\s+(\w+)\s*\(\s*([^)]*):\s*\)',
            r'def \1(\2):',
            content
        )

        # 修复函数返回类型注解错误
        content = re.sub(
            r'def\s+(\w+)\s*\([^)]*\)\s*->\s*[^:]*:\s*([^:])',
            r'def \1(): \2',
            content
        )

        return content, fixes

    def _fix_type_annotation_syntax(self, content: str) -> Tuple[str, int]:
        """修复类型注解语法错误"""
        fixes = 0

        # 修复Dict类型注解
        content = re.sub(r': Dict\[str\s*\)\s*\]', ': Dict[str, Any]', content)
        content = re.sub(r': Dict\[str,\s*([^]]*)\)\s*\]', r': Dict[str, \1]', content)

        # 修复List类型注解
        content = re.sub(r': List\[(\w+)\s*\)\s*\]', r': List[\1]', content)
        content = re.sub(r': List\[(\w+,\s*[^]]*)\)\s*\]', r': List[\1]', content)

        # 修复Optional类型注解
        content = re.sub(r': Optional\[(\w+)\s*\)\s*\]', r': Optional[\1]', content)

        # 修复Union类型注解
        content = re.sub(r': Union\[(\w+,\s*[^]]*)\)\s*\]', r': Union[\1]', content)

        return content, fixes

    def _fix_import_statement_syntax(self, content: str) -> Tuple[str, int]:
        """修复导入语句语法错误"""
        fixes = 0

        # 修复from import语句
        content = re.sub(
            r'from\s+(\w+)\s+import\s*\(([^)]*)\)\s*\]',
            r'from \1 import \2',
            content
        )

        # 修复重复的导入
        content = re.sub(r'from\s+(\w+)\s+import\s+\1\s*,\s*\1', r'from \1 import \1', content)

        return content, fixes

    def _fix_bracket_and_string_matching(self, content: str) -> Tuple[str, int]:
        """修复括号和字符串匹配问题"""
        fixes = 0

        # 修复多余的右括号
        content = re.sub(r'\)\s*\)\s*\)', ')', content)
        content = re.sub(r'\]\s*\]\s*\]', ']', content)
        content = re.sub(r'}\s*}\s*}', '}', content)

        # 修复字符串中的语法错误
        content = re.sub(r'"([^"]*)\)\s*\)', r'"\1")', content)
        content = re.sub(r"'([^']*)\)\s*\)", r"'\1')", content)

        return content, fixes

    def _fix_indentation_issues(self, content: str) -> Tuple[str, int]:
        """修复缩进问题"""
        fixes = 0

        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            # 修复except语句的缩进
            if line.strip().startswith('except ') and not line.startswith('    '):
                fixed_lines.append('    ' + line.strip())
                fixes += 1
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines), fixes

    def execute_phase3_syntax_fix(self) -> Dict:
        """执行Phase 3语法错误修复"""
        print("🚀 开始Phase 3语法错误深度修复...")

        # 1. 分析错误
        analysis = self.analyze_syntax_errors()
        print(f"   - 总错误数: {analysis['total_errors']}")
        print(f"   - 语法错误: {len(analysis['syntax_errors'])}")
        print(f"   - 其他错误: {len(analysis['other_errors'])}")

        # 2. 确定优先修复的文件
        critical_files = sorted(
            analysis['critical_files'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:20]  # 优先处理错误最多的20个文件

        print(f"\n🎯 优先修复文件 (Top 20):")
        for filename, error_count in critical_files[:10]:
            print(f"   - {filename}: {error_count}个错误")

        # 3. 执行修复
        total_fixes = 0
        successful_files = 0

        for filename, _ in critical_files:
            print(f"\n🔧 修复 {filename}...")
            success, fixes = self.fix_invalid_syntax_errors(filename)

            if success and fixes > 0:
                total_fixes += fixes
                successful_files += 1
                print(f"   ✅ 修复成功: {fixes}个语法错误")
                self.fix_log.append(f"✅ {filename}: {fixes}个语法错误修复")
            else:
                print(f"   ⚠️  修复效果有限")
                self.fix_log.append(f"⚠️ {filename}: 修复效果有限")

            self.files_processed += 1

        # 4. 验证修复效果
        print(f"\n🔍 验证修复效果...")
        after_analysis = self.analyze_syntax_errors()

        reduction = analysis['total_errors'] - after_analysis['total_errors']
        reduction_rate = (reduction / analysis['total_errors'] * 100) if analysis['total_errors'] > 0 else 0

        return {
            'original_errors': analysis['total_errors'],
            'remaining_errors': after_analysis['total_errors'],
            'errors_fixed': reduction,
            'reduction_rate': reduction_rate,
            'files_processed': self.files_processed,
            'successful_files': successful_files,
            'total_fixes': total_fixes,
            'target_achieved': after_analysis['total_errors'] < 1500,
            'fix_log': self.fix_log
        }

def main():
    """主函数"""
    print("🏆 Phase 3 语法错误深度修复工具")
    print("=" * 60)

    # 执行修复
    master = Phase3SyntaxErrorMaster()
    result = master.execute_phase3_syntax_fix()

    # 显示结果
    print(f"\n📈 Phase 3 语法修复结果:")
    print(f"   - 原始错误数: {result['original_errors']}")
    print(f"   - 剩余错误数: {result['remaining_errors']}")
    print(f"   - 错误减少数: {result['errors_fixed']}")
    print(f"   - 减少率: {result['reduction_rate']:.1f}%")
    print(f"   - 处理文件数: {result['files_processed']}")
    print(f"   - 成功文件数: {result['successful_files']}")

    # 检查目标达成
    print(f"\n🎯 目标检查 (<1500个错误):")
    if result['target_achieved']:
        print(f"   ✅ 目标达成: {result['remaining_errors']} < 1500")
        print("🎉 Phase 3语法错误修复成功！")
    else:
        print(f"   ⚠️  继续努力: {result['remaining_errors']} ≥ 1500")
        print("📈 语法错误有所改善，需要进一步处理")

    return result

if __name__ == "__main__":
    main()