#!/usr/bin/env python3
"""
清理拆分过程中创建的损坏文件
"""

import shutil
from pathlib import Path


def remove_broken_split_files():
    """删除拆分过程中创建的损坏文件"""

    # 需要删除的目录列表
    dirs_to_remove = [
        # src/api 拆分目录
        "src/api/data",
        "src/api/features",
        "src/api/health",
        "src/api/models",
        "src/api/predictions",
        "src/api/predictions_mod",
        # src/cache 拆分目录
        "src/cache/redis",
        "src/cache/ttl_cache_improved_mod",
        # src/collectors 拆分目录
        "src/collectors/odds",
        "src/collectors/scores",
        # src/config 拆分目录
        "src/config/openapi",
        # src/core 拆分目录
        "src/core/error_handling",
        "src/core/logging",
        "src/core/prediction",
        # src/data 拆分目录
        "src/data/collectors/streaming",
        "src/data/features/feature_store",
        "src/data/processing/football_data_cleaner_mod",
        "src/data/quality/anomaly_detector",
        "src/data/quality/detectors",
        "src/data/quality/exception_handler_mod",
        "src/data/quality/prometheus",
        "src/data/quality/stats",
        "src/data/storage/lake",
        # src/database 拆分目录
        "src/database/compatibility",
        "src/database/connection",
        "src/database/connection_mod",
        "src/database/models/feature_mod",
        # src/features 拆分目录
        "src/features/feature_calculator_mod",
        "src/features/store",
        # src/lineage 拆分目录
        "src/lineage/metadata",
        # src/models 拆分目录
        "src/models/common",
        "src/models/prediction",
        "src/models/prediction_service",
        "src/models/training",
        # src/monitoring 拆分目录
        "src/monitoring/alert_manager_mod",
        "src/monitoring/alerts",
        "src/monitoring/anomaly",
        "src/monitoring/metrics",
        "src/monitoring/metrics_collector_enhanced_mod",
        "src/monitoring/metrics_exporter_mod",
        "src/monitoring/quality",
        "src/monitoring/system",
        "src/monitoring/system_monitor_mod",
        # src/scheduler 拆分目录
        "src/scheduler/core",
        "src/scheduler/dependency",
        "src/scheduler/recovery",
        "src/scheduler/tasks",
        # src/services 拆分目录
        "src/services/audit",
        "src/services/audit_service_mod",
        "src/services/data_processing",
        "src/services/data_processing_mod",
        "src/services/manager",
        # src/streaming 拆分目录
        "src/streaming/consumer",
        "src/streaming/kafka",
        "src/streaming/producer",
        "src/streaming/stream_processor",
        # src/tasks 拆分目录
        "src/tasks/backup_tasks_new",
        "src/tasks/collection",
        # src/utils 拆分目录
        "src/utils/_retry",
    ]

    base_path = Path(".")
    removed_count = 0

    for dir_name in dirs_to_remove:
        dir_path = base_path / dir_name
        if dir_path.exists():
            print(f"删除目录: {dir_path}")
            shutil.rmtree(dir_path)
            removed_count += 1

    # 删除特定的损坏文件
    files_to_remove = [
        "src/services/manager_mod.py",
        "src/services/manager_original.py",
        "src/data/features/feature_store_original.py",
        "src/data/quality/anomaly_detector_original.py",
        "src/database/compatibility.py",
        "src/models/prediction_service_refactored.py",
    ]

    for file_name in files_to_remove:
        file_path = base_path / file_name
        if file_path.exists():
            print(f"删除文件: {file_path}")
            file_path.unlink()
            removed_count += 1

    print(f"\n总共删除了 {removed_count} 个目录和文件")

    # 清理空的 __pycache__ 目录
    print("\n清理 __pycache__ 目录...")
    for pycache in base_path.rglob("__pycache__"):
        if pycache.is_dir():
            try:
                pycache.rmdir()
                print(f"删除空的 __pycache__: {pycache}")
            except OSError:
                pass  # 目录不为空，跳过


if __name__ == "__main__":
    remove_broken_split_files()
