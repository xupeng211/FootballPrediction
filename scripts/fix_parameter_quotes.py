#!/usr/bin/env python3
"""修复函数参数中的引号错误"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

def fix_parameter_quotes_in_file(file_path: str) -> bool:
    """修复文件中的参数引号错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复函数参数定义中的引号
        # 匹配模式: "参数名": 类型
        patterns = [
            # 函数定义中的参数
            (r'(\s+)("([^"]+)"):\s*([^,=)]+)', r'\1\3: \4'),
            # 类型注解中的Optional
            (r'Optional\["([^"]+)"\]', r'Optional[\1]'),
            # 类型注解中的List
            (r'List\["([^"]+)"\]', r'List[\1]'),
            (r'Dict\["([^"]+)",\s*"([^"]+)"\]', r'Dict[\1, \2]'),
            # 修复Union类型
            (r'Union\["([^"]+)",\s*"([^"]+)"\]', r'Union[\1, \2]'),
            # 修复Tuple类型
            (r'Tuple\["([^"]+)",\s*"([^"]+)"\]', r'Tuple[\1, \2]'),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        # 特殊修复：处理被错误加引号的参数
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 跳过注释和文档字符串
            if line.strip().startswith('#') or '"""' in line or "'''" in line:
                fixed_lines.append(line)
                continue

            # 修复函数参数行
            if ':' in line and not line.strip().startswith('def ') and not line.strip().startswith('class '):
                # 检查是否是参数定义行
                if re.search(r'^\s+"[^"]+":\s*\w+', line):
                    # 移除参数名周围的引号
                    line = re.sub(r'^(\s+)"([^"]+)":', r'\1\2:', line)

            fixed_lines.append(line)

        content = '\n'.join(fixed_lines)

        # 额外的全局修复
        # 修复字典中的键（如果是参数名）
        content = re.sub(r'"([^"]+)":\s*(None|True|False|\d+)', r'\1: \2', content)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 修复了参数引号: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"✗ 修复文件失败 {file_path}: {e}")
        return False

def fix_specific_issues(content: str) -> str:
    """修复特定的语法问题"""
    # 修复列表/字典初始化
    content = re.sub(r'\[\s*,\s*"[^"]*"', '["", ', content)
    content = re.sub(r'\{\s*"[^"]*"\s*:\s*\[\s*,', '{""', content)

    # 修复未闭合的字符串
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # 修复行末的逗号引号问题
        if line.endswith('",') and not line.startswith('"'):
            # 检查是否应该是引号逗号
            if line.count('"') % 2 == 1:
                # 奇数个引号，说明可能有问题
                pass  # 保持原样

        # 修复字典值中的额外引号
        if ': "' in line and line.endswith('",') and line.count('"') >= 4:
            # 可能有多余的引号
            parts = line.split(': "', 1)
            if len(parts) == 2:
                key = parts[0]
                value = parts[1]
                if value.startswith('"') and value.endswith('",'):
                    value = value[1:-2] + ','
                    line = key + ': "' + value

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def main():
    """主函数"""
    print("修复参数引号错误工具")
    print("=" * 60)

    # 查找所有Python文件
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    print(f"找到 {len(python_files)} 个Python文件")

    fixed_count = 0
    error_count = 0

    for file_path in python_files:
        try:
            # 检查文件是否有引号错误
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查是否有参数引号错误
            if re.search(r'^\s+"[^"]+":\s*\w+', content, re.MULTILINE):
                if fix_parameter_quotes_in_file(file_path):
                    fixed_count += 1

            # 检查并修复其他问题
            content = fix_specific_issues(content)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        except Exception as e:
            error_count += 1
            print(f"✗ 处理文件失败 {file_path}: {e}")

    print(f"\n修复完成:")
    print(f"  修复的文件数: {fixed_count}")
    print(f"  错误数: {error_count}")

    # 验证修复结果
    print("\n验证修复结果...")
    success_count = 0
    total_count = 0

    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                total_count += 1
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    compile(content, file_path, 'exec')
                    success_count += 1
                except SyntaxError:
                    pass

    print(f"\n语法正确的文件: {success_count}/{total_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")

    if success_count == total_count:
        print("\n🎉 所有文件语法正确!")
        return True
    else:
        print(f"\n剩余 {total_count - success_count} 个文件需要进一步修复")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
