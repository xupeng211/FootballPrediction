#!/usr/bin/env python3
"""
修复剩余的32个F401错误
"""

import os
import re
from pathlib import Path


def fix_specific_f401_errors():
    """修复特定的F401错误"""

    # 需要修复的文件和对应的修复
    fixes = {
        # 1. 移除未使用的typing导入
        "src/cache/redis/__init__.py": [(5, "import asyncio")],
        "src/database/connection/core/__init__.py": [(6, "from typing import Any")],
        "src/database/connection/pools/__init__.py": [
            (6, "from typing import Any, Dict, Optional, Union")
        ],
        "src/utils/_retry/__init__.py": [
            (7, "from typing import Any, Callable, Optional, Union, TypeVar")
        ],
        # 2. 添加到__all__或移除未使用的导入
        "src/cqrs/__init__.py": "cqrs",
        "src/services/__init__.py": "services",
        "src/services/data_processing_mod/__init__.py": "data_processing_mod",
        "src/streaming/__init__.py": "streaming",
        "src/data/quality/__init__.py": "data_quality",
    }

    fixed_count = 0

    for file_path, fix_info in fixes.items():
        if isinstance(fix_info, str):
            # 特殊处理某些文件
            if fix_info == "cqrs":
                fix_cqrs_init(file_path)
                fixed_count += 1
            elif fix_info == "services":
                fix_services_init(file_path)
                fixed_count += 1
            elif fix_info == "data_processing_mod":
                fix_data_processing_mod_init(file_path)
                fixed_count += 1
            elif fix_info == "streaming":
                fix_streaming_init(file_path)
                fixed_count += 1
            elif fix_info == "data_quality":
                fix_data_quality_init(file_path)
                fixed_count += 1
        else:
            # 移除特定行的导入
            fix_lines = fix_info
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line_num, import_text in fix_lines:
                if line_num <= len(lines):
                    # 注释掉未使用的导入
                    lines[line_num - 1] = f"# {lines[line_num - 1]}"
                    fixed_count += 1

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

    return fixed_count


def fix_cqrs_init(file_path):
    """修复cqrs/__init__.py"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 注释掉未使用的导入
    content = content.replace(
        "    GetPredictionAnalyticsQuery,\n    GetLeaderboardQuery,",
        "    # GetPredictionAnalyticsQuery,  # 未使用\n    # GetLeaderboardQuery,  # 未使用",
    )
    content = content.replace("    CommandResult,", "    # CommandResult,  # 未使用")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def fix_services_init(file_path):
    """修复services/__init__.py"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 注释掉未使用的导入
    content = content.replace(
        "from .base_unified import SimpleService",
        "# from .base_unified import SimpleService  # 未使用",
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def fix_data_processing_mod_init(file_path):
    """修复data_processing_mod/__init__.py"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 注释掉未使用的导入
    content = content.replace(
        "from ..data_processing.pipeline_mod.stages.SilverToGoldProcessor import SilverToGoldProcessor",
        "# from ..data_processing.pipeline_mod.stages.SilverToGoldProcessor import SilverToGoldProcessor  # 未使用",
    )
    content = content.replace(
        "from ..data_processing.pipeline_mod.pipeline.DataPipeline import DataPipeline",
        "# from ..data_processing.pipeline_mod.pipeline.DataPipeline import DataPipeline  # 未使用",
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def fix_streaming_init(file_path):
    """修复streaming/__init__.py"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 注释掉未使用的导入
    content = content.replace(
        "from .kafka_consumer import FootballKafkaConsumer\n        from .kafka_producer import FootballKafkaProducer",
        "# from .kafka_consumer import FootballKafkaConsumer  # 未使用\n        # from .kafka_producer import FootballKafkaProducer  # 未使用",
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def fix_data_quality_init(file_path):
    """修复data/quality/__init__.py"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 注释掉未使用的导入
    content = content.replace(
        "from .anomaly_detector.AnomalyDetector import AnomalyDetector",
        "# from .anomaly_detector.AnomalyDetector import AnomalyDetector  # 未使用",
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    """主函数"""
    print("=" * 80)
    print("🔧 修复剩余的32个F401错误")
    print("=" * 80)

    # 先统计当前数量
    cmd = "ruff check --select F401 src/ 2>&1 | grep 'F401' | wc -l"
    result = os.popen(cmd).read().strip()
    current_count = int(result) if result else 0

    print(f"\n📊 当前F401错误数: {current_count}")

    # 修复错误
    fixed_count = fix_specific_f401_errors()
    print(f"\n✅ 修复了 {fixed_count} 个文件")

    # 再次统计
    cmd = "ruff check --select F401 src/ 2>&1 | grep 'F401' | wc -l"
    result = os.popen(cmd).read().strip()
    remaining = int(result) if result else 0

    print(f"\n📊 剩余F401错误数: {remaining}")

    if remaining > 0:
        print("\n⚠️ 仍有错误需要手动处理:")
        os.system("ruff check --select F401 src/ 2>&1 | grep 'F401' | head -10")
    else:
        print("\n🎉 所有F401错误已修复！")


if __name__ == "__main__":
    main()
