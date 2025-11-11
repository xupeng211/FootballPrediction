#!/usr/bin/env python3
"""
F821错误修复脚本
专门处理numpy和pandas导入问题
"""

import os
import re
from pathlib import Path

def fix_numpy_imports(file_path):
    """修复numpy导入问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否使用了np但没有导入
        if 'np.' in content and 'import numpy' not in content and 'import np' not in content:
            # 查找导入区域
            import_end = 0
            lines = content.split('\n')

            # 找到最后一个import语句
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    import_end = i + 1

            # 插入numpy导入
            lines.insert(import_end, 'import numpy as np')
            content = '\n'.join(lines)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✅ 修复了 {file_path} 的numpy导入")
            return True

        return False

    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def fix_pandas_imports(file_path):
    """修复pandas导入问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否使用了pd但没有导入
        if 'pd.' in content or 'pd.DataFrame' in content:
            if 'import pandas' not in content and 'import pd' not in content:
                # 查找导入区域
                import_end = 0
                lines = content.split('\n')

                # 找到最后一个import语句
                for i, line in enumerate(lines):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        import_end = i + 1

                # 插入pandas导入
                lines.insert(import_end, 'import pandas as pd')
                content = '\n'.join(lines)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"✅ 修复了 {file_path} 的pandas导入")
                return True

        return False

    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 开始修复F821 numpy和pandas导入错误...")

    # 需要修复的文件
    files_to_fix = [
        "src/services/betting/enhanced_ev_calculator.py",
        "src/services/processing/processors/match_processor.py", 
        "src/services/processing/processors/match_processor_fixed.py",
        "src/data/processing/football_data_cleaner.py",
        "src/data/processing/data_preprocessor.py",
        "src/data/processing/missing_data_handler.py"
    ]

    fixed_count = 0

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_numpy_imports(file_path):
                fixed_count += 1
            if fix_pandas_imports(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  文件不存在: {file_path}")

    print(f"🎯 修复完成！共修复了 {fixed_count} 个导入问题")

if __name__ == "__main__":
    main()
