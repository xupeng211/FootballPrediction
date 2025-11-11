#!/usr/bin/env python3
"""
修复E721类型比较错误 - 使用isinstance()替代type()比较
"""

import re

def fix_e721_type_comparisons():
    """修复E721类型比较错误"""

    files_to_fix = [
        "tests/unit/api/test_health.py",
        "tests/unit/test_core_auto_binding.py",
        "tests/unit/test_core_config_di.py",
        "tests/unit/test_core_di.py",
        "tests/unit/utils/test_warning_filters_init.py"
    ]

    total_fixes = 0

    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 修复 type(x) == SomeType 模式
            content = re.sub(
                r'type\(([^)]+)\)\s*==\s*([A-Za-z_][A-Za-z0-9_]*)',
                r'isinstance(\1, \2)',
                content
            )

            # 修复 type(x) != SomeType 模式
            content = re.sub(
                r'type\(([^)]+)\)\s*!=\s*([A-Za-z_][A-Za-z0-9_]*)',
                r'not isinstance(\1, \2)',
                content
            )

            # 修复 SomeType == type(x) 模式
            content = re.sub(
                r'([A-Za-z_][A-Za-z0-9_]*)\s*==\s*type\(([^)]+)\)',
                r'isinstance(\2, \1)',
                content
            )

            # 修复 SomeType != type(x) 模式
            content = re.sub(
                r'([A-Za-z_][A-Za-z0-9_]*)\s*!=\s*type\(([^)]+)\)',
                r'not isinstance(\2, \1)',
                content
            )

            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 修复了 {file_path}")
                total_fixes += 1
            else:
                print(f"⏭️ 跳过 {file_path} (无需修复)")

        except Exception as e:
            print(f"❌ 修复 {file_path} 时出错: {e}")

    return total_fixes

if __name__ == "__main__":
    print("🔧 修复E721类型比较错误...")
    fixes = fix_e721_type_comparisons()
    print(f"📊 总共修复了 {fixes} 个文件")