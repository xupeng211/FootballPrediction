#!/usr/bin/env python3
"""批量语法修复高级版"""

import os
import re
import ast
import sys
from pathlib import Path

def fix_file_syntax(file_path: str) -> bool:
    """修复单个文件的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')
        modified = False

        # 1. 修复参数定义中的引号错误
        for i, line in enumerate(lines):
            # 修复类属性或函数参数
            patterns = [
                # 移除参数名中的引号
                (r'^(\s+)"([^"]+)":\s*(str|int|float|bool|Optional|List|Dict|Union|Tuple|Callable|Any)', r'\1\2: \3'),
                # 修复字典键
                (r'^(\s+)"([^"]+)":\s*(None|True|False)', r'\1\2: \3'),
                # 修复数据类字段
                (r'^(\s+)"([^"]+)":\s*(.+?=.+)$', r'\1\2: \3'),
            ]

            for pattern, replacement in patterns:
                new_line = re.sub(pattern, replacement, line)
                if new_line != line:
                    lines[i] = new_line
                    modified = True

        # 2. 修复未闭合的字符串（更精确）
        for i, line in enumerate(lines):
            # 检查未闭合的三引号
            if '"""' in line and line.count('"""') % 2 == 1:
                if not line.rstrip().endswith('"""'):
                    lines[i] = line + '"""'
                    modified = True

            # 检查未闭合的普通引号
            elif line.count('"') % 2 == 1 and not line.strip().startswith('#'):
                if ':' in line and not line.strip().endswith(':'):
                    if line.rstrip().endswith(','):
                        lines[i] = line[:-1] + '",'
                    else:
                        lines[i] = line + '"'
                    modified = True

        # 3. 修复类型注解中的常见错误
        content = '\n'.join(lines)
        patterns = [
            # 修复 Optional[List[str] = None] -> Optional[List[str]] = None
            (r'Optional\[(\w+)\[([^\]]+)\]\s*=\s*None\]', r'Optional[\1[\2]]] = None'),
            # 修复 List[Dict[str, Any]) -> List[Dict[str, Any]]
            (r'List\[Dict\[str, Any\)\]', r'List[Dict[str, Any]]'),
            # 修复 Dict[str, Any]
            (r'Dict\[str,\s*Any\)\]', r'Dict[str, Any]]'),
            # 修复 Tuple[str, Any]
            (r'Tuple\[(\w+),\s*(\w+)\)\)\]', r'Tuple[\1, \2]]'),
        ]

        for pattern, replacement in patterns:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                modified = True

        # 4. 修复字典/列表结构错误
        lines = content.split('\n')
        for i in range(len(lines)):
            line = lines[i]
            # 修复字典定义中的格式错误
            if '{' in line and '}' in line and ':' in line:
                # 修复 {"key": value,} -> {"key": value}
                if line.strip().endswith('"}'):
                    lines[i] = line[:-2] + '}'
                    modified = True

        content = '\n'.join(lines)

        # 5. 修复缩进问题
        lines = content.split('\n')
        for i in range(len(lines) - 1):
            line = lines[i]
            next_line = lines[i + 1]

            # 如果当前行以冒号结尾，下一行应该缩进
            if line.strip().endswith(':') and not next_line.strip().startswith('#'):
                if not (next_line.startswith('    ') or next_line.startswith('\t')):
                    lines[i + 1] = '    ' + next_line
                    modified = True

        content = '\n'.join(lines)

        # 验证修复
        if modified:
            try:
                ast.parse(content)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            except SyntaxError:
                # 恢复原内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                return False

        return False

    except Exception as e:
        print(f"  错误: {e}")
        return False

def main():
    """主函数"""
    print("批量语法修复高级版")
    print("=" * 60)

    # 查找所有Python文件
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    print(f"找到 {len(python_files)} 个Python文件")

    # 检查并修复
    error_count = 0
    fixed_count = 0
    skipped_count = 0

    for file_path in python_files:
        try:
            # 检查语法
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
        except SyntaxError as e:
            error_count += 1
            print(f"\n处理: {file_path}")
            print(f"  错误: 第{e.lineno}行 - {e.msg}")

            if fix_file_syntax(file_path):
                fixed_count += 1
                print(f"  ✓ 修复成功")
            else:
                skipped_count += 1
                print(f"  - 跳过（需要手动修复）")

    # 最终统计
    print("\n" + "=" * 60)
    print(f"发现错误: {error_count} 个文件")
    print(f"修复成功: {fixed_count} 个文件")
    print(f"需要手动: {skipped_count} 个文件")

    # 验证最终状态
    success_count = 0
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            success_count += 1
        except SyntaxError:
            pass

    print(f"\n语法正确: {success_count}/{len(python_files)} ({success_count/len(python_files)*100:.1f}%)")

    if success_count == len(python_files):
        print("\n🎉 所有文件语法正确!")
    else:
        print(f"\n剩余 {len(python_files) - success_count} 个文件需要手动修复")

    return success_count == len(python_files)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)