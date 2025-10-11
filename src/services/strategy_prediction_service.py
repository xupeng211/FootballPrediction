"""
基于策略模式的预测服务
Strategy-based Prediction Service

使用策略模式重构的预测服务，提供灵活的预测算法选择。
Refactored prediction service using strategy pattern for flexible algorithm selection.
"""

import logging
from typing import Dict, Any, List, Optional

from ..domain.strategies import (  # type: ignore
    PredictionStrategy,
    PredictionStrategyFactory,
    PredictionInput,
    PredictionOutput,
    PredictionContext,
)
from ..domain.models import Team, Prediction
from ..domain.services import PredictionDomainService
from ..database.repositories import MatchRepository, PredictionRepository
from ..core.di import DIContainer

logger = logging.getLogger(__name__)


class StrategyPredictionService:
    """基于策略模式的预测服务

    使用策略模式管理多种预测算法，提供灵活的预测服务。
    Uses strategy pattern to manage multiple prediction algorithms.
    """

    def __init__(
        self,
        strategy_factory: PredictionStrategyFactory,
        prediction_domain_service: PredictionDomainService,
        match_repository: MatchRepository,
        prediction_repository: PredictionRepository,
        default_strategy: str = "ensemble_predictor",
    ):
        """初始化预测服务

        Args:
            strategy_factory: 策略工厂
            prediction_domain_service: 预测领域服务
            match_repository: 比赛仓储
            prediction_repository: 预测仓储
            default_strategy: 默认策略名称
        """
        self._strategy_factory = strategy_factory
        self._prediction_domain_service = prediction_domain_service
        self._match_repository = match_repository
        self._prediction_repository = prediction_repository
        self._default_strategy = default_strategy
        self._current_strategies: Dict[str, PredictionStrategy] = {}

    async def initialize(self) -> None:
        """初始化服务"""
        # 初始化默认策略
        await self._strategy_factory.initialize_default_strategies()

        # 加载默认策略
        default_strategy = self._strategy_factory.get_strategy(self._default_strategy)
        if default_strategy:
            self._current_strategies[self._default_strategy] = default_strategy
            logger.info(f"加载默认策略: {self._default_strategy}")

        logger.info("策略预测服务初始化完成")

    async def predict_match(
        self,
        match_id: int,
        user_id: int,
        strategy_name: Optional[str] = None,
        confidence: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Prediction:
        """预测单场比赛

        Args:
            match_id: 比赛ID
            user_id: 用户ID
            strategy_name: 使用的策略名称，None表示使用默认策略
            confidence: 预测信心度
            notes: 预测备注

        Returns:
            Prediction: 创建的预测
        """
        # 获取比赛信息
        match = await self._match_repository.get_by_id(match_id)
        if not match:
            raise ValueError(f"比赛不存在: {match_id}")

        # 获取球队信息
        home_team = await self._get_team_info(match.home_team_id)
        away_team = await self._get_team_info(match.away_team_id)

        # 选择策略
        strategy_name = strategy_name or self._default_strategy
        strategy = await self._get_or_create_strategy(strategy_name)

        # 创建预测上下文
        context = PredictionContext(
            match=match,
            home_team=home_team,
            away_team=away_team,
            user_id=user_id,  # type: ignore
        )

        # 准备预测输入
        prediction_input = await self._prepare_prediction_input(context)

        # 执行预测
        prediction_output = await strategy.predict(prediction_input)

        # 使用领域服务创建预测
        prediction = self._prediction_domain_service.create_prediction(
            user_id=user_id,
            match=match,  # type: ignore
            predicted_home=prediction_output.predicted_home_score,
            predicted_away=prediction_output.predicted_away_score,
            confidence=prediction_output.confidence,
            notes=notes,
        )

        # 保存预测
        await self._prediction_repository.create(prediction)  # type: ignore

        # 记录预测详情
        await self._log_prediction_details(prediction, prediction_output, strategy_name)

        logger.info(
            f"用户 {user_id} 对比赛 {match_id} 完成预测，使用策略: {strategy_name}"
        )

        return prediction

    async def batch_predict(
        self, match_ids: List[int], user_id: int, strategy_name: Optional[str] = None
    ) -> List[Prediction]:
        """批量预测比赛

        Args:
            match_ids: 比赛ID列表
            user_id: 用户ID
            strategy_name: 使用的策略名称

        Returns:
            List[Prediction]: 创建的预测列表
        """
        # 选择策略
        strategy_name = strategy_name or self._default_strategy
        strategy = await self._get_or_create_strategy(strategy_name)

        # 批量获取比赛信息
        matches = await self._match_repository.get_by_ids(match_ids)  # type: ignore
        if not matches:
            raise ValueError("没有找到有效的比赛")

        # 准备批量预测输入
        prediction_inputs = []
        contexts = []

        for match in matches:
            home_team = await self._get_team_info(match.home_team_id)
            away_team = await self._get_team_info(match.away_team_id)

            context = PredictionContext(
                match=match, home_team=home_team, away_team=away_team, user_id=user_id
            )

            prediction_input = await self._prepare_prediction_input(context)
            prediction_inputs.append(prediction_input)
            contexts.append(context)

        # 执行批量预测
        prediction_outputs = await strategy.batch_predict(prediction_inputs)

        # 创建预测对象
        predictions = []
        for context, output in zip(contexts, prediction_outputs):
            prediction = self._prediction_domain_service.create_prediction(
                user_id=user_id,
                match=context.match,
                predicted_home=output.predicted_home_score,
                predicted_away=output.predicted_away_score,
                confidence=output.confidence,
            )
            predictions.append(prediction)

        # 批量保存
        await self._prediction_repository.create_many(predictions)  # type: ignore

        logger.info(f"用户 {user_id} 完成批量预测 {len(predictions)} 场比赛")

        return predictions

    async def compare_strategies(
        self, match_id: int, strategy_names: Optional[List[str]] = None
    ) -> Dict[str, PredictionOutput]:
        """比较不同策略的预测结果

        Args:
            match_id: 比赛ID
            strategy_names: 要比较的策略列表，None表示比较所有可用策略

        Returns:
            Dict[str, PredictionOutput]: 各策略的预测结果
        """
        # 获取比赛信息
        match = await self._match_repository.get_by_id(match_id)
        if not match:
            raise ValueError(f"比赛不存在: {match_id}")

        # 获取球队信息
        home_team = await self._get_team_info(match.home_team_id)
        away_team = await self._get_team_info(match.away_team_id)

        # 准备预测输入
        context = PredictionContext(
            match=match,
            home_team=home_team,
            away_team=away_team,  # type: ignore
        )
        prediction_input = await self._prepare_prediction_input(context)

        # 选择要比较的策略
        if strategy_names is None:
            strategy_names = list(self._strategy_factory.list_configured_strategies())

        # 执行各策略预测
        results = {}
        for strategy_name in strategy_names:
            try:
                strategy = await self._get_or_create_strategy(strategy_name)
                output = await strategy.predict(prediction_input)
                results[strategy_name] = output
                logger.info(
                    f"策略 {strategy_name} 预测结果: {output.predicted_home_score}:{output.predicted_away_score}"
                )
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"策略 {strategy_name} 预测失败: {e}")
                results[strategy_name] = None  # type: ignore

        return results

    async def get_strategy_performance(
        self, strategy_name: str, days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """获取策略性能指标

        Args:
            strategy_name: 策略名称
            days: 统计天数

        Returns:
            Optional[Dict[str, Any]]: 性能指标
        """
        strategy = self._strategy_factory.get_strategy(strategy_name)
        if not strategy:
            return None

        metrics = strategy.get_metrics()
        if not metrics:
            return None

        # 获取最近的预测进行对比
        recent_predictions = await self._prediction_repository.get_recent_predictions(  # type: ignore
            strategy_name=strategy_name, days=days
        )

        # 计算实际性能（需要比赛结果）
        actual_performance = await self._calculate_actual_performance(
            recent_predictions
        )

        return {
            "strategy_name": strategy_name,
            "strategy_type": strategy.strategy_type.value,
            "metrics": {
                "accuracy": metrics.accuracy,
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1_score": metrics.f1_score,
                "total_predictions": metrics.total_predictions,
                "last_updated": metrics.last_updated.isoformat(),
            },
            "actual_performance": actual_performance,
            "recent_predictions_count": len(recent_predictions),
        }

    async def update_strategy_weights(self, strategy_weights: Dict[str, float]) -> None:
        """更新集成策略的权重

        Args:
            strategy_weights: 策略权重字典
        """
        ensemble_strategy = self._strategy_factory.get_strategy("ensemble_predictor")
        if ensemble_strategy:
            for strategy_name, weight in strategy_weights.items():
                ensemble_strategy.update_strategy_weight(strategy_name, weight)  # type: ignore
            logger.info("更新集成策略权重")

    async def switch_default_strategy(self, strategy_name: str) -> None:
        """切换默认策略

        Args:
            strategy_name: 新的默认策略名称
        """
        strategy = self._strategy_factory.get_strategy(strategy_name)
        if not strategy:
            raise ValueError(f"策略不存在: {strategy_name}")

        old_strategy = self._default_strategy
        self._default_strategy = strategy_name
        logger.info(f"默认策略从 {old_strategy} 切换到 {strategy_name}")

    async def get_available_strategies(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用策略信息"""
        health_report = await self._strategy_factory.health_check()

        strategies_info = {}
        for name, strategy in self._strategy_factory.get_all_strategies().items():
            strategies_info[name] = {
                "name": name,
                "type": strategy.strategy_type.value,
                "healthy": strategy.is_healthy(),
                "is_default": name == self._default_strategy,
                "metrics": strategy.get_metrics().__dict__
                if strategy.get_metrics()
                else None,
                "health": health_report.get(name, {}),
            }

        return strategies_info

    # 私有方法
    async def _get_or_create_strategy(self, strategy_name: str) -> PredictionStrategy:
        """获取或创建策略实例"""
        strategy = self._strategy_factory.get_strategy(strategy_name)
        if not strategy:
            strategy = await self._strategy_factory.create_strategy(strategy_name)
            self._current_strategies[strategy_name] = strategy

        return strategy

    async def _get_team_info(self, team_id: int) -> Team:
        """获取球队信息（简化实现）"""
        # 实际应该从team repository获取
        # 这里返回模拟数据
        return Team(id=team_id, name=f"Team_{team_id}", league_id=1)  # type: ignore

    async def _prepare_prediction_input(
        self, context: PredictionContext
    ) -> PredictionInput:
        """准备预测输入数据"""
        # 收集历史数据
        historical_data = await self._collect_historical_data(context)

        # 创建预测输入
        return PredictionInput(
            match=context.match,
            home_team=context.home_team,
            away_team=context.away_team,
            historical_data=historical_data,
            additional_features={
                "user_id": context.user_id,
                "request_time": context.timestamp.isoformat(),
            },
        )

    async def _collect_historical_data(
        self, context: PredictionContext
    ) -> Dict[str, Any]:
        """收集历史数据"""
        # 这里应该从数据库或缓存获取历史数据
        # 简化实现，返回模拟数据
        return {
            "home_team_recent_form": [
                {"goals_for": 2, "goals_against": 1, "result": "win"},
                {"goals_for": 1, "goals_against": 1, "result": "draw"},
                {"goals_for": 3, "goals_against": 0, "result": "win"},
            ],
            "away_team_recent_form": [
                {"goals_for": 1, "goals_against": 2, "result": "loss"},
                {"goals_for": 0, "goals_against": 1, "result": "loss"},
                {"goals_for": 2, "goals_against": 2, "result": "draw"},
            ],
            "head_to_head": [
                {"home_score": 2, "away_score": 1},
                {"home_score": 1, "away_score": 1},
                {"home_score": 0, "away_score": 2},
            ],
            "features": {
                "home_team_rating": 85.5,
                "away_team_rating": 78.2,
                "home_advantage": 1.15,
            },
        }

    async def _log_prediction_details(
        self,
        prediction: Prediction,
        prediction_output: PredictionOutput,
        strategy_name: str,
    ) -> None:
        """记录预测详情"""
        details = {
            "prediction_id": prediction.id,
            "strategy_used": strategy_name,
            "predicted_score": f"{prediction_output.predicted_home_score}:{prediction_output.predicted_away_score}",
            "confidence": prediction_output.confidence,
            "execution_time_ms": prediction_output.execution_time_ms,
            "probability_distribution": prediction_output.probability_distribution,
            "feature_importance": prediction_output.feature_importance,
            "metadata": prediction_output.metadata,
        }

        logger.info(f"预测详情: {details}")

    async def _calculate_actual_performance(
        self, predictions: List[Prediction]
    ) -> Dict[str, Any]:
        """计算实际性能"""
        if not predictions:
            return {}

        correct_predictions = 0
        total_predictions = len(predictions)
        score_differences = []

        for pred in predictions:
            # 需要获取比赛实际结果
            # 这里简化处理
            actual_home = 2  # 应该从match获取
            actual_away = 1

            if (
                pred.predicted_home == actual_home  # type: ignore
                and pred.predicted_away == actual_away  # type: ignore
            ):
                correct_predictions += 1

            score_diff = abs(pred.predicted_home - actual_home) + abs(  # type: ignore
                pred.predicted_away - actual_away  # type: ignore
            )
            score_differences.append(score_diff)

        accuracy = (
            correct_predictions / total_predictions if total_predictions > 0 else 0
        )
        avg_score_diff = (
            sum(score_differences) / len(score_differences) if score_differences else 0
        )

        return {
            "accuracy": accuracy,
            "correct_predictions": correct_predictions,
            "total_predictions": total_predictions,
            "average_score_difference": avg_score_diff,
        }


# 依赖注入配置
def configure_strategy_prediction_services(container: DIContainer) -> None:
    """配置策略预测服务的依赖注入"""

    # 注册策略工厂
    container.register_singleton(PredictionStrategyFactory)

    # 注册策略预测服务
    container.register_scoped(StrategyPredictionService)
