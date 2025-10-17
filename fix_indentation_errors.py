#!/usr/bin/env python3
"""
专门修复缩进错误
"""

import re
from pathlib import Path

def fix_indentation_errors(file_path: Path) -> bool:
    """修复文件的缩进错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # 修复 Python 代码块后的缩进
            stripped = line.strip()
            
            # 检查是否是控制结构
            if stripped.startswith(('def ', 'class ', 'async def ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'with ', 'try:', 'except', 'finally:', 'except ', 'async def')):
                # 确保有冒号
                if any(stripped.startswith(x) for x in ['def ', 'class ', 'async def ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'with ', 'try:']):
                    if ':' not in stripped and not stripped.endswith(','):
                        if '(' in line and ')' in line and line.count('(') == line.count(')'):
                            line = line + ':'
                        elif '(' not in line:
                            line = line + ':'
                
                # 确保下一行有正确的缩进
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.strip() and not next_line.startswith('    ') and not next_line.startswith('\t'):
                        if not next_line.strip().startswith('#') and next_line.strip() != '':
                            # 计算正确的缩进
                            if stripped.startswith(('def ', 'class ', 'async def ')):
                                # 函数或类定义
                                lines[i + 1] = '    ' + next_line.strip()
                            elif stripped.startswith(('if ', 'elif ', 'else:', 'for ', 'while ', 'with ', 'try:')):
                                # 控制结构
                                current_indent = len(line) - len(line.lstrip())
                                lines[i + 1] = ' ' * (current_indent + 4) + next_line.strip()
                            elif stripped.startswith(('except', 'finally:')):
                                # 异常处理
                                current_indent = len(line) - len(line.lstrip())
                                lines[i + 1] = ' ' * (current_indent + 4) + next_line.strip()
            
            # 修复 try-except 块
            if stripped.startswith('try:') and not line.endswith(':'):
                line = line + ':'
            
            if stripped.startswith('except') and ':' not in line:
                if '(' in line and ')' in line:
                    line = line + ':'
            
            # 修复 with 语句
            if stripped.startswith('with ') and ':' not in line:
                if '(' in line and ')' in line:
                    line = line + ':'
            
            fixed_lines.append(line)
        
        # 修复其他常见模式
        content = '\n'.join(fixed_lines)
        
        # 修复未闭合的三引号
        if '"""' in content:
            quote_count = content.count('"""')
            if quote_count % 2 != 0:
                content = content.rstrip() + '\n"""'
        
        # 写回文件
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"    错误: {file_path} - {e}")
        return False

def main():
    """主函数"""
    print("修复缩进错误...")
    
    # 查找所有测试文件
    test_files = list(Path('tests').rglob('*.py'))
    
    fixed_count = 0
    for test_file in test_files:
        if '__pycache__' in str(test_file):
            continue
        
        if fix_indentation_errors(test_file):
            fixed_count += 1
            print(f"  ✓ 修复: {test_file}")
    
    print(f"\n修复完成！修复了 {fixed_count} 个文件")

if __name__ == '__main__':
    main()
