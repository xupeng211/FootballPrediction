#!/usr/bin/env python3
"""
修复类型注解错误
"""

import os
import re
from pathlib import Path


def fix_type_annotations():
    """修复类型注解错误"""

    Path("src")
    fixed_files = []

    # 需要修复的文件和模式
    fixes = [
        # (文件路径, 搜索模式, 替换模式)
        (
            "src/facades/facades.py",
            r"dependencies: Optional\[List\[str\]\] = None",
            "dependencies: Optional[List[str]] = None",
        ),
        (
            "src/facades/subsystems/database.py",
            r"dependencies: Optional\[List\[str\]\] = None",
            "dependencies: Optional[List[str]] = None",
        ),
        (
            "src/patterns/decorator.py",
            r"dependencies: Optional\[List\[Any\]\] = None",
            "dependencies: Optional[List[Any]] = None",
        ),
        (
            "src/patterns/facade.py",
            r"dependencies: Optional\[List\[str\]\] = None",
            "dependencies: Optional[List[str]] = None",
        ),
        (
            "src/patterns/facade_simple.py",
            r"config: Optional\[Dict\[str, Any\]\] = None",
            "config: Optional[Dict[str, Any]] = None",
        ),
        (
            "src/monitoring/alert_manager_mod/__init__.py",
            r"dependencies: Optional\[List\[str\]\] = None",
            "dependencies: Optional[List[str]] = None",
        ),
        (
            "src/performance/profiler.py",
            r"metadata: Dict\[str, Any\] = field\(default_factory=Dict\[str, Any\]\)",
            "metadata: Dict[str, Any] = field(default_factory=dict)",
        ),
        (
            "src/performance/analyzer.py",
            r"dependencies: Optional\[List\[str\]\] = None",
            "dependencies: Optional[List[str]] = None",
        ),
        (
            "src/ml/model_training.py",
            r"params: Optional\[Dict\[str, Any\]\] = None",
            "params: Optional[Dict[str, Any]] = None",
        ),
        (
            "src/models/prediction_model.py",
            r"config: Optional\[Dict\[str, Any\]\] = None",
            "config: Optional[Dict[str, Any]] = None",
        ),
        (
            "src/decorators/decorators.py",
            r"dependencies: Optional\[List\[Any\]\] = None",
            "dependencies: Optional[List[Any]] = None",
        ),
        (
            "src/domain/models/prediction.py",
            r"metadata: Optional\[Dict\[str, Any\]\] = None",
            "metadata: Optional[Dict[str, Any]] = None",
        ),
    ]

    for file_path, search_pattern, replace_pattern in fixes:
        full_path = Path(file_path)
        if full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            original = content
            content = re.sub(search_pattern, replace_pattern, content)

            if content != original:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                fixed_files.append(file_path)
                print(f"✓ 修复: {file_path}")

    print(f"\n总共修复了 {len(fixed_files)} 个文件")
    return fixed_files


if __name__ == "__main__":
    # 切换到项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    fix_type_annotations()
