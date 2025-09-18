"""
模型预测服务

提供实时比赛预测功能，支持：
- 从MLflow加载最新生产模型
- 实时特征获取和预测
- 预测结果存储到数据库
- Prometheus指标导出
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import mlflow.sklearn
import numpy as np
from sqlalchemy import select, text

import mlflow
from mlflow import MlflowClient
from src.database.connection import DatabaseManager
from src.database.models import Match, Prediction
from src.features.feature_store import FootballFeatureStore

from .metrics_exporter import ModelMetricsExporter

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """预测结果数据类"""

    match_id: int
    model_version: str
    model_name: str = "football_baseline_model"

    # 预测概率
    home_win_probability: float = 0.0
    draw_probability: float = 0.0
    away_win_probability: float = 0.0

    # 预测结果
    predicted_result: str = "draw"  # 'home', 'draw', 'away'
    confidence_score: float = 0.0

    # 元数据
    features_used: Optional[Dict[str, Any]] = None
    prediction_metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    # 结果验证（比赛结束后更新）
    actual_result: Optional[str] = None
    is_correct: Optional[bool] = None
    verified_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "match_id": self.match_id,
            "model_version": self.model_version,
            "model_name": self.model_name,
            "home_win_probability": self.home_win_probability,
            "draw_probability": self.draw_probability,
            "away_win_probability": self.away_win_probability,
            "predicted_result": self.predicted_result,
            "confidence_score": self.confidence_score,
            "features_used": self.features_used,
            "prediction_metadata": self.prediction_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "actual_result": self.actual_result,
            "is_correct": self.is_correct,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }


class PredictionService:
    """
    预测服务

    提供实时比赛预测功能，支持：
    - 从MLflow加载最新生产模型
    - 实时特征获取和预测
    - 预测结果存储到数据库
    - Prometheus指标导出
    """

    def __init__(self, mlflow_tracking_uri: str = "http://localhost:5002"):
        """
        初始化预测服务

        Args:
            mlflow_tracking_uri: MLflow跟踪服务器URI
        """
        self.db_manager = DatabaseManager()
        self.feature_store = FootballFeatureStore()
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.metrics_exporter = ModelMetricsExporter()

        # 设置MLflow跟踪URI
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)

        # 模型缓存
        self.model_cache: Dict[str, Any] = {}
        self.model_metadata_cache: Dict[str, Dict[str, Any]] = {}

        # 定义模型预期的特征顺序
        self.feature_order: List[str] = [
            "home_team_form",
            "away_team_form",
            "head_to_head_ratio",
            "home_goals_avg",
            "away_goals_avg",
            "home_defense_rating",
            "away_defense_rating",
            "recent_performance_home",
            "recent_performance_away",
        ]

    async def get_production_model(
        self, model_name: str = "football_baseline_model"
    ) -> Tuple[Any, str]:
        """
        获取生产环境模型

        Args:
            model_name: 模型名称

        Returns:
            (模型对象, 模型版本)
        """
        try:
            client = MlflowClient(tracking_uri=self.mlflow_tracking_uri)

            # 获取生产阶段的最新模型
            production_versions = client.get_latest_versions(
                name=model_name, stages=["Production"]
            )

            if not production_versions:
                # 如果没有生产版本，尝试获取Staging版本
                staging_versions = client.get_latest_versions(
                    name=model_name, stages=["Staging"]
                )
                if not staging_versions:
                    # 如果也没有Staging版本，获取最新版本
                    all_versions = client.get_latest_versions(name=model_name)
                    if not all_versions:
                        raise ValueError(f"模型 {model_name} 没有可用版本")
                    model_version_info = all_versions[0]
                    logger.warning(f"使用最新版本 {model_version_info.version}，建议推广模型到生产环境")
                else:
                    model_version_info = staging_versions[0]
                    logger.warning(
                        f"使用Staging版本 {model_version_info.version}，建议推广到生产环境"
                    )
            else:
                model_version_info = production_versions[0]
                logger.info(f"使用生产版本 {model_version_info.version}")

            version = model_version_info.version

            # 构建模型URI
            model_uri = f"models:/{model_name}/{version}"

            # 检查缓存
            if model_uri in self.model_cache:
                logger.debug(f"从缓存加载模型 {model_uri}")
                return self.model_cache[model_uri], version

            # 加载模型
            start_time = datetime.now()
            model = mlflow.sklearn.load_model(model_uri)
            load_duration = (datetime.now() - start_time).total_seconds()

            # 记录加载时间
            self.metrics_exporter.model_load_duration.labels(
                model_name=model_name, model_version=version
            ).observe(load_duration)

            # 缓存模型
            self.model_cache[model_uri] = model
            self.model_metadata_cache[model_uri] = {
                "name": model_name,
                "version": version,
                "stage": model_version_info.current_stage,
                "loaded_at": datetime.now(),
            }

            logger.info(f"成功加载模型 {model_name} 版本 {version}")
            return model, version

        except Exception as e:
            logger.error(f"加载生产模型失败: {e}")
            raise

    async def predict_match(self, match_id: int) -> PredictionResult:
        """
        预测比赛结果

        Args:
            match_id: 比赛ID

        Returns:
            预测结果
        """
        start_time = datetime.now()

        try:
            logger.info(f"开始预测比赛 {match_id}")

            # 获取生产模型
            model, model_version = await self.get_production_model()

            # 查询比赛信息
            match_info = await self._get_match_info(match_id)
            if not match_info:
                raise ValueError(f"比赛 {match_id} 不存在")

            # 从特征存储获取实时特征
            features = await self.feature_store.get_match_features_for_prediction(
                match_id=match_id,
                home_team_id=match_info["home_team_id"],
                away_team_id=match_info["away_team_id"],
            )

            if not features:
                logger.warning(f"比赛 {match_id} 无法获取特征，使用默认特征")
                features = self._get_default_features()

            # 准备特征数组
            features_array = self._prepare_features_for_prediction(features)

            # 进行预测
            prediction_proba = model.predict_proba(features_array)
            predicted_class = model.predict(features_array)[0]

            # 解析预测结果
            # XGBoost分类器的类别顺序通常是按字母顺序：['away', 'draw', 'home']
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

            # 存储预测结果
            await self._store_prediction(result)

            # 导出指标
            await self.metrics_exporter.export_prediction_metrics(result)

            # 记录预测时间
            prediction_duration = (datetime.now() - start_time).total_seconds()
            self.metrics_exporter.prediction_duration.labels(
                model_name="football_baseline_model", model_version=model_version
            ).observe(prediction_duration)

            logger.info(
                f"比赛 {match_id} 预测完成：{predicted_class} (置信度: {result.confidence_score:.3f})"
            )
            return result

        except Exception as e:
            logger.error(f"预测比赛 {match_id} 失败: {e}")
            raise

    async def _get_match_info(self, match_id: int) -> Optional[Dict[str, Any]]:
        """获取比赛信息"""
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

    def _get_default_features(self) -> Dict[str, Any]:
        """获取默认特征（当特征服务不可用时）"""
        return {
            "home_recent_wins": 2,
            "home_recent_goals_for": 6,
            "home_recent_goals_against": 4,
            "away_recent_wins": 2,
            "away_recent_goals_for": 5,
            "away_recent_goals_against": 5,
            "h2h_home_advantage": 0.5,
            "home_implied_probability": 0.4,
            "draw_implied_probability": 0.3,
            "away_implied_probability": 0.3,
        }

    def _prepare_features_for_prediction(self, features: Dict[str, Any]) -> np.ndarray:
        """准备用于预测的特征数组"""
        # 定义特征顺序（应该与训练时保持一致）
        feature_order = [
            "home_recent_wins",
            "home_recent_goals_for",
            "home_recent_goals_against",
            "away_recent_wins",
            "away_recent_goals_for",
            "away_recent_goals_against",
            "h2h_home_advantage",
            "home_implied_probability",
            "draw_implied_probability",
            "away_implied_probability",
        ]

        # 构建特征数组
        feature_values = []
        for feature_name in feature_order:
            value = features.get(feature_name, 0.0)
            feature_values.append(float(value))

        return np.array([feature_values])

    async def _store_prediction(self, result: PredictionResult) -> None:
        """存储预测结果到数据库"""
        async with self.db_manager.get_async_session() as session:
            try:
                prediction = Prediction(
                    match_id=result.match_id,
                    model_version=result.model_version,
                    model_name=result.model_name,
                    home_win_probability=result.home_win_probability,
                    draw_probability=result.draw_probability,
                    away_win_probability=result.away_win_probability,
                    predicted_result=result.predicted_result,
                    confidence_score=result.confidence_score,
                    features_used=result.features_used,
                    prediction_metadata=result.prediction_metadata,
                    created_at=result.created_at or datetime.now(),
                )

                session.add(prediction)
                await session.commit()
                logger.debug(f"预测结果已存储到数据库：比赛 {result.match_id}")

            except Exception as e:
                await session.rollback()
                logger.error(f"存储预测结果失败: {e}")
                raise

    async def verify_prediction(self, match_id: int) -> bool:
        """
        验证预测结果（比赛结束后调用）

        Args:
            match_id: 比赛ID

        Returns:
            是否验证成功
        """
        try:
            async with self.db_manager.get_async_session() as session:
                # 获取比赛实际结果
                match_query = select(
                    Match.id, Match.home_score, Match.away_score, Match.match_status
                ).where(Match.id == match_id, Match.match_status == "completed")

                match_result = await session.execute(match_query)
                match = match_result.first()

                if not match:
                    logger.warning(f"比赛 {match_id} 未完成或不存在")
                    return False

                # 计算实际结果
                actual_result = self._calculate_actual_result(
                    match.home_score, match.away_score
                )

                # 更新预测记录
                update_query = text(
                    """
                    UPDATE predictions
                    SET actual_result = :actual_result,
                        is_correct = (predicted_result = :actual_result),
                        verified_at = :verified_at
                    WHERE match_id = :match_id
                      AND actual_result IS NULL
                """
                )

                await session.execute(
                    update_query,
                    {
                        "actual_result": actual_result,
                        "match_id": match_id,
                        "verified_at": datetime.now(),
                    },
                )

                await session.commit()
                logger.info(f"比赛 {match_id} 预测结果已验证：实际结果 {actual_result}")
                return True

        except Exception as e:
            logger.error(f"验证预测结果失败: {e}")
            return False

    def _calculate_actual_result(self, home_score: int, away_score: int) -> str:
        """计算实际比赛结果"""
        if home_score > away_score:
            return "home"
        elif home_score < away_score:
            return "away"
        else:
            return "draw"

    async def get_model_accuracy(
        self, model_name: str = "football_baseline_model", days: int = 7
    ) -> Optional[float]:
        """
        获取模型准确率

        Args:
            model_name: 模型名称
            days: 计算天数

        Returns:
            准确率（0-1之间）
        """
        try:
            async with self.db_manager.get_async_session() as session:
                # 查询最近N天已验证的预测
                query = text(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) as correct
                    FROM predictions
                    WHERE model_name = :model_name
                      AND is_correct IS NOT NULL
                      AND created_at >= NOW() - INTERVAL ':days days'
                """
                )

                result = await session.execute(
                    query, {"model_name": model_name, "days": days}
                )

                row = result.first()
                if row and row.total > 0:
                    accuracy = row.correct / row.total
                    logger.info(
                        f"模型 {model_name} 最近 {days} 天准确率: {accuracy:.3f} ({row.correct}/{row.total})"
                    )
                    return accuracy

                return None

        except Exception as e:
            logger.error(f"获取模型准确率失败: {e}")
            return None

    async def batch_predict_matches(
        self, match_ids: List[int]
    ) -> List[PredictionResult]:
        """
        批量预测比赛结果

        Args:
            match_ids: 比赛ID列表

        Returns:
            预测结果列表
        """
        results = []

        # 获取生产模型（只加载一次）
        model, model_version = await self.get_production_model()

        for match_id in match_ids:
            try:
                result = await self.predict_match(match_id)
                results.append(result)
            except Exception as e:
                logger.error(f"批量预测中，比赛 {match_id} 预测失败: {e}")
                continue

        logger.info(f"批量预测完成：{len(results)}/{len(match_ids)} 场比赛预测成功")
        return results

    async def get_prediction_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        获取预测统计信息

        Args:
            days: 统计天数

        Returns:
            统计信息字典
        """
        try:
            async with self.db_manager.get_async_session() as session:
                query = text(
                    """
                    SELECT
                        model_version,
                        COUNT(*) as total_predictions,
                        AVG(confidence_score) as avg_confidence,
                        COUNT(CASE WHEN predicted_result = 'home' THEN 1 END) as home_predictions,
                        COUNT(CASE WHEN predicted_result = 'draw' THEN 1 END) as draw_predictions,
                        COUNT(CASE WHEN predicted_result = 'away' THEN 1 END) as away_predictions,
                        SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) as correct_predictions,
                        COUNT(CASE WHEN is_correct IS NOT NULL THEN 1 END) as verified_predictions
                    FROM predictions
                    WHERE created_at >= NOW() - INTERVAL ':days days'
                    GROUP BY model_version
                    ORDER BY model_version DESC
                """
                )

                result = await session.execute(query, {"days": days})
                stats = []

                for row in result:
                    accuracy = (
                        row.correct_predictions / row.verified_predictions
                        if row.verified_predictions > 0
                        else None
                    )

                    stats.append(
                        {
                            "model_version": row.model_version,
                            "total_predictions": row.total_predictions,
                            "avg_confidence": float(row.avg_confidence)
                            if row.avg_confidence
                            else 0.0,
                            "predictions_by_result": {
                                "home": row.home_predictions,
                                "draw": row.draw_predictions,
                                "away": row.away_predictions,
                            },
                            "accuracy": accuracy,
                            "verified_predictions": row.verified_predictions,
                        }
                    )

                return {"period_days": days, "statistics": stats}

        except Exception as e:
            logger.error(f"获取预测统计信息失败: {e}")
            return {"period_days": days, "statistics": []}
