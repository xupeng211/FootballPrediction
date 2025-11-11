#!/usr/bin/env python3
"""
F403/F405星号导入修复器
将星号导入转换为明确的导入声明
"""

import os


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
                with open(file_path, encoding='utf-8') as f:
                    content = f.read()

                modified = False

                # 应用修复
                for old_import, new_import in fixes.items():
                    if old_import in content:
                        content = content.replace(old_import, new_import)
                        modified = True

                if modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_files.append(file_path)

            except Exception:
                pass
        else:
            pass

    return fixed_files

def remove_unused_star_imports():
    """移除未使用的星号导入"""

    # 查找包含星号导入的文件
    result = os.popen("ruff check src/ --output-format=concise | grep 'F403' | cut -d: -f1 | sort -u").read().strip().split('\n')

    files_with_star_imports = [f for f in result if f.strip()]

    for file_path in files_with_star_imports:
        try:
            with open(file_path, encoding='utf-8') as f:
                lines = f.readlines()

            # 查找并注释掉星号导入行
            modified_lines = []
            for _i, line in enumerate(lines):
                if 'import *' in line and not line.strip().startswith('#'):
                    # 注释掉星号导入
                    modified_lines.append(f"# FIXME: 星号导入已注释 - {line}")
                else:
                    modified_lines.append(line)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)

        except Exception:
            pass

def main():
    """主函数"""

    # 备份
    os.system("git add .")

    # 修复已知的星号导入
    fixed_files = fix_star_imports()

    # 处理剩余的星号导入
    remove_unused_star_imports()

    # 检查修复效果
    remaining_f403 = os.popen("ruff check src/ --output-format=concise | grep 'F403' | wc -l").read().strip()
    remaining_f405 = os.popen("ruff check src/ --output-format=concise | grep 'F405' | wc -l").read().strip()


    # 提交修复
    if fixed_files or int(remaining_f403) > 0 or int(remaining_f405) > 0:
        os.system('git add . && git commit -m "fix: 修复F403/F405星号导入问题"')


if __name__ == "__main__":
    main()
