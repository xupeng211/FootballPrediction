#!/usr/bin/env python3
"""
修复asyncio导入问题的脚本
"""

import os
import re

def fix_asyncio_import(file_path):
    """为需要asyncio的文件添加导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否使用asyncio但没有导入
        if 'asyncio.' in content and 'import asyncio' not in content:
            lines = content.split('\n')
            
            # 找到合适的导入位置
            import_pos = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    import_pos = i + 1
            
            # 插入asyncio导入
            lines.insert(import_pos, 'import asyncio')
            content = '\n'.join(lines)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print(f"✅ 修复了 {file_path} 的asyncio导入")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def main():
    files_to_fix = [
        "tests/unit/adapters/test_adapters_standalone.py",
        "tests/unit/api/test_api_endpoint.py",
        "tests/unit/api/test_auth_dependencies_fixed.py",
        "tests/unit/api/test_cache_performance_api.py",
        "tests/unit/api/test_database_optimization.py",
        "tests/unit/test_core_exceptions_massive.py",
        "tests/integration/test_api_services_integration.py"
    ]
    
    fixed_count = 0
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_asyncio_import(file_path):
                fixed_count += 1
    
    print(f"🎯 修复了 {fixed_count} 个asyncio导入问题")

if __name__ == "__main__":
    main()
