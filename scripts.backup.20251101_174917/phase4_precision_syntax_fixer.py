#!/usr/bin/env python3
"""
Phase 4: 语法错误精准修复攻坚工具
目标：基于Phase 3.5 AI分析的4种错误聚类，精准修复3093个语法错误
"""

import ast
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter

class Phase4PrecisionSyntaxFixer:
    def __init__(self):
        self.fix_attempts = 0
        self.successful_fixes = 0
        self.fixed_files = []
        self.error_patterns = {}

    def analyze_error_patterns(self) -> Dict:
        """分析高频语法错误模式"""
        print("🔍 分析高频语法错误模式...")

        # 基于Phase 3.5 AI分析的4种错误聚类
        error_clusters = {
            "unmatched_parentheses": {
                "description": "括号不匹配",
                "patterns": [
                    r'\(\s*$',  # 开括号无闭括号
                    r'\[\s*$',  # 开方括号无闭括号
                    r'\{\s*$',  # 开花括号无闭括号
                ],
                "fixes": [
                    "add_missing_closing_paren",
                    "fix_method_calls",
                    "fix_import_statements"
                ]
            },
            "unexpected_indent": {
                "description": "缩进错误",
                "patterns": [
                    r'^\s+def\s+\w+\([^)]*\):\s*$',  # 函数定义后无内容
                    r'^\s+class\s+\w+:',  # 类定义问题
                    r'^\s+if\s+.*:\s*$',  # if语句后无内容
                ],
                "fixes": [
                    "fix_indentation",
                    "add_pass_statement",
                    "fix_block_structure"
                ]
            },
            "unterminated_string": {
                "description": "字符串未终止",
                "patterns": [
                    r'("[^"]*$',  # 双引号未结束
                    r'(\'[^\']*$',  # 单引号未结束
                    r'"""[^"]*$',  # 三重引号未结束
                ],
                "fixes": [
                    "add_missing_quotes",
                    "fix_string_escapes",
                    "fix_docstring_format"
                ]
            },
            "invalid_syntax": {
                "description": "语法结构错误",
                "patterns": [
                    r'def\s+\w+\([^)]*$',  # 函数定义不完整
                    r'=\s*$',  # 赋值语句不完整
                    r'->\s*$',  # 类型注解不完整
                ],
                "fixes": [
                    "complete_function_definition",
                    "fix_assignment_statements",
                    "fix_type_annotations"
                ]
            }
        }

        print(f"   发现4种错误聚类:")
        for cluster_name, cluster_info in error_clusters.items():
            print(f"   - {cluster_info['description']}: {len(cluster_info['patterns'])}种模式")

        self.error_patterns = error_clusters
        return error_clusters

    def prioritize_files_for_fixing(self) -> List[str]:
        """确定修复优先级的文件列表"""
        print("🎯 确定修复优先级...")

        # 基于重要性和错误数量的优先级排序
        priority_files = [
            # 核心模块 - 高优先级
            "src/utils/dict_utils.py",
            "src/utils/string_utils.py",
            "src/utils/response.py",
            "src/config/config_manager.py",

            # API层 - 高优先级
            "src/api/features.py",
            "src/api/tenant_management.py",
            "src/api/health/__init__.py",

            # 领域层 - 中优先级
            "src/domain/services/scoring_service.py",
            "src/domain/strategies/enhanced_ml_model.py",

            # 服务层 - 中优先级
            "src/services/processing/validators/data_validator.py",
            "src/services/processing/processors/match_processor.py",
            "src/services/processing/caching/processing_cache.py",
            "src/services/betting/betting_service.py",

            # 仓储层 - 低优先级
            "src/repositories/base.py",
            "src/repositories/user.py",
            "src/repositories/match.py"
        ]

        # 过滤存在的文件
        existing_files = [f for f in priority_files if Path(f).exists()]

        print(f"   优先级文件: {len(existing_files)}个")
        return existing_files

    def fix_unmatched_parentheses(self, content: str, file_path: str) -> Tuple[str, int]:
        """修复不匹配的括号"""
        original_content = content
        fixes = 0

        # 统计括号数量
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
            print(f"      添加{missing}个缺失的圆括号")

        # 修复方括号
        if open_brackets > close_brackets:
            missing = open_brackets - close_brackets
            content += ']' * missing
            fixes += missing
            print(f"      添加{missing}个缺失的方括号")

        # 修复花括号
        if open_braces > close_braces:
            missing = open_braces - close_braces
            content += '}' * missing
            fixes += missing
            print(f"      添加{missing}个缺失的花括号")

        return content, fixes

    def fix_indentation_errors(self, content: str, file_path: str) -> Tuple[str, int]:
        """修复缩进错误"""
        original_content = content
        fixes = 0
        lines = content.split('\n')
        fixed_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]
            fixed_lines.append(line)

            # 检查是否是不完整的函数/类/if定义
            if re.match(r'^\s*(def|class|if|elif|else|for|while|try|except|finally|with)\s+', line):
                # 检查下一行是否存在
                if i + 1 >= len(lines) or lines[i + 1].strip() == '':
                    # 添加pass语句
                    indent = len(line) - len(line.lstrip())
                    pass_line = ' ' * indent + '    pass  # 修复缺失的语句体'
                    fixed_lines.append(pass_line)
                    fixes += 1
                    print(f"      在第{i+1}行添加pass语句")

            i += 1

        return '\n'.join(fixed_lines), fixes

    def fix_unterminated_strings(self, content: str, file_path: str) -> Tuple[str, int]:
        """修复未终止的字符串"""
        original_content = content
        fixes = 0
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            fixed_line = line

            # 检查双引号
            double_quotes = line.count('"')
            if double_quotes % 2 == 1:
                fixed_line += '"'
                fixes += 1
                print(f"      修复未终止的双引号字符串")

            # 检查单引号
            single_quotes = line.count("'")
            if single_quotes % 2 == 1:
                fixed_line += "'"
                fixes += 1
                print(f"      修复未终止的单引号字符串")

            fixed_lines.append(fixed_line)

        return '\n'.join(fixed_lines), fixes

    def fix_invalid_syntax(self, content: str, file_path: str) -> Tuple[str, int]:
        """修复无效语法"""
        original_content = content
        fixes = 0
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            fixed_line = line

            # 修复不完整的函数定义
            if re.match(r'^\s*def\s+\w+\([^)]*$', line):
                if not line.strip().endswith(':'):
                    fixed_line += ':'
                    fixes += 1
                    print(f"      修复第{i+1}行函数定义，添加冒号")

            # 修复不完整的类型注解
            if re.search(r'->\s*$', line):
                fixed_line = fixed_line.replace('->', '-> Any')
                fixes += 1
                print(f"      修复第{i+1}行类型注解")

            # 修复不完整的赋值语句
            if re.search(r'=\s*$', line) and not line.strip().endswith(')'):
                fixed_line += ' None'
                fixes += 1
                print(f"      修复第{i+1}行赋值语句")

            fixed_lines.append(fixed_line)

        return '\n'.join(fixed_lines), fixes

    def fix_file_syntax_errors(self, file_path: str) -> Dict:
        """精准修复单个文件的语法错误"""
        print(f"   🔧 精准修复 {file_path}")

        try:
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": "文件不存在"}

            content = path.read_text(encoding='utf-8')
            original_content = content
            total_fixes = 0

            # 应用各种修复策略
            print(f"      应用括号修复...")
            content, paren_fixes = self.fix_unmatched_parentheses(content, file_path)
            total_fixes += paren_fixes

            print(f"      应用缩进修复...")
            content, indent_fixes = self.fix_indentation_errors(content, file_path)
            total_fixes += indent_fixes

            print(f"      应用字符串修复...")
            content, string_fixes = self.fix_unterminated_strings(content, file_path)
            total_fixes += string_fixes

            print(f"      应用语法修复...")
            content, syntax_fixes = self.fix_invalid_syntax(content, file_path)
            total_fixes += syntax_fixes

            # 验证修复效果
            if content != original_content:
                # 保存修复后的文件
                path.write_text(content, encoding='utf-8')

                # 验证语法是否正确
                try:
                    ast.parse(content)
                    self.successful_fixes += 1
                    self.fixed_files.append(file_path)
                    print(f"      ✅ 修复成功，语法验证通过")
                    return {
                        "success": True,
                        "total_fixes": total_fixes,
                        "paren_fixes": paren_fixes,
                        "indent_fixes": indent_fixes,
                        "string_fixes": string_fixes,
                        "syntax_fixes": syntax_fixes
                    }
                except SyntaxError as e:
                    print(f"      ⚠️  修复完成但仍有语法错误: {e}")
                    return {
                        "success": False,
                        "total_fixes": total_fixes,
                        "remaining_error": str(e)
                    }
            else:
                print(f"      ℹ️  未发现需要修复的问题")
                return {"success": True, "total_fixes": 0}

        except Exception as e:
            print(f"      ❌ 修复失败: {e}")
            return {"success": False, "error": str(e)}

    def execute_precision_fixing(self) -> Dict:
        """执行精准语法错误修复"""
        print("🚀 开始精准语法错误修复...")

        # 1. 分析错误模式
        self.analyze_error_patterns()

        # 2. 确定修复优先级
        priority_files = self.prioritize_files_for_fixing()

        # 3. 执行精准修复
        total_fixes = 0
        successful_files = []
        failed_files = []

        for file_path in priority_files:
            self.fix_attempts += 1
            result = self.fix_file_syntax_errors(file_path)

            if result.get("success", False):
                total_fixes += result.get("total_fixes", 0)
                if result.get("total_fixes", 0) > 0:
                    successful_files.append(file_path)
            else:
                failed_files.append(file_path)

        return {
            "total_attempts": self.fix_attempts,
            "successful_files": len(successful_files),
            "failed_files": len(failed_files),
            "total_fixes": total_fixes,
            "success_rate": (len(successful_files) / self.fix_attempts * 100) if self.fix_attempts > 0 else 0,
            "fixed_files": successful_files,
            "failed_files": failed_files
        }

    def verify_fixing_results(self) -> Dict:
        """验证修复结果"""
        print("\n🔍 验证修复结果...")

        try:
            # 运行语法检查
            result = subprocess.run(
                ['python3', '-m', 'py_compile', 'src/'] +
                [f for f in Path('src/').rglob('*.py') if f.is_file()],
                capture_output=True,
                text=True,
                timeout=60
            )

            # 获取当前错误数量
            syntax_errors = result.stderr.count('SyntaxError')

            return {
                "syntax_errors": syntax_errors,
                "total_fixes": self.successful_fixes,
                "fixed_files": len(self.fixed_files),
                "improvement": 3093 - syntax_errors,  # 原始错误数 - 当前错误数
                "improvement_rate": ((3093 - syntax_errors) / 3093 * 100) if syntax_errors < 3093 else 0
            }

        except Exception as e:
            print(f"   ❌ 验证失败: {e}")
            return {
                "syntax_errors": 3093,  # 假设没有改进
                "total_fixes": 0,
                "fixed_files": 0,
                "improvement": 0,
                "improvement_rate": 0
            }

def main():
    """主函数"""
    print("🔧 Phase 4: 语法错误精准修复攻坚工具")
    print("=" * 70)

    fixer = Phase4PrecisionSyntaxFixer()

    # 执行精准修复
    result = fixer.execute_precision_fixing()

    print(f"\n📊 精准修复结果:")
    print(f"   - 尝试修复文件: {result['total_attempts']}个")
    print(f"   - 成功修复文件: {result['successful_files']}个")
    print(f"   - 失败文件: {result['failed_files']}个")
    print(f"   - 总修复数: {result['total_fixes']}个")
    print(f"   - 成功率: {result['success_rate']:.1f}%")

    # 验证修复效果
    verification = fixer.verify_fixing_results()

    print(f"\n🎯 修复效果验证:")
    print(f"   - 剩余语法错误: {verification['syntax_errors']}个")
    print(f"   - 修复成功数: {verification['total_fixes']}个")
    print(f"   - 改进幅度: {verification['improvement']}个")
    print(f"   - 改进率: {verification['improvement_rate']:.1f}%")

    if verification['improvement'] > 1000:
        print(f"\n🎉 精准修复攻坚成功！显著改善语法错误状况")
    elif verification['improvement'] > 500:
        print(f"\n📈 精准修复攻坚部分成功，需要继续改进")
    else:
        print(f"\n⚠️  精准修复攻坚效果有限，需要更高级的策略")

    return verification

if __name__ == "__main__":
    main()