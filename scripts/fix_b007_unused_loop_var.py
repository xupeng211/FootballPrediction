#!/usr/bin/env python3
"""
修复B007未使用循环变量错误
"""

import re

def fix_b007_unused_loop_vars():
    """修复B007未使用循环变量错误"""

    files_to_fix = [
        "tests/integration/test_imports_only.py",
        "tests/integration/test_prediction_api_integration.py",
        "tests/unit/data/test_processing_simple.py",
        "tests/unit/events/test_event_system.py",
        "tests/unit/utils/test_crypto_utils_comprehensive.py"
    ]

    total_fixes = 0

    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 将未使用的循环变量替换为下划线
            # 处理 for var in iterable: 模式
            content = re.sub(
                r'for (\w+)\s+in\s+([^:]+):',
                lambda m: f"for _ in {m.group(2)}:" if m.group(1) not in content[content.find(m.group(0)):content.find(m.group(0)) + 200] else m.group(0),
                content
            )

            # 更精确的方法：找到具体的问题并修复
            lines = content.split('\n')
            new_lines = []

            for i, line in enumerate(lines):
                # 检查是否是包含B007错误的for循环行
                if 'for ' in line and ' in ' in line and line.strip().endswith(':'):
                    # 提取变量名
                    var_match = re.search(r'for\s+(\w+)\s+in\s+', line)
                    if var_match:
                        var_name = var_match.group(1)
                        # 检查接下来几行是否使用了这个变量
                        used = False
                        # 检查接下来的10行
                        for j in range(i + 1, min(i + 11, len(lines))):
                            next_line = lines[j]
                            if var_name in next_line:
                                used = True
                                break
                            # 如果遇到新的函数或类定义，停止检查
                            if re.match(r'^\s*(def|class|@|\s#)', next_line):
                                break

                        # 如果变量没有被使用，替换为下划线
                        if not used:
                            line = re.sub(rf'for\s+{var_name}\s+in\s+', 'for _ in ', line)

                new_lines.append(line)

            content = '\n'.join(new_lines)

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

def manual_fix_b007():
    """手动修复B007错误的更精确方法"""

    fixes = {
        "tests/integration/test_imports_only.py": [
            (45, "for module in modules:", "for _ in modules:")
        ],
        "tests/integration/test_prediction_api_integration.py": [
            (728, "for scenario in test_scenarios:", "for _ in test_scenarios:"),
            (729, "for outcome in expected_outcomes:", "for _ in expected_outcomes:")
        ],
        "tests/unit/data/test_processing_simple.py": [
            (408, "for column in columns:", "for _ in columns:")
        ],
        "tests/unit/events/test_event_system.py": [
            (536, "for i in range(5):", "for _ in range(5):")
        ],
        "tests/unit/utils/test_crypto_utils_comprehensive.py": [
            (355, "for i in range(10):", "for _ in range(10):")
        ]
    }

    total_fixes = 0

    for file_path, line_fixes in fixes.items():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, old_pattern, new_pattern in line_fixes:
                if line_num <= len(lines):
                    if old_pattern in lines[line_num - 1]:
                        lines[line_num - 1] = lines[line_num - 1].replace(old_pattern, new_pattern)
                        print(f"✅ 修复了 {file_path}:{line_num}")
                        total_fixes += 1

            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

        except Exception as e:
            print(f"❌ 修复 {file_path} 时出错: {e}")

    return total_fixes

if __name__ == "__main__":
    print("🔧 修复B007未使用循环变量错误...")
    fixes = manual_fix_b007()
    print(f"📊 总共修复了 {fixes} 个文件")