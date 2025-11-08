#!/usr/bin/env python3
"""
修复测试文件中重复的import logging语句
"""

import os


def fix_duplicate_logging_imports(file_path):
    """修复文件中重复的import logging语句"""
    try:
        with open(file_path, encoding='utf-8') as f:
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
            return True
        else:
            return False

    except Exception:
        return False

def main():
    """主函数"""

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
            pass


if __name__ == "__main__":
    main()
