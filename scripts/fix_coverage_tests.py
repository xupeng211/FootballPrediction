#!/usr/bin/env python3
"""
快速修复覆盖率测试中的语法错误
"""

import os
import re

def fix_module_name_errors():
    """修复module_name未定义的错误"""

    print("🔧 修复覆盖率测试文件中的语法错误...")

    # 需要修复的文件列表
    test_files = [
        'tests/unit/adapters/base_test.py',
        'tests/unit/adapters/factory_test.py',
        'tests/unit/adapters/factory_simple_test.py',
        'tests/unit/adapters/football_test.py',
        'tests/unit/adapters/registry_test.py',
        'tests/unit/adapters/registry_simple_test.py',
        'tests/unit/api/adapters_test.py',
        'tests/unit/api/app_test.py',
        'tests/unit/api/buggy_api_test.py',
        'tests/unit/api/decorators_test.py'
    ]

    fixed_count = 0

    for test_file in test_files:
        if os.path.exists(test_file):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 修复module_name变量未定义的问题
                content = re.sub(
                    r'print\(f"成功导入模块: \{module_name\}"\)',
                    'print("成功导入模块: adapters.base")',
                    content
                )

                # 更通用的修复
                module_name = os.path.basename(test_file).replace('_test.py', '')
                content = content.replace(
                    'print(f"成功导入模块: {module_name}")',
                    f'print("成功导入模块: {module_name}")'
                )

                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                fixed_count += 1
                print(f"   ✅ 修复完成: {test_file}")

            except Exception as e:
                print(f"   ❌ 修复失败: {test_file} - {e}")
        else:
            print(f"   ⚠️ 文件不存在: {test_file}")

    print("\n📊 修复统计:")
    print(f"✅ 成功修复: {fixed_count} 个文件")

    return fixed_count

def main():
    """主函数"""
    print("🔧 Issue #83 覆盖率测试语法修复工具")
    print("=" * 40)

    fixed_count = fix_module_name_errors()

    if fixed_count > 0:
        print("\n🎉 语法修复完成！")
        print("📋 现在可以重新运行覆盖率测试验证效果")
    else:
        print("\n⚠️ 没有找到需要修复的文件")

if __name__ == "__main__":
    main()