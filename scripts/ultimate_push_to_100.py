#!/usr/bin/env python3
"""
终极冲刺到100个错误以下的脚本
专门修复最容易的错误，目标减少21个以上问题
"""

import os
import re

def fix_syntax_errors_fast(file_path):
    """快速修复语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复常见的语法错误
        fixes = [
            # 修复 trailing comma not allowed
            (r'from src\.domain\.models\.match import Match, # MatchStatus',
             'from src.domain.models.match import Match'),
            (r'from decimal import # Decimal',
             '# from decimal import Decimal'),
            (r'from src\.core\.config import # Config',
             '# from src.core.config import Config'),
            (r'from src\.services\.prediction import # PredictionService',
             '# from src.services.prediction import PredictionService'),

            # 修复缩进问题
            (r'\n    async def test_data_collection_flow\(self\):',
             '\n\nasync def test_data_collection_flow(self):'),
            (r'\n    async def test_cache_workflow\(self\):',
             '\n\nasync def test_cache_workflow(self):'),
            (r'\n        teams = \[\]',
             '\n    teams = []'),
        ]

        for pattern, replacement in fixes:
            content = content.replace(pattern, replacement)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path} 的语法错误")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def fix_unused_imports_comprehensive(file_path):
    """全面修复未使用导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 移除未使用的导入
        unused_patterns = [
            'MatchEventData',
            'PredictionEventData',
            'pydantic.Field',
        ]

        for pattern in unused_patterns:
            # 移除包含这些模式的导入行
            lines = content.split('\n')
            new_lines = []

            for line in lines:
                if pattern in line and 'import' in line:
                    # 注释掉而不是删除，更安全
                    if not line.strip().startswith('#'):
                        new_lines.append('# ' + line.strip())
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            content = '\n'.join(new_lines)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path} 的未使用导入")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def fix_import_positions_fast(file_path):
    """快速修复导入位置"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 处理sys.path.insert之后的导入
        lines = content.split('\n')
        new_lines = []
        moved_imports = []

        for line in lines:
            # 查找需要移动的导入
            if 'sys.path.insert' in line:
                # 查找后面需要移动的导入
                new_lines.append(line)
                # 继续处理后面的行
            elif 'sys.path.insert(0,' in content and line.strip().startswith('from ') and line not in moved_imports:
                moved_imports.append(line)
            else:
                new_lines.append(line)

        # 将移动的插入到文件开头
        if moved_imports:
            # 找到第一个导入的位置
            insert_pos = 0
            for i, line in enumerate(new_lines):
                if line.strip().startswith(('import ', 'from ')):
                    insert_pos = i
                    break

            # 插入移动的导入
            for import_line in reversed(moved_imports):
                new_lines.insert(insert_pos, import_line)

            # 移除原来的导入
            new_lines = [line for line in new_lines if line not in moved_imports]
            content = '\n'.join(new_lines)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path} 的导入位置")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始终极冲刺到100个错误以下...")

    # 目标文件 - 专注于最容易修复的问题
    target_files = [
        # 语法错误文件
        "tests/integration/conftest.py",
        "tests/integration/test_api_domain_integration.py",
        "tests/performance/test_load.py",
        "tests/integration/test_data_flow.py",
        "tests/integration/test_database_integration.py",
        "tests/integration/test_full_workflow.py",
        "tests/unit/data/collectors/test_fixtures_collector.py",

        # 未使用导入文件
        "src/domain/events/__init__.py",
        "src/events/__init__.py",
        "tests/unit/api/test_health_endpoints_comprehensive.py",

        # 导入位置文件
        "tests/integration/test_api_data_source_simple.py",
        "tests/unit/api/test_api_endpoint.py",
    ]

    fixed_count = 0
    for file_path in target_files:
        if os.path.exists(file_path):
            if fix_syntax_errors_fast(file_path):
                fixed_count += 1
            elif fix_unused_imports_comprehensive(file_path):
                fixed_count += 1
            elif fix_import_positions_fast(file_path):
                fixed_count += 1

    print(f"🎯 终极冲刺完成！共修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()
