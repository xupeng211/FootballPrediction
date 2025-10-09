"""
预测处理器

负责执行实际的预测逻辑
"""



logger = logging.getLogger(__name__)


class PredictionProcessor:
    """
    预测处理器

    负责特征获取、模型推理和结果处理
    """

    def __init__(
        self,
        feature_store: FootballFeatureStore,
        metrics_exporter: ModelMetricsExporter,
        config: PredictionConfig
    ):
        """
        初始化预测处理器

        Args:
            feature_store: 特征存储实例
            metrics_exporter: 指标导出器实例
            config: 预测配置
        """
        self.feature_store = feature_store
        self.metrics_exporter = metrics_exporter
        self.config = config

    async def predict_match(
        self,
        match_id: int,
        match_info: Dict[str, Any],
        model: Any,
        model_version: str
    ) -> PredictionResult:
        """
        预测单场比赛

        Args:
            match_id: 比赛ID
            match_info: 比赛信息
            model: 模型对象
            model_version: 模型版本

        Returns:
            PredictionResult: 预测结果
        """
        start_time = datetime.now()

        # 从特征存储获取实时特征
        try:
            raw_features = self.feature_store.get_match_features_for_prediction(
                match_id=match_id,
                home_team_id=match_info["home_team_id"],
                away_team_id=match_info["away_team_id"],
            )
            features = (
                await raw_features
                if inspect.isawaitable(raw_features)
                else raw_features
            )
        except Exception as e:
            logger.warning(f"获取比赛 {match_id} 的特征失败: {e}，使用默认特征")
            features = self._get_default_features()

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
            model_name=self.config.default_model_name,
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

        # 记录预测时间
        prediction_duration = (datetime.now() - start_time).total_seconds()
        self.metrics_exporter.prediction_duration.labels(
            model_name=self.config.default_model_name, model_version=model_version
        ).observe(prediction_duration)

        logger.info(
            f"比赛 {match_id} 预测完成：{predicted_class} (置信度: {result.confidence_score:.3f})"
        )
        return result

    async def batch_predict_matches(
        self,
        match_ids: List[int],
        match_info_list: List[Dict[str, Any]],
        model: Any,
        model_version: str
    ) -> List[PredictionResult]:
        """
        批量预测比赛

        Args:
            match_ids: 比赛ID列表
            match_info_list: 比赛信息列表
            model: 模型对象
            model_version: 模型版本

        Returns:
            List[PredictionResult]: 预测结果列表
        """
        results = []

        for match_id, match_info in zip(match_ids, match_info_list):
            try:
                result = await self.predict_match(
                    match_id, match_info, model, model_version
                )
                results.append(result)
            except Exception as e:
                logger.error(f"批量预测中，比赛 {match_id} 预测失败: {e}")
                continue

        return results

    def _get_default_features(self) -> Dict[str, Any]:
        """
        获取默认特征（当特征服务不可用时）
        """
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
        """
        准备用于预测的特征数组

        Args:
            features: 特征字典

        Returns:
            np.ndarray: 用于预测的二维特征数组
        """
        # 使用配置中定义的特征顺序，保持一致性
        feature_values = []
        for feature_name in self.config.feature_order:
            value = features.get(str(feature_name), 0.0)
            feature_values.append(float(value))

        return np.array([feature_values])
from datetime import datetime
import inspect

import numpy as np

from src.models.prediction.core import PredictionResult

