#!/usr/bin/env python3
"""
V28.0 生产级特征流水线
========================

核心功能:
1. 使用 SyncDatabasePool 管理数据库连接
2. 集成 MultiPathExtractor 进行鲁棒 JSONB 提取
3. 时间对齐的滚动特征计算（严格 match_date < current_match_date）
4. 批量处理机制（默认 500 条/批次）
5. 全面的错误处理和进度报告

验收指标:
- 填充率 80%+（通过多路径降级）
- 零数据泄露（严格时间隔离）
- 内存安全（批量处理）

Author: Senior Data Engineer
Version: V28.0
Date: 2025-12-27
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from .multipath_extractor import MultiPathExtractor, MatchStats, ExtractionPath
from ..database.db_pool import SyncDatabasePool

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """流水线配置"""
    batch_size: int = 500
    rolling_window: int = 5
    min_matches_required: int = 3

    # 时间对齐严格模式
    strict_temporal_isolation: bool = True


@dataclass
class PipelineReport:
    """流水线执行报告"""
    total_processed: int = 0
    successful_extractions: int = 0
    rolling_features_computed: int = 0
    failed_records: int = 0

    extraction_path_stats: Dict[str, int] = field(default_factory=dict)
    fill_rates: Dict[str, float] = field(default_factory=dict)


class V28FeaturePipeline:
    """
    V28.0 生产级特征流水线

    核心职责:
    1. 从 raw_match_data 提取 L2 统计数据
    2. 计算时间对齐的滚动特征
    3. 更新 match_features_training 表

    使用示例:
        pipeline = V28FeaturePipeline(SyncDatabasePool())
        report = pipeline.run_full_pipeline()
    """

    # 特征列定义
    NUMERIC_FEATURES = [
        'home_xg', 'away_xg',
        'home_possession', 'away_possession',
        'home_shots', 'away_shots',
        'home_shots_on_target', 'away_shots_on_target',
        'home_passes', 'away_passes',
        'home_team_rating', 'away_team_rating'
    ]

    def __init__(self, db_pool: SyncDatabasePool, config: Optional[PipelineConfig] = None):
        """
        初始化流水线

        Args:
            db_pool: SyncDatabasePool 实例
            config: 流水线配置（可选）
        """
        self.db_pool = db_pool
        self.config = config or PipelineConfig()
        self.extractor = MultiPathExtractor()
        self.report = PipelineReport()

    def run_full_pipeline(self) -> PipelineReport:
        """
        执行完整的特征流水线

        Returns:
            PipelineReport: 执行报告
        """
        logger.info("=" * 70)
        logger.info("V28.0 生产级特征流水线启动")
        logger.info("=" * 70)

        # 阶段 1: L2 数据提取
        logger.info("\n[阶段 1/3] L2 统计数据提取...")
        l2_stats = self._extract_l2_statistics()

        # 阶段 2: 滚动特征计算
        logger.info("\n[阶段 2/3] 滚动特征计算...")
        rolling_stats = self._compute_rolling_features()

        # 阶段 3: 合并并更新训练表
        logger.info("\n[阶段 3/3] 合并特征并更新训练表...")
        final_stats = self._merge_and_update(l2_stats, rolling_stats)

        # 生成最终报告
        self._generate_final_report()

        logger.info("\n" + "=" * 70)
        logger.info("V28.0 流水线执行完成！")
        logger.info("=" * 70)

        return self.report

    # ========================================================================
    # 阶段 1: L2 统计数据提取
    # ========================================================================

    def _extract_l2_statistics(self) -> Dict[str, int]:
        """
        从 raw_match_data 提取 L2 统计数据

        Returns:
            Dict: 提取统计
        """
        logger.info("开始 L2 统计数据提取...")

        with self.db_pool.get_connection() as conn:  # type: ignore[assignment]
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # 获取需要处理的比赛总数
            cur.execute("""
                SELECT COUNT(*) as total
                FROM raw_match_data r
                JOIN matches m ON r.match_id = m.match_id::text
                WHERE m.is_finished = true
            """)
            total_matches = cur.fetchone()['total']
            logger.info(f"需要处理的比赛数: {total_matches}")

            # 批量处理
            offset = 0
            batch_num = 0

            while offset < total_matches:
                batch_num += 1
                logger.info(f"\n处理批次 {batch_num} (offset={offset})...")

                # 获取当前批次数据
                cur.execute("""
                    SELECT
                        r.match_id,
                        m.match_date,
                        m.home_team,
                        m.away_team,
                        m.home_score,
                        m.away_score,
                        r.raw_data
                    FROM raw_match_data r
                    JOIN matches m ON r.match_id = m.match_id::text
                    WHERE m.is_finished = true
                    ORDER BY m.match_date
                    LIMIT %s OFFSET %s
                """, (self.config.batch_size, offset))

                batch_records = cur.fetchall()

                # 提取并更新
                extracted_count = self._process_extraction_batch(batch_records, conn)

                offset += len(batch_records)
                self.report.total_processed += len(batch_records)
                self.report.successful_extractions += extracted_count

                logger.info(f"批次 {batch_num} 完成: {extracted_count}/{len(batch_records)} 条成功提取")

            # 获取提取路径统计
            extraction_report = self.extractor.get_extraction_report()
            self.report.extraction_path_stats = extraction_report['path_success_counts']

            logger.info(f"\nL2 提取完成:")
            logger.info(f"  总处理: {self.report.total_processed} 条")
            logger.info(f"  成功: {self.report.successful_extractions} 条")
            logger.info(f"  成功率: {self.report.successful_extractions/self.report.total_processed*100:.2f}%")

            for path, count in self.report.extraction_path_stats.items():
                logger.info(f"  {path}: {count} 条")

        return {
            'total': self.report.total_processed,
            'successful': self.report.successful_extractions
        }

    def _process_extraction_batch(self, batch_records: List[Any], conn: Any) -> int:
        """
        处理单个批次的数据提取

        Args:
            batch_records: 批次记录
            conn: 数据库连接

        Returns:
            int: 成功提取的数量
        """
        extracted_count = 0
        cur = conn.cursor(cursor_factory=RealDictCursor)

        for record in batch_records:
            match_id = record['match_id']

            # 使用多路径提取器
            stats = self.extractor.extract_from_jsonb(
                match_id=match_id,
                raw_data=record['raw_data'],
                match_date=str(record['match_date']),
                home_team=record['home_team'],
                away_team=record['away_team'],
                home_score=record['home_score'],
                away_score=record['away_score']
            )

            if stats.extraction_success:
                # 准备 UPSERT 数据（包含 season 和 match_date）
                # 从 match_date 推导 season（例如 2024-08-01 -> "2425"）
                match_date_obj = record['match_date']
                if hasattr(match_date_obj, 'year'):
                    year = match_date_obj.year
                    month = match_date_obj.month
                    # 足球赛季跨年：8月后开始新的赛季
                    if month >= 8:
                        season = f"{str(year)[-2:]}{str(year + 1)[-2:]}"
                    else:
                        season = f"{str(year - 1)[-2:]}{str(year)[-2:]}"
                else:
                    # Fallback
                    season = "2324"

                data = self._prepare_l2_upsert_data(stats, season, match_date_obj)

                # 执行 UPSERT
                cur.execute("""
                    INSERT INTO match_features_training (
                        match_id, season, match_date, home_team, away_team,
                        home_xg, away_xg,
                        home_possession, away_possession,
                        home_shots, away_shots,
                        home_shots_on_target, away_shots_on_target,
                        home_passes, away_passes,
                        home_team_rating, away_team_rating
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (match_id) DO UPDATE SET
                        home_xg = EXCLUDED.home_xg,
                        away_xg = EXCLUDED.away_xg,
                        home_possession = EXCLUDED.home_possession,
                        away_possession = EXCLUDED.away_possession,
                        home_shots = EXCLUDED.home_shots,
                        away_shots = EXCLUDED.away_shots,
                        home_shots_on_target = EXCLUDED.home_shots_on_target,
                        away_shots_on_target = EXCLUDED.away_shots_on_target,
                        home_passes = EXCLUDED.home_passes,
                        away_passes = EXCLUDED.away_passes,
                        home_team_rating = EXCLUDED.home_team_rating,
                        away_team_rating = EXCLUDED.away_team_rating
                """, data)

                extracted_count += 1
            else:
                self.report.failed_records += 1

        conn.commit()
        return extracted_count

    def _prepare_l2_upsert_data(self, stats: MatchStats, season: str, match_date: Any) -> Tuple[Any, ...]:
        """准备 L2 UPSERT 数据"""
        return (
            stats.match_id,
            season,
            match_date,
            stats.home_team,
            stats.away_team,
            stats.home_xg, stats.away_xg,
            stats.home_possession, stats.away_possession,
            stats.home_shots, stats.away_shots,
            stats.home_shots_on_target, stats.away_shots_on_target,
            stats.home_passes, stats.away_passes,
            stats.home_team_rating, stats.away_team_rating
        )

    # ========================================================================
    # 阶段 2: 滚动特征计算
    # ========================================================================

    def _compute_rolling_features(self) -> Dict[str, int]:
        """
        计算时间对齐的滚动特征

        核心原则: 严格 match_date < current_match_date

        Returns:
            Dict: 计算统计
        """
        logger.info("开始滚动特征计算...")

        with self.db_pool.get_connection() as conn:  # type: ignore[assignment]
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # 创建临时表存储历史统计数据
            logger.info("创建临时历史统计表...")
            cur.execute("""
                DROP TABLE IF EXISTS tmp_l2_stats;
                CREATE TEMP TABLE tmp_l2_stats AS
                SELECT
                    m.match_id,
                    m.match_date,
                    m.home_team,
                    m.away_team,
                    COALESCE(mft.home_xg, 0) as home_xg,
                    COALESCE(mft.away_xg, 0) as away_xg,
                    COALESCE(mft.home_shots_on_target, 0) as home_shots_on_target,
                    COALESCE(mft.away_shots_on_target, 0) as away_shots_on_target,
                    COALESCE(mft.home_possession, 0) as home_possession,
                    COALESCE(mft.away_possession, 0) as away_possession,
                    COALESCE(mft.home_team_rating, 0) as home_team_rating,
                    COALESCE(mft.away_team_rating, 0) as away_team_rating
                FROM matches m
                LEFT JOIN match_features_training mft ON m.match_id = mft.match_id::text
                WHERE m.is_finished = true
                ORDER BY m.match_date;
            """)

            # 创建索引
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tmp_date ON tmp_l2_stats(match_date);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tmp_home ON tmp_l2_stats(home_team);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tmp_away ON tmp_l2_stats(away_team);")

            logger.info("临时表创建完成，开始计算滚动特征...")

            # 计算滚动特征（严格时间对齐）
            window = self.config.rolling_window
            cur.execute(f"""
                UPDATE match_features_training mft
                SET
                    rolling_xg_home = (
                        SELECT COALESCE(AVG(hm.home_xg), 0)
                        FROM tmp_l2_stats hm
                        WHERE hm.home_team = mft.home_team
                          AND hm.match_date < (
                              SELECT m.match_date
                              FROM matches m
                              WHERE m.match_id = mft.match_id::text
                          )
                          AND hm.home_xg > 0
                        ORDER BY hm.match_date DESC
                        LIMIT {window}
                    ),
                    rolling_xg_away = (
                        SELECT COALESCE(AVG(am.away_xg), 0)
                        FROM tmp_l2_stats am
                        WHERE am.away_team = mft.away_team
                          AND am.match_date < (
                              SELECT m.match_date
                              FROM matches m
                              WHERE m.match_id = mft.match_id::text
                          )
                          AND am.away_xg > 0
                        ORDER BY am.match_date DESC
                        LIMIT {window}
                    ),
                    rolling_shots_on_target_home = (
                        SELECT COALESCE(AVG(hm.home_shots_on_target), 0)
                        FROM tmp_l2_stats hm
                        WHERE hm.home_team = mft.home_team
                          AND hm.match_date < (
                              SELECT m.match_date
                              FROM matches m
                              WHERE m.match_id = mft.match_id::text
                          )
                          AND hm.home_shots_on_target > 0
                        ORDER BY hm.match_date DESC
                        LIMIT {window}
                    ),
                    rolling_shots_on_target_away = (
                        SELECT COALESCE(AVG(am.away_shots_on_target), 0)
                        FROM tmp_l2_stats am
                        WHERE am.away_team = mft.away_team
                          AND am.match_date < (
                              SELECT m.match_date
                              FROM matches m
                              WHERE m.match_id = mft.match_id::text
                          )
                          AND am.away_shots_on_target > 0
                        ORDER BY am.match_date DESC
                        LIMIT {window}
                    ),
                    rolling_possession_home = (
                        SELECT COALESCE(AVG(hm.home_possession), 0)
                        FROM tmp_l2_stats hm
                        WHERE hm.home_team = mft.home_team
                          AND hm.match_date < (
                              SELECT m.match_date
                              FROM matches m
                              WHERE m.match_id = mft.match_id::text
                          )
                          AND hm.home_possession > 0
                        ORDER BY hm.match_date DESC
                        LIMIT {window}
                    ),
                    rolling_possession_away = (
                        SELECT COALESCE(AVG(am.away_possession), 0)
                        FROM tmp_l2_stats am
                        WHERE am.away_team = mft.away_team
                          AND am.match_date < (
                              SELECT m.match_date
                              FROM matches m
                              WHERE m.match_id = mft.match_id::text
                          )
                          AND am.away_possession > 0
                        ORDER BY am.match_date DESC
                        LIMIT {window}
                    ),
                    rolling_team_rating_home = (
                        SELECT COALESCE(AVG(hm.home_team_rating), 0)
                        FROM tmp_l2_stats hm
                        WHERE hm.home_team = mft.home_team
                          AND hm.match_date < (
                              SELECT m.match_date
                              FROM matches m
                              WHERE m.match_id = mft.match_id::text
                          )
                          AND hm.home_team_rating > 0
                        ORDER BY hm.match_date DESC
                        LIMIT {window}
                    ),
                    rolling_team_rating_away = (
                        SELECT COALESCE(AVG(am.away_team_rating), 0)
                        FROM tmp_l2_stats am
                        WHERE am.away_team = mft.away_team
                          AND am.match_date < (
                              SELECT m.match_date
                              FROM matches m
                              WHERE m.match_id = mft.match_id::text
                          )
                          AND am.away_team_rating > 0
                        ORDER BY am.match_date DESC
                        LIMIT {window}
                    )
            """)

            updated = cur.rowcount
            conn.commit()

            self.report.rolling_features_computed = updated

            logger.info(f"滚动特征计算完成: {updated} 条记录更新")

        return {
            'updated': updated
        }

    # ========================================================================
    # 阶段 3: 合并并更新训练表
    # ========================================================================

    def _merge_and_update(self, l2_stats: Dict, rolling_stats: Dict) -> Dict:
        """
        合并 L2 统计和滚动特征

        Args:
            l2_stats: L2 提取统计
            rolling_stats: 滚动特征统计

        Returns:
            Dict: 合并统计
        """
        logger.info("合并特征并计算最终填充率...")

        with self.db_pool.get_connection() as conn:  # type: ignore[assignment]
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # 计算填充率
            for feature in self.NUMERIC_FEATURES + [
                'rolling_xg_home', 'rolling_xg_away',
                'rolling_shots_on_target_home', 'rolling_shots_on_target_away',
                'rolling_possession_home', 'rolling_possession_away',
                'rolling_team_rating_home', 'rolling_team_rating_away'
            ]:
                cur.execute(f"""
                    SELECT
                        COUNT(*) as total,
                        COUNT({feature}) as filled,
                        ROUND(
                            COUNT({feature})::numeric / NULLIF(COUNT(*), 0) * 100,
                            2
                        ) as fill_rate
                    FROM match_features_training
                """)

                row = cur.fetchone()
                self.report.fill_rates[feature] = row['fill_rate'] or 0.0

        # 计算平均填充率
        avg_fill_rate = sum(self.report.fill_rates.values()) / len(self.report.fill_rates)

        logger.info("\n填充率统计:")
        logger.info(f"  平均填充率: {avg_fill_rate:.2f}%")

        if avg_fill_rate >= 80:
            logger.info("  ✅ 达到 80% 填充率目标")
        else:
            logger.warning(f"  ⚠️  填充率低于 80% 目标: {avg_fill_rate:.2f}%")

        return {
            'avg_fill_rate': avg_fill_rate,
            'feature_fill_rates': self.report.fill_rates
        }

    # ========================================================================
    # 报告生成
    # ========================================================================

    def _generate_final_report(self) -> None:
        """生成最终报告"""
        logger.info("\n" + "=" * 70)
        logger.info("V28.0 流水线执行报告")
        logger.info("=" * 70)

        logger.info(f"\n总体统计:")
        logger.info(f"  总处理记录: {self.report.total_processed}")
        logger.info(f"  成功提取: {self.report.successful_extractions}")
        logger.info(f"  滚动特征: {self.report.rolling_features_computed}")
        logger.info(f"  失败记录: {self.report.failed_records}")

        logger.info(f"\n提取路径分布:")
        for path, count in self.report.extraction_path_stats.items():
            pct = count / self.report.total_processed * 100 if self.report.total_processed > 0 else 0
            logger.info(f"  {path}: {count} ({pct:.1f}%)")

        logger.info(f"\n特征填充率 Top 10:")
        sorted_features = sorted(
            self.report.fill_rates.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        for feature, fill_rate in sorted_features:
            status = "✅" if fill_rate >= 80 else "⚠️" if fill_rate >= 50 else "❌"
            logger.info(f"  {status} {feature}: {fill_rate:.2f}%")


# ============================================================================
# 便捷函数
# ============================================================================

def run_v28_pipeline(db_pool: SyncDatabasePool,
                    batch_size: int = 500,
                    rolling_window: int = 5) -> PipelineReport:
    """
    便捷函数：运行 V28.0 流水线

    Args:
        db_pool: SyncDatabasePool 实例
        batch_size: 批次大小
        rolling_window: 滚动窗口大小

    Returns:
        PipelineReport: 执行报告
    """
    config = PipelineConfig(
        batch_size=batch_size,
        rolling_window=rolling_window
    )

    pipeline = V28FeaturePipeline(db_pool, config)
    return pipeline.run_full_pipeline()
