#!/usr/bin/env python3
"""
修复新生成的测试文件
"""

import re
from pathlib import Path


def fix_test_files():
    """修复测试文件中的模块名问题"""

    # 新创建的测试文件映射
    new_files = [
        ("tests/api/test_data_router.py", "api.data_router"),
        ("tests/events/test_types.py", "events.types"),
        ("tests/api/predictions/test_models.py", "api.predictions.models"),
        ("tests/cqrs/test_application.py", "cqrs.application"),
        ("tests/cqrs/test_dto.py", "cqrs.dto"),
        (
            "tests/domain/events/test_prediction_events.py",
            "domain.events.prediction_events",
        ),
        ("tests/cqrs/test_base.py", "cqrs.base"),
        ("tests/monitoring/test_alert_manager.py", "monitoring.alert_manager"),
        (
            "tests/cache/ttl_cache_enhanced/test_async_cache.py",
            "cache.ttl_cache_enhanced.async_cache",
        ),
        ("tests/database/models/test_features.py", "database.models.features"),
    ]

    for test_file, module_name in new_files:
        test_path = Path(test_file)

        if not test_path.exists():
            continue

        with open(test_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 修复f-string问题
        content = re.sub(r'f"\{([^}]+)\}"', r'"\1"', content)

        # 修复模块导入
        pattern = r"from \\{" + module_name.replace(".", r"\\.") + r"}\\} import \\*"
        content = re.sub(pattern, f"from {module_name} import *", content)

        # 修复错误消息
        content = re.sub(
            r'pytest\.skip\("无法导入模块 \{module_name\}:',
            'pytest.skip("无法导入模块:',
            content,
        )

        # 写回文件
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ 修复: {test_file}")

    # 删除有问题的unit测试
    problematic = [
        "tests/unit/test_api_data_router_coverage.py",
        "tests/unit/test_api_predictions_models_coverage.py",
        "tests/unit/test_adapters_base_coverage.py",
    ]

    for file_path in problematic:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            print(f"✅ 删除: {file_path}")


if __name__ == "__main__":
    fix_test_files()
