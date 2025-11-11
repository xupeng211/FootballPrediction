#!/usr/bin/env python3
"""
修复高频F821错误
专门处理最频繁出现的未定义名称错误
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def get_f821_errors():
    """获取所有F821错误"""
    import subprocess
    result = subprocess.run(
        ["ruff", "check", "src/", "tests/", "--output-format=concise"],
        capture_output=True,
        text=True
    )

    errors = []
    for line in result.stdout.split('\n'):
        if 'F821' in line:
            parts = line.split(':')
            if len(parts) >= 4:
                file_path = Path(parts[0])
                line_num = int(parts[1])
                error_msg = ':'.join(parts[3:]).strip()
                # 提取未定义名称
                undefined_name = error_msg.split('Undefined name `')[-1].split('`')[0]
                errors.append({
                    'file': file_path,
                    'line': line_num,
                    'undefined_name': undefined_name,
                    'error': error_msg
                })

    return errors

def fix_test_api_services_integration(content):
    """修复test_api_services_integration.py中的asyncio问题"""
    if 'asyncio.TimeoutError' in content and 'import asyncio' not in content:
        # 查找导入部分
        lines = content.split('\n')

        # 查找最后一个导入
        last_import = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                last_import = i

        if last_import >= 0:
            lines.insert(last_import + 1, 'import asyncio')
        else:
            # 在文档字符串后添加
            lines.insert(0, 'import asyncio')

        content = '\n'.join(lines)

    return content

def fix_test_api_endpoint(content):
    """修复test_api_endpoint.py中的导入问题"""
    lines = content.split('\n')

    # 查找文件开头
    insert_index = 0

    # 添加缺失的导入
    imports_to_add = []

    if 'load_dotenv()' in content and 'import dotenv' not in content and 'from dotenv' not in content:
        imports_to_add.append('from dotenv import load_dotenv')

    if 'data_source_manager' in content and 'import data_source_manager' not in content:
        imports_to_add.append('from src.collectors.data_sources import data_source_manager')

    if 'timedelta' in content and 'from datetime import timedelta' not in content and 'import timedelta' not in content:
        imports_to_add.append('from datetime import timedelta')

    # 在适当位置插入导入
    if imports_to_add:
        for imp in imports_to_add:
            lines.insert(insert_index, imp)
            insert_index += 1

    return '\n'.join(lines)

def fix_mock_user_service(content):
    """修复mock_user_service相关F821错误"""

    # 检查是否需要添加mock_user_service的Mock定义
    if 'mock_user_service' in content and 'def mock_user_service' not in content:

        # 查找适当的插入位置
        lines = content.split('\n')
        insert_index = -1

        # 查找import结束的位置
        for i, line in enumerate(lines):
            if line.strip() and not (line.strip().startswith('import ') or
                                   line.strip().startswith('from ') or
                                   line.startswith('#') or
                                   line.startswith('"""') or
                                   line.startswith("'''") or
                                   line.strip() == ''):
                insert_index = i
                break

        if insert_index >= 0:
            mock_service_def = '''
# Mock user service for testing
mock_user_service = Mock()
mock_user_service.update_display_preferences.return_value = {
    "user_id": 1,
    "preferences": {"theme": "dark", "notifications": True}
}
mock_user_service.update_privacy_preferences.return_value = {
    "user_id": 1,
    "privacy": {"profile_visibility": "public", "data_sharing": False}
}
mock_user_service.update_prediction_preferences.return_value = {
    "user_id": 1,
    "predictions": {"auto_predictions": True, "confidence_threshold": 0.7}
}
'''
            lines.insert(insert_index, mock_service_def)

        content = '\n'.join(lines)

    return content

def fix_common_imports(content, file_path):
    """修复常见导入问题"""

    # 文件特定的修复
    if 'test_api_services_integration.py' in str(file_path):
        return fix_test_api_services_integration(content)
    elif 'test_api_endpoint.py' in str(file_path):
        return fix_test_api_endpoint(content)
    elif 'test_user_management_e2e.py' in str(file_path):
        return fix_mock_user_service(content)

    return content

def fix_file(file_path, errors):
    """修复单个文件"""
    print(f"🔧 修复文件: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 应用修复
        content = fix_common_imports(content, file_path)

        # 通用导入修复
        undefined_names = set(error['undefined_name'] for error in errors)

        # 常见导入映射
        import_map = {
            'asyncio': 'import asyncio',
            'os': 'import os',
            'sys': 'import sys',
            'time': 'import time',
            'datetime': 'from datetime import datetime',
            'timedelta': 'from datetime import timedelta',
            'Path': 'from pathlib import Path',
            'json': 'import json',
            'pytest': 'import pytest',
            'Mock': 'from unittest.mock import Mock',
            'AsyncMock': 'from unittest.mock import AsyncMock',
            'patch': 'from unittest.mock import patch',
            'HTTPException': 'from fastapi import HTTPException',
            'status': 'from fastapi import status',
            'TokenData': 'from src.api.auth import TokenData',
            'JWTAuthManager': 'from src.api.auth import JWTAuthManager',
            'UserAuth': 'from src.domain.models.auth import UserAuth',
            'load_dotenv': 'from dotenv import load_dotenv',
        }

        for undefined_name in undefined_names:
            if undefined_name in import_map:
                import_statement = import_map[undefined_name]

                # 检查导入是否已存在
                if import_statement not in content:
                    # 在文件开头添加导入
                    lines = content.split('\n')

                    # 查找合适的插入位置
                    insert_index = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith('#!/'):
                            continue
                        elif line.strip().startswith('"""') or line.strip().startswith("'''"):
                            # 跳过文档字符串
                            continue
                        elif line.strip().startswith('import ') or line.strip().startswith('from '):
                            insert_index = i + 1
                        elif line.strip() and not line.startswith('#'):
                            if insert_index == 0:
                                insert_index = i
                            break

                    lines.insert(insert_index, import_statement)
                    content = '\n'.join(lines)

        # 写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"  ✅ 修复完成")
            return len(undefined_names)
        else:
            print(f"  ⚠️  未找到合适的修复方案")
            return 0

    except Exception as e:
        print(f"  ❌ 修复失败: {e}")
        return 0

def main():
    """主函数"""
    print("🚀 开始修复高频F821错误...")

    # 获取所有F821错误
    errors = get_f821_errors()
    print(f"📊 发现 {len(errors)} 个F821错误")

    # 分析错误分布
    name_stats = defaultdict(int)
    for error in errors:
        name_stats[error['undefined_name']] += 1

    print("📈 高频F821错误分布:")
    for name, count in sorted(name_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {name}: {count}次")

    # 按文件分组
    files_to_fix = defaultdict(list)
    for error in errors:
        files_to_fix[error['file']].append(error)

    # 修复每个文件
    total_fixed = 0
    for file_path, file_errors in files_to_fix.items():
        fixed = fix_file(file_path, file_errors)
        total_fixed += fixed

    print(f"🎉 高频F821错误修复完成！预计修复 {total_fixed} 个错误")
    return total_fixed

if __name__ == "__main__":
    main()