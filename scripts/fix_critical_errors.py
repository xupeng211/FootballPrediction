#!/usr/bin/env python3
"""
修复关键错误的脚本
重点处理最容易修复的错误类型，快速接近100个错误目标
"""

import os
import re

def fix_unused_imports_fast(file_path):
    """快速修复未使用导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')
        new_lines = []
        skip_next = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # 跳过未使用导入
            if ('F401' in line_stripped and 'imported but unused' in line_stripped) or \
               (line_stripped.startswith('from decimal import Decimal') and 'Decimal' not in content[i+1:]):
                continue

            # 跳过pydantic.Field未使用
            if 'pydantic.Field' in line_stripped and 'imported but unused' in line_stripped:
                continue

            # 保留其他行
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
        if 'sys.path.insert' in content:
            # 找到所有需要移动的导入
            import_pattern = r'(sys\.path\.insert.*?\n)(\s*from\s+[^\n]+\n)'
            matches = re.findall(import_pattern, content, re.MULTILINE | re.DOTALL)

            for match in matches:
                sys_path_line, import_line = match
                # 将导入移到sys.path.insert之前
                content = content.replace(match, import_line + sys_path_line)

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
    print("🔧 开始快速修复关键错误...")

    # 直接处理最常见的问题文件
    files_to_fix = [
        "src/domain/events/__init__.py",
        "src/events/__init__.py",
        "tests/integration/conftest.py",
        "tests/integration/test_api_domain_integration.py",
        "tests/performance/test_load.py",
        "tests/unit/api/test_health_endpoints_comprehensive.py",
        "tests/unit/api/test_auth_simple.py"
    ]

    fixed_count = 0
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_unused_imports_fast(file_path):
                fixed_count += 1

    # 处理导入位置
    import_files = [
        "tests/integration/test_api_data_source_simple.py",
        "tests/integration/test_football_data_api.py",
        "tests/unit/api/test_api_endpoint.py"
    ]

    for file_path in import_files:
        if os.path.exists(file_path):
            if fix_import_positions_fast(file_path):
                fixed_count += 1

    print(f"🎯 快速修复完成！共修复了 {fixed_count} 个错误")

if __name__ == "__main__":
    main()
