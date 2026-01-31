"""
V41.500 Pipeline Integration - 自动化流水线集成
===============================================

功能：
1. 焊死 FeatureFactory 到数据采集流水线
2. 每场比赛采集完成后，自动生成 V41.500 特征
3. 将结果写入 golden_features 列

集成点：
- FotMobCoreCollector.save_extracted_features()
- 或独立的后处理钩子

Author: V41.500 Pipeline Team
Version: V41.500 "The Automated Pipeline"
Date: 2026-01-21
"""

from __future__ import annotations

import json
import logging
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
from src.processors.feature_factory import FeatureFactory, get_feature_factory

logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Integrator - 流水线集成器
# =============================================================================

class PipelineIntegrator:
    """
    V41.500 流水线集成器

    功能：
    1. 自动调用 FeatureFactory 生成特征
    2. 将特征合并到 golden_features
    3. 写入数据库

    使用方式：
        integrator = PipelineIntegrator()
        integrator.process_match(match_id)
    """

    def __init__(
        self,
        feature_factory: FeatureFactory | None = None
    ):
        """
        初始化流水线集成器

        Args:
            feature_factory: 特征工厂实例
        """
        self.feature_factory = feature_factory or get_feature_factory()
        self.settings = get_settings()

    def _get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.settings.database.host,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

    def _load_match_data(self, match_id: str) -> dict[str, Any] | None:
        """
        加载比赛数据（用于特征生成）

        Args:
            match_id: 比赛 ID

        Returns:
            比赛数据字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                match_id, league_name, season, home_team, away_team,
                match_date, actual_result, technical_features,
                golden_features, l2_raw_json
            FROM matches
            WHERE match_id = %s
        """

        cursor.execute(query, (match_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return dict(result) if result else None

    def process_match(
        self,
        match_id: str,
        verbose: bool = False
    ) -> bool:
        """
        处理单场比赛：生成 V41.500 特征并保存

        Args:
            match_id: 比赛 ID
            verbose: 是否打印详细日志

        Returns:
            是否成功
        """
        try:
            # 1. 加载比赛数据
            match_data = self._load_match_data(match_id)
            if not match_data:
                logger.warning(f"Match not found: {match_id}")
                return False

            # 2. 生成 V41.500 特征
            v41_500_features = self.feature_factory.process_match(
                match_data, verbose=verbose
            )

            if not v41_500_features:
                logger.warning(f"No V41.500 features generated for {match_id}")
                return False

            # 3. 合并到现有的 golden_features
            existing_golden = match_data.get("golden_features")
            if existing_golden and isinstance(existing_golden, str):
                try:
                    existing_golden = json.loads(existing_golden)
                except json.JSONDecodeError:
                    existing_golden = {}
            elif not existing_golden:
                existing_golden = {}

            # 合并特征（V41.500 特征优先级更高）
            merged_features = dict(existing_golden)
            merged_features.update(v41_500_features)
            merged_features["_meta"] = {
                **existing_golden.get("_meta", {}),
                "v41_500_generated": True,
                "v41_500_feature_count": len(v41_500_features),
                "v41_500_timestamp": str(get_settings().get_current_time()),
            }

            # 4. 保存到数据库
            return self._save_golden_features(match_id, merged_features)

        except Exception as e:
            logger.exception(f"Error processing match {match_id}: {e}")
            return False

    def _save_golden_features(
        self,
        match_id: str,
        golden_features: dict[str, Any]
    ) -> bool:
        """
        保存 golden_features 到数据库

        Args:
            match_id: 比赛 ID
            golden_features: 黄金特征字典

        Returns:
            是否成功
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
            UPDATE matches SET
                golden_features = %s::jsonb,
                updated_at = NOW()
            WHERE match_id = %s
            """

            cursor.execute(query, (json.dumps(golden_features), match_id))
            conn.commit()

            logger.info(f"V41.500 features saved for {match_id} ({len(golden_features)} features)")
            return True

        except Exception as e:
            if conn:
                conn.rollback()
            logger.exception(f"Failed to save golden_features for {match_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def process_batch(
        self,
        match_ids: list[str],
        verbose: bool = False
    ) -> dict[str, int]:
        """
        批量处理比赛

        Args:
            match_ids: 比赛 ID 列表
            verbose: 是否打印详细日志

        Returns:
            处理统计 {"success": X, "failed": Y}
        """
        success_count = 0
        failed_count = 0

        for i, match_id in enumerate(match_ids):
            if self.process_match(match_id, verbose=False):
                success_count += 1
            else:
                failed_count += 1

            if verbose and (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(match_ids)} matches")

        return {
            "success": success_count,
            "failed": failed_count,
            "total": len(match_ids)
        }

    def process_recent_matches(
        self,
        limit: int = 100,
        league_name: str | None = None
    ) -> dict[str, int]:
        """
        处理最近的比赛（重新生成 V41.500 特征）

        Args:
            limit: 处理数量
            league_name: 联赛名称（可选）

        Returns:
            处理统计
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT match_id
            FROM matches
            WHERE l2_raw_json IS NOT NULL
        """

        params = []
        if league_name:
            query += " AND league_name = %s"
            params.append(league_name)

        query += " ORDER BY collected_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        match_ids = [row["match_id"] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        logger.info(f"Found {len(match_ids)} matches to process")
        return self.process_batch(match_ids, verbose=True)

    def cleanup(self):
        """清理资源"""
        self.feature_factory.cleanup()


# =============================================================================
# Convenience Functions
# =============================================================================

def process_match_after_collection(match_id: str) -> bool:
    """
    数据采集完成后的钩子函数

    在 FotMobCoreCollector 或其他采集器中调用：

    >>> from src.collectors.v41_500_pipeline_integration import process_match_after_collection
    >>> process_match_after_collection(match_id)

    Args:
        match_id: 比赛 ID

    Returns:
        是否成功
    """
    integrator = PipelineIntegrator()
    try:
        return integrator.process_match(match_id)
    finally:
        integrator.cleanup()


def batch_process_matches(match_ids: list[str]) -> dict[str, int]:
    """
    批量处理比赛的便捷函数

    Args:
        match_ids: 比赛 ID 列表

    Returns:
        处理统计
    """
    integrator = PipelineIntegrator()
    try:
        return integrator.process_batch(match_ids, verbose=True)
    finally:
        integrator.cleanup()


# =============================================================================
# Main - 独立运行模式
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info("")
    logger.info("=" * 80)
    logger.info("V41.500 Pipeline Integration - 自动化流水线集成")
    logger.info("=" * 80)
    logger.info("")

    integrator = PipelineIntegrator()

    try:
        # 处理最近 100 场比赛
        logger.info("Processing recent 100 matches...")
        stats = integrator.process_recent_matches(limit=100)

        logger.info("")
        logger.info("=" * 80)
        logger.info("V41.500 Pipeline Processing Complete")
        logger.info("=" * 80)
        logger.info(f"  Success: {stats['success']}")
        logger.info(f"  Failed:  {stats['failed']}")
        logger.info(f"  Total:   {stats['total']}")
        logger.info("=" * 80)

    finally:
        integrator.cleanup()
