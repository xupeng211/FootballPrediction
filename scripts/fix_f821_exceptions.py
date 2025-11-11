#!/usr/bin/env python3
"""
F821错误修复脚本 - 异常类篇
专门处理自定义异常类未定义问题
"""

import os
import re
from pathlib import Path

def fix_exception_imports(file_path):
    """修复异常类导入问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 需要添加的异常类
        exceptions_needed = []
        
        if 'ServiceError' in content and 'from src.core.exceptions import' not in content:
            exceptions_needed.append('ServiceError')
        if 'ModelError' in content and 'from src.core.exceptions import' not in content:
            exceptions_needed.append('ModelError')
        if 'DependencyInjectionError' in content and 'from src.core.exceptions import' not in content:
            exceptions_needed.append('DependencyInjectionError')
        if 'FootballPredictionError' in content and 'from src.core.exceptions import' not in content:
            exceptions_needed.append('FootballPredictionError')
        if 'ConfigError' in content and 'from src.core.exceptions import' not in content:
            exceptions_needed.append('ConfigError')
        if 'DataError' in content and 'from src.core.exceptions import' not in content:
            exceptions_needed.append('DataError')
        if 'PredictionError' in content and 'from src.core.exceptions import' not in content:
            exceptions_needed.append('PredictionError')
        if 'CacheError' in content and 'from src.core.exceptions import' not in content:
            exceptions_needed.append('CacheError')
        if 'DatabaseError' in content and 'from src.core.exceptions import' not in content:
            exceptions_needed.append('DatabaseError')
        if 'ValidationError' in content and 'from src.core.exceptions import' not in content:
            exceptions_needed.append('ValidationError')

        if exceptions_needed:
            # 查找导入区域
            import_end = 0
            lines = content.split('\n')

            # 找到最后一个import语句
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    import_end = i + 1

            # 构建导入语句
            import_line = f"from src.core.exceptions import ({', '.join(exceptions_needed)})"
            lines.insert(import_end, import_line)
            content = '\n'.join(lines)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✅ 修复了 {file_path} 的异常类导入: {', '.join(exceptions_needed)}")
            return True

        return False

    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def fix_pytest_imports(file_path):
    """修复pytest导入问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if 'pytest.' in content and 'import pytest' not in content:
            # 查找导入区域
            import_end = 0
            lines = content.split('\n')

            # 找到最后一个import语句
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    import_end = i + 1

            # 插入pytest导入
            lines.insert(import_end, 'import pytest')
            content = '\n'.join(lines)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✅ 修复了 {file_path} 的pytest导入")
            return True

        return False

    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 开始修复F821异常类和pytest导入错误...")

    # 需要修复的测试文件
    files_to_fix = [
        "tests/unit/test_core_exceptions.py",
        "tests/unit/test_core_exceptions_massive.py",
        "tests/unit/utils/test_formatters.py"
    ]

    fixed_count = 0

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_exception_imports(file_path):
                fixed_count += 1
            if fix_pytest_imports(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  文件不存在: {file_path}")

    print(f"🎯 修复完成！共修复了 {fixed_count} 个异常类导入问题")

if __name__ == "__main__":
    main()
