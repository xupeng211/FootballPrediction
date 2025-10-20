#!/usr/bin/env python3
"""
智能检测并添加缺失的typing导入
"""

import re
from pathlib import Path

def has_typing_import(content):
    """检查是否已有typing导入"""
    return 'from typing import' in content

def get_used_typing_names(content):
    """获取文件中使用的typing名称"""
    # 查找类型注解中使用的typing名称
    pattern = r'\b(Any|Dict|List|Optional|Union|Tuple|Set|Callable|Type|Iterator|Generator|Protocol|Literal|Final|ClassVar|cast|overload)\b'
    matches = re.findall(pattern, content)
    # 去重并排序
    return sorted(set(matches))

def add_typing_import(file_path):
    """为文件添加typing导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 跳过已经有typing导入的文件
        if has_typing_import(content):
            return False
        
        # 获取使用的typing名称
        used_names = get_used_typing_names(content)
        if not used_names:
            return False
        
        # 查找插入位置（在其他import之后）
        lines = content.split('\n')
        insert_index = 0
        
        # 找到最后一个import语句
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                insert_index = i + 1
        
        # 构建typing导入语句
        typing_import = f"from typing import {', '.join(used_names)}"
        
        # 插入typing导入
        lines.insert(insert_index, typing_import)
        lines.insert(insert_index + 1, '')  # 添加空行
        
        # 写回文件
        new_content = '\n'.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✓ Added typing import to {file_path}: {', '.join(used_names)}")
        return True
        
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False

def main():
    """主函数"""
    src_dir = Path("src")
    fixed_count = 0
    
    # 处理所有Python文件
    for py_file in src_dir.rglob("*.py"):
        if add_typing_import(py_file):
            fixed_count += 1
    
    print(f"\n处理完成！为 {fixed_count} 个文件添加了typing导入")

if __name__ == "__main__":
    main()
