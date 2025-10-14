#!/usr/bin/env python3
"""
为工具类添加缺失的方法
"""

import ast
import re
from pathlib import Path

def analyze_missing_methods(test_file_path: str):
    """分析测试文件中调用的缺失方法"""
    
    with open(test_file_path, 'r') as f:
        content = f.read()
    
    # 查找所有方法调用
    method_calls = re.findall(r'(\w+)\.(\w+)\(', content)
    
    # 过滤出FileUtils的方法调用
    fileutils_methods = set()
    for obj, method in method_calls:
        if obj == 'FileUtils':
            fileutils_methods.add(method)
    
    return fileutils_methods

def read_existing_methods(class_file_path: str):
    """读取类中已存在的方法"""
    
    try:
        with open(class_file_path, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        existing_methods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and isinstance(node.parent, ast.ClassDef):
                existing_methods.add(node.name)
        
        return existing_methods
    except:
        return set()

if __name__ == "__main__":
    # 分析FileUtils缺失的方法
    missing = analyze_missing_methods("tests/unit/utils/test_file_utils.py")
    print("FileUtils测试中使用的方法:", missing)
    
    # 读取已存在的方法
    existing = read_existing_methods("src/utils/file_utils.py") 
    print("FileUtils中已存在的方法:", existing)
    
    # 找出缺失的方法
    actually_missing = missing - existing
    print("需要添加的方法:", actually_missing)
