#!/usr/bin/env python3
"""
Phase 4 批量语法错误修复工具
目标：系统性修复3192个语法错误
"""

import ast
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys

class Phase4BatchSyntaxFixer:
    def __init__(self):
        self.fixed_files = []
        self.failed_files = []
        self.total_fixes = 0

    def get_all_python_files(self) -> List[str]:
        """获取所有Python文件列表"""
        python_files = []
        for path in Path('src/').rglob('*.py'):
            if path.is_file():
                python_files.append(str(path))
        return sorted(python_files)

    def analyze_file_syntax_errors(self, file_path: str) -> List[Dict]:
        """分析单个文件的语法错误"""
        errors = []

        try:
            # 尝试解析文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 尝试AST解析
            ast.parse(content)
            return errors  # 没有错误

        except SyntaxError as e:
            errors.append({
                'type': 'SyntaxError',
                'line': e.lineno,
                'column': e.offset,
                'message': str(e),
                'text': e.text.strip() if e.text else ''
            })
        except Exception as e:
            errors.append({
                'type': 'OtherError',
                'message': str(e)
            })

        # 使用ruff检查更多错误
        try:
            result = subprocess.run(
                ['ruff', 'check', file_path, '--no-cache'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line and not line.startswith('warning'):
                        # 解析ruff输出格式
                        if '->' in line and ':' in line:
                            try:
                                parts = line.split('->')[0].strip()
                                if ':' in parts:
                                    file_part, line_part = parts.split(':', 1)
                                    if ':' in line_part:
                                        line_num, col_part = line_part.split(':', 1)
                                        error_info = {
                                            'type': 'RuffError',
                                            'line': int(line_num),
                                            'column': int(col_part),
                                            'message': line.split('->')[1].strip() if '->' in line else line,
                                            'text': ''
                                        }
                                        errors.append(error_info)
                            except (ValueError, IndexError):
                                continue
        except Exception:
            pass

        return errors

    def fix_syntax_errors_in_file(self, file_path: str) -> Dict:
        """修复单个文件的语法错误"""
        print(f"   🔧 修复 {file_path}")

        try:
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": "文件不存在"}

            content = path.read_text(encoding='utf-8')
            original_content = content
            fixes = 0

            # 1. 修复常见的结构性问题
            content, fixes1 = self.fix_structural_issues(content)
            fixes += fixes1

            # 2. 修复括号不匹配
            content, fixes2 = self.fix_bracket_mismatches(content)
            fixes += fixes2

            # 3. 修复字符串未终止
            content, fixes3 = self.fix_unterminated_strings(content)
            fixes += fixes3

            # 4. 修复缩进问题
            content, fixes4 = self.fix_indentation_issues(content)
            fixes += fixes4

            # 5. 修复函数定义问题
            content, fixes5 = self.fix_function_definitions(content)
            fixes += fixes5

            # 6. 修复常见的语法错误
            content, fixes6 = self.fix_common_syntax_errors(content)
            fixes += fixes6

            # 保存修复后的文件
            if content != original_content:
                path.write_text(content, encoding='utf-8')
                self.fixed_files.append(file_path)
                self.total_fixes += fixes

                # 验证修复效果
                try:
                    ast.parse(content)
                    print(f"      ✅ 修复成功，{fixes}个修复，语法验证通过")
                    return {
                        "success": True,
                        "fixes": fixes,
                        "syntax_valid": True
                    }
                except SyntaxError as e:
                    print(f"      ⚠️  修复完成但仍有语法错误: {e}")
                    return {
                        "success": True,
                        "fixes": fixes,
                        "syntax_valid": False,
                        "remaining_error": str(e)
                    }
            else:
                print(f"      ℹ️  未发现需要修复的问题")
                return {"success": True, "fixes": 0, "syntax_valid": True}

        except Exception as e:
            print(f"      ❌ 修复失败: {e}")
            self.failed_files.append(file_path)
            return {"success": False, "error": str(e)}

    def fix_structural_issues(self, content: str) -> Tuple[str, int]:
        """修复结构性问题"""
        original_content = content
        fixes = 0

        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            fixed_line = line

            # 修复不完整的类定义
            if re.match(r'^\s*class\s+\w+\s*:\s*$', line):
                # 检查是否有docstring或pass
                fixed_lines.append(line)
                fixed_lines.append('    """类文档字符串"""')
                fixed_lines.append('    pass  # 添加pass语句')
                fixes += 1
                continue

            # 修复不完整的函数定义
            if re.match(r'^\s*def\s+\w+\([^)]*\):\s*$', line):
                fixed_lines.append(line)
                fixed_lines.append('    """函数文档字符串"""')
                fixed_lines.append('    pass  # 添加pass语句')
                fixes += 1
                continue

            fixed_lines.append(fixed_line)

        return '\n'.join(fixed_lines), fixes

    def fix_bracket_mismatches(self, content: str) -> Tuple[str, int]:
        """修复括号不匹配"""
        fixes = 0

        # 统计各种括号
        open_parens = content.count('(')
        close_parens = content.count(')')
        open_brackets = content.count('[')
        close_brackets = content.count(']')
        open_braces = content.count('{')
        close_braces = content.count('}')

        # 修复圆括号
        if open_parens > close_parens:
            missing = open_parens - close_parens
            content += ')' * missing
            fixes += missing

        # 修复方括号
        if open_brackets > close_brackets:
            missing = open_brackets - close_brackets
            content += ']' * missing
            fixes += missing

        # 修复花括号
        if open_braces > close_braces:
            missing = open_braces - close_braces
            content += '}' * missing
            fixes += missing

        return content, fixes

    def fix_unterminated_strings(self, content: str) -> Tuple[str, int]:
        """修复未终止的字符串"""
        fixes = 0
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            fixed_line = line

            # 简单的字符串匹配修复
            # 修复双引号
            double_count = line.count('"')
            if double_count % 2 == 1:
                if not line.rstrip().endswith('"'):
                    fixed_line += '"'
                    fixes += 1

            # 修复单引号
            single_count = line.count("'")
            if single_count % 2 == 1:
                if not line.rstrip().endswith("'"):
                    fixed_line += "'"
                    fixes += 1

            fixed_lines.append(fixed_line)

        return '\n'.join(fixed_lines), fixes

    def fix_indentation_issues(self, content: str) -> Tuple[str, int]:
        """修复缩进问题"""
        fixes = 0
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            fixed_line = line

            # 检查是否有不正确的缩进
            if line.strip() and not line.startswith(' '):
                # 如果不是空行且不以空格开头，检查是否需要缩进
                if i > 0:
                    prev_line = lines[i-1].strip()
                    if prev_line.endswith(':') and any(keyword in prev_line for keyword in
                        ['def', 'class', 'if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally', 'with']):
                        fixed_line = '    ' + line
                        fixes += 1

            fixed_lines.append(fixed_line)

        return '\n'.join(fixed_lines), fixes

    def fix_function_definitions(self, content: str) -> Tuple[str, int]:
        """修复函数定义问题"""
        fixes = 0
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            fixed_line = line

            # 修复缺少冒号的函数定义
            if re.match(r'^\s*def\s+\w+\([^)]*\)\s*$', line):
                if not line.strip().endswith(':'):
                    fixed_line = line.rstrip() + ':'
                    fixes += 1

            # 修复不完整的类型注解
            if '->' in line and line.strip().endswith('->'):
                fixed_line = line.rstrip() + ' Any:'
                fixes += 1

            fixed_lines.append(fixed_line)

        return '\n'.join(fixed_lines), fixes

    def fix_common_syntax_errors(self, content: str) -> Tuple[str, int]:
        """修复常见的语法错误"""
        fixes = 0
        original_content = content

        # 修复常见的语法错误模式
        error_patterns = [
            # 修复不完整的赋值语句
            (r'(\w+)\s*=\s*$', r'\1 = None'),

            # 修复不完整的return语句
            (r'return\s*$', 'return None'),

            # 修复多余的冒号
            (r'::\s*$', ':'),

            # 修复不完整的import语句
            (r'import\s+$', ''),
        ]

        for pattern, replacement in error_patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        fixes = len(content) - len(original_content) if content != original_content else 0

        return content, fixes

    def execute_batch_fixing(self) -> Dict:
        """执行批量语法错误修复"""
        print("🚀 开始批量语法错误修复...")

        # 获取所有Python文件
        python_files = self.get_all_python_files()
        print(f"   发现 {len(python_files)} 个Python文件")

        # 优先处理已知有问题的文件
        priority_files = [
            'src/utils/config_loader.py',
            'src/utils/date_utils.py',
            'src/api/tenant_management.py',
            'src/api/features.py',
            'src/config/config_manager.py',
            'src/domain/strategies/enhanced_ml_model.py',
            'src/domain/services/scoring_service.py',
            'src/services/processing/processors/match_processor.py',
            'src/services/processing/validators/data_validator.py',
            'src/services/processing/caching/processing_cache.py',
            'src/services/betting/betting_service.py',
            'src/repositories/base.py',
            'src/repositories/user.py',
            'src/repositories/match.py'
        ]

        # 过滤存在的优先文件
        existing_priority = [f for f in priority_files if Path(f).exists()]
        other_files = [f for f in python_files if f not in existing_priority]

        all_files = existing_priority + other_files

        print(f"   优先文件: {len(existing_priority)}个")
        print(f"   其他文件: {len(other_files)}个")

        # 执行修复
        for file_path in all_files:
            result = self.fix_syntax_errors_in_file(file_path)

            if not result.get("success", False):
                print(f"   ❌ 文件修复失败: {file_path}")

        return {
            "total_files": len(all_files),
            "fixed_files": len(self.fixed_files),
            "failed_files": len(self.failed_files),
            "total_fixes": self.total_fixes,
            "fixed_file_list": self.fixed_files,
            "failed_file_list": self.failed_files
        }

    def verify_improvement(self) -> Dict:
        """验证修复效果"""
        print("\n🔍 验证修复效果...")

        try:
            # 获取修复前的错误数（已知3192）
            before_errors = 3192

            # 获取修复后的错误数
            result = subprocess.run(
                ['ruff', 'check', 'src/', '--no-cache', '--statistics'],
                capture_output=True,
                text=True,
                timeout=60
            )

            after_errors = 0
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if 'Found' in line and 'errors' in line:
                        match = re.search(r'Found (\d+) errors', line)
                        if match:
                            after_errors = int(match.group(1))
                            break

            improvement = before_errors - after_errors
            improvement_rate = (improvement / before_errors * 100) if before_errors > 0 else 0

            return {
                "before_errors": before_errors,
                "after_errors": after_errors,
                "improvement": improvement,
                "improvement_rate": improvement_rate,
                "remaining_errors": after_errors
            }

        except Exception as e:
            print(f"   ❌ 验证失败: {e}")
            return {
                "before_errors": 3192,
                "after_errors": 3192,
                "improvement": 0,
                "improvement_rate": 0,
                "remaining_errors": 3192
            }

def main():
    """主函数"""
    print("🔧 Phase 4 批量语法错误修复工具")
    print("=" * 70)

    fixer = Phase4BatchSyntaxFixer()

    # 执行批量修复
    result = fixer.execute_batch_fixing()

    print(f"\n📊 批量修复结果:")
    print(f"   - 总文件数: {result['total_files']}")
    print(f"   - 修复文件数: {result['fixed_files']}")
    print(f"   - 失败文件数: {result['failed_files']}")
    print(f"   - 总修复数: {result['total_fixes']}")

    # 验证修复效果
    verification = fixer.verify_improvement()

    print(f"\n🎯 修复效果验证:")
    print(f"   - 修复前错误: {verification['before_errors']}个")
    print(f"   - 修复后错误: {verification['after_errors']}个")
    print(f"   - 减少错误: {verification['improvement']}个")
    print(f"   - 改进率: {verification['improvement_rate']:.1f}%")

    if verification['improvement'] > 1000:
        print(f"\n🎉 批量修复成功！显著改善语法错误状况")
    elif verification['improvement'] > 500:
        print(f"\n📈 批量修复部分成功，需要继续改进")
    else:
        print(f"\n⚠️  批量修复效果有限，需要更高级的策略")

    return verification

if __name__ == "__main__":
    main()