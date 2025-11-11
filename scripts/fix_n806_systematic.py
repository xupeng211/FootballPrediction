#!/usr/bin/env python3
"""
系统化N806变量命名修复工具
批量修改变量名符合PEP8规范
"""

import os
import re
from pathlib import Path

def fix_n806_errors():
    """系统化修复N806变量命名错误"""
    print("🔧 开始系统化修复N806变量命名错误...")

    # 变量名映射规则
    variable_mappings = {
        # 测试配置文件中的中文变量名
        '基础库': 'basic_libs',
        '依赖列表': 'dependency_list',
        '依赖名': 'dependency_name',
        '最低版本': 'min_version',
        '模块': 'module',
        '版本': 'version',
        '关键目录': 'key_directories',
        '关键文件': 'key_files',
        '目录': 'directory',
        '文件': 'file',
        '工具列表': 'tool_list',
        '工具': 'tool',

        # 数据分析中的变量名
        'Q1': 'q1',
        'Q3': 'q3',
        'IQR': 'iqr',

        # Mock对象变量名
        'Session': 'session',
        'MockDBManager': 'mock_db_manager',
    }

    # 文件和对应的修复模式
    file_fixes = {
        'tests/integration/test_environment_validator.py': [
            # 中文变量名替换
            ('基础库\s*=', 'basic_libs ='),
            ('依赖列表\s*=', 'dependency_list ='),
            ('for\s+依赖名,', 'for dependency_name,'),
            ('最低版本\s+in\s+依赖列表:', 'min_version in dependency_list:'),
            ('模块\s*=\s*importlib\.import_module\(\s*依赖名\s*\)', 'module = importlib.import_module(dependency_name)'),
            ('版本\s*=\s*getattr\(\s*模块\s*,', 'version = getattr(module,'),
            ('if\s+最低版本\s+and\s+版本\s*!=\s*"unknown":', 'if min_version and version != "unknown":'),
            ('关键目录\s*=', 'key_directories ='),
            ('关键文件\s*=', 'key_files ='),
            ('for\s+目录\s+in\s+关键目录:', 'for directory in key_directories:'),
            ('for\s+文件\s+in\s+关键文件:', 'for file in key_files:'),
            ('工具列表\s*=', 'tool_list ='),
            ('for\s+工具\s+in\s+工具列表:', 'for tool in tool_list:'),
        ],
        'tests/unit/data/test_football_data_cleaner.py': [
            # 统计变量名替换
            ('Q1\s*=\s*data\[\"values\"\]\.quantile\(0\.25\)', 'q1 = data["values"].quantile(0.25)'),
            ('Q3\s*=\s*data\[\"values\"\]\.quantile\(0\.75\)', 'q3 = data["values"].quantile(0.75)'),
            ('IQR\s*=\s*Q3\s*-\s*Q1', 'iqr = q3 - q1'),
            ('upper_bound\s*=\s*Q3\s*\+\s*1\.5\s*\*\s*IQR', 'upper_bound = q3 + 1.5 * iqr'),
            ('assert\s+processed_data\.loc\[5,\s*\"values\"\]\s*==\s*upper_bound', 'assert processed_data.loc[5, "values"] == upper_bound'),
        ],
        'tests/integration/conftest.py': [
            # Session变量名替换
            ('Session\s*=\s*sessionmaker\(', 'session_factory = sessionmaker('),
            ('session\s*=\s*Session\(\)', 'session = session_factory()'),
        ],
    }

    total_fixes = 0

    for file_path, patterns in file_fixes.items():
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content
                file_fixes_count = 0

                # 应用所有修复模式
                for pattern, replacement in patterns:
                    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
                    if new_content != content:
                        content = new_content
                        file_fixes_count += count
                        print(f"  ✅ 修复 {file_path} - {pattern[:30]}... ({count}处)")

                # 处理MockDBManager的特殊情况
                if 'MockDBManager' in content:
                    content = re.sub(r'with\s+patch\("database\.base\.DatabaseManager"\)\s+as\s+MockDBManager:',
                               'with patch("database.base.DatabaseManager") as mock_db_manager:',
                               content)
                    file_fixes_count += 1

                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    total_fixes += file_fixes_count
                    print(f"  📝 修复文件: {file_path} ({file_fixes_count}处修改)")
                else:
                    print(f"  ⚠️  文件无需修改: {file_path}")

            except Exception as e:
                print(f"  ❌ 修复文件失败: {file_path} - {e}")
        else:
            print(f"  ⚠️  文件不存在: {file_path}")

    print(f"\n🎉 N806变量命名错误系统化修复完成！总计修复 {total_fixes} 处修改")
    return total_fixes

if __name__ == "__main__":
    fix_n806_errors()