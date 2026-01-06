#!/usr/bin/env python3
"""V145.1 L2 数据清理脚本 - 清理损坏的小型 JSON 记录

此脚本用于清理 matches 表中损坏的 L2 数据（小于 10KB 的记录）。

功能：
1. 检测 l2_raw_json 字段大小小于 10KB 的记录
2. 提供预览模式（不实际删除）
3. 提供确认模式（交互式删除）
4. 记录清理日志

Author: V145.1 Data Engineering Team
Version: 1.0.0
Date: 2026-01-06
"""

import logging
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/clean_corrupt_l2.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class L2DataCleaner:
    """L2 数据清理器"""

    def __init__(self, min_size_kb: int = 10):
        """初始化清理器

        Args:
            min_size_kb: 最小允许的 L2 JSON 大小（KB）
        """
        self.min_size_kb = min_size_kb
        self.min_size_bytes = min_size_kb * 1024
        self.settings = get_settings()
        self.conn = None

    def connect(self):
        """连接数据库"""
        try:
            self.conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
            )
            logger.info("✅ 数据库连接成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("✅ 数据库连接已关闭")

    def detect_corrupt_records(self) -> list[dict]:
        """检测损坏的 L2 记录（小于最小大小）

        Returns:
            List[dict]: 损坏记录列表
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor(cursor_factory=RealDictCursor)

        query = """
        SELECT
            id,
            external_id,
            home_team,
            away_team,
            match_time,
            l2_data_version,
            octet_length(l2_raw_json::text) AS l2_size_bytes,
            pg_size_pretty(octet_length(l2_raw_json::text)) AS l2_size_pretty
        FROM matches
        WHERE l2_raw_json IS NOT NULL
          AND octet_length(l2_raw_json::text) < %s
        ORDER BY l2_size_bytes ASC
        """

        cursor.execute(query, (self.min_size_bytes,))
        corrupt_records = cursor.fetchall()
        cursor.close()

        logger.info(f"🔍 检测到 {len(corrupt_records)} 条损坏记录 (< {self.min_size_kb}KB)")
        return corrupt_records

    def preview_cleanup(self, corrupt_records: list[dict]):
        """预览清理操作（不实际删除）

        Args:
            corrupt_records: 损坏记录列表
        """
        if not corrupt_records:
            logger.info("✅ 没有检测到损坏记录")
            return

        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 预览模式 - 损坏记录列表 (< {self.min_size_kb}KB)")
        logger.info(f"{'='*80}\n")

        for i, record in enumerate(corrupt_records, 1):
            logger.info(
                f"{i}. Match ID: {record['id']} | "
                f"{record['home_team']} vs {record['away_team']} | "
                f"Size: {record['l2_size_pretty']} | "
                f"Version: {record['l2_data_version']}"
            )

        total_size = sum(r['l2_size_bytes'] for r in corrupt_records)
        logger.info(f"\n📊 统计:")
        logger.info(f"  - 损坏记录数: {len(corrupt_records)}")
        logger.info(f"  - 总占用空间: {total_size / 1024:.2f} KB")

    def clean_corrupt_records(self, corrupt_records: list[dict], dry_run: bool = True):
        """清理损坏的 L2 记录

        Args:
            corrupt_records: 损坏记录列表
            dry_run: 是否为干跑模式（不实际删除）
        """
        if not corrupt_records:
            logger.info("✅ 没有需要清理的记录")
            return

        if dry_run:
            logger.info("\n🔍 DRY RUN 模式 - 不会实际删除记录")
            self.preview_cleanup(corrupt_records)
            return

        # 交互式确认
        logger.info(f"\n⚠️  准备删除 {len(corrupt_records)} 条损坏记录")
        confirm = input("确认删除? (yes/no): ").strip().lower()

        if confirm != "yes":
            logger.info("❌ 取消清理操作")
            return

        cursor = self.conn.cursor()

        deleted_count = 0
        for record in corrupt_records:
            try:
                # 将 l2_raw_json 设置为 NULL（保留记录）
                update_query = """
                UPDATE matches
                SET l2_raw_json = NULL,
                    l2_data_version = NULL,
                    l2_collected_at = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """
                cursor.execute(update_query, (record['id'],))
                deleted_count += 1
            except Exception as e:
                logger.error(f"❌ 清理记录 {record['id']} 失败: {e}")

        self.conn.commit()
        cursor.close()

        logger.info(f"✅ 成功清理 {deleted_count} 条记录")

    def get_statistics(self) -> dict:
        """获取 L2 数据统计信息

        Returns:
            Dict: 统计信息
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor(cursor_factory=RealDictCursor)

        # 总体统计
        stats_query = """
        SELECT
            COUNT(*) AS total_matches,
            COUNT(l2_raw_json) AS l2_collected,
            COUNT(*) - COUNT(l2_raw_json) AS l2_missing,
            ROUND(100.0 * COUNT(l2_raw_json) / COUNT(*), 2) AS l2_coverage_pct
        FROM matches
        """

        cursor.execute(stats_query)
        overall_stats = cursor.fetchone()

        # 版本分布统计
        version_query = """
        SELECT
            l2_data_version,
            COUNT(*) AS count,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
        FROM matches
        WHERE l2_raw_json IS NOT NULL
        GROUP BY l2_data_version
        ORDER BY count DESC
        """

        cursor.execute(version_query)
        version_stats = cursor.fetchall()

        # 大小分布统计
        size_query = """
        SELECT
            COUNT(*) FILTER (
                WHERE octet_length(l2_raw_json::text) < 10240
            ) AS small_size,
            COUNT(*) FILTER (
                WHERE octet_length(l2_raw_json::text) >= 10240
                AND octet_length(l2_raw_json::text) < 102400
            ) AS medium_size,
            COUNT(*) FILTER (
                WHERE octet_length(l2_raw_json::text) >= 102400
            ) AS large_size
        FROM matches
        WHERE l2_raw_json IS NOT NULL
        """

        cursor.execute(size_query)
        size_stats = cursor.fetchone()

        cursor.close()

        return {
            "overall": overall_stats,
            "versions": version_stats,
            "size_distribution": size_stats
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="V145.1 L2 数据清理脚本")
    parser.add_argument(
        "--min-size",
        type=int,
        default=10,
        help="最小允许的 L2 JSON 大小（KB），默认 10KB"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干跑模式，不实际删除记录"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制清理，无需确认"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="显示统计信息"
    )

    args = parser.parse_args()

    cleaner = L2DataCleaner(min_size_kb=args.min_size)

    try:
        cleaner.connect()

        if args.stats:
            # 显示统计信息
            stats = cleaner.get_statistics()
            logger.info("\n" + "="*80)
            logger.info("📊 L2 数据统计信息")
            logger.info("="*80 + "\n")

            logger.info("🎯 总体统计:")
            overall = stats['overall']
            logger.info(f"  - 总比赛数: {overall['total_matches']}")
            logger.info(f"  - L2 已采集: {overall['l2_collected']}")
            logger.info(f"  - L2 缺失: {overall['l2_missing']}")
            logger.info(f"  - 覆盖率: {overall['l2_coverage_pct']}%")

            logger.info("\n📋 版本分布:")
            for v in stats['versions']:
                logger.info(f"  - {v['l2_data_version']}: {v['count']} ({v['pct']}%)")

            logger.info("\n📏 大小分布:")
            size = stats['size_distribution']
            logger.info(f"  - 小型 (<10KB): {size['small_size']}")
            logger.info(f"  - 中型 (10-100KB): {size['medium_size']}")
            logger.info(f"  - 大型 (>=100KB): {size['large_size']}")
            return

        # 检测损坏记录
        corrupt_records = cleaner.detect_corrupt_records()

        if not corrupt_records:
            logger.info("✅ 没有检测到损坏记录，无需清理")
            return

        # 清理操作
        cleaner.clean_corrupt_records(corrupt_records, dry_run=args.dry_run)

    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        cleaner.close()


if __name__ == "__main__":
    main()
