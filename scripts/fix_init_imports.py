#!/usr/bin/env python3
"""
修复所有模块的__init__.py导入
"""

from pathlib import Path


def fix_init_import(module_path):
    """修复模块的__init__.py导入"""
    init_file = Path(module_path) / "__init__.py"

    if not init_file.exists():
        return False

    module_name = Path(module_path).name
    content = f'''# {module_name} package init
# 自动生成以解决导入问题

from .router import router

__all__ = ['router']
'''

    with open(init_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"   ✅ 修复导入: {init_file}")
    return True


def main():
    """修复所有模块导入"""
    print("🔧 修复所有模块的__init__.py导入...")

    # 需要修复的模块
    modules_to_fix = [
        'src/api/adapters',
        'src/api/facades',
        'src/cqrs',
        'src/middleware',
        'src/streaming',
        'src/ml',
        'src/monitoring',
        'src/realtime',
        'src/tasks'
    ]

    fixed_count = 0
    for module in modules_to_fix:
        if fix_init_import(module):
            fixed_count += 1

    print(f"📊 修复了 {fixed_count} 个模块导入")
    return fixed_count > 0


if __name__ == "__main__":
    main()