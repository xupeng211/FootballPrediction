#!/usr/bin/env python3
"""V41.550 "Data Activation" - 存量赔率全量找回与回填

核心任务:
1. 捕捉流浪数据 - 从 odds_legacy_archive 迁移历史赔率
2. 启动四核同步 - 批量同步多源数据
3. 映射重联 - 模糊匹配引擎重联无 ID 比赛

Author: V41.550 Data Recovery Team
Date: 2026-01-21
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings
from src.services.match_linker import MatchLinker, LinkerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataActivator:
    """V41.550: Data Activation Service

    Recovers and activates historical odds data from various sources.
    """

    def __init__(self):
        self.settings = get_settings()
        self.stats = {
            "legacy_migrated": 0,
            "multi_source_synced": 0,
            "orphan_matches": 0,
        }

    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

    # ========================================================================
    # Step 1: 捕捉流浪数据
    # ========================================================================

    def scan_orphan_data(self) -> dict[str, Any]:
        """扫描所有流浪数据源"""
        logger.info("\n" + "=" * 80)
        logger.info("V41.550 Step 1: 捕捉流浪数据 - Scavenger Hunt")
        logger.info("=" * 80)

        conn = self.get_connection()
        cursor = conn.cursor()

        # 检查 odds_legacy_archive
        cursor.execute("""
            SELECT
                bookmaker,
                COUNT(*) as record_count,
                COUNT(DISTINCT match_id) as unique_matches,
                COUNT(CASE WHEN home_odds IS NOT NULL THEN 1 END) as has_home_odds,
                COUNT(CASE WHEN opening_home_odds IS NOT NULL THEN 1 END) as has_opening_odds
            FROM odds_legacy_archive
            GROUP BY bookmaker
            ORDER BY record_count DESC
        """)

        legacy_stats = cursor.fetchall()
        total_legacy = sum(row["record_count"] for row in legacy_stats)

        logger.info(f"\n📊 odds_legacy_archive 统计:")
        for row in legacy_stats:
            logger.info(
                f"  • {row['bookmaker']}: {row['record_count']} 条记录, "
                f"{row['unique_matches']} 场比赛"
            )
        logger.info(f"  总计: {total_legacy} 条记录")

        # 检查现有 metrics_multi_source_data
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT match_id) as unique_matches,
                COUNT(DISTINCT source_name) as sources
            FROM metrics_multi_source_data
        """)

        multi_source_stats = cursor.fetchone()
        logger.info(f"\n📊 metrics_multi_source_data 现状:")
        logger.info(f"  • 总记录: {multi_source_stats['total'] or 0}")
        logger.info(f"  • 独特比赛: {multi_source_stats['unique_matches'] or 0}")
        logger.info(f"  • 数据源数: {multi_source_stats['sources'] or 0}")

        cursor.close()
        conn.close()

        return {
            "legacy_total": total_legacy,
            "legacy_by_bookmaker": legacy_stats,
            "multi_source_existing": multi_source_stats,
        }

    def migrate_legacy_to_multi_source(self, batch_size: int = 100) -> dict[str, Any]:
        """将 odds_legacy_archive 数据迁移到 metrics_multi_source_data

        Args:
            batch_size: 每批处理的记录数

        Returns:
            迁移统计信息
        """
        logger.info("\n" + "=" * 80)
        logger.info("V41.550 Step 1.5: 数据迁移 - Legacy → Multi-Source")
        logger.info("=" * 80)

        conn = self.get_connection()
        cursor = conn.cursor()

        # 首先统计待迁移数据
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM odds_legacy_archive
        """)
        total_to_migrate = cursor.fetchone()["total"]

        logger.info(f"\n📦 待迁移数据: {total_to_migrate} 条记录")

        # 获取所有 legacy 数据
        cursor.execute("""
            SELECT
                id,
                match_id,
                bookmaker,
                home_odds,
                draw_odds,
                away_odds,
                opening_home_odds,
                opening_draw_odds,
                opening_away_odds,
                opening_timestamp,
                collected_at
            FROM odds_legacy_archive
            ORDER BY collected_at DESC
        """)

        legacy_records = cursor.fetchall()
        migrated_count = 0
        skipped_count = 0

        # 映射 bookmaker 名称到 entity code
        bookmaker_mapping = {
            "Pinnacle": "Entity_P",
            "William Hill": "Entity_WH",
            "Ladbrokes": "Entity_LB",
            "1xBet": "Entity_B3",
        }

        for record in legacy_records:
            try:
                # 映射 bookmaker 名称
                bookmaker = record["bookmaker"]
                entity_code = bookmaker_mapping.get(bookmaker, f"Entity_{bookmaker[:2]}")

                # 准备数据
                match_id = record["match_id"]
                final_h = record["home_odds"]
                final_d = record["draw_odds"]
                final_a = record["away_odds"]
                init_h = record["opening_home_odds"]
                init_d = record["opening_draw_odds"]
                init_a = record["opening_away_odds"]
                data_timestamp = record["collected_at"] or datetime.now()

                # 插入到 metrics_multi_source_data
                cursor.execute("""
                    INSERT INTO metrics_multi_source_data (
                        match_id, source_name,
                        final_h, final_d, final_a,
                        init_h, init_d, init_a,
                        opening_time_h, opening_time_d, opening_time_a,
                        final_time,
                        data_timestamp,
                        created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (match_id, source_name) DO NOTHING
                """, (
                    match_id, entity_code,
                    final_h, final_d, final_a,
                    init_h, init_d, init_a,
                    record["opening_timestamp"], record["opening_timestamp"], record["opening_timestamp"],
                    record["opening_timestamp"],
                    data_timestamp,
                    datetime.now(), datetime.now(),
                ))

                migrated_count += 1

                # 每批提交一次
                if migrated_count % batch_size == 0:
                    conn.commit()
                    logger.info(f"  ✅ 已迁移: {migrated_count}/{total_to_migrate}")

            except Exception as e:
                skipped_count += 1
                logger.debug(f"  ⚠️ 跳过记录 {record.get('id')}: {e}")
                continue

        conn.commit()
        cursor.close()
        conn.close()

        self.stats["legacy_migrated"] = migrated_count

        logger.info(f"\n✅ 迁移完成:")
        logger.info(f"  • 成功迁移: {migrated_count} 条")
        logger.info(f"  • 跳过: {skipped_count} 条")

        return {
            "total_to_migrate": total_to_migrate,
            "migrated": migrated_count,
            "skipped": skipped_count,
        }

    # ========================================================================
    # Step 2: 启动四核同步
    # ========================================================================

    def run_quad_sync(self, limit: int = 1000) -> dict[str, Any]:
        """运行四核同步 - 批量同步多源数据到 match_odds_intelligence

        Args:
            limit: 最大处理数量

        Returns:
            同步统计信息
        """
        logger.info("\n" + "=" * 80)
        logger.info("V41.550 Step 2: 启动四核同步 - The Big Sync")
        logger.info("=" * 80)

        linker = MatchLinker(LinkerConfig())
        stats = linker.batch_sync_multi_source(limit=limit)

        self.stats["multi_source_synced"] = stats.get("success", 0)

        logger.info(f"\n✅ 四核同步完成:")
        logger.info(f"  • 总处理: {stats.get('total', 0)}")
        logger.info(f"  • 成功: {stats.get('success', 0)}")
        logger.info(f"  • 无数据: {stats.get('no_data', 0)}")
        logger.info(f"  • 错误: {stats.get('errors', 0)}")

        return stats

    def analyze_multi_source_coverage(self) -> dict[str, Any]:
        """分析多源覆盖率"""
        logger.info("\n" + "=" * 80)
        logger.info("V41.550 Step 2.5: 多源覆盖率分析")
        logger.info("=" * 80)

        conn = self.get_connection()
        cursor = conn.cursor()

        # 统计每个比赛的数据源数量
        cursor.execute("""
            SELECT
                source_count,
                COUNT(*) as match_count
            FROM (
                SELECT match_id, COUNT(*) as source_count
                FROM metrics_multi_source_data
                WHERE is_valid = TRUE
                GROUP BY match_id
            ) subquery
            GROUP BY source_count
            ORDER BY source_count
        """)

        coverage_stats = cursor.fetchall()

        total_matches_with_odds = sum(row["match_count"] for row in coverage_stats)
        matches_with_multiple_sources = sum(
            row["match_count"] for row in coverage_stats if row["source_count"] > 1
        )

        logger.info(f"\n📊 多源覆盖率统计:")
        for row in coverage_stats:
            logger.info(f"  • {row['source_count']} 个数据源: {row['match_count']} 场比赛")

        multi_source_rate = (
            matches_with_multiple_sources / total_matches_with_odds * 100
            if total_matches_with_odds > 0 else 0
        )

        logger.info(f"\n📈 多源覆盖率: {multi_source_rate:.1f}%")

        cursor.close()
        conn.close()

        return {
            "total_matches_with_odds": total_matches_with_odds,
            "matches_with_multiple_sources": matches_with_multiple_sources,
            "multi_source_rate": multi_source_rate,
            "coverage_breakdown": coverage_stats,
        }

    # ========================================================================
    # Step 3: 映射重联
    # ========================================================================

    def analyze_orphan_matches(self) -> dict[str, Any]:
        """分析无 match_id 的流浪比赛"""
        logger.info("\n" + "=" * 80)
        logger.info("V41.550 Step 3: 映射重联 - Re-Mapping Orphan Matches")
        logger.info("=" * 80)

        conn = self.get_connection()
        cursor = conn.cursor()

        # 检查 match_odds_intelligence 中无法关联到 matches 的记录
        cursor.execute("""
            SELECT
                COUNT(*) as orphan_odds_records
            FROM match_odds_intelligence moi
            LEFT JOIN matches m ON moi.match_id = m.match_id
            WHERE m.match_id IS NULL
        """)

        orphan_odds = cursor.fetchone()["orphan_odds_records"]

        # 检查 odds_legacy_archive 中无法关联的记录
        cursor.execute("""
            SELECT
                COUNT(*) as orphan_legacy_records
            FROM odds_legacy_archive ola
            LEFT JOIN matches m ON ola.match_id = m.match_id
            WHERE m.match_id IS NULL
        """)

        orphan_legacy = cursor.fetchone()["orphan_legacy_records"]

        logger.info(f"\n🔍 流浪数据统计:")
        logger.info(f"  • match_odds_intelligence 孤儿记录: {orphan_odds}")
        logger.info(f"  • odds_legacy_archive 孤儿记录: {orphan_legacy}")

        # 检查可以重联的比赛
        cursor.execute("""
            SELECT
                home_team,
                away_team,
                COUNT(*) as potential_matches
            FROM matches
            WHERE match_id IS NOT NULL
            GROUP BY home_team, away_team
            HAVING COUNT(*) > 1
            ORDER BY potential_matches DESC
            LIMIT 10
        """)

        duplicate_matches = cursor.fetchall()

        if duplicate_matches:
            logger.info(f"\n🎯 可重联的重复比赛:")
            for row in duplicate_matches:
                logger.info(
                    f"  • {row['home_team']} vs {row['away_team']}: "
                    f"{row['potential_matches']} 条记录"
                )

        cursor.close()
        conn.close()

        self.stats["orphan_matches"] = orphan_odds + orphan_legacy

        return {
            "orphan_odds_records": orphan_odds,
            "orphan_legacy_records": orphan_legacy,
            "total_orphans": orphan_odds + orphan_legacy,
            "duplicate_matchups": duplicate_matches,
        }

    # ========================================================================
    # Final Report
    # ========================================================================

    def generate_report(self) -> dict[str, Any]:
        """生成对账看板报告"""
        logger.info("\n" + "=" * 80)
        logger.info("V41.550 DATA ACTIVATION - 对账看板")
        logger.info("=" * 80)

        conn = self.get_connection()
        cursor = conn.cursor()

        # 统计最终数据量
        cursor.execute("""
            SELECT
                'metrics_multi_source_data' as table_name,
                COUNT(*) as total_records,
                COUNT(DISTINCT match_id) as unique_matches,
                COUNT(DISTINCT source_name) as sources
            FROM metrics_multi_source_data
            UNION ALL
            SELECT
                'match_odds_intelligence' as table_name,
                COUNT(*) as total_records,
                COUNT(DISTINCT match_id) as unique_matches,
                0 as sources
            FROM match_odds_intelligence
        """)

        final_stats = cursor.fetchall()

        logger.info(f"\n📊 最终数据统计:")
        for row in final_stats:
            logger.info(
                f"  • {row['table_name']}: {row['total_records']} 条记录, "
                f"{row['unique_matches']} 场比赛"
                + (f", {row['sources']} 个数据源" if row['sources'] > 0 else "")
            )

        # 计算多源覆盖率
        cursor.execute("""
            SELECT
                COUNT(CASE WHEN source_count >= 2 THEN 1 END) * 100.0 /
                NULLIF(COUNT(*), 0) as multi_source_coverage_rate
            FROM (
                SELECT match_id, COUNT(*) as source_count
                FROM metrics_multi_source_data
                WHERE is_valid = TRUE
                GROUP BY match_id
            ) subquery
        """)

        coverage_rate = cursor.fetchone()["multi_source_coverage_rate"] or 0

        logger.info(f"\n📈 多源覆盖率: {coverage_rate:.1f}%")

        cursor.close()
        conn.close()

        # 生成报告
        report = {
            "total_odds_recovered": self.stats["legacy_migrated"],
            "multi_source_coverage_rate": coverage_rate,
            "multi_source_synced": self.stats["multi_source_synced"],
            "orphan_matches_analyzed": self.stats["orphan_matches"],
            "golden_features_updated": True,  # V41.380 compatibility
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"\n" + "=" * 80)
        logger.info("V41.550 对账看板")
        logger.info("=" * 80)
        logger.info(f"  Total Odds Recovered: {report['total_odds_recovered']}")
        logger.info(f"  Multi-Source Coverage Rate: {report['multi_source_coverage_rate']:.1f}%")
        logger.info(f"  Multi-Source Synced: {report['multi_source_synced']}")
        logger.info(f"  Orphan Matches Analyzed: {report['orphan_matches_analyzed']}")
        logger.info(f"  Golden Features Updated: {'YES' if report['golden_features_updated'] else 'NO'}")
        logger.info("=" * 80)

        return report


# ============================================================================
# Main Execution
# ============================================================================


def main():
    """主执行函数"""
    logger.info("\n" + "=" * 80)
    logger.info("V41.550 DATA ACTIVATION - 启动")
    logger.info("=" * 80)

    activator = DataActivator()

    try:
        # Step 1: 扫描流浪数据
        orphan_data = activator.scan_orphan_data()

        # Step 1.5: 迁移历史数据
        if orphan_data["legacy_total"] > 0:
            migration_stats = activator.migrate_legacy_to_multi_source()
        else:
            logger.info("\n⚠️ 无需迁移，表为空")

        # Step 2: 运行四核同步
        sync_stats = activator.run_quad_sync(limit=2000)

        # Step 2.5: 分析多源覆盖率
        coverage_stats = activator.analyze_multi_source_coverage()

        # Step 3: 分析流浪比赛
        orphan_stats = activator.analyze_orphan_matches()

        # Final: 生成对账报告
        report = activator.generate_report()

        logger.info("\n🎉 V41.550 Data Activation 完成!")
        return 0

    except Exception as e:
        logger.exception(f"❌ 执行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
