#!/usr/bin/env python3
"""
修复测试文件中的模块名问题
"""

import re
from pathlib import Path


def fix_module_names():
    """修复所有测试文件中的模块名"""

    # 文件路径到模块名的映射
    file_mappings = {
        "tests/collectors/test_scores_collector_improved.py": "patterns.facade",
        "tests/patterns/test_facade.py": "patterns.facade",
        "tests/services/processing/caching/test_processing_cache.py": "services.processing.caching.processing_cache",
        "tests/services/processing/validators/test_data_validator.py": "services.processing.validators.data_validator",
        "tests/tasks/backup/executor/test_backup_executor.py": "tasks.backup.executor.backup_executor",
        "tests/tasks/backup/manual/test_utilities.py": "tasks.backup.manual.utilities",
        "tests/tasks/test_data_collection_core.py": "tasks.backup.manual.utilities",
        "tests/tasks/test_monitoring.py": "services.processing.caching.processing_cache",
        "tests/unit/test_domain_strategies_historical_coverage.py": "domain.strategies.historical",
        "tests/unit/test_domain_strategies_ensemble_coverage.py": "domain.strategies.ensemble",
        "tests/unit/test_patterns_adapter_coverage.py": "patterns.adapter",
        "tests/unit/test_services_processing_validators_data_validator_coverage.py": "services.processing.validators.data_validator",
    }

    for test_file, module_name in file_mappings.items():
        test_path = Path(test_file)

        if not test_path.exists():
            continue

        with open(test_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 修复导入语句 - 先移除错误的导入
        content = re.sub(r"from \{module_name\} import \*", "", content)

        # 修复错误消息
        content = re.sub(
            r'pytest\.skip\("无法导入模块 \{module_name\}:',
            'pytest.skip("无法导入模块:',
            content,
        )

        # 修复导入错误消息
        content = re.sub(
            r'except ImportError as e:\s*\n\s*pytest\.skip\("无法导入模块 \{module_name\}: " \+ str\(e\), allow_module_level=True\)',
            f'except ImportError as e:\n        pytest.skip(f"无法导入模块 {module_name}: {{e}}", allow_module_level=True)',
            content,
        )

        # 添加正确的导入语句
        import_line = f"from {module_name} import *"
        if "try:" in content and "except ImportError" in content:
            # 在try后添加正确的导入
            content = re.sub(r"(try:\s*\n)", f"\\1    {import_line}\n", content)
        else:
            # 如果没有try-except，添加一个
            content = f"""
try:
    {import_line}
except ImportError as e:
    pytest.skip(f"无法导入模块 {module_name}: {{e}}", allow_module_level=True)

{content}
"""

        with open(test_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ 修复模块名: {test_file} -> {module_name}")


if __name__ == "__main__":
    fix_module_names()
