#!/usr/bin/env python3
"""
快速修复导入问题的脚本
"""

import os
import re

def fix_common_imports(file_path):
    """快速修复常见导入问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 需要添加的导入
        imports_to_add = []

        # 检查需要的导入
        if 'create_async_engine' in content and 'from sqlalchemy import' not in content:
            imports_to_add.append('from sqlalchemy import create_async_engine, create_engine')
        
        if 'sessionmaker' in content and 'from sqlalchemy.orm import' not in content:
            imports_to_add.append('from sqlalchemy.orm import sessionmaker')
        
        if 'AsyncSession' in content and 'from sqlalchemy.ext.asyncio' not in content:
            imports_to_add.append('from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker')
        
        if 'TestClient' in content and 'from fastapi.testclient import' not in content:
            imports_to_add.append('from fastapi.testclient import TestClient')
        
        if 'AsyncClient' in content and 'from httpx import' not in content:
            imports_to_add.append('from httpx import AsyncClient')
        
        if 'datetime' in content and 'import datetime' not in content:
            imports_to_add.append('from datetime import datetime')
        
        if 'psutil' in content and 'import psutil' not in content:
            imports_to_add.append('import psutil')
        
        if 'os' in content and 'import os' not in content:
            imports_to_add.append('import os')
        
        if 'asyncio' in content and 'import asyncio' not in content:
            imports_to_add.append('import asyncio')

        # 添加导入到文件开头
        if imports_to_add:
            lines = content.split('\n')
            
            # 找到合适的导入位置
            import_pos = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    import_pos = i + 1
                elif line.strip().startswith('#') and i > 0:
                    # 遇到注释，停止查找
                    break
            
            # 添加导入
            for imp in imports_to_add:
                if imp not in content:
                    lines.insert(import_pos, imp)
                    import_pos += 1
            
            content = '\n'.join(lines)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path} 的导入")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 快速修复常见导入问题...")

    # 需要修复的文件
    files_to_fix = [
        "tests/integration/conftest.py",
        "tests/unit/data/collectors/test_fixtures_collector.py",
        "tests/unit/services/test_service_manager_comprehensive.py"
    ]

    fixed_count = 0
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_common_imports(file_path):
                fixed_count += 1

    print(f"🎯 快速修复完成！共修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()
