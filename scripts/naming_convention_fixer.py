#!/usr/bin/env python3
"""
命名规范修复工具 - 修复N801类名和N802函数名规范问题
Naming Convention Fixer - Fix N801 class names and N802 function names
"""

import os
import re


def fix_class_naming(file_path: str) -> int:
    """修复类名命名规范 (N801) - 将下划线命名改为驼峰命名"""

    if not os.path.exists(file_path):
        return 0

    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fixes_count = 0

        # 修复类名 - 将 ClassName 改为 ClassName
        # 匹配 class 后面跟着包含下划线的标识符
        class_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)'

        def fix_class_name(match):
            class_name = match.group(1)
            if '_' in class_name and not class_name.isupper():
                # 转换为驼峰命名
                fixed_name = ''.join(word.capitalize() for word in class_name.split('_'))
                if fixed_name != class_name:
                    nonlocal fixes_count
                    fixes_count += 1
                    return match.group(0).replace(class_name, fixed_name)
            return match.group(0)

        content = re.sub(class_pattern, fix_class_name, content)

        # 修复函数名 - 将驼峰命名改为下划线命名 (N802)
        # 主要是针对一些特殊情况的函数名
        def_pattern = r'def\s+([a-z][A-Z][a-zA-Z0-9_]*)\s*\('

        def fix_function_name(match):
            func_name = match.group(1)
            if re.search(r'[A-Z]', func_name):
                # 转换为下划线命名
                fixed_name = re.sub(r'(?<!^)(?=[A-Z])', '_', func_name).lower()
                if fixed_name != func_name:
                    nonlocal fixes_count
                    fixes_count += 1
                    return match.group(0).replace(func_name, fixed_name)
            return match.group(0)

        content = re.sub(def_pattern, fix_function_name, content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        return fixes_count

    except Exception:
        return 0

def main():
    """主函数"""

    # 需要修复的文件列表
    files_to_fix = [
        "src/alerting/alert_engine.py",
        "src/api/realtime_streaming.py",
        "src/bad_example.py",
        "src/cache/api_cache.py",
        "src/collectors/fixtures_collector.py",
        "src/config/config_manager.py",
        "src/core/config.py",
        "src/data/collectors/base_collector.py",
    ]

    total_fixes = 0

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            fixes = fix_class_naming(file_path)
            total_fixes += fixes
        else:
            pass


if __name__ == "__main__":
    main()
