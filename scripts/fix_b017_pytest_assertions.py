#!/usr/bin/env python3
"""
修复B017 pytest断言错误的脚本
将通用的Exception断言改为具体的异常类型
"""

import os
import re

def fix_pytest_exception_assertions(file_path):
    """修复pytest中的异常断言"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 替换一些常见的模式
        fixes = [
            # 数据库相关异常
            (r'with pytest\.raises\(Exception\):\s*#\s*具体异常类型可能因数据库而异\s*await test_db_session\.commit\(\)',
             'with pytest.raises((IntegrityError, OperationalError)):\n            # 数据库约束违反异常\n            await test_db_session.commit()'),

            # 认证相关异常
            (r'with pytest\.raises\(Exception\):\s*#\s*应该抛出HTTPException\s*await auth_manager\.verify_token\("invalid_token"\)',
             'with pytest.raises(HTTPException):\n            # 应该抛出HTTPException\n            await auth_manager.verify_token("invalid_token")'),

            # 通用异常模式
            (r'with pytest\.raises\(Exception\):\s*#\s*应该抛出HTTPException',
             'with pytest.raises(HTTPException):  # 应该抛出HTTPException'),

            # 无效凭据异常
            (r'with pytest\.raises\(Exception\):\s*await auth_module\.authenticate_user\(None, None, auth_manager\)',
             'with pytest.raises((ValueError, AuthenticationError)):\n            await auth_module.authenticate_user(None, None, auth_manager)'),

            # 配置验证异常
            (r'with pytest\.raises\(Exception\):\s*FixturesCollector\(api_key=None\)\s*#\s*可能会抛出异常',
             'with pytest.raises((ValueError, ConfigurationError)):\n            FixturesCollector(api_key=None)  # 可能会抛出异常'),

            # URL验证异常
            (r'with pytest\.raises\(Exception\):\s*FixturesCollector\(base_url="invalid_url"\)\s*#\s*可能会抛出异常',
             'with pytest.raises((ValueError, ValidationError)):\n            FixturesCollector(base_url="invalid_url")  # 可能会抛出异常'),
        ]

        for pattern, replacement in fixes:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)

        # 添加必要的导入
        if content != original_content:
            needed_imports = []
            if 'HTTPException' in content and 'from fastapi import HTTPException' not in content:
                needed_imports.append('from fastapi import HTTPException')
            if 'IntegrityError' in content or 'OperationalError' in content:
                if 'from sqlalchemy.exc import' not in content:
                    needed_imports.append('from sqlalchemy.exc import IntegrityError, OperationalError')
            if 'AuthenticationError' in content and 'AuthenticationError' not in content:
                needed_imports.append('from src.core.exceptions import AuthenticationError')
            if 'ConfigurationError' in content and 'ConfigurationError' not in content:
                needed_imports.append('from src.core.exceptions import ConfigError as ConfigurationError')
            if 'ValidationError' in content and 'ValidationError' not in content:
                needed_imports.append('from src.core.exceptions import ValidationError')

            # 添加导入
            if needed_imports:
                lines = content.split('\n')
                import_pos = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith(('import ', 'from ')):
                        import_pos = i + 1

                for imp in needed_imports:
                    lines.insert(import_pos, imp)
                    import_pos += 1
                content = '\n'.join(lines)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path} 的pytest异常断言")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 开始修复B017 pytest异常断言错误...")

    # 找到所有需要修复的文件
    result = os.popen("ruff check tests/ --select=B017 --output-format=json").read()
    files_to_fix = set()

    for line in result.split('\n'):
        if '"filename":' in line:
            filename = line.split('"')[3]
            files_to_fix.add(filename)

    fixed_count = 0
    for file_path in sorted(files_to_fix):
        if os.path.exists(file_path):
            if fix_pytest_exception_assertions(file_path):
                fixed_count += 1

    print(f"🎯 修复完成！共修复了 {fixed_count} 个文件的pytest异常断言")

if __name__ == "__main__":
    main()
