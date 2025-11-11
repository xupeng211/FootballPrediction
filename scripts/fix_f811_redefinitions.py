#!/usr/bin/env python3
"""
修复F811重复定义错误
"""

import re

def fix_f811_redefinitions():
    """修复F811重复定义错误"""

    files_to_fix = [
        "tests/integration/test_repositories_real_endpoints.py",
        "tests/unit/api/test_auth_dependencies.py",
        "tests/unit/api/test_auth_dependencies_fixed.py",
        "tests/unit/utils/test_string_utils_comprehensive.py"
    ]

    total_fixes = 0

    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 处理test_repositories_match_statistics重复定义
            if "test_repositories_real_endpoints.py" in file_path:
                # 删除第二个重复的函数定义
                content = re.sub(
                    r'def test_repositories_match_statistics\(\):.*?(?=\ndef|\nclass|\Z)',
                    '',
                    content,
                    flags=re.DOTALL
                )

            # 处理Mock/patch重复导入
            elif "test_auth_dependencies.py" in file_path:
                # 删除重复的Mock/patch导入
                content = re.sub(
                    r'from unittest\.mock import Mock, patch\s*\n',
                    '',
                    content,
                    count=1
                )
                # 删除重复的HTTPException导入
                content = re.sub(
                    r'from fastapi import HTTPException\s*\n',
                    '',
                    content,
                    count=1
                )

            elif "test_auth_dependencies_fixed.py" in file_path:
                # 删除重复的Mock导入
                content = re.sub(
                    r'from unittest\.mock import Mock\s*\n',
                    '',
                    content,
                    count=1
                )

            elif "test_string_utils_comprehensive.py" in file_path:
                # 删除重复的函数定义
                duplicate_functions = [
                    'find_substring_positions',
                    'replace_multiple',
                    'split_text',
                    'join_text'
                ]

                for func_name in duplicate_functions:
                    # 查找并删除第二个及以后的函数定义
                    pattern = rf'def {func_name}\([^)]*\):.*?(?=\ndef {func_name}|\ndef|\nclass|\Z)'
                    matches = re.findall(pattern, content, flags=re.DOTALL)
                    if len(matches) > 1:
                        # 保留第一个，删除其余的
                        first_match = re.search(pattern, content, flags=re.DOTALL)
                        if first_match:
                            content = content[:first_match.end()] + re.sub(
                                pattern, '', content[first_match.end():],
                                flags=re.DOTALL
                            )

            # 清理多余的空行
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            content = re.sub(r'\n+\Z', '\n', content)

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
    print("🔧 修复F811重复定义错误...")
    fixes = fix_f811_redefinitions()
    print(f"📊 总共修复了 {fixes} 个文件")