#!/usr/bin/env python3
"""
修复E402模块导入位置错误 - 将模块级导入移到文件顶部
"""

import re

def fix_e402_import_positions():
    """修复E402导入位置错误"""

    files_to_fix = [
        "tests/integration/test_football_data_api.py",
        "tests/integration/test_full_workflow.py",
        "tests/integration/test_oddsportal_integration.py",
        "tests/integration/test_oddsportal_scraper.py",
        "tests/unit/api/test_auth_dependencies.py",
        "tests/unit/api/test_auth_simple.py",
        "tests/unit/scripts/test_coverage_improvement_executor.py",
        "tests/unit/scripts/test_coverage_improvement_executor_extended.py",
        "tests/unit/scripts/test_create_api_tests.py",
        "tests/unit/scripts/test_create_service_tests.py",
        "tests/unit/scripts/test_phase35_ai_coverage_master.py",
        "tests/unit/scripts/test_phase35_ai_coverage_master_extended.py"
    ]

    total_fixes = 0

    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 分割为行
            lines = content.split('\n')

            # 找到所有import语句（模块级import）
            import_statements = []
            other_lines = []
            in_function_or_class = False
            indent_level = 0

            for line in lines:
                stripped = line.strip()

                # 检查是否在函数或类内部
                if stripped.startswith(('def ', 'class ', 'async def ')):
                    in_function_or_class = True
                    indent_level = len(line) - len(line.lstrip())
                elif in_function_or_class and line.strip() and len(line) - len(line.lstrip()) <= indent_level:
                    # 回到模块级别
                    in_function_or_class = False
                    indent_level = 0

                # 收集模块级别的import语句
                if stripped.startswith('import ') or stripped.startswith('from '):
                    if not in_function_or_class and (len(line) - len(line.lstrip())) == 0:
                        # 这是模块级别的import
                        import_statements.append(line)
                    else:
                        # 函数或类内部的import，保持原样
                        other_lines.append(line)
                else:
                    other_lines.append(line)

            # 重新组织内容
            # 1. 文档字符串
            module_lines = []
            i = 0
            while i < len(other_lines):
                line = other_lines[i]
                if line.strip().startswith(('"""', "'''")):
                    # 处理文档字符串
                    module_lines.append(line)
                    i += 1
                    if i < len(other_lines) and not line.strip().endswith(('"""', "'''")):
                        # 多行文档字符串
                        while i < len(other_lines) and not other_lines[i].strip().endswith(('"""', "'''")):
                            module_lines.append(other_lines[i])
                            i += 1
                        if i < len(other_lines):
                            module_lines.append(other_lines[i])
                            i += 1
                elif line.strip() and not line.strip().startswith('#'):
                    # 遇到非空非注释行，停止收集文档字符串
                    break
                else:
                    module_lines.append(line)
                    i += 1

            # 剩余的行
            remaining_lines = other_lines[i:]

            # 构建新内容
            new_content = []

            # 1. 添加文档字符串
            new_content.extend(module_lines)

            # 2. 添加空行（如果需要）
            if new_content and new_content[-1].strip():
                new_content.append('')

            # 3. 添加import语句
            if import_statements:
                new_content.extend(import_statements)

            # 4. 添加空行（如果需要）
            if import_statements and remaining_lines and remaining_lines[0].strip():
                new_content.append('')

            # 5. 添加剩余内容
            new_content.extend(remaining_lines)

            # 重新组合内容
            final_content = '\n'.join(new_content)

            if final_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(final_content)
                print(f"✅ 修复了 {file_path}")
                total_fixes += 1
            else:
                print(f"⏭️ 跳过 {file_path} (无需修复)")

        except Exception as e:
            print(f"❌ 修复 {file_path} 时出错: {e}")

    return total_fixes

if __name__ == "__main__":
    print("🔧 修复E402模块导入位置错误...")
    fixes = fix_e402_import_positions()
    print(f"📊 总共修复了 {fixes} 个文件")