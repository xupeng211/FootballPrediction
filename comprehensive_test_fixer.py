#!/usr/bin/env python3
"""
全面的测试文件修复工具
专注于修复语法错误，恢复测试运行能力
"""

import ast
import re
import sys
from pathlib import Path

def fix_indentation_issues(content):
    """修复缩进问题"""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # 标准化制表符为空格
        line = line.replace('\t', '    ')
        # 修复行尾多余空格
        line = line.rstrip()
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def fix_string_literals(content):
    """修复字符串字面量问题"""
    # 修复未闭合的字符串
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # 修复分离的f-string
        if re.search(r'f"[^"]*$', line) and not re.search(r'f".*"$', line):
            # 查找下一行是否有字符串 continuation
            line = re.sub(r'f"([^"]*)$', r'f"\1"', line)
        
        # 修复分离的字符串连接
        line = re.sub(r'("[^"]*")\s*\n\s*"([^"]*")', r'\1\2', line)
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def fix_function_calls(content):
    """修复函数调用问题"""
    # 修复分离的函数参数
    content = re.sub(
        r'(\w+)\(\s*\n\s+([^)]+)\s*\)',
        r'\1(\2)',
        content
    )
    
    # 修复未闭合的括号
    content = re.sub(r'\(\s*\n\s*\)', r'()', content)
    
    return content

def fix_common_patterns(content):
    """修复常见的语法错误模式"""
    # 修复logger.debug()调用
    content = re.sub(r'logger\.debug\(\s*\)\s*f"([^"]*)"', r'logger.debug(f"\1")', content)
    
    # 修复分离的断言语句
    content = re.sub(r'assert\s+([^,\n]+)\s*,\s*\n\s*"([^"]*)"', r'assert \1, "\2"', content)
    
    # 修复未闭合的print语句
    content = re.sub(r'print\(\s*([^)]*)\s*\n\s*\)', r'print(\1)', content)
    
    return content

def fix_test_file(file_path):
    """修复单个测试文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 应用修复
        content = fix_indentation_issues(content)
        content = fix_string_literals(content)
        content = fix_function_calls(content)
        content = fix_common_patterns(content)
        
        # 验证语法
        try:
            ast.parse(content)
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            return True, "修复成功"
        except SyntaxError as e:
            return False, f"语法错误: 行 {e.lineno} - {e.msg}"
            
    except Exception as e:
        return False, f"处理失败: {e}"

def main():
    """主修复函数"""
    # 获取所有测试文件
    test_dir = Path("tests")
    test_files = list(test_dir.rglob("test_*.py")) + list(test_dir.rglob("*_test.py"))
    
    print(f"🔍 找到 {len(test_files)} 个测试文件")
    
    fixed_count = 0
    failed_count = 0
    skipped_count = 0
    
    for test_file in test_files:
        try:
            # 先检查语法是否正确
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            print(f"✅ {test_file}: 语法正确")
            skipped_count += 1
            continue
        except SyntaxError:
            pass  # 需要修复
        
        success, message = fix_test_file(test_file)
        if success:
            print(f"✅ {test_file}: {message}")
            fixed_count += 1
        else:
            print(f"❌ {test_file}: {message}")
            failed_count += 1
    
    print(f"\n📊 修复统计:")
    print(f"  ✅ 修复成功: {fixed_count}")
    print(f"  ❌ 修复失败: {failed_count}")
    print(f"  ⚠️  跳过(已正确): {skipped_count}")
    print(f"  📁 总文件数: {len(test_files)}")
    
    return fixed_count, failed_count, skipped_count

if __name__ == "__main__":
    main()
