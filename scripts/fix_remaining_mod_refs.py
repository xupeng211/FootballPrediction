#!/usr/bin/env python3
"""
修复剩余的 _mod 模块引用
"""

import os
import re
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent

def fix_file(filepath: Path):
    """修复单个文件中的 _mod 引用"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # 替换各种 _mod 引用
        content = content.replace('src.services.data_processing', 'src.services.data_processing')
        content = content.replace('src.services.audit_service', 'src.services.audit_service')
        content = content.replace('src.monitoring.alert_manager', 'src.monitoring.alert_manager')
        content = content.replace('src.monitoring.metrics_collector_enhanced', 'src.monitoring.metrics_collector_enhanced')
        content = content.replace('src.database.models.features', 'src.database.models.features')

        # 处理相对导入
        content = re.sub(r'from\s+\.(\w+_mod)\s+import', lambda m: f"from .{m.group(1).replace('_mod', '')} import", content)

        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 修复: {filepath.relative_to(ROOT_DIR)}")
            return True
    except Exception as e:
        print(f"✗ 错误: {filepath} - {e}")

    return False

def main():
    print("🔧 修复剩余的 _mod 模块引用...")

    fixed_count = 0

    # 遍历所有 Python 文件
    for root, dirs, files in os.walk(ROOT_DIR):
        if '.git' in root or '.venv' in root or '__pycache__' in root:
            continue

        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                if fix_file(filepath):
                    fixed_count += 1

    print(f"\n✅ 完成！修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()
