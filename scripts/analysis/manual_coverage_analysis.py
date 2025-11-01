#!/usr/bin/env python3
"""
基于已知pytest输出结果的手动覆盖率分析
"""

import json
import subprocess
from pathlib import Path


def count_lines_of_code(file_path: str) -> int:
    """计算文件的有效代码行数"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        code_lines = 0
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                code_lines += 1
        return code_lines
    try:
        pass
def main():
    """主函数"""
    print("🚀 开始手动覆盖率分析...")

    # 基于之前pytest输出中的已知数据
    known_coverage_data = {
        "src/api/buggy_api.py": {"total_stmts": 16, "coverage": 69.0},
        "src/api/data.py": {"total_stmts": 181, "coverage": 51.0},
        "src/api/features.py": {"total_stmts": 189, "coverage": 15.0},
        "src/api/features_improved.py": {"total_stmts": 105, "coverage": 19.0},
        "src/api/health.py": {"total_stmts": 178, "coverage": 17.0},
        "src/api/models.py": {"total_stmts": 192, "coverage": 19.0},
        "src/api/monitoring.py": {"total_stmts": 177, "coverage": 70.0},
        "src/api/predictions.py": {"total_stmts": 123, "coverage": 17.0},
        "src/cache/consistency_manager.py": {"total_stmts": 11, "coverage": 54.0},
        "src/cache/redis_manager.py": {"total_stmts": 429, "coverage": 15.0},
        "src/cache/ttl_cache.py": {"total_stmts": 72, "coverage": 28.0},
        "src/core/config.py": {"total_stmts": 84, "coverage": 46.0},
        "src/core/logger.py": {"total_stmts": 13, "coverage": 93.0},
        "src/data/collectors/base_collector.py": {"total_stmts": 154, "coverage": 19.0},
        "src/data/collectors/fixtures_collector.py": {
            "total_stmts": 109,
            "coverage": 11.0,
        },
        "src/data/collectors/odds_collector.py": {"total_stmts": 144, "coverage": 9.0},
        "src/data/collectors/scores_collector.py": {
            "total_stmts": 178,
            "coverage": 17.0,
        },
        "src/data/collectors/streaming_collector.py": {
            "total_stmts": 145,
            "coverage": 12.0,
        },
        "src/data/features/examples.py": {"total_stmts": 126, "coverage": 0.0},
        "src/data/features/feature_store.py": {"total_stmts": 138, "coverage": 16.0},
        "src/data/processing/football_data_cleaner.py": {
            "total_stmts": 183,
            "coverage": 10.0,
        },
        "src/data/processing/missing_data_handler.py": {
            "total_stmts": 62,
            "coverage": 15.0,
        },
        "src/data/quality/anomaly_detector.py": {"total_stmts": 458, "coverage": 8.0},
        "src/data/quality/data_quality_monitor.py": {
            "total_stmts": 149,
            "coverage": 39.0,
        },
        "src/data/quality/exception_handler.py": {"total_stmts": 197, "coverage": 9.0},
        "src/data/quality/ge_prometheus_exporter.py": {
            "total_stmts": 126,
            "coverage": 12.0,
        },
        "src/data/quality/great_expectations_config.py": {
            "total_stmts": 110,
            "coverage": 11.0,
        },
        "src/data/storage/data_lake_storage.py": {"total_stmts": 322, "coverage": 6.0},
        "src/database/base.py": {"total_stmts": 38, "coverage": 33.0},
        "src/database/config.py": {"total_stmts": 64, "coverage": 59.0},
        "src/database/connection.py": {"total_stmts": 282, "coverage": 31.0},
        "src/database/migrations/env.py": {"total_stmts": 68, "coverage": 100.0},
        "src/database/models/match.py": {"total_stmts": 95, "coverage": 100.0},
        "src/database/models/odds.py": {"total_stmts": 48, "coverage": 100.0},
        "src/database/models/prediction.py": {"total_stmts": 42, "coverage": 100.0},
        "src/database/models/team.py": {"total_stmts": 33, "coverage": 100.0},
        "src/database/models/user.py": {"total_stmts": 26, "coverage": 100.0},
        "src/lineage/metadata_manager.py": {"total_stmts": 155, "coverage": 0.0},
        "src/lineage/lineage_reporter.py": {"total_stmts": 112, "coverage": 0.0},
        "src/models/model_training.py": {"total_stmts": 208, "coverage": 12.0},
        "src/models/prediction_service.py": {"total_stmts": 231, "coverage": 20.0},
        "src/models/common_models.py": {"total_stmts": 59, "coverage": 100.0},
        "src/monitoring/alert_manager.py": {"total_stmts": 233, "coverage": 0.0},
        "src/monitoring/anomaly_detector.py": {"total_stmts": 248, "coverage": 0.0},
        "src/monitoring/metrics_collector.py": {"total_stmts": 248, "coverage": 18.0},
        "src/monitoring/metrics_exporter.py": {"total_stmts": 138, "coverage": 17.0},
        "src/monitoring/quality_monitor.py": {"total_stmts": 323, "coverage": 0.0},
        "src/scheduler/recovery_handler.py": {"total_stmts": 0, "coverage": 0.0},
        "src/services/audit_service.py": {"total_stmts": 359, "coverage": 11.0},
        "src/services/base.py": {"total_stmts": 27, "coverage": 67.0},
        "src/services/content_analysis.py": {"total_stmts": 33, "coverage": 32.0},
        "src/services/data_processing.py": {"total_stmts": 503, "coverage": 7.0},
        "src/services/manager.py": {"total_stmts": 44, "coverage": 46.0},
        "src/services/user_profile.py": {"total_stmts": 46, "coverage": 30.0},
        "src/streaming/kafka_consumer.py": {"total_stmts": 242, "coverage": 10.0},
        "src/streaming/kafka_producer.py": {"total_stmts": 211, "coverage": 11.0},
        "src/streaming/stream_config.py": {"total_stmts": 48, "coverage": 79.0},
        "src/streaming/stream_processor.py": {"total_stmts": 177, "coverage": 17.0},
        "src/tasks/backup_tasks.py": {"total_stmts": 242, "coverage": 16.0},
        "src/tasks/celery_app.py": {"total_stmts": 32, "coverage": 84.0},
        "src/tasks/data_collection_tasks.py": {"total_stmts": 187, "coverage": 13.0},
        "src/tasks/error_logger.py": {"total_stmts": 106, "coverage": 21.0},
        "src/tasks/maintenance_tasks.py": {"total_stmts": 150, "coverage": 10.0},
        "src/tasks/monitoring.py": {"total_stmts": 175, "coverage": 12.0},
        "src/tasks/streaming_tasks.py": {"total_stmts": 134, "coverage": 15.0},
        "src/tasks/utils.py": {"total_stmts": 82, "coverage": 11.0},
        "src/utils/crypto_utils.py": {"total_stmts": 70, "coverage": 22.0},
        "src/utils/data_validator.py": {"total_stmts": 50, "coverage": 30.0},
        "src/utils/dict_utils.py": {"total_stmts": 22, "coverage": 27.0},
        "src/utils/file_utils.py": {"total_stmts": 72, "coverage": 29.0},
        "src/utils/response.py": {"total_stmts": 30, "coverage": 47.0},
        "src/utils/retry.py": {"total_stmts": 105, "coverage": 34.0},
        "src/utils/string_utils.py": {"total_stmts": 29, "coverage": 48.0},
        "src/utils/time_utils.py": {"total_stmts": 17, "coverage": 71.0},
        "src/utils/warning_filters.py": {"total_stmts": 39, "coverage": 37.0},
    }

    # 分析源文件
    src_dir = Path("/home/user/projects/FootballPrediction/src")
    analysis_results = []

    print("🔍 扫描源文件并合并数据...")
    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        relative_path = py_file.relative_to(src_dir.parent)
        file_str = str(relative_path)
        loc = count_lines_of_code(py_file)

        if file_str in known_coverage_data:
            coverage_info = known_coverage_data[file_str]
            analysis_results.append(
                {
                    "file_path": file_str,
                    "loc": loc,
                    "total_stmts": coverage_info["total_stmts"],
                    "coverage": coverage_info["coverage"],
                    "missing_stmts": int(
                        coverage_info["total_stmts"] * (100 - coverage_info["coverage"]) / 100
                    ),
                    "abs_path": str(py_file),
                }
            )

    # 按优先级排序：覆盖率低 -> 文件行数大 -> 语句数大
    analysis_results.sort(key=lambda x: (x["coverage"], -x["loc"], -x["total_stmts"]))

    # 输出结果
    print("\n" + "=" * 100)
    print("📋 全局代码体量与覆盖率分析结果")
    print("=" * 100)

    print(f"{'文件路径':<55} {'代码行数':<8} {'总语句':<8} {'覆盖率':<8} {'优先级':<6}")
    print("-" * 100)

    for i, item in enumerate(analysis_results[:25], 1):
        priority = "🔴" if item["coverage"] < 20 else "🟡" if item["coverage"] < 50 else "🟢"
        print(
            f"{item['file_path']:<55} {item['loc']:<8} {item['total_stmts']:<8} {item['coverage']:<8.1f}% {priority}"
        )

    # 输出前10个需要补测的文件
    print("\n" + "=" * 100)
    print("🎯 前10个优先补测文件 (Batch-Ω 系列)")
    print("=" * 100)

    top_10_files = analysis_results[:10]
    for i, item in enumerate(top_10_files, 1):
        batch_id = f"Batch-Ω-{i:03d}"
        impact_score = item["loc"] * (100 - item["coverage"]) / 100
        print(f"{batch_id}: {item['file_path']}")
        print(f"         - 代码行数: {item['loc']:,} 行")
        print(f"         - 语句总数: {item['total_stmts']:,} 句")
        print(f"         - 当前覆盖率: {item['coverage']:.1f}%")
        print(f"         - 未覆盖语句: {item['missing_stmts']:,} 句")
        print(f"         - 影响分数: {impact_score:.1f}")
        print("         - 目标覆盖率: ≥70%")
        print()

    # 计算总体统计
    total_files = len(analysis_results)
    total_loc = sum(item["loc"] for item in analysis_results)
    total_stmts = sum(item["total_stmts"] for item in analysis_results)
    weighted_coverage = (
        sum(item["coverage"] * item["total_stmts"] for item in analysis_results) / total_stmts
        if total_stmts > 0
        else 0
    )

    print("📊 总体统计:")
    print(f"   - 总文件数: {total_files}")
    print(f"   - 总代码行数: {total_loc:,} 行")
    print(f"   - 总语句数: {total_stmts:,} 句")
    print(f"   - 加权平均覆盖率: {weighted_coverage:.1f}%")
    print()

    # 保存结果到文件
    with open(
        "/home/user/projects/FootballPrediction/coverage_analysis_manual.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "timestamp": subprocess.run(
                    ["date"], capture_output=True, text=True
                ).stdout.strip(),
                "total_files": total_files,
                "total_loc": total_loc,
                "total_stmts": total_stmts,
                "weighted_coverage": weighted_coverage,
                "top_10_files": top_10_files,
                "all_files": analysis_results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("✅ 分析完成，结果已保存到 coverage_analysis_manual.json")
    return top_10_files


if __name__ == "__main__":
    main()
