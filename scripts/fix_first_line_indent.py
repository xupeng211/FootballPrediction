#!/usr/bin/env python3
"""
修复文件第一行缩进问题
"""

import os

def fix_first_line_indentation(filepath):
    """修复文件第一行的缩进问题"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        if lines:
            first_line = lines[0]
            # 如果第一行是缩进的docstring开始，修复它
            if first_line.strip().startswith('"""') and first_line.startswith('    '):
                lines[0] = first_line.lstrip()

                # 写回文件
                fixed_content = '\n'.join(lines)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                return True
        return False
    except Exception as e:
        print(f"修复文件 {filepath} 时出错: {e}")
        return False

def main():
    """主函数"""
    # 需要修复的文件列表
    files_to_fix = [
        'tests/unit/adapters/base_test_phase3.py',
        'tests/unit/api/data_router_test_phase3.py',
        'tests/unit/api/decorators_test_phase3.py',
        'tests/unit/utils/helpers_test_phase3.py',
        'tests/unit/utils/formatters_test_phase3.py',
        'tests/unit/utils/dict_utils_test_phase3.py',
        'tests/unit/utils/file_utils_test_phase3.py',
        'tests/unit/utils/time_utils_test_phase3.py',
        'tests/unit/domain/test_prediction_algorithms_part_2.py',
        'tests/unit/domain/test_prediction_algorithms_part_4.py',
        'tests/unit/domain/test_prediction_algorithms_part_3.py',
        'tests/unit/domain/test_prediction_algorithms_part_5.py',
        'tests/unit/cqrs/application_test_phase3.py',
        'tests/unit/cqrs/base_test_phase3.py',
        'tests/unit/cqrs/dto_test_phase3.py',
        'tests/unit/database/config_test_phase3.py',
        'tests/unit/database/definitions_test_phase3.py',
        'tests/unit/database/dependencies_test_phase3.py',
        'tests/unit/core/logging_test_phase3.py',
        'tests/unit/core/service_lifecycle_test_phase3.py',
        'tests/unit/core/auto_binding_test_phase3.py',
        'tests/unit/data/processing/football_data_cleaner_test_phase3.py',
        'tests/unit/data/quality/data_quality_monitor_test_phase3.py',
        'tests/unit/data/quality/exception_handler_test_phase3.py',
        'tests/unit/events/types_test_phase3.py',
        'tests/unit/events/base_test_phase3.py'
    ]

    print("🔧 修复第一行缩进问题...")

    fixed_count = 0
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            if fix_first_line_indentation(filepath):
                print(f"✅ 修复: {os.path.relpath(filepath, 'tests')}")
                fixed_count += 1
            else:
                print(f"⚪ 跳过: {os.path.relpath(filepath, 'tests')} (无需修复)")
        else:
            print(f"❌ 文件不存在: {filepath}")

    print(f"\n📊 修复总结: {fixed_count}/{len(files_to_fix)} 个文件已修复")

if __name__ == "__main__":
    main()