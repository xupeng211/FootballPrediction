#!/usr/bin/env python3
"""
修复集成测试中的导入问题
"""

import os
from pathlib import Path


def fix_fixture_imports():
    """修复 conftest.py 中的导入问题"""
    conftest_path = Path("tests/conftest.py")

    if not conftest_path.exists():
        print("conftest.py 不存在")
        return

    with open(conftest_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 修复导入路径
    old_imports = [
        "from src.database.models.features import Features",
        "from src.database.models.match import Match",
        "from src.database.models.odds import Odds",
        "from src.database.models.predictions import Predictions",
        "from src.database.models.team import Team",
        "from src.database.models.user import User",
        "from src.services.data_processing import DataProcessingService",
        "from src.services.manager import ServiceManager",
    ]

    new_imports = [
        "from src.database.models.features import Features",
        "from src.database.models.match import Match",
        "from src.database.models.odds import Odds",
        "from src.database.models.predictions import Predictions",
        "from src.database.models.team import Team",
        "from src.database.models.user import User",
        "from src.services.data_processing import DataProcessingService",
        "from src.services.manager_mod import ServiceManager",
    ]

    for old, new in zip(old_imports, new_imports):
        content = content.replace(old, new)

    with open(conftest_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("✓ 修复 conftest.py 导入")


def fix_test_imports():
    """修复测试文件中的导入问题"""
    test_files = [
        "tests/integration/api/test_features_integration.py",
        "tests/integration/api/test_predictions_integration.py",
        "tests/e2e/test_prediction_workflow.py",
    ]

    import_mappings = {
        "from src.services.data_processing import DataProcessingService": "from src.services.data_processing import DataProcessingService",
        "from src.services.manager import ServiceManager": "from src.services.manager_mod import ServiceManager",
        "from src.services.audit_service import AuditService": "from src.services.audit_service import AuditService",
        "from src.api.predictions import router as predictions_router": "from src.api.predictions_mod import router as predictions_router",
        "from src.api.features import router as features_router": "from src.api.features_mod import router as features_router",
    }

    for test_file in test_files:
        file_path = Path(test_file)
        if not file_path.exists():
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        updated = False
        for old_import, new_import in import_mappings.items():
            if old_import in content:
                content = content.replace(old_import, new_import)
                updated = True

        if updated:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ 修复 {test_file} 导入")


def create_missing_modules():
    """创建缺失的模块"""
    modules_to_create = [
        (
            "src/api/predictions_mod.py",
            "from src.api.predictions import *  # noqa: F403,F401\n",
        ),
        (
            "src/api/features_mod.py",
            "from src.api.features import *  # noqa: F403,F401\n",
        ),
    ]

    for module_path, content in modules_to_create:
        path = Path(module_path)
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ 创建模块 {module_path}")


if __name__ == "__main__":
    print("=== 修复集成测试导入问题 ===")

    os.chdir(Path(__file__).parent.parent)

    create_missing_modules()
    fix_fixture_imports()
    fix_test_imports()

    print("\n✅ 集成测试导入修复完成")
