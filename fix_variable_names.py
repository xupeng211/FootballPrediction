#!/usr/bin/env python3
"""批量修复变量命名规范问题"""

import re
import os
import sys

# 定义变量名映射
variable_mappings = {
    'Q1': 'q1',
    'Q3': 'q3', 
    'IQR': 'iqr',
    'X_train': 'x_train',
    'X_test': 'x_test',
    'X': 'x',
    'val_X': 'val_x',
    'HAS_BCRYPT': 'has_bcrypt',
}

def fix_variable_names_in_file(file_path):
    """修复单个文件中的变量名"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for old_name, new_name in variable_mappings.items():
            # 匹配变量赋值，避免匹配类名、函数名等
            # 使用正则表达式精确匹配变量赋值模式
            patterns = [
                rf'{old_name}\s*=',  # 赋值模式: Q1 = 
                rf'{old_name}\s*\]',  # 列表/字典索引: data[Q1]
                rf'{old_name}\s*:',  # 类型注解: data: Dict[str, Q1]
                rf'{old_name}\s*=',  # 赋值等号后
                rf'for {old_name}\s+in',  # for循环: for X_train in 
                rf'def {old_name}\(',  # 函数参数: def X_train(
                rf'class {old_name}\(',  # 类继承: class X_train(
            ]
            
            replacement_map = {
                rf'{old_name}\s*=': f'{new_name} =',
                rf'{old_name}\s*]': f'{new_name}]',
                rf'{old_name}\s*:': f'{new_name}:',
                rf'{old_name}\s*,': f'{new_name},',
                rf'for {old_name}\s+in': f'for {new_name} in',
                rf'def {old_name}\(': f'def {new_name}(',
                rf'class {old_name}\(': f'class {new_name}(',
            }
            
            for pattern, replacement in replacement_map.items():
                content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 修复了 {file_path}")
            return True
        return False
        
    except Exception as e:
        print(f"✗ 处理 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python fix_variable_names.py <文件路径>")
        return
    
    file_path = sys.argv[1]
    if os.path.exists(file_path):
        fix_variable_names_in_file(file_path)
    else:
        print(f"文件不存在: {file_path}")

if __name__ == "__main__":
    main()
