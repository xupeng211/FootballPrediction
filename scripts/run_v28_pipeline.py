#!/usr/bin/env python3
"""
V28.0 生产级流水线执行脚本
==========================

核心功能:
1. 初始化 SyncDatabasePool
2. 运行 V28FeaturePipeline 处理 9,305 场比赛
3. 输出填充率报告和性能统计

Usage:
    python scripts/run_v28_pipeline.py [--batch-size 500] [--rolling-window 5]

Author: Senior Data Engineer
Version: V28.0
Date: 2025-12-27
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings
from src.database.db_pool import SyncDatabasePool, DatabasePoolConfig
from src.data_engineering import V28FeaturePipeline, PipelineConfig, run_v28_pipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s",
    handlers=[
        logging.FileHandler("logs/v28_pipeline.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="V28.0 生产级流水线执行脚本")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="批次大小（默认: 500）"
    )
    parser.add_argument(
        "--rolling-window",
        type=int,
        default=5,
        help="滚动窗口大小（默认: 5）"
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("V28.0 生产级流水线执行脚本")
    logger.info("=" * 70)
    logger.info(f"批次大小: {args.batch_size}")
    logger.info(f"滚动窗口: {args.rolling_window}")

    # 获取数据库配置
    settings = get_settings()
    db = settings.database

    # 数据库主机选择逻辑：
    # 1. 优先使用环境变量 DB_HOST（如果显式设置）
    # 2. Docker 环境下使用 'db'（仅对 docker-compose 服务有效）
    # 3. 否则使用配置中的主机
    db_host_override = os.getenv('DB_HOST')
    if db_host_override:
        host = db_host_override
    elif os.path.exists('/.dockerenv'):
        # 在 Docker 容器内，使用 docker-compose 服务名
        host = 'db'
    else:
        host = db.host

    # 创建数据库连接池配置
    config = DatabasePoolConfig(
        host=host,
        port=db.port,
        user=db.user,
        password=db.password.get_secret_value(),
        database=db.name,
        min_size=2,
        max_size=10
    )

    # 初始化连接池
    pool = SyncDatabasePool(config)
    pool.init_pool()

    try:
        # 运行流水线
        pipeline_config = PipelineConfig(
            batch_size=args.batch_size,
            rolling_window=args.rolling_window,
            strict_temporal_isolation=True
        )

        pipeline = V28FeaturePipeline(pool, pipeline_config)
        report = pipeline.run_full_pipeline()

        # 输出最终报告
        logger.info("\n" + "=" * 70)
        logger.info("V28.0 流水线执行完成！")
        logger.info("=" * 70)

        # 计算总体统计
        total_records = report.total_processed
        successful = report.successful_extractions
        rolling_features = report.rolling_features_computed

        logger.info(f"\n总体统计:")
        logger.info(f"  总处理记录: {total_records}")
        logger.info(f"  L2 提取成功: {successful} ({successful/total_records*100:.1f}%)")
        logger.info(f"  滚动特征计算: {rolling_features}")
        logger.info(f"  失败记录: {report.failed_records}")

        logger.info(f"\n提取路径分布:")
        for path, count in report.extraction_path_stats.items():
            pct = count / total_records * 100 if total_records > 0 else 0
            logger.info(f"  {path}: {count} ({pct:.1f}%)")

        logger.info(f"\n特征填充率:")
        sorted_features = sorted(
            report.fill_rates.items(),
            key=lambda x: x[1],
            reverse=True
        )

        avg_fill_rate = sum(report.fill_rates.values()) / len(report.fill_rates)

        for feature, fill_rate in sorted_features:
            status = "✅" if fill_rate >= 80 else "⚠️" if fill_rate >= 50 else "❌"
            logger.info(f"  {status} {feature}: {fill_rate:.2f}%")

        logger.info(f"\n平均填充率: {avg_fill_rate:.2f}%")

        if avg_fill_rate >= 80:
            logger.info("  ✅ 达到 80% 填充率目标！")
        else:
            logger.warning(f"  ⚠️  填充率低于 80% 目标: {avg_fill_rate:.2f}%")

    except Exception as e:
        logger.error(f"流水线执行失败: {e}")
        raise
    finally:
        pool.close()


if __name__ == "__main__":
    main()
