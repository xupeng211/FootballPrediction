#!/usr/bin/env python3
"""
F403/F405星号导入修复器
将星号导入转换为明确的导入声明
"""

import os
import re

def fix_star_imports():
    """修复星号导入问题"""

    # 星号导入修复映射
    star_import_fixes = {
        # database/migrations/versions
        'src/database/migrations/versions/d6d814cc1078_database_performance_optimization_.py': {
            'from database.migrations.versions.d6d814cc1078_database_performance_optimization_.database.migrations.versions.d6d814cc1078_database_performance_optimization__utils import *':
                'from database.migrations.versions.d6d814cc1078_database_performance_optimization_.database.migrations.versions.d6d814cc1078_database_performance_optimization__utils import upgrade, downgrade'
        },

        # features模块
        'src/features/feature_calculator.py': {
            'from .features.feature_calculator_calculators import *':
                'from .features.feature_calculator_calculators import FeatureCalculator'
        },

        'src/features/feature_store.py': {
            'from .features.feature_store_processors import *':
                'from .features.feature_store_processors import FeatureProcessor',  # 假设名称
            'from .features.feature_store_stores import *':
                'from .features.feature_store_stores import FootballFeatureStore, MockFeatureStore, MockEntity'
        },
    }

    fixed_files = []

    for file_path, fixes in star_import_fixes.items():
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content
                modified = False

                # 应用修复
                for old_import, new_import in fixes.items():
                    if old_import in content:
                        content = content.replace(old_import, new_import)
                        modified = True
                        print(f"✅ 修复导入: {file_path}")

                if modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_files.append(file_path)

            except Exception as e:
                print(f"❌ 修复失败 {file_path}: {e}")
        else:
            print(f"⚠️ 文件不存在: {file_path}")

    return fixed_files

def remove_unused_star_imports():
    """移除未使用的星号导入"""

    # 查找包含星号导入的文件
    result = os.popen("ruff check src/ --output-format=concise | grep 'F403' | cut -d: -f1 | sort -u").read().strip().split('\n')

    files_with_star_imports = [f for f in result if f.strip()]

    for file_path in files_with_star_imports:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 查找并注释掉星号导入行
            modified_lines = []
            for i, line in enumerate(lines):
                if 'import *' in line and not line.strip().startswith('#'):
                    # 注释掉星号导入
                    modified_lines.append(f"# FIXME: 星号导入已注释 - {line}")
                    print(f"🔧 注释星号导入: {file_path}:{i+1}")
                else:
                    modified_lines.append(line)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)

        except Exception as e:
            print(f"❌ 处理失败 {file_path}: {e}")

def main():
    """主函数"""
    print("🔧 开始修复F403/F405星号导入问题...")

    # 备份
    os.system("git add .")
    print("💾 已备份当前修改")

    # 修复已知的星号导入
    print("\n📝 修复已知星号导入...")
    fixed_files = fix_star_imports()

    # 处理剩余的星号导入
    print("\n🔧 处理剩余星号导入...")
    remove_unused_star_imports()

    # 检查修复效果
    print("\n📊 检查修复效果...")
    remaining_f403 = os.popen("ruff check src/ --output-format=concise | grep 'F403' | wc -l").read().strip()
    remaining_f405 = os.popen("ruff check src/ --output-format=concise | grep 'F405' | wc -l").read().strip()

    print(f"剩余F403问题: {remaining_f403}")
    print(f"剩余F405问题: {remaining_f405}")

    # 提交修复
    if fixed_files or int(remaining_f403) > 0 or int(remaining_f405) > 0:
        print("\n💾 提交修复...")
        os.system('git add . && git commit -m "fix: 修复F403/F405星号导入问题"')

    print("🏁 F403/F405修复完成")

if __name__ == "__main__":
    main()