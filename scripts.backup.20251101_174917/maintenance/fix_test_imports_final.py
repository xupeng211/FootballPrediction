#!/usr/bin/env python3
"""
修复测试中的最终导入问题
"""

import os
from pathlib import Path


def create_core_module():
    """创建核心预测模块"""
    # 确保目录存在
    os.makedirs("src/core/prediction", exist_ok=True)

    # 创建 __init__.py 导出所有类
    init_content = """# 从原始模块导出所有类
from ..prediction_engine import PredictionEngine, PredictionConfig, PredictionStatistics

__all__ = ["PredictionEngine", "PredictionConfig", "PredictionStatistics"]
"""

    init_path = Path("src/core/prediction/__init__.py")
    if not init_path.exists():
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(init_content)
        print("✓ 创建 src/core/prediction/__init__.py")


def fix_specific_test_imports():
    """修复特定测试文件的导入"""
    test_fixes = {
        "tests/unit/core/test_prediction_engine_modular.py": {
            "from src.core.prediction import PredictionEngine, PredictionConfig, PredictionStatistics": "from src.core.prediction_engine import PredictionEngine, PredictionConfig, PredictionStatistics"
        }
    }

    for test_file, fixes in test_fixes.items():
        file_path = Path(test_file)
        if not file_path.exists():
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        updated = False
        for old_import, new_import in fixes.items():
            if old_import in content:
                content = content.replace(old_import, new_import)
                updated = True

        if updated:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ 修复 {test_file} 导入")


if __name__ == "__main__":
    print("=== 修复测试最终导入问题 ===")

    os.chdir(Path(__file__).parent.parent)

    create_core_module()
    fix_specific_test_imports()

    print("\n✅ 导入问题修复完成")
