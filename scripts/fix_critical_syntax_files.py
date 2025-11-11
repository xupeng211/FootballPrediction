#!/usr/bin/env python3
"""
关键语法文件修复工具
专门处理无法通过自动工具修复的语法错误文件
"""

import os
import re
from pathlib import Path


def fix_syntax_file(file_path):
    """修复单个文件的语法错误"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复常见的语法问题
        # 1. 修复错误的import语句格式
        content = re.sub(r'from\s+\.([^a-zA-Z_])', r'from .\1', content)

        # 2. 修复不完整的中文注释导致的语法错误
        content = re.sub(r'from\s+\.([\u4e00-\u9fff][^"]*?)\s+import', '"""\\1"""', content)

        # 3. 修复错误的行尾格式
        content = re.sub(r'from\s+\.([^(]*?)\s+import\s*\(', 'from .\\1 import (', content)

        # 4. 移除包含中文字符的错误import行
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 跳过包含中文且格式错误的import语句
            if re.search(r'from\s+\.[\u4e00-\u9fff]', line):
                continue
            # 跳过包含未闭合括号的行
            elif line.count('(') != line.count(')') and 'import' in line:
                continue
            # 跳过只有右括号的行
            elif line.strip() == ')' and not any('import' in prev_line for prev_line in fixed_lines[-5:]):
                continue
            else:
                fixed_lines.append(line)

        fixed_content = '\n'.join(fixed_lines)

        # 5. 如果是__init__.py文件且内容有问题，创建简单版本
        if '__init__.py' in str(file_path):
            if not fixed_content.strip() or 'import' not in fixed_content:
                fixed_content = '''"""
模块初始化文件
"""

# 模块级别的导入和配置
'''

        # 6. 修复numpy导入问题
        if 'import numpy as np' in fixed_content:
            # 确保numpy导入在文件顶部
            lines = fixed_content.split('\n')
            numpy_imported = False
            fixed_lines = []

            for line in lines:
                if line.strip().startswith('import numpy as np'):
                    numpy_imported = True
                    fixed_lines.insert(0, line)  # 移到顶部
                elif line.strip() and not line.startswith('#') and not numpy_imported and not any(line.startswith(prefix) for prefix in ['import ', 'from ', '"""', "'''"]):
                    # 在第一个代码块前添加numpy导入
                    fixed_lines.append('import numpy as np')
                    numpy_imported = True
                    fixed_lines.append(line)
                else:
                    fixed_lines.append(line)

            fixed_content = '\n'.join(fixed_lines)

        # 检查是否有实际修改
        if fixed_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        else:
            return False

    except Exception:
        return False

def main():
    """主函数"""

    # 需要修复的文件列表
    critical_files = [
        "src/features/feature_store.py",
        "src/domain/strategies/__init__.py",
        "src/monitoring/anomaly_detector.py",
        "src/data/features/__init__.py",
        "src/patterns/__init__.py",
        "src/features/feature_calculator.py",
        "src/domain/events/__init__.py",
        "src/realtime/__init__.py",
        "src/queues/__init__.py",
        "src/domain/strategies/statistical.py",
        "src/repositories/__init__.py",
        "src/domain/strategies/enhanced_ml_model.py",
        "src/events/__init__.py",
        "src/domain/strategies/ml_model.py",
        "src/data/collectors/odds_collector.py",
        "src/performance/__init__.py"
    ]

    fixed_count = 0
    len(critical_files)

    for file_path in critical_files:
        full_path = Path(file_path)
        if full_path.exists():
            if fix_syntax_file(full_path):
                fixed_count += 1
        else:
            pass


    # 验证修复效果
    os.popen("ruff check src/ --output-format=concise | grep 'invalid-syntax' | wc -l").read().strip()

    # 尝试重新格式化以验证语法
    for file_path in critical_files[:3]:  # 测试前3个文件
        full_path = Path(file_path)
        if full_path.exists():
            try:
                # 尝试编译验证
                os.system(f"python3 -m py_compile {file_path} 2>/dev/null && echo '✅ {file_path} 语法正确' || echo '❌ {file_path} 仍有语法错误'")
            except Exception:
                pass

if __name__ == "__main__":
    main()
