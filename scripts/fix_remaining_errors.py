#!/usr/bin/env python3
"""
修复剩余的语法错误
"""

import os
import re
from pathlib import Path


def fix_file(file_path: str, patterns: list):
    """修复单个文件"""
    path = Path(file_path)
    if not path.exists():
        print(f"⚠️  文件不存在: {file_path}")
        return False

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    modified = False

    for search_pattern, replace_pattern in patterns:
        if re.search(search_pattern, content):
            content = re.sub(search_pattern, replace_pattern, content)
            modified = True
            print(f"  - 修复: {search_pattern}")

    if modified:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    return False


def main():
    """主函数"""
    # 切换到项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    print("修复剩余的语法错误...")
    print("-" * 50)

    # 定义修复模式
    fixes = [
        # 文件路径，搜索模式，替换模式
        (
            "src/facades/facades.py",
            [
                r"dependencies: Optional\[List\[str\]\] = None",
                r"list_subsystems\(\)\s*-\>\s*List\[str\]\]\]",
            ],
            [
                r"dependencies: Optional[List[str]] = None",
                r"list_subsystems() -> List[str]",
            ],
        ),
        (
            "src/facades/subsystems/database.py",
            [r"dependencies: Optional\[List\[str\]\] = None"],
            [r"dependencies: Optional[List[str]] = None"],
        ),
        (
            "src/facades/base.py",
            [r"_initialization_order: List\[str\]\]\s*=\s*\[\]"],
            [r"_initialization_order: List[str] = []"],
        ),
        (
            "src/patterns/decorator.py",
            [r"dependencies: Optional\[List\[Any\]\] = None"],
            [r"dependencies: Optional[List[Any]] = None"],
        ),
        (
            "src/patterns/facade.py",
            [r"dependencies: Optional\[List\[str\]\] = None"],
            [r"dependencies: Optional[List[str]] = None"],
        ),
        (
            "src/patterns/facade_simple.py",
            [r"config: Optional\[Dict\[str, Any\]\] = None"],
            [r"config: Optional[Dict[str, Any]] = None"],
        ),
        (
            "src/monitoring/alert_manager_mod/__init__.py",
            [r"dependencies: Optional\[List\[str\]\] = None"],
            [r"dependencies: Optional[List[str]] = None"],
        ),
        (
            "src/performance/analyzer.py",
            [r"dependencies: Optional\[List\[str\]\] = None"],
            [r"dependencies: Optional[List[str]] = None"],
        ),
        (
            "src/ml/model_training.py",
            [r"params: Optional\[Dict\[str, Any\]\] = None"],
            [r"params: Optional[Dict[str, Any]] = None"],
        ),
        (
            "src/models/prediction_model.py",
            [r"config: Optional\[Dict\[str, Any\]\] = None"],
            [r"config: Optional[Dict[str, Any]] = None"],
        ),
        (
            "src/decorators/decorators.py",
            [r"dependencies: Optional\[List\[Any\]\] = None"],
            [r"dependencies: Optional[List[Any]] = None"],
        ),
        (
            "src/domain/models/prediction.py",
            [r"metadata: Optional\[Dict\[str, Any\]\] = None"],
            [r"metadata: Optional[Dict[str, Any]] = None"],
        ),
    ]

    fixed_count = 0
    for file_path, search_patterns, replace_patterns in fixes:
        print(f"\n检查文件: {file_path}")
        if fix_file(file_path, list(zip(search_patterns, replace_patterns))):
            fixed_count += 1
            print(f"✓ 已修复: {file_path}")

    print("\n" + "=" * 50)
    print(f"修复完成！总共修复了 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
