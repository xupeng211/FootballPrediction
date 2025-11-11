#!/usr/bin/env python3
"""
修复F821未定义名称错误的脚本
专门处理高优先级的未定义名称问题
"""

import os
import re
from pathlib import Path

def fix_asyncio_imports(file_path):
    """修复asyncio导入问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

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

def fix_database_error_imports(file_path):
    """修复数据库异常导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 检查是否使用了数据库异常但没有导入
        if ('IntegrityError' in content or 'OperationalError' in content) and \
           'from sqlalchemy.exc import' not in content:
            
            lines = content.split('\n')
            
            # 找到合适的导入位置
            import_pos = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    import_pos = i + 1
            
            # 插入数据库异常导入
            lines.insert(import_pos, 'from sqlalchemy.exc import IntegrityError, OperationalError')
            content = '\n'.join(lines)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print(f"✅ 修复了 {file_path} 的数据库异常导入")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def fix_json_import(file_path):
    """修复json导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 检查是否使用json但没有导入
        if 'json.' in content and 'import json' not in content:
            lines = content.split('\n')
            
            # 找到合适的导入位置
            import_pos = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    import_pos = i + 1
            
            # 插入json导入
            lines.insert(import_pos, 'import json')
            content = '\n'.join(lines)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print(f"✅ 修复了 {file_path} 的json导入")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def fix_exception_imports(file_path):
    """修复自定义异常导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fixes_needed = []

        # 检查需要的异常类
        if 'AuthenticationError' in content and 'from src.core.exceptions import' not in content:
            fixes_needed.append('AuthenticationError')
        if 'ConfigurationError' in content and 'ConfigError as ConfigurationError' not in content:
            fixes_needed.append('ConfigError as ConfigurationError')
        if 'ValidationError' in content and 'from src.core.exceptions import' not in content:
            fixes_needed.append('ValidationError')

        if fixes_needed:
            lines = content.split('\n')
            
            # 找到合适的导入位置
            import_pos = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    import_pos = i + 1
            
            # 插入异常导入
            import_line = f"from src.core.exceptions import ({', '.join(fixes_needed)})"
            lines.insert(import_pos, import_line)
            content = '\n'.join(lines)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print(f"✅ 修复了 {file_path} 的异常导入: {', '.join(fixes_needed)}")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def fix_mock_variable_definitions(file_path):
    """修复mock变量定义问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 查找未定义的mock_user_service
        if 'mock_user_service' in content and 'mock_user_service =' not in content:
            lines = content.split('\n')
            
            # 找到第一个使用mock_user_service的位置
            for i, line in enumerate(lines):
                if 'mock_user_service' in line and '=' not in line:
                    # 在此位置之前添加mock定义
                    lines.insert(i, '        mock_user_service = Mock()')
                    content = '\n'.join(lines)
                    break
            
            # 确保导入了Mock
            if 'from unittest.mock import Mock' not in content:
                import_pos = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith(('import ', 'from ')):
                        import_pos = i + 1
                lines.insert(import_pos, 'from unittest.mock import Mock')
                content = '\n'.join(lines)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                print(f"✅ 修复了 {file_path} 的mock变量定义")
                return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 开始修复F821未定义名称错误...")

    # 获取所有包含F821错误的文件
    result = os.popen("ruff check src/ tests/ --select=F821 --output-format=json").read()
    files_to_fix = set()
    
    for line in result.split('\n'):
        if '"filename":' in line:
            filename = line.split('"')[3]
            files_to_fix.add(filename)

    fixed_count = 0
    for file_path in sorted(files_to_fix):
        if os.path.exists(file_path):
            # 尝试不同的修复方法
            if fix_asyncio_imports(file_path):
                fixed_count += 1
            elif fix_database_error_imports(file_path):
                fixed_count += 1
            elif fix_json_import(file_path):
                fixed_count += 1
            elif fix_exception_imports(file_path):
                fixed_count += 1
            elif fix_mock_variable_definitions(file_path):
                fixed_count += 1

    print(f"🎯 修复完成！共修复了 {fixed_count} 个F821未定义名称问题")

if __name__ == "__main__":
    main()
