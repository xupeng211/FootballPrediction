#!/usr/bin/env python3
"""检查所有_mod目录是否被引用"""

import os
import subprocess
from pathlib import Path

# 需要检查的_mod目录
mod_dirs = [
    "src/api/predictions_mod",
    "src/monitoring/alert_manager_mod",
    "src/monitoring/metrics_exporter_mod",
    "src/monitoring/system_monitor_mod",
    "src/monitoring/metrics_collector_enhanced_mod",
    "src/database/models/feature_mod",
    "src/database/connection_mod",
    "src/services/data_processing/pipeline_mod",
    "src/services/audit_service_mod",
    "src/services/data_processing_mod",
    "src/features/feature_calculator_mod",
    "src/data/processing/football_data_cleaner_mod",
    "src/data/quality/exception_handler_mod",
]

# Legacy目录（如果存在）
legacy_dirs = [
    "src/streaming/kafka_producer_legacy",
    "src/data/storage/lake/utils_mod",
    "src/monitoring/alerts/models/alert_mod",
    "src/monitoring/alerts/models/escalation_mod",
]

all_dirs = mod_dirs + legacy_dirs

print("🔍 检查所有_mod和_legacy目录的引用情况...\n")

# 检查每个目录
for dir_path in all_dirs:
    dir_name = os.path.basename(dir_path)
    parent_dir = os.path.dirname(dir_path).replace("src/", "")

    # 检查目录是否存在
    if not os.path.exists(dir_path):
        print(f"✅ {dir_path}: 不存在")
        continue

    # 检查是否有Python文件
    py_files = list(Path(dir_path).rglob("*.py"))
    if not py_files:
        print(f"⚠️  {dir_path}: 存在但无Python文件")
        continue

    # 检查引用
    print(f"🔍 检查 {dir_path}...")

    # 构建可能的导入路径
    import_patterns = [
        f"from {dir_path.replace('/', '.')}",
        f"import {dir_path.replace('/', '.')}",
        f"from {dir_path.replace('src.', '')}",
        f"import {dir_path.replace('src.', '')}",
    ]

    found_refs = False
    for pattern in import_patterns:
        try:
            result = subprocess.run(
                ["grep", "-r", "--include=*.py", pattern, "src/"],
                capture_output=True,
                text=True,
            )
            if result.stdout and dir_path not in result.stdout:
                print(f"  ❌ 发现引用: {pattern}")
                print(f"    {result.stdout.split()[0]}")
                found_refs = True
        except:
            pass

    if not found_refs:
        print("  ✅ 无引用，可以删除")

print("\n✅ 检查完成！")
