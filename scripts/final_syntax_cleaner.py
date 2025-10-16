#!/usr/bin/env python3
"""最终语法清理工具 - 安全地修复最常见的错误"""

import ast
import os
import re
import sys
from pathlib import Path

def clean_syntax_errors(file_path: str) -> bool:
    """安全地清理语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        modified = False

        # 1. 修复参数定义中的引号（只修复明显的错误）
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 跳过注释和文档字符串
            if line.strip().startswith('#') or '"""' in line:
                fixed_lines.append(line)
                continue

            # 修复函数参数定义（只在明显错误的情况下）
            # 检查是否是参数定义行（包含冒号和类型）
            if re.match(r'^\s+"[^"]+":\s*\w+', line):
                # 确保这行不在类或函数定义中
                if not any(keyword in line for keyword in ['class ', 'def ', 'async def']):
                    # 移除参数名中的引号
                    line = re.sub(r'^(\s+)"([^"]+)":', r'\1\2:', line)
                    modified = True

            # 修复字典定义中缺失的键（只修复明显的情况）
            if ': "' in line and not line.rstrip().endswith('"'):
                # 检查是否是字典项且看起来缺少引号
                if line.count('"') % 2 == 1 and '=' not in line.split(':')[0]:
                    if line.rstrip().endswith(','):
                        line = line[:-1] + '",'
                    else:
                        line = line + '"'
                    modified = True

            fixed_lines.append(line)

        content = '\n'.join(fixed_lines)

        # 2. 修复全局变量定义中的引号（保守修复）
        # 只修复明显的全局变量，不修复类属性或函数参数
        patterns = [
            # 修复全局变量定义（只在行首）
            (r'^(\s*)_([A-Z_]+): Optional\[', r'\1\2: Optional['),
            (r'^(\s*)_([A-Z_]+): List\[', r'\1\2: List['),
            (r'^(\s*)_([A-Z_]+): Dict\[', r'\1\2: Dict['),
            # 修复函数参数（更保守）
            (r'^(\s+)([a-z_][a-z0-9_]*)"', r'\1\2'),
            (r'"([a-z_][a-z0-9_]*)": Optional\[', r'\1: Optional['),
            (r'"([a-z_][a-z0-9_]*)": List\[', r'\1: List['),
            (r'"([a-z_][a-z0-9_]*)": Dict\[', r'\1: Dict['),
        ]

        for pattern, replacement in patterns:
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            if new_content != content:
                content = new_content
                modified = True

        # 3. 修复类型注解中的常见错误
        type_fixes = [
            # Optional[List[str] = None] -> Optional[List[str]] = None
            (r'Optional\[(\w+)\[([^\]]+)\]\s*=\s*None\]', r'Optional[\1[\2]]] = None'),
            # List[Dict[str, Any]) -> List[Dict[str, Any]]
            (r'List\[Dict\[str, Any\)\]', r'List[Dict[str, Any]]'),
            # Dict[str, List[float]] = { 后面跟了错误的格式
            (r'Dict\[str, List\[float\]\]\s*=\s*\{\s*"[^"]*"\s*,', r'Dict[str, List[float]] = {\n        "'),
        ]

        for pattern, replacement in type_fixes:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                modified = True

        # 4. 修复文件末尾的额外字符（保守修复）
        lines = content.split('\n')
        if lines:
            last_line = lines[-1].strip()
            # 只移除明显的多余字符
            if last_line in ['"}', '}"}', '"', '"}']:
                lines[-1] = ''
                content = '\n'.join(lines)
                modified = True

        # 验证修复后的内容
        if modified:
            try:
                ast.parse(content)
                # 如果语法正确，写回文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            except SyntaxError:
                # 修复失败，恢复原内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                print(f"  警告: 修复失败，已恢复原文件")
                return False

        return False

    except Exception as e:
        print(f"  错误: {e}")
        return False

def main():
    """主函数"""
    print("最终语法清理工具")
    print("=" * 60)

    # 查找所有Python文件
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    print(f"找到 {len(python_files)} 个Python文件")

    # 检查和修复
    error_count = 0
    fixed_count = 0

    for file_path in python_files:
        try:
            # 检查语法
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
        except SyntaxError:
            error_count += 1
            print(f"\n检查: {file_path}")
            if clean_syntax_errors(file_path):
                fixed_count += 1
                print(f"  ✓ 修复成功")
                # 再次验证
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    ast.parse(content)
                except SyntaxError as e:
                    print(f"  ✗ 仍有语法错误: {e}")
            else:
                print(f"  - 无法自动修复")

    # 最终统计
    print("\n" + "=" * 60)
    print(f"语法错误文件: {error_count}")
    print(f"成功修复: {fixed_count}")

    # 统计当前正确的文件数
    success_count = 0
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            success_count += 1
        except SyntaxError:
            pass

    print(f"\n语法正确文件: {success_count}/{len(python_files)} ({success_count/len(python_files)*100:.1f}%)")

    if success_count == len(python_files):
        print("\n🎉 所有文件语法正确!")
    else:
        print(f"\n剩余 {len(python_files) - success_count} 个文件需要手动修复")

        # 生成报告
        with open('syntax_status_report.txt', 'w') as f:
            f.write(f"语法状态报告\n")
            f.write(f"=" * 50 + "\n")
            f.write(f"总文件数: {len(python_files)}\n")
            f.write(f"语法正确: {success_count}\n")
            f.write(f"语法错误: {len(python_files) - success_count}\n")
            f.write(f"成功率: {success_count/len(python_files)*100:.1f}%\n\n")

            # 列出仍有错误的文件
            f.write("仍有语法错误的文件:\n")
            for file_path in python_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    ast.parse(content)
                except SyntaxError as e:
                    f.write(f"- {file_path}: 第{e.lineno}行 - {e.msg}\n")

        print("\n详细报告已保存到: syntax_status_report.txt")

    return success_count == len(python_files)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
