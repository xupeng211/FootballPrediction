#!/usr/bin/env python3
"""
基于 AST 的语法错误检测和修复工具
"""

import ast
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

class SyntaxFixer:
    """语法错误修复器"""
    
    def __init__(self):
        self.fixed_files = []
        self.failed_files = []
        
    def fix_file(self, file_path: Path) -> bool:
        """修复单个文件的语法错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试解析 AST
            try:
                ast.parse(content)
                return True  # 文件没有语法错误
            except SyntaxError as e:
                print(f"  需要修复: {file_path} - {e}")
            
            # 修复常见错误
            fixed_content = self.apply_fixes(content)
            
            # 验证修复结果
            try:
                ast.parse(fixed_content)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                self.fixed_files.append(str(file_path))
                print(f"  ✓ 修复成功: {file_path}")
                return True
            except SyntaxError:
                self.failed_files.append((str(file_path), "仍有语法错误"))
                print(f"  ✗ 仍有错误: {file_path}")
                return False
                
        except Exception as e:
            self.failed_files.append((str(file_path), str(e)))
            print(f"  ✗ 处理失败: {file_path} - {e}")
            return False
    
    def apply_fixes(self, content: str) -> str:
        """应用语法修复"""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # 修复第1类错误：未闭合的括号导致的换行问题
            if line.count('(') > line.count(')') and not line.rstrip().endswith(','):
                # 如果行末有未闭合的括号，需要检查下一行
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # 如果下一行是表达式的一部分但缩进不对
                    if next_line.strip() and not next_line.startswith('    ') and not next_line.startswith('\t'):
                        if not next_line.strip().startswith('#'):
                            lines[i + 1] = '    ' + next_line.strip()
            
            # 修复第2类错误：多行参数/列表的语法
            if line.strip().startswith(('def ', 'class ', 'async def ')):
                # 检查函数/类定义行
                if ':' not in line and '(' in line and ')' in line:
                    line = line + ':'
            
            # 修复第3类错误：条件语句
            if line.strip().startswith('if ') and '(' in line and ')' in line:
                if ':' not in line and line.count('(') == line.count(')'):
                    line = line + ':'
            
            # 修复第4类错误：import 语句
            if 'import (' in line and not line.endswith(')'):
                # 多行 import，需要找到结束括号
                j = i + 1
                paren_count = 1
                while j < len(lines) and paren_count > 0:
                    if '(' in lines[j]:
                        paren_count += 1
                    if ')' in lines[j]:
                        paren_count -= 1
                        if paren_count == 0:
                            break
                    j += 1
            
            fixed_lines.append(line)
        
        # 修复第5类错误：整体字符串替换
        content = '\n'.join(fixed_lines)
        
        # 常见模式替换
        replacements = [
            ('__all__ = [)', '__all__ = []'),
            ('return [)', 'return []'),
            ('return {)', 'return {}'),
            ('dict {)', 'dict {}'),
            ('list {)', 'list []'),
            ('tuple {)', 'tuple ()'),
            ('set {)', 'set {}'),
            ('(,)', '(None,)'),
        ]
        
        for old, new in replacements:
            content = content.replace(old, new)
        
        return content
    
    def fix_directory(self, directory: str) -> Dict[str, int]:
        """修复目录下的所有 Python 文件"""
        print(f"\n修复 {directory} 目录...")
        
        for py_file in Path(directory).rglob('*.py'):
            # 跳过 __pycache__ 和其他临时文件
            if '__pycache__' in str(py_file):
                continue
            
            self.fix_file(py_file)
        
        return {
            'fixed': len(self.fixed_files),
            'failed': len(self.failed_files)
        }

def fix_test_files():
    """修复测试文件"""
    fixer = SyntaxFixer()
    
    # 优先级1：核心业务逻辑测试
    priority_tests = [
        'tests/unit/predictions/',
        'tests/unit/domain/',
        'tests/unit/services/',
        'tests/unit/repositories/',
    ]
    
    # 优先级2：API 测试
    api_tests = [
        'tests/unit/api/',
        'tests/integration/api/',
    ]
    
    # 优先级3：工具类测试
    utils_tests = [
        'tests/unit/utils/',
        'tests/integration/',
    ]
    
    print("=" * 60)
    print("开始分阶段修复测试文件")
    print("=" * 60)
    
    # 第一阶段：修复核心业务逻辑测试
    print("\n[第一阶段] 修复核心业务逻辑测试...")
    for test_dir in priority_tests:
        if Path(test_dir).exists():
            result = fixer.fix_directory(test_dir)
            print(f"  {test_dir}: 修复 {result['fixed']} 个, 失败 {result['failed']} 个")
    
    # 第二阶段：修复 API 测试
    print("\n[第二阶段] 修复 API 测试...")
    for test_dir in api_tests:
        if Path(test_dir).exists():
            result = fixer.fix_directory(test_dir)
            print(f"  {test_dir}: 修复 {result['fixed']} 个, 失败 {result['failed']} 个")
    
    # 第三阶段：修复其他测试
    print("\n[第三阶段] 修复其他测试...")
    for test_dir in utils_tests:
        if Path(test_dir).exists():
            result = fixer.fix_directory(test_dir)
            print(f"  {test_dir}: 修复 {result['fixed']} 个, 失败 {result['failed']} 个")
    
    return fixer

if __name__ == '__main__':
    fixer = fix_test_files()
    
    print("\n" + "=" * 60)
    print("修复总结")
    print("=" * 60)
    print(f"成功修复: {len(fixer.fixed_files)} 个文件")
    print(f"修复失败: {len(fixer.failed_files)} 个文件")
    
    if fixer.failed_files:
        print("\n失败的文件（前10个）:")
        for file, error in fixer.failed_files[:10]:
            print(f"  - {file}: {error}")
