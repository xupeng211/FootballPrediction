#!/usr/bin/env python3
"""
修复拆分模块中BaseService的导入问题
"""

import os
from pathlib import Path
from typing import List, Tuple

def fix_baseservice_in_file(file_path: Path) -> bool:
    """
    在文件中添加BaseService导入

    Returns:
        是否成功修复
    """
    if not file_path.exists():
        return False

    content = file_path.read_text(encoding='utf-8')

    # 如果已经有BaseService导入，跳过
    if "BaseService" in content and ("from src.services.base_service import BaseService" in content or
                                      "from ..base_service import BaseService" in content):
        return True

    # 如果使用了BaseService但没有导入
    if "BaseService" in content:
        lines = content.split('\n')

        # 找到最后一个import位置
        last_import_idx = -1
        for i, line in enumerate(lines):
            if line.startswith('from ') or line.startswith('import '):
                last_import_idx = i

        # 在最后一个import后添加BaseService导入
        if last_import_idx >= 0:
            lines.insert(last_import_idx + 1, "from src.services.base_service import BaseService")
            content = '\n'.join(lines)
            file_path.write_text(content, encoding='utf-8')
            print(f"  ✓ 修复了 {file_path.name}")
            return True

    return False

def main():
    """主函数"""
    print("=" * 60)
    print("修复BaseService导入问题")
    print("=" * 60)

    # 需要修复的文件
    files_to_fix = [
        "src/services/audit_service_mod/service.py",
        "src/services/manager/manager.py",  # manager.py在manager目录下
        "src/services/data_processing_mod/service.py"
    ]

    fixed_count = 0

    for file_str in files_to_fix:
        file_path = Path(file_str)
        print(f"\n检查 {file_path}:")

        if fix_baseservice_in_file(file_path):
            fixed_count += 1
        else:
            print(f"  - 无需修复或修复失败")

    print("\n" + "=" * 60)
    print(f"修复完成！共修复了 {fixed_count} 个文件")
    print("=" * 60)

if __name__ == "__main__":
    main()