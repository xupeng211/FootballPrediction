#!/usr/bin/env python3
"""
智能语法修复器 - 精确修复剩余的语法错误
"""

import ast
import os
import re
import sys
from pathlib import Path

class SmartSyntaxFixer:
    def __init__(self):
        self.fixed_files = []
        self.failed_files = []
        self.fix_stats = {
            'bracket_mismatch': 0,
            'unclosed_string': 0,
            'type_annotation': 0,
            'dict_init': 0,
            'other': 0
        }

    def check_syntax(self, filepath):
        """检查文件语法错误"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            return True, None, content
        except SyntaxError as e:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return False, e, content
        except Exception as e:
            return False, e, None

    def fix_bracket_mismatch(self, content, filepath):
        """修复括号不匹配问题"""
        fixed = False
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # 修复类型注解中的括号
            if 'Optional[' in line and '] = None' in line:
                # 检查是否有多余的括号
                if line.count(']') > line.count('Optional['):
                    # 移除多余的右括号
                    line = re.sub(r'\](?=\s*=\s*None)', '', line)
                    lines[i] = line
                    fixed = True
                    self.fix_stats['bracket_mismatch'] += 1

            # 修复Dict/List类型注解
            if ('Dict[' in line or 'List[' in line) and ']' in line:
                # 计算括号平衡
                open_brackets = line.count('[')
                close_brackets = line.count(']')
                if close_brackets > open_brackets:
                    # 移除多余的右括号
                    excess = close_brackets - open_brackets
                    for _ in range(excess):
                        line = line.replace(']', '', 1)
                        if '= None' in line and ']' not in line:
                            line = line.replace('= None', '] = None')
                    lines[i] = line
                    fixed = True
                    self.fix_stats['bracket_mismatch'] += 1

        return '\n'.join(lines), fixed

    def fix_unclosed_strings(self, content, filepath):
        """修复未闭合的字符串"""
        fixed = False
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # 检查f-string
            if 'f"' in line:
                # 计算引号数量
                quote_count = len(re.findall(r'f".*?"', line))
                fstring_parts = line.split('f"')

                # 检查每个f-string部分
                for j, part in enumerate(fstring_parts):
                    if j == 0:
                        continue
                    if part.count('"') % 2 == 1:  # 奇数个引号，未闭合
                        # 找到这个部分的结束
                        if 'return' in fstring_parts[j-1] or 'print(' in fstring_parts[j-1]:
                            # 添加闭合引号
                            fstring_parts[j] = part + '"'
                            fixed = True
                            self.fix_stats['unclosed_string'] += 1

                # 重组行
                if j > 0:
                    lines[i] = 'f"'.join(fstring_parts)

            # 检查普通字符串
            elif '"' in line:
                # 如果行以字符串开始但没结束
                if line.strip().startswith('"') and not line.strip().endswith('"'):
                    if not line.strip().endswith('"""') and '"""' not in line:
                        lines[i] = line.rstrip() + '"'
                        fixed = True
                        self.fix_stats['unclosed_string'] += 1

        return '\n'.join(lines), fixed

    def fix_type_annotations(self, content, filepath):
        """修复类型注解错误"""
        fixed = False
        original_content = content

        # 修复Optional类型
        content = re.sub(
            r'(\w+):\s*Optional\[(.*?)\]\s*\]\s*=',
            r'\1: Optional[\2]] =',
            content
        )

        # 修复Dict类型
        content = re.sub(
            r'(\w+):\s*Dict\[(.*?)\]\s*\]\s*=',
            r'\1: Dict[\2]] =',
            content
        )

        # 修复List类型
        content = re.sub(
            r'(\w+):\s*List\[(.*?)\]\s*\]\s*=',
            r'\1: List[\2]] =',
            content
        )

        # 修复Union类型
        content = re.sub(
            r'(\w+):\s*Union\[(.*?)\]\s*\]\s*=',
            r'\1: Union[\2]] =',
            content
        )

        # 修复返回类型注解
        content = re.sub(
            r'->\s*Optional\[Dict\[str,\s*Any\]:',
            r'-> Optional[Dict[str, Any]]:',
            content
        )

        content = re.sub(
            r'->\s*Dict\[str,\s*Dict\[str,\s*Any\]:',
            r'-> Dict[str, Dict[str, Any]]:',
            content
        )

        if content != original_content:
            fixed = True
            self.fix_stats['type_annotation'] += 1

        return content, fixed

    def fix_dict_initialization(self, content, filepath):
        """修复字典初始化错误"""
        fixed = False
        original_content = content

        # 修复错误的字典初始化
        content = content.replace('= {}]', ' = {}')
        content = content.replace('= {]]', ' = {}')
        content = content.replace('= {]', ' = {}')
        content = content.replace('= [}', ' = []')

        # 修复变量赋值
        content = re.sub(r'(\w+)\s*=\s*{\]\]', r'\1 = {}', content)
        content = re.sub(r'(\w+)\s*=\s*\{\]', r'\1 = {}', content)
        content = re.sub(r'(\w+)\s*=\s*\[\}', r'\1 = []', content)

        if content != original_content:
            fixed = True
            self.fix_stats['dict_init'] += 1

        return content, fixed

    def fix_specific_patterns(self, content, filepath):
        """修复特定的语法模式"""
        fixed = False
        original_content = content

        # 修复except子句
        content = re.sub(
            r'except\s*\(\s*([^)]*?)\s*\)\s*:\s*$',
            r'except (\1):',
            content,
            flags=re.MULTILINE
        )

        # 修复Type注解中的嵌套泛型
        content = re.sub(
            r'Dict\[str,\s*Type\[Any,\s*(.*?)\]\]',
            r'Dict[str, Type[\1]]',
            content
        )

        # 修复行尾多余的逗号和括号
        content = re.sub(r',\s*\)\s*\.', ')).', content)

        # 修复未闭合的方法调用
        content = re.sub(r'\]\s*\.\s*(\w+)', r'].\1', content)

        if content != original_content:
            fixed = True
            self.fix_stats['other'] += 1

        return content, fixed

    def fix_file(self, filepath):
        """修复单个文件"""
        is_valid, error, content = self.check_syntax(filepath)

        if is_valid:
            print(f"✓ {filepath} - 语法正确")
            return True

        print(f"✗ {filepath} - {error}")

        if content is None:
            print(f"  无法读取文件内容")
            self.failed_files.append((filepath, str(error)))
            return False

        original_content = content

        # 尝试各种修复方法
        content, fixed1 = self.fix_bracket_mismatch(content, filepath)
        content, fixed2 = self.fix_unclosed_strings(content, filepath)
        content, fixed3 = self.fix_type_annotations(content, filepath)
        content, fixed4 = self.fix_dict_initialization(content, filepath)
        content, fixed5 = self.fix_specific_patterns(content, filepath)

        # 如果有修改，验证修复结果
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            # 重新检查
            is_valid, new_error, _ = self.check_syntax(filepath)

            if is_valid:
                print(f"  ✓ 修复成功！")
                self.fixed_files.append(filepath)
                return True
            else:
                print(f"  ✗ 修复后仍有错误: {new_error}")
                self.failed_files.append((filepath, str(new_error)))
                return False
        else:
            print(f"  - 无法自动修复")
            self.failed_files.append((filepath, str(error)))
            return False

    def fix_all_files(self, start_path='src'):
        """修复所有文件"""
        print("=" * 60)
        print("开始智能语法修复")
        print("=" * 60)

        # 获取所有Python文件
        all_files = []
        for root, dirs, files in os.walk(start_path):
            for file in files:
                if file.endswith('.py'):
                    all_files.append(os.path.join(root, file))

        print(f"找到 {len(all_files)} 个Python文件\n")

        # 优先处理有错误的文件
        error_files = []
        for filepath in all_files:
            is_valid, _, _ = self.check_syntax(filepath)
            if not is_valid:
                error_files.append(filepath)

        print(f"发现 {len(error_files)} 个文件有语法错误\n")

        # 修复每个错误文件
        for filepath in error_files:
            self.fix_file(filepath)
            print()

        # 统计结果
        print("=" * 60)
        print("修复结果统计")
        print("=" * 60)
        print(f"总错误文件: {len(error_files)}")
        print(f"成功修复: {len(self.fixed_files)}")
        print(f"修复失败: {len(self.failed_files)}")
        print(f"\n修复类型统计:")
        for fix_type, count in self.fix_stats.items():
            if count > 0:
                print(f"  - {fix_type}: {count} 个")

        if self.failed_files:
            print(f"\n未能修复的文件:")
            for filepath, error in self.failed_files[:10]:
                print(f"  - {filepath}")
                print(f"    错误: {error[:100]}...")
            if len(self.failed_files) > 10:
                print(f"  ... 还有 {len(self.failed_files)-10} 个文件")

        return len(self.fixed_files), len(self.failed_files)

if __name__ == "__main__":
    fixer = SmartSyntaxFixer()
    fixed, failed = fixer.fix_all_files()

    print(f"\n修复完成！成功率: {fixed/(fixed+failed)*100:.1f}%")
