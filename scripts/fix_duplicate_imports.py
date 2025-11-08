#!/usr/bin/env python3
"""
修复测试文件中重复的import logging语句
"""

import os
import re
from pathlib import Path

def fix_duplicate_logging_imports(file_path):
    """修复文件中重复的import logging语句"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        fixed_lines = []
        seen_logging_import = False

        for line in lines:
            # 检查是否是import logging语句
            if line.strip() == 'import logging':
                if not seen_logging_import:
                    fixed_lines.append(line)  # 保留第一个
                    seen_logging_import = True
                # 跳过重复的import logging
            else:
                fixed_lines.append(line)

        fixed_content = '\n'.join(fixed_lines)

        if content != fixed_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ 修复重复导入: {file_path}")
            return True
        else:
            print(f"⏭️  无需修复: {file_path}")
            return False

    except Exception as e:
        print(f"❌ 修复失败 {file_path}: {e}")
        return False

def main():
    """主函数"""
    print("🔧 修复测试文件中重复的import logging语句...")

    # 需要修复的文件列表
    files_to_fix = [
        "tests/integration/test_domain_match_comprehensive.py",
        "tests/integration/test_domain_prediction_comprehensive.py",
        "tests/unit/data/test_data_processing.py",
        "tests/unit/test_service_lifecycle_comprehensive.py"
    ]

    fixed_count = 0
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_duplicate_logging_imports(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  文件不存在: {file_path}")

    print(f"\n🎉 修复完成！共修复 {fixed_count} 个文件")

if __name__ == "__main__":
    main()