# mypy: ignore-errors
"""
事件驱动的预测服务
Event-Driven Prediction Service

集成事件系统的预测服务,发布预测相关事件.
Prediction service integrated with event system, publishing prediction-related events.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.di import DIContainer
from src.domain.models import Match, Prediction
from src.events import (
    PredictionMadeEvent,
    PredictionMadeEventData,
    PredictionUpdatedEvent,
    PredictionUpdatedEventData,
    get_event_bus,
)
from src.events.types import MatchCreatedEventData, UserRegisteredEventData
from .strategy_prediction_service import StrategyPredictionService

logger = logging.getLogger(__name__)


class EventDrivenPredictionService(StrategyPredictionService):
    """事件驱动的预测服务"

    继承自策略预测服务,添加事件发布功能.
    Inherits from strategy prediction service, adding event publishing capabilities.
    """

    def __init__(self, *args, **kwargs):
        """函数文档字符串"""
        pass
        # 添加pass语句
        """初始化事件驱动预测服务"""
        super().__init__(*args, **kwargs)
        self._event_bus = get_event_bus()
        self._event_source = "prediction_service"

    async def predict_match(
        self,
        match_id: int,
        user_id: int,
        strategy_name: Optional[str] = None,
        confidence: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Prediction:
        """预测单场比赛并发布事件"

        Args:
            match_id: 比赛ID
            user_id: 用户ID
            strategy_name: 使用的策略名称
            confidence: 预测信心度
            notes: 预测备注

        Returns:
            Prediction: 创建的预测
        """
        # 执行原有预测逻辑
        _prediction = await super().predict_match(
            match_id, user_id, strategy_name, confidence, notes
        )

        # 发布预测创建事件
        await self._publish_prediction_made_event(prediction, strategy_name)

        return prediction

    async def update_prediction(
        self,
        prediction_id: int,
        user_id: int,
        new_predicted_home: Optional[int] = None,
        new_predicted_away: Optional[int] = None,
        new_confidence: Optional[float] = None,
        new_notes: Optional[str] = None,
        update_reason: Optional[str] = None,
    ) -> Prediction:
        """更新预测并发布事件"

        Args:
            prediction_id: 预测ID
            user_id: 用户ID
            new_predicted_home: 新的主队预测得分
            new_predicted_away: 新的客队预测得分
            new_confidence: 新的信心度
            new_notes: 新的备注
            update_reason: 更新原因

        Returns:
            Prediction: 更新后的预测
        """
        # 获取原有预测
        original_prediction = await self._prediction_repository.get_by_id(prediction_id)
        if not original_prediction:
            raise ValueError(f"预测不存在: {prediction_id}")

        # 保存原有数据用于事件
        previous_prediction = {
            "predicted_home": original_prediction.predicted_home,
            "predicted_away": original_prediction.predicted_away,
            "confidence": original_prediction.confidence,
            "notes": original_prediction.notes,
        }

        # 更新预测
        if new_predicted_home is not None:
            original_prediction.predicted_home = new_predicted_home
        if new_predicted_away is not None:
            original_prediction.predicted_away = new_predicted_away
        if new_confidence is not None:
            original_prediction.confidence = new_confidence
        if new_notes is not None:
            original_prediction.notes = new_notes

        original_prediction.updated_at = datetime.utcnow()
        await self._prediction_repository.update(original_prediction)

        # 发布预测更新事件
        await self._publish_prediction_updated_event(
            original_prediction,
            previous_prediction,
            update_reason,
        )

        return original_prediction

    async def batch_predict(
        self, match_ids: List[int], user_id: int, strategy_name: Optional[str] = None
    ) -> List[Prediction]:
        """批量预测并发布事件"

        Args:
            match_ids: 比赛ID列表
            user_id: 用户ID
            strategy_name: 使用的策略名称

        Returns:
            List[Prediction]: 创建的预测列表
        """
        # 执行批量预测
        predictions = await super().batch_predict(match_ids, user_id, strategy_name)

        # 为每个预测发布事件
        for prediction in predictions:
            await self._publish_prediction_made_event(prediction, strategy_name)

        return predictions

    async def _publish_prediction_made_event(
        self, prediction: Prediction, strategy_name: Optional[str]
    ) -> None:
        """发布预测创建事件"

        Args:
            prediction: 创建的预测
            strategy_name: 使用的策略名称
        """
        try:
            # 创建事件数据
            event_data = PredictionMadeEventData(
                prediction_id=prediction.id,
                match_id=prediction.match_id,
                user_id=prediction.user_id,
                predicted_home=(
                    float(prediction.predicted_home_score)
                    if prediction.predicted_home_score
                    else None
                ),
                predicted_away=(
                    float(prediction.predicted_away_score)
                    if prediction.predicted_away_score
                    else None
                ),
                confidence=(
                    float(prediction.confidence_score)
                    if prediction.confidence_score
                    else None
                ),
                strategy_used=strategy_name,
                source=self._event_source,
                metadata={
                    "prediction_time": prediction.created_at.isoformat(),
                    "notes": prediction.notes,
                },
            )

            # 创建事件
            event = PredictionMadeEvent(event_data)

            # 发布事件
            await self._event_bus.publish(event)

            logger.debug(f"发布预测创建事件: prediction_id={prediction.id}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"发布预测创建事件失败: {e}")

    async def _publish_prediction_updated_event(
        self,
        prediction: Prediction,
        previous_prediction: Dict[str, Any],
        update_reason: Optional[str],
    ) -> None:
        """发布预测更新事件"

        Args:
            prediction: 更新后的预测
            previous_prediction: 更新前的预测数据
            update_reason: 更新原因
        """
        try:
            # 创建事件数据
            event_data = PredictionUpdatedEventData(
                prediction_id=prediction.id,
                match_id=prediction.match_id,
                user_id=prediction.user_id,
                predicted_home=(
                    float(prediction.predicted_home_score)
                    if prediction.predicted_home_score
                    else None
                ),
                predicted_away=(
                    float(prediction.predicted_away_score)
                    if prediction.predicted_away_score
                    else None
                ),
                confidence=(
                    float(prediction.confidence_score)
                    if prediction.confidence_score
                    else None
                ),
                strategy_used=None,  # 更新时可能没有策略信息
                previous_prediction=previous_prediction,
                update_reason=update_reason,
                source=self._event_source,
                metadata={
                    "update_time": prediction.updated_at.isoformat(),
                    "notes": prediction.notes,
                },
            )

            # 创建事件
            event = PredictionUpdatedEvent(event_data)

            # 发布事件
            await self._event_bus.publish(event)

            logger.debug(f"发布预测更新事件: prediction_id={prediction.id}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"发布预测更新事件失败: {e}")


# 事件驱动的比赛服务
class EventDrivenMatchService:
    """类文档字符串"""

    pass  # 添加pass语句
    """事件驱动的比赛服务"

    处理比赛相关的事件发布.
    Handles match-related event publishing.
    """

    def __init__(self, match_repository):
        """函数文档字符串"""
        pass
        # 添加pass语句
        """初始化比赛服务"

        Args:
            match_repository: 比赛仓储
        """
        self._match_repository = match_repository
        self._event_bus = get_event_bus()
        self._event_source = "match_service"

    async def create_match(
        self,
        home_team_id: int,
        away_team_id: int,
        league_id: int,
        match_time: datetime,
        venue: Optional[str] = None,
        weather: Optional[Dict[str, Any]] = None,
        created_by: Optional[int] = None,
        initial_odds: Optional[Dict[str, float]] = None,
    ) -> Match:
        """创建比赛并发布事件"

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            league_id: 联赛ID
            match_time: 比赛时间
            venue: 场地
            weather: 天气信息
            created_by: 创建者ID
            initial_odds: 初始赔率

        Returns:
            Match: 创建的比赛
        """
        # 创建比赛
        match = Match(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            league_id=league_id,
            match_date=match_time,
            venue=venue,
        )

        # 保存到数据库
        await self._match_repository.create(match)

        # 发布比赛创建事件
        await self._publish_match_created_event(
            match, created_by, initial_odds, weather
        )

        return match

    async def _publish_match_created_event(
        self,
        match: Match,
        created_by: Optional[int],
        initial_odds: Optional[Dict[str, float]],
        weather: Optional[Dict[str, Any]],
    ) -> None:
        """发布比赛创建事件"""
        try:
            # 创建事件数据
            event_data = MatchCreatedEventData(
                match_id=match.id,
                home_team_id=match.home_team_id,
                away_team_id=match.away_team_id,
                league_id=match.league_id,
                match_time=match.match_time,
                status=match.status,
                venue=match.venue,
                weather=weather,
                created_by=created_by,
                initial_odds=initial_odds,
                source=self._event_source,
                metadata={
                    "creation_time": datetime.utcnow().isoformat(),
                },
            )

            # 创建事件
            from ..events.types import MatchCreatedEvent

            event = MatchCreatedEvent(event_data)

            # 发布事件
            await self._event_bus.publish(event)

            logger.debug(f"发布比赛创建事件: match_id={match.id}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"发布比赛创建事件失败: {e}")


# 事件驱动的用户服务
class EventDrivenUserService:
    """类文档字符串"""

    pass  # 添加pass语句
    """事件驱动的用户服务"

    处理用户相关的事件发布.
    Handles user-related event publishing.
    """

    def __init__(self, user_repository):
        """函数文档字符串"""
        pass
        # 添加pass语句
        """初始化用户服务"

        Args:
            user_repository: 用户仓储
        """
        self._user_repository = user_repository
        self._event_bus = get_event_bus()
        self._event_source = "user_service"

    async def register_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        referral_code: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Any:
        """注册用户并发布事件"

        Args:
            username: 用户名
            email: 邮箱
            password_hash: 密码哈希
            referral_code: 推荐码
            ip_address: IP地址
            user_agent: 用户代理

        Returns:
            创建的用户
        """
        # 创建用户（简化实现）
        _user = {
            "id": 1,  # 实际应该由数据库生成
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "registration_date": datetime.utcnow(),
        }

        # 保存到数据库
        # await self._user_repository.create(user)

        # 发布用户注册事件
        await self._publish_user_registered_event(
            user, referral_code, ip_address, user_agent
        )

        return user

    async def _publish_user_registered_event(
        self,
        user: Dict[str, Any],
        referral_code: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> None:
        """发布用户注册事件"""
        try:
            # 创建事件数据
            event_data = UserRegisteredEventData(
                user_id=user["id"],
                username=user["username"],
                email=user["email"],
                registration_date=user["registration_date"],
                referral_code=referral_code,
                ip_address=ip_address,
                user_agent=user_agent,
                source=self._event_source,
                metadata={
                    "registration_method": "web",
                },
            )

            # 创建事件
            from ..events.types import UserRegisteredEvent

            event = UserRegisteredEvent(event_data)

            # 发布事件
            await self._event_bus.publish(event)

            logger.debug(f"发布用户注册事件: user_id={user['id']}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"发布用户注册事件失败: {e}")


# 依赖注入配置
def configure_event_driven_services(container: DIContainer) -> None:
    """配置事件驱动服务的依赖注入"""

    # 注册事件驱动的预测服务
    container.register_scoped(EventDrivenPredictionService)

    # 注册事件驱动的比赛服务
    # container.register_scoped(EventDrivenMatchService)

    # 注册事件驱动的用户服务
    # container.register_scoped(EventDrivenUserService)
