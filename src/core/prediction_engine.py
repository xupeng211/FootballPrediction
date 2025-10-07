"""
足球预测引擎核心模块
Football Prediction Engine Core Module

集成了机器学习模型、特征工程、数据收集和缓存管理，
提供高性能的比赛预测服务。

Integrates machine learning models, feature engineering, data collection,
and cache management to provide high-performance match prediction services.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_manager import RedisManager, CacheKeyManager
from src.collectors.fixtures_collector import FixturesCollector
from src.collectors.odds_collector import OddsCollector
from src.collectors.scores_collector import ScoresCollector
from src.database.connection import DatabaseManager
from src.database.models import (
    Match,
    MatchStatus,
    Prediction,
    Team,
    League,
    Features,
    Odds,
)
from src.features.feature_store import FootballFeatureStore
from src.models.prediction_service import PredictionService, PredictionResult
from src.monitoring.metrics_exporter import ModelMetricsExporter
from src.utils.retry import RetryConfig, retry

logger = logging.getLogger(__name__)


class PredictionEngine:
    """
    足球预测引擎主类
    Football Prediction Engine Main Class

    提供完整的比赛预测功能，包括：
    - 实时比赛预测
    - 批量预测处理
    - 模型性能监控
    - 缓存优化
    - 数据收集管道

    Provides complete match prediction functionality, including:
    - Real-time match prediction
    - Batch prediction processing
    - Model performance monitoring
    - Cache optimization
    - Data collection pipeline
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        redis_manager: Optional[RedisManager] = None,
        mlflow_tracking_uri: Optional[str] = None,
    ):
        """
        初始化预测引擎

        Args:
            db_manager: 数据库管理器
            redis_manager: Redis缓存管理器
            mlflow_tracking_uri: MLflow跟踪URI
        """
        self.db_manager = db_manager or DatabaseManager()
        self.redis_manager = redis_manager or RedisManager()
        self.cache_key_manager = CacheKeyManager()

        # 初始化MLflow URI
        self.mlflow_tracking_uri = mlflow_tracking_uri or os.getenv(
            "MLFLOW_TRACKING_URI", "http://localhost:5002"
        )

        # 初始化预测服务
        self.prediction_service = PredictionService(self.mlflow_tracking_uri)

        # 初始化特征存储
        self.feature_store = FootballFeatureStore()

        # 初始化数据收集器
        self.fixtures_collector = None  # 延迟初始化
        self.odds_collector = None
        self.scores_collector = None

        # 初始化指标导出器
        self.metrics_exporter = ModelMetricsExporter()

        # 配置参数
        self.max_concurrent_predictions = int(os.getenv("MAX_CONCURRENT_PREDICTIONS", "10"))
        self.prediction_timeout = float(os.getenv("PREDICTION_TIMEOUT", "30.0"))
        self.cache_warmup_enabled = os.getenv("CACHE_WARMUP_ENABLED", "true").lower() == "true"

        # 性能统计
        self.stats = {
            "total_predictions": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "prediction_errors": 0,
            "avg_prediction_time": 0.0,
        }

    async def _init_collectors(self):
        """延迟初始化数据收集器"""
        if self.fixtures_collector is None:
            async with self.db_manager.get_async_session() as session:
                self.fixtures_collector = FixturesCollector(session, self.redis_manager)
                self.odds_collector = OddsCollector(session, self.redis_manager)
                self.scores_collector = ScoresCollector(session, self.redis_manager)

    async def predict_match(
        self,
        match_id: int,
        force_refresh: bool = False,
        include_features: bool = False,
    ) -> Dict[str, Any]:
        """
        预测单场比赛结果

        Args:
            match_id: 比赛ID
            force_refresh: 是否强制刷新缓存
            include_features: 是否包含特征信息

        Returns:
            Dict[str, Any]: 预测结果
        """
        start_time = time.time()

        # 检查缓存
        cache_key = self.cache_key_manager.prediction_key(match_id)
        if not force_refresh:
            cached_result = await self.redis_manager.aget(cache_key)
            if cached_result:
                self.stats["cache_hits"] += 1
                if include_features and "features" not in cached_result:
                    cached_result["features"] = await self._get_match_features(match_id)
                return cached_result

        self.stats["cache_misses"] += 1

        try:
            # 获取比赛信息
            match_info = await self._get_match_info(match_id)
            if not match_info:
                raise ValueError(f"比赛 {match_id} 不存在")

            # 收集最新数据（如果需要）
            await self._collect_latest_data(match_id, match_info)

            # 执行预测
            prediction_result = await self.prediction_service.predict_match(match_id)

            # 构建响应
            result = {
                "match_id": match_id,
                "prediction": prediction_result.predicted_result,
                "probabilities": {
                    "home_win": prediction_result.home_win_probability,
                    "draw": prediction_result.draw_probability,
                    "away_win": prediction_result.away_win_probability,
                },
                "confidence": prediction_result.confidence_score,
                "model_version": prediction_result.model_version,
                "model_name": prediction_result.model_name,
                "prediction_time": prediction_result.created_at.isoformat(),
                "match_info": match_info,
            }

            # 添加特征信息（如果需要）
            if include_features:
                result["features"] = await self._get_match_features(match_id)

            # 添加赔率信息（如果有）
            odds_info = await self._get_match_odds(match_id)
            if odds_info:
                result["odds"] = odds_info

            # 缓存结果
            await self.redis_manager.aset(
                cache_key,
                result,
                ttl=self.cache_key_manager.get_ttl("predictions"),
            )

            # 更新统计
            self.stats["total_predictions"] += 1
            prediction_time = time.time() - start_time
            self.stats["avg_prediction_time"] = (
                self.stats["avg_prediction_time"] * (self.stats["total_predictions"] - 1) + prediction_time
            ) / self.stats["total_predictions"]

            logger.info(f"比赛 {match_id} 预测完成: {prediction_result.predicted_result} "
                       f"(置信度: {prediction_result.confidence_score:.3f}, "
                       f"耗时: {prediction_time:.3f}s)")

            return result

        except Exception as e:
            self.stats["prediction_errors"] += 1
            logger.error(f"预测比赛 {match_id} 失败: {e}")
            raise

    async def batch_predict(
        self,
        match_ids: List[int],
        force_refresh: bool = False,
        include_features: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        批量预测比赛结果

        Args:
            match_ids: 比赛ID列表
            force_refresh: 是否强制刷新缓存
            include_features: 是否包含特征信息

        Returns:
            List[Dict[str, Any]]: 预测结果列表
        """
        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent_predictions)

        async def predict_with_semaphore(match_id: int) -> Dict[str, Any]:
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        self.predict_match(match_id, force_refresh, include_features),
                        timeout=self.prediction_timeout,
                    )
                except asyncio.TimeoutError:
                    logger.error(f"预测比赛 {match_id} 超时")
                    return {
                        "match_id": match_id,
                        "error": "Prediction timeout",
                        "prediction": None,
                    }
                except Exception as e:
                    logger.error(f"预测比赛 {match_id} 失败: {e}")
                    return {
                        "match_id": match_id,
                        "error": str(e),
                        "prediction": None,
                    }

        # 并发执行所有预测
        tasks = [predict_with_semaphore(match_id) for match_id in match_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"预测比赛 {match_ids[i]} 出现异常: {result}")
                processed_results.append({
                    "match_id": match_ids[i],
                    "error": str(result),
                    "prediction": None,
                })
            else:
                processed_results.append(result)

        success_count = sum(1 for r in processed_results if "error" not in r)
        logger.info(f"批量预测完成: {success_count}/{len(match_ids)} 成功")

        return processed_results

    async def predict_upcoming_matches(
        self,
        hours_ahead: int = 24,
        league_ids: Optional[List[int]] = None,
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        预测即将开始的比赛

        Args:
            hours_ahead: 预测未来多少小时内的比赛
            league_ids: 联赛ID列表（None表示所有联赛）
            force_refresh: 是否强制刷新缓存

        Returns:
            List[Dict[str, Any]]: 预测结果列表
        """
        # 获取即将开始的比赛
        upcoming_matches = await self._get_upcoming_matches(hours_ahead, league_ids)

        if not upcoming_matches:
            logger.info("没有找到即将开始的比赛")
            return []

        # 提取比赛ID
        match_ids = [match["id"] for match in upcoming_matches]

        # 执行批量预测
        predictions = await self.batch_predict(match_ids, force_refresh)

        # 合并比赛信息和预测结果
        results = []
        for prediction in predictions:
            match_info = next(
                (m for m in upcoming_matches if m["id"] == prediction["match_id"]),
                None,
            )
            if match_info:
                result = {**match_info, **prediction}
                results.append(result)

        # 按比赛时间排序
        results.sort(key=lambda x: x.get("match_time", ""))

        logger.info(f"预测了 {len(results)} 场即将开始的比赛")
        return results

    async def get_prediction_accuracy(
        self,
        model_name: str = "football_baseline_model",
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        获取模型预测准确率

        Args:
            model_name: 模型名称
            days: 统计天数

        Returns:
            Dict[str, Any]: 准确率统计信息
        """
        return await self.prediction_service.get_model_accuracy(model_name, days)

    async def verify_predictions(self, match_ids: List[int]) -> Dict[str, Any]:
        """
        验证预测结果（比赛结束后调用）

        Args:
            match_ids: 要验证的比赛ID列表

        Returns:
            Dict[str, Any]: 验证结果统计
        """
        stats = {
            "total_matches": len(match_ids),
            "verified": 0,
            "correct": 0,
            "incorrect": 0,
            "accuracy": 0.0,
        }

        for match_id in match_ids:
            try:
                success = await self.prediction_service.verify_prediction(match_id)
                if success:
                    stats["verified"] += 1
                    # 获取验证结果
                    async with self.db_manager.get_async_session() as session:
                        query = select(Prediction).where(
                            Prediction.match_id == match_id,
                            Prediction.is_correct.isnot(None),
                        )
                        result = await session.execute(query)
                        prediction = result.scalar_one_or_none()
                        if prediction:
                            if prediction.is_correct:
                                stats["correct"] += 1
                            else:
                                stats["incorrect"] += 1
            except Exception as e:
                logger.error(f"验证比赛 {match_id} 预测失败: {e}")

        if stats["verified"] > 0:
            stats["accuracy"] = stats["correct"] / stats["verified"]

        logger.info(f"预测验证完成: {stats['correct']}/{stats['verified']} 正确 "
                   f"(准确率: {stats['accuracy']:.2%})")

        return stats

    async def _get_match_info(self, match_id: int) -> Optional[Dict[str, Any]]:
        """获取比赛基本信息"""
        async with self.db_manager.get_async_session() as session:
            query = select(
                Match.id,
                Match.home_team_id,
                Match.away_team_id,
                Match.league_id,
                Match.match_time,
                Match.match_status,
                Match.venue,
                Team.team_name.label("home_team_name"),
                Team.team_name.label("away_team_name"),
                League.league_name,
            ).select_from(
                Match.join(Team, Match.home_team_id == Team.id)
                .join(Team, Match.away_team_id == Team.id, isouter=True)
                .join(League, Match.league_id == League.id, isouter=True)
            ).where(Match.id == match_id)

            result = await session.execute(query)
            match = result.first()

            if match:
                return {
                    "id": match.id,
                    "home_team_id": match.home_team_id,
                    "away_team_id": match.away_team_id,
                    "league_id": match.league_id,
                    "match_time": match.match_time.isoformat(),
                    "match_status": match.match_status.value,
                    "venue": match.venue,
                    "home_team": match.home_team_name,
                    "away_team": match.away_team_name,
                    "league": match.league_name,
                }
            return None

    async def _get_match_features(self, match_id: int) -> Optional[Dict[str, Any]]:
        """获取比赛特征"""
        try:
            async with self.db_manager.get_async_session() as session:
                query = select(Features).where(Features.match_id == match_id)
                result = await session.execute(query)
                features = result.scalar_one_or_none()

                if features:
                    return {
                        "home_recent_wins": features.home_recent_wins,
                        "home_recent_goals_for": features.home_recent_goals_for,
                        "home_recent_goals_against": features.home_recent_goals_against,
                        "away_recent_wins": features.away_recent_wins,
                        "away_recent_goals_for": features.away_recent_goals_for,
                        "away_recent_goals_against": features.away_recent_goals_against,
                        "h2h_home_advantage": features.h2h_home_advantage,
                        "home_implied_probability": features.home_implied_probability,
                        "draw_implied_probability": features.draw_implied_probability,
                        "away_implied_probability": features.away_implied_probability,
                    }
                return None
        except Exception as e:
            logger.error(f"获取比赛 {match_id} 特征失败: {e}")
            return None

    async def _get_match_odds(self, match_id: int) -> Optional[Dict[str, Any]]:
        """获取比赛赔率信息"""
        try:
            async with self.db_manager.get_async_session() as session:
                query = select(Odds).where(
                    Odds.match_id == match_id,
                    Odds.market_type == "match_winner",
                ).order_by(Odds.created_at.desc())

                result = await session.execute(query)
                odds = result.scalar_one_or_none()

                if odds:
                    return {
                        "home_win": odds.home_win_odds,
                        "draw": odds.draw_odds,
                        "away_win": odds.away_win_odds,
                        "bookmaker": odds.bookmaker,
                        "last_updated": odds.created_at.isoformat(),
                    }
                return None
        except Exception as e:
            logger.error(f"获取比赛 {match_id} 赔率失败: {e}")
            return None

    async def _collect_latest_data(self, match_id: int, match_info: Dict[str, Any]):
        """收集最新数据（如果需要）"""
        await self._init_collectors()

        # 如果比赛即将开始（2小时内），收集最新数据
        match_time = datetime.fromisoformat(match_info["match_time"])
        if match_time - datetime.now() <= timedelta(hours=2):
            try:
                # 收集最新赔率
                if self.odds_collector:
                    await self.odds_collector.collect_match_odds(match_id)

                # 如果比赛进行中，收集实时比分
                if match_info["match_status"] in ["in_progress", "paused"]:
                    if self.scores_collector:
                        await self.scores_collector.collect_match_score(match_id)
            except Exception as e:
                logger.warning(f"收集比赛 {match_id} 最新数据失败: {e}")

    async def _get_upcoming_matches(
        self,
        hours_ahead: int,
        league_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """获取即将开始的比赛列表"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=hours_ahead)

        async with self.db_manager.get_async_session() as session:
            query = select(
                Match.id,
                Match.home_team_id,
                Match.away_team_id,
                Match.league_id,
                Match.match_time,
                Match.match_status,
                Team.team_name.label("home_team_name"),
                Team.team_name.label("away_team_name"),
                League.league_name,
            ).select_from(
                Match.join(Team, Match.home_team_id == Team.id)
                .join(Team, Match.away_team_id == Team.id, isouter=True)
                .join(League, Match.league_id == League.id, isouter=True)
            ).where(
                Match.match_time >= start_time,
                Match.match_time <= end_time,
                Match.match_status == MatchStatus.SCHEDULED,
            )

            if league_ids:
                query = query.where(Match.league_id.in_(league_ids))

            query = query.order_by(Match.match_time)

            result = await session.execute(query)
            matches = result.all()

            return [
                {
                    "id": match.id,
                    "home_team_id": match.home_team_id,
                    "away_team_id": match.away_team_id,
                    "league_id": match.league_id,
                    "match_time": match.match_time.isoformat(),
                    "match_status": match.match_status.value,
                    "home_team": match.home_team_name,
                    "away_team": match.away_team_name,
                    "league": match.league_name,
                }
                for match in matches
            ]

    async def warmup_cache(self, hours_ahead: int = 24) -> Dict[str, int]:
        """
        预热缓存

        Args:
            hours_ahead: 预热未来多少小时内的比赛缓存

        Returns:
            Dict[str, int]: 预热统计
        """
        if not self.cache_warmup_enabled:
            logger.info("缓存预热已禁用")
            return {"skipped": 0, "warmed_up": 0}

        # 获取即将开始的比赛
        upcoming_matches = await self._get_upcoming_matches(hours_ahead)

        stats = {"skipped": 0, "warmed_up": 0}

        for match in upcoming_matches:
            match_id = match["id"]
            cache_key = self.cache_key_manager.prediction_key(match_id)

            # 检查是否已有缓存
            if await self.redis_manager.aexists(cache_key):
                stats["skipped"] += 1
                continue

            try:
                # 预热预测缓存
                await self.predict_match(match_id, force_refresh=False)
                stats["warmed_up"] += 1

                # 预热比赛信息缓存
                info_key = self.cache_key_manager.build_key("match", match_id, "info")
                await self.redis_manager.aset(
                    info_key,
                    match,
                    ttl=self.cache_key_manager.get_ttl("match_info"),
                )
            except Exception as e:
                logger.error(f"预热比赛 {match_id} 缓存失败: {e}")

        logger.info(f"缓存预热完成: {stats['warmed_up']} 个新缓存, "
                   f"{stats['skipped']} 个已有缓存")

        return stats

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取引擎性能统计"""
        return {
            **self.stats,
            "cache_hit_rate": (
                self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"])
                if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0
                else 0.0
            ),
            "error_rate": (
                self.stats["prediction_errors"] / self.stats["total_predictions"]
                if self.stats["total_predictions"] > 0
                else 0.0
            ),
        }

    async def clear_cache(self, pattern: str = "predictions:*") -> int:
        """
        清理缓存

        Args:
            pattern: 缓存键模式

        Returns:
            int: 清理的键数量
        """
        try:
            keys = await self.redis_manager.client.keys(pattern)
            if keys:
                deleted = await self.redis_manager.adelete(*keys)
                logger.info(f"清理了 {deleted} 个缓存键")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return 0

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            Dict[str, Any]: 健康状态
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {},
        }

        # 检查数据库连接
        try:
            async with self.db_manager.get_async_session() as session:
                await session.execute(text("SELECT 1"))
            health_status["components"]["database"] = "healthy"
        except Exception as e:
            health_status["components"]["database"] = f"unhealthy: {e}"
            health_status["status"] = "degraded"

        # 检查Redis连接
        try:
            await self.redis_manager.aping()
            health_status["components"]["redis"] = "healthy"
        except Exception as e:
            health_status["components"]["redis"] = f"unhealthy: {e}"
            health_status["status"] = "degraded"

        # 检查MLflow连接
        try:
            await self.prediction_service.get_production_model()
            health_status["components"]["mlflow"] = "healthy"
        except Exception as e:
            health_status["components"]["mlflow"] = f"unhealthy: {e}"
            health_status["status"] = "degraded"

        return health_status

    async def close(self):
        """关闭引擎，释放资源"""
        try:
            await self.redis_manager.aclose()
            logger.info("预测引擎已关闭")
        except Exception as e:
            logger.error(f"关闭预测引擎失败: {e}")


# 全局引擎实例
_engine: Optional[PredictionEngine] = None


async def get_prediction_engine() -> PredictionEngine:
    """获取全局预测引擎实例"""
    global _engine
    if _engine is None:
        _engine = PredictionEngine()
    return _engine


async def init_prediction_engine():
    """初始化全局预测引擎"""
    global _engine
    if _engine is None:
        _engine = PredictionEngine()
        # 可选：预热缓存
        await _engine.warmup_cache()
    return _engine


async def close_prediction_engine():
    """关闭全局预测引擎"""
    global _engine
    if _engine:
        await _engine.close()
        _engine = None