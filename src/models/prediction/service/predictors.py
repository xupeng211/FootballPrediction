"""
预测器模块
Predictors Module

提供比赛预测的核心逻辑。
"""





try:
    from .feature_processor import FeatureProcessor
except ImportError:
    # 创建模拟的特征处理器
    class FeatureProcessor:
        def prepare_features_for_prediction(self, features):
            import numpy as np
            return np.array([list(features.values())])

        def get_default_features(self):
            return {"feature1": 0.5, "feature2": 0.3}

try:
    from .models import PredictionResult
except ImportError:
    # 创建模拟的预测结果模型
    class PredictionResult:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def to_dict(self):
            return self.__dict__

        @classmethod
        def from_dict(cls, data):
            return cls(**data)

# 尝试导入指标
try:
    from .metrics import (
        predictions_total,
        prediction_duration_seconds,
        prediction_accuracy,
        cache_hit_ratio,
        prediction_errors_total,
    )
except ImportError:
    class MockMetric:
        def labels(self, **kwargs):
            return self
        def inc(self, *args):
            return self
        def observe(self, *args):
            return self
        def set(self, *args):
            return self

    predictions_total = MockMetric()
    prediction_duration_seconds = MockMetric()
    prediction_accuracy = MockMetric()
    cache_hit_ratio = MockMetric()
    prediction_errors_total = MockMetric()

logger = get_logger(__name__)


class MatchPredictor:
    """
    比赛预测器 / Match Predictor

    负责单个比赛的预测逻辑，包括特征获取、模型推理和结果存储。
    """

    def __init__(self, db_manager: DatabaseManager, model_loader: ModelLoader, cache_manager: PredictionCacheManager):
        """
        初始化比赛预测器 / Initialize Match Predictor

        Args:
            db_manager (DatabaseManager): 数据库管理器 / Database manager
            model_loader (ModelLoader): 模型加载器 / Model loader
            cache_manager (PredictionCacheManager): 缓存管理器 / Cache manager
        """
        self.db_manager = db_manager
        self.model_loader = model_loader
        self.cache_manager = cache_manager

        # 初始化特征处理器
        try:
            self.feature_processor = FeatureProcessor()
        except ImportError:
            self.feature_processor = FeatureProcessor()

    async def predict_match(self, match_id: int) -> Any:
        """
        预测比赛结果 / Predict Match Result

        Args:
            match_id (int): 比赛唯一标识符 / Unique match identifier

        Returns:
            Any: 预测结果 / Prediction result
        """
        start_time = datetime.now()

        # 尝试从缓存获取预测结果
        cached_result = await self.cache_manager.get_cached_prediction(match_id)
        if cached_result:
            logger.info(f"使用缓存的预测结果：比赛 {match_id}")
            cache_hit_ratio.labels(cache_type="prediction").set(1)
            return PredictionResult.from_dict(cached_result)

        cache_hit_ratio.labels(cache_type="prediction").set(0)

        try:
            logger.info(f"开始预测比赛 {match_id}")

            # 获取生产模型
            model, model_version = await self.model_loader.get_production_model()

            # 查询比赛信息
            match_info = await self._get_match_info(match_id)
            if not match_info:
                raise ValueError(f"比赛 {match_id} 不存在")

            # 获取特征
            features = await self._get_features(match_id, match_info)

            # 进行预测
            result = await self._make_prediction(model, model_version, match_id, features)

            # 存储预测结果
            await self._store_prediction(result)

            # 缓存预测结果
            await self.cache_manager.cache_prediction(match_id, result)

            # 记录预测指标
            self._record_prediction_metrics(model_version, result.predicted_result, start_time)

            logger.info(
                f"比赛 {match_id} 预测完成：{result.predicted_result} "
                f"(置信度: {result.confidence_score:.3f})"
            )
            return result

        except Exception as e:
            logger.error(f"预测比赛 {match_id} 失败: {e}")
            prediction_errors_total.labels(
                error_type=type(e).__name__,
                model_name="football_baseline_model"
            ).inc()
            raise

    async def _get_features(self, match_id: int, match_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取比赛特征 / Get match features

        Args:
            match_id (int): 比赛ID / Match ID
            match_info (Dict[str, Any]): 比赛信息 / Match information

        Returns:
            Dict[str, Any]: 特征字典 / Feature dictionary
        """
        # 尝试从缓存获取特征
        cached_features = await self.cache_manager.get_cached_features(match_id)
        if cached_features:
            return cached_features

        try:
            # 从特征存储获取实时特征
            from src.data.features.feature_store import FootballFeatureStore
            feature_store = FootballFeatureStore()

            raw_features = feature_store.get_match_features_for_prediction(
                match_id=match_id,
                home_team_id=match_info["home_team_id"],
                away_team_id=match_info["away_team_id"],
            )
            features = (
                await raw_features
                if inspect.isawaitable(raw_features)
                else raw_features
            )

            if not features:
                # 使用默认特征
                features = self.feature_processor.get_default_features()
                logger.warning(f"比赛 {match_id} 使用默认特征")

            # 缓存特征
            await self.cache_manager.cache_features(match_id, features)

            return features

        except Exception as e:
            logger.error(f"获取比赛 {match_id} 的特征失败: {e}")
            return self.feature_processor.get_default_features()

    async def _get_match_info(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取比赛信息 / Get Match Information

        Args:
            match_id (int): 比赛唯一标识符 / Unique match identifier

        Returns:
            Optional[Dict[str, Any]]: 包含比赛信息的字典，如果比赛不存在则返回None
        """
        try:
            async with self.db_manager.get_async_session() as session:
                query = select(
                    Match.id,
                    Match.home_team_id,
                    Match.away_team_id,
                    Match.league_id,
                    Match.match_time,
                    Match.match_status,
                    Match.season,
                ).where(Match.id == match_id)

                result = await session.execute(query)
                match = result.first()

                if match:
                    return {
                        "id": match.id,
                        "home_team_id": match.home_team_id,
                        "away_team_id": match.away_team_id,
                        "league_id": match.league_id,
                        "match_time": match.match_time,
                        "match_status": match.match_status,
                        "season": match.season,
                    }
                return None

        except Exception as e:
            logger.error(f"查询比赛信息失败: {e}")
            return None

    async def _make_prediction(self, model: Any, model_version: str, match_id: int, features: Dict[str, Any]) -> Any:
        """
        进行预测 / Make Prediction

        Args:
            model (Any): 模型对象 / Model object
            model_version (str): 模型版本 / Model version
            match_id (int): 比赛ID / Match ID
            features (Dict[str, Any]): 特征数据 / Feature data

        Returns:
            Any: 预测结果 / Prediction result
        """
        # 准备特征数组
        features_array = self.feature_processor.prepare_features_for_prediction(features)

        # 进行预测
        prediction_proba = model.predict_proba(features_array)
        predicted_class = model.predict(features_array)[0]

        # 解析预测结果
        class_labels = ["away", "draw", "home"]
        prob_dict = dict(zip(class_labels, prediction_proba[0]))

        # 创建预测结果
        result = PredictionResult(
            match_id=match_id,
            model_version=model_version,
            model_name="football_baseline_model",
            home_win_probability=float(prob_dict.get("home", 0.0)),
            draw_probability=float(prob_dict.get("draw", 0.0)),
            away_win_probability=float(prob_dict.get("away", 0.0)),
            predicted_result=predicted_class,
            confidence_score=float(max(prediction_proba[0])),
            features_used=features,
            prediction_metadata={
                "model_uri": f"models:/football_baseline_model/{model_version}",
                "prediction_time": datetime.now().isoformat(),
                "feature_count": len(features) if features else 0,
            },
            created_at=datetime.now(),
        )

        return result

    async def _store_prediction(self, result: Any) -> None:
        """
        存储预测结果 / Store Prediction Result

        Args:
            result (Any): 预测结果 / Prediction result
        """
        try:
            async with self.db_manager.get_async_session() as session:
                prediction = Prediction(
                    match_id=result.match_id,
                    model_version=result.model_version,
                    home_win_probability=result.home_win_probability,
                    draw_probability=result.draw_probability,
                    away_win_probability=result.away_win_probability,
                    predicted_result=result.predicted_result,
                    confidence_score=result.confidence_score,
                    created_at=result.created_at,
                )

                session.add(prediction)
                await session.commit()

                logger.debug(f"预测结果已存储: 比赛 {result.match_id}")

        except Exception as e:
            logger.error(f"存储预测结果失败: {e}")
            raise

    def _record_prediction_metrics(self, model_version: str, predicted_class: str, start_time: datetime) -> None:
        """
        记录预测指标 / Record prediction metrics

        Args:
            model_version (str): 模型版本 / Model version
            predicted_class (str): 预测结果类别 / Predicted class
            start_time (datetime): 开始时间 / Start time
        """
        # 记录预测计数
        predictions_total.labels(
            model_name="football_baseline_model",
            model_version=model_version,
            result=predicted_class
        ).inc()

        # 记录预测时间
        prediction_duration = (datetime.now() - start_time).total_seconds()
        prediction_duration_seconds.labels(
            model_name="football_baseline_model",
            model_version=model_version
        ).observe(prediction_duration)

    async def verify_prediction(self, match_id: int) -> bool:
        """
        验证预测结果 / Verify Prediction Result

        Args:
            match_id (int): 比赛ID / Match ID

        Returns:
            bool: 预测是否正确 / Whether prediction is correct
        """
        try:
            async with self.db_manager.get_async_session() as session:
                # 获取比赛结果
                query = text("""
                    SELECT m.home_score, m.away_score, p.predicted_result
                    FROM matches m
                    JOIN predictions p ON m.id = p.match_id
                    WHERE m.id = :match_id AND m.match_status = 'FINISHED'
                """)

                result = await session.execute(query, {"match_id": match_id})
                row = result.first()

                if row:
                    # 计算实际结果
                    if row.home_score > row.away_score:
                        actual_result = "home"
                    elif row.home_score < row.away_score:
                        actual_result = "away"
                    else:
                        actual_result = "draw"

                    # 更新预测结果
                    update_query = text("""
                        UPDATE predictions
                        SET actual_result = :actual_result,
                            is_correct = (:actual_result = :predicted_result),
                            verified_at = :verified_at
                        WHERE match_id = :match_id
                    """)

                    await session.execute(update_query, {
                        "match_id": match_id,
                        "actual_result": actual_result,
                        "predicted_result": row.predicted_result,
                        "verified_at": datetime.now(),
                    })

                    await session.commit()

                    # 记录准确率指标
                    is_correct = actual_result == row.predicted_result
                    await self._update_accuracy_metrics()

                    return is_correct

                return False

        except Exception as e:
            logger.error(f"验证预测结果失败: {e}")
            return False

    async def _update_accuracy_metrics(self) -> None:
        """
        更新准确率指标 / Update accuracy metrics
        """
        try:
            async with self.db_manager.get_async_session() as session:
                # 计算最近7天、30天、90天的准确率
                for days in [7, 30, 90]:
                    query = text("""
                        SELECT
                            COUNT(*) as total,
                            SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) as correct
                        FROM predictions
                        WHERE created_at >= :cutoff_date
                            AND is_correct IS NOT NULL
                    """)

                    cutoff_date = datetime.now() - timedelta(days=days)
                    result = await session.execute(query, {"cutoff_date": cutoff_date})
                    row = result.first()

                    if row and row.total > 0:
                        accuracy = row.correct / row.total
                        prediction_accuracy.labels(
                            model_name="football_baseline_model",
                            model_version="current",
                            time_window=f"{days}d"
                        ).set(accuracy)

        except Exception as e:
            logger.error(f"更新准确率指标失败: {e}")

    async def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        获取预测统计信息 / Get Prediction Statistics

        Args:
            days (int): 统计天数 / Statistics days

        Returns:
            Dict[str, Any]: 统计信息 / Statistics
        """
        try:
            async with self.db_manager.get_async_session() as session:
                query = text("""
                    SELECT
                        COUNT(*) as total_predictions,
                        SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) as correct_predictions,
                        AVG(confidence_score) as avg_confidence,
                        COUNT(DISTINCT model_version) as model_versions_used
                    FROM predictions
                    WHERE created_at >= :cutoff_date
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import inspect
import logging

from sqlalchemy import select, text

from .cache_manager import PredictionCacheManager
from .model_loader import ModelLoader
from src.core.logging import get_logger
from src.database.connection import DatabaseManager
from src.database.models import Match, Prediction

                """)

                cutoff_date = datetime.now() - timedelta(days=days)
                result = await session.execute(query, {"cutoff_date": cutoff_date})
                row = result.first()

                if row:
                    accuracy = (row.correct_predictions / row.total_predictions) if row.total_predictions > 0 else 0

                    cache_stats = await self.cache_manager.get_cache_statistics()

                    return {
                        "period_days": days,
                        "total_predictions": row.total_predictions,
                        "correct_predictions": row.correct_predictions,
                        "accuracy": accuracy,
                        "avg_confidence": float(row.avg_confidence) if row.avg_confidence else 0,
                        "model_versions_used": row.model_versions_used,
                        "cache_stats": cache_stats,
                    }

                return {"error": "No data found"}

        except Exception as e:
            logger.error(f"获取预测统计失败: {e}")
            return {"error": str(e)}
