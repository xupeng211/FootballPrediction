#!/usr/bin/env python3
"""
修复核心模块的语法错误
"""

import re
from pathlib import Path

def fix_core_directory():
    """修复 src/core/ 目录"""
    print("修复 src/core/ 目录的语法错误...")
    
    core_files = list(Path('src/core').rglob('*.py'))
    fixed_count = 0
    
    for file_path in core_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            
            # 修复常见的语法错误
            content = fix_common_patterns(content)
            
            if content != original:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_count += 1
                print(f"  ✓ 修复: {file_path}")
            else:
                print(f"  - 正常: {file_path}")
                
        except Exception as e:
            print(f"  ✗ 错误: {file_path} - {e}")
    
    print(f"\n修复完成！修复了 {fixed_count} 个文件")

def fix_common_patterns(content):
    """修复常见的语法错误模式"""
    # 1. 修复括号错误
    content = content.replace('[)', '[]')
    content = content.replace('{)', '{}')
    content = content.replace('(,)', '(None,)')
    content = content.replace('__all__ = [)', '__all__ = []')
    
    # 2. 修复字典和列表
    content = content.replace('dict {)', 'dict {}')
    content = content.replace('list {)', 'list []')
    content = content.replace('tuple {)', 'tuple ()')
    content = content.replace('set {)', 'set {}')
    
    # 3. 修复 return 语句
    content = content.replace('return [)', 'return []')
    content = content.replace('return {)', 'return {}')
    
    # 4. 修复多行语句的缩进
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # 修复 logger 调用
        if 'logger.' in line and line.count('(') > line.count(')'):
            # 检查是否是多行 logger 调用
            j = i + 1
            paren_count = line.count('(') - line.count(')')
            while j < len(lines) and paren_count > 0:
                if '(' in lines[j]:
                    paren_count += 1
                if ')' in lines[j]:
                    paren_count -= 1
                j += 1
            
            # 修复中间行的缩进
            base_indent = len(line) - len(line.lstrip())
            for k in range(i + 1, min(j, len(lines))):
                if lines[k].strip() and not lines[k].startswith(' ' * (base_indent + 4)):
                    if not lines[k].strip().startswith('#'):
                        lines[k] = ' ' * (base_indent + 4) + lines[k].strip()
        
        # 修复异常处理
        if line.strip().startswith('except ') and ':' not in line:
            if '(' in line and ')' in line:
                line = line + ':'
        
        # 修复 if 语句
        if line.strip().startswith('if ') and '(' in line and ')' in line:
            if ':' not in line and line.count('(') == line.count(')'):
                line = line + ':'
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

if __name__ == '__main__':
    fix_core_directory()
