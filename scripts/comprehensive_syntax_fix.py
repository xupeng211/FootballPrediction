#!/usr/bin/env python3
"""综合语法错误修复工具 - 使用Python编译器进行精确修复"""

import ast
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Dict

def check_file_syntax(file_path: str) -> Optional[str]:
    """检查文件语法，返回错误信息"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        compile(content, file_path, 'exec')
        return None
    except SyntaxError as e:
        return f"第{e.lineno}行: {e.msg}"

def fix_specific_errors(file_path: str) -> bool:
    """修复特定文件的已知错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')
        fixed_lines = lines.copy()

        # 根据文件路径应用特定的修复
        if 'facade' in file_path:
            # 修复facade文件中的常见错误
            for i, line in enumerate(fixed_lines):
                # 修复 List[Dict[str, Any]) -> List[Dict[str, Any]]
                line = re.sub(r'List\[Dict\[str, Any\)\]', r'List[Dict[str, Any]]', line)
                # 修复类似的模式
                line = re.sub(r'Tuple\[str, Any\)\]', r'Tuple[str, Any]]', line)
                line = re.sub(r'Optional\[Dict\[str, Any\)\]', r'Optional[Dict[str, Any]]', line)
                fixed_lines[i] = line

        elif 'models' in file_path:
            # 修复models文件中的错误
            for i, line in enumerate(fixed_lines):
                # 修复类型注解
                line = re.sub(r'Optional\[List\[(.*?)\]\s*=\s*None\]', r'Optional[List[\1]] = None', line)
                line = re.sub(r'Optional\[Dict\[(.*?)\]\s*=\s*None\]', r'Optional[Dict[\1]] = None', line)
                # 修复未闭合的字符串
                if ':' in line and '"' in line and not line.count('"') % 2 == 0:
                    if line.strip().endswith(','):
                        line = line[:-1] + '",'
                    else:
                        line = line + '"'
                fixed_lines[i] = line

        elif 'strategies' in file_path or 'domain' in file_path:
            # 修复domain strategies文件
            for i, line in enumerate(fixed_lines):
                # 修复括号不匹配
                line = re.sub(r'\]\s*\)\s*]', ']]', line)
                line = re.sub(r'\}\s*\]\s*\}', '}}', line)
                # 修复类型注解
                line = re.sub(r'List\[Dict\[str, Any\)\]', r'List[Dict[str, Any]]', line)
                fixed_lines[i] = line

        # 通用修复
        for i, line in enumerate(fixed_lines):
            # 修复文件末尾的多余符号
            if i == len(fixed_lines) - 1:
                line = re.sub(r'[\]}"]+$', '', line)

            # 修复字典键缺少引号
            if ': ' in line and not line.strip().startswith('#'):
                # 检查是否是字典项
                parts = line.split(': ', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    # 如果键没有引号，添加引号
                    if not (key.startswith('"') and key.endswith('"')) and not (key.startswith("'") and key.endswith("'")):
                        if key.replace('_', '').replace('-', '').isalnum():
                            fixed_lines[i] = f'    "{key}": {parts[1]}'

            # 修复未闭合的字符串（简单情况）
            quote_count = line.count('"')
            if quote_count % 2 == 1 and ':' in line:
                if not line.rstrip().endswith(','):
                    line = line + '"'
                else:
                    line = line[:-1] + '",'
                fixed_lines[i] = line

        content = '\n'.join(fixed_lines)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"修复文件失败 {file_path}: {e}")
        return False

def manual_fix_instructions(file_path: str, error_msg: str) -> str:
    """生成手动修复指导"""
    instructions = f"\n文件: {file_path}\n"
    instructions += f"错误: {error_msg}\n"

    if "unterminated string literal" in error_msg:
        instructions += "修复建议: 查找未闭合的字符串，添加结束引号\n"
    elif "unmatched" in error_msg or "does not match" in error_msg:
        instructions += "修复建议: 检查括号匹配，确保 [] () {} 正确配对\n"
    elif "invalid syntax" in error_msg:
        instructions += "修复建议: 检查语法错误，可能是缺少逗号、引号或括号\n"
    elif "unexpected indent" in error_msg:
        instructions += "修复建议: 检查缩进是否正确\n"

    return instructions

def main():
    """主函数"""
    print("综合语法错误修复工具")
    print("=" * 60)

    # 查找所有Python文件
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    print(f"找到 {len(python_files)} 个Python文件")

    # 第一轮：自动修复
    print("\n第一轮：自动修复...")
    auto_fixed = 0
    for file_path in python_files:
        if fix_specific_errors(file_path):
            auto_fixed += 1
            print(f"✓ 自动修复: {file_path}")

    print(f"\n自动修复完成: {auto_fixed} 个文件")

    # 第二轮：检查剩余错误
    print("\n第二轮：检查语法错误...")
    error_files = []
    for file_path in python_files:
        error = check_file_syntax(file_path)
        if error:
            error_files.append((file_path, error))

    if error_files:
        print(f"\n发现 {len(error_files)} 个文件仍有语法错误:")

        # 生成Python编译命令用于调试
        with open('debug_syntax.sh', 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("# 调试语法错误的脚本\n\n")
            for file_path, error in error_files[:10]:  # 只显示前10个
                f.write(f'echo "检查文件: {file_path}"\n')
                f.write(f'python -m py_compile "{file_path}"\n')
                f.write('echo "---"\n')

        os.chmod('debug_syntax.sh', 0o755)

        # 显示错误详情
        for file_path, error in error_files[:20]:  # 只显示前20个
            print(f"\n✗ {file_path}")
            print(f"  {error}")
            # 尝试自动修复
            if fix_specific_errors(file_path):
                print("  → 尝试修复...")
                new_error = check_file_syntax(file_path)
                if not new_error:
                    print("  ✓ 修复成功!")
                else:
                    print(f"  ✗ 仍有错误: {new_error}")

        # 生成详细的修复指导文件
        with open('syntax_fix_guide.md', 'w', encoding='utf-8') as f:
            f.write("# 语法错误修复指南\n\n")
            f.write(f"剩余需要手动修复的文件数: {len(error_files)}\n\n")

            for file_path, error in error_files:
                f.write(f"## {file_path}\n")
                f.write(f"错误: {error}\n")
                f.write(f"\n修复建议:\n")
                f.write("```bash\n")
                f.write(f"# 使用Python检查详细错误\n")
                f.write(f'python -c "import ast; print(ast.parse(open(\'{file_path}\').read()))"\n')
                f.write("```\n\n")

        print(f"\n详细修复指南已保存到: syntax_fix_guide.md")
        print("运行 ./debug_syntax.sh 查看详细的编译错误")

    # 最终统计
    print("\n" + "=" * 60)
    success_count = len(python_files) - len(error_files)
    print(f"语法正确的文件: {success_count}/{len(python_files)}")
    print(f"成功率: {success_count/len(python_files)*100:.1f}%")

    if error_files:
        print(f"\n剩余 {len(error_files)} 个文件需要手动修复")
        return False
    else:
        print("\n🎉 所有文件语法正确!")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
