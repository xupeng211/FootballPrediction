#!/usr/bin/env python3
"""
修复所有 _mod 模块的导入引用
Fix all _mod module import references
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent

# 需要替换的模块映射
MODULE_MAPPING = {
    "alert_manager_mod": "alert_manager",
    "metrics_collector_enhanced_mod": "metrics_collector_enhanced",
    "audit_service_mod": "audit_service",
    "data_processing_mod": "data_processing",
    "feature_mod": "features",
}

# 需要更新的导入模式
IMPORT_PATTERNS = [
    # from .module import ...
    (r"from\s+\.?(\w+_mod)\s+import", r"from .\1 import"),
    # from src.path.module_mod import ...
    (r"from\s+src\.[\w\.]+\.(\w+_mod)\s+import", r"from src.\1 import"),
    # import module_mod
    (r"import\s+(\w+_mod)", r"import \1"),
]

def find_python_files(directory: Path) -> List[Path]:
    """查找所有 Python 文件"""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # 跳过特定目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)

    return python_files

def fix_imports_in_file(file_path: Path) -> Tuple[int, List[str]]:
    """修复单个文件中的导入"""
    changes_made = 0
    changes_log = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复导入语句
        for old_mod, new_mod in MODULE_MAPPING.items():
            # 处理相对导入
            content = re.sub(
                f"from\\s+\\.?{old_mod}\\s+import",
                f"from .{new_mod} import",
                content
            )

            # 处理绝对导入
            content = re.sub(
                f"from\\s+src\\.[\\w\\.]+\\.{old_mod}\\s+import",
                f"from src.{new_mod.replace('_', '.')} import",
                content
            )

            # 处理直接导入
            content = re.sub(
                f"import\\s+{old_mod}",
                f"import {new_mod}",
                content
            )

        # 检查是否有变化
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            changes_made = 1
            changes_log.append(f"Updated imports in {file_path.relative_to(ROOT_DIR)}")

    except Exception as e:
        changes_log.append(f"Error processing {file_path}: {str(e)}")

    return changes_made, changes_log

def main():
    """主函数"""
    print("🔧 开始修复所有 _mod 模块的导入引用...")

    # 查找所有 Python 文件
    python_files = find_python_files(ROOT_DIR / "src")
    python_files.extend(find_python_files(ROOT_DIR / "tests"))

    total_changes = 0
    all_changes_log = []

    for file_path in python_files:
        # 跳过 _mod 文件本身
        if "_mod.py" in file_path.name:
            continue

        changes, log = fix_imports_in_file(file_path)
        total_changes += changes
        all_changes_log.extend(log)

    # 输出结果
    print(f"\n✅ 完成！共更新了 {total_changes} 个文件")

    if all_changes_log:
        print("\n📝 更新详情：")
        for log in all_changes_log:
            if log:
                print(f"  - {log}")

    # 提醒删除 _mod 文件
    print("\n⚠️  下一步：手动删除所有 _mod 兼容性模块文件")
    mod_files = list(ROOT_DIR.glob("**/*_mod.py"))
    if mod_files:
        print("\n以下 _mod 文件可以删除：")
        for mod_file in mod_files:
            print(f"  - {mod_file.relative_to(ROOT_DIR)}")

if __name__ == "__main__":
    main()