# 设计模式应用文档

## 📋 概述

足球预测系统在架构设计中采用了多种设计模式，这些模式提高了代码的可维护性、可扩展性和可测试性。本文档详细说明了系统中使用的主要设计模式及其应用场景。

---

## 🏗️ 1. 策略模式 (Strategy Pattern)

### 应用场景
预测算法的动态选择和切换，不同的预测策略可以基于数据可用性、用户偏好或性能要求进行选择。

### 实现示例

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

class PredictionStrategyType(Enum):
    ML_MODEL = "ml_model"
    STATISTICAL = "statistical"
    ENSEMBLE = "ensemble"
    RULE_BASED = "rule_based"

# 策略接口
class PredictionStrategy(ABC):
    @abstractmethod
    async def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行预测计算"""
        pass

    @abstractmethod
    def get_confidence_score(self, data: Dict[str, Any]) -> float:
        """获取预测置信度"""
        pass

    @abstractmethod
    def get_required_data_fields(self) -> list[str]:
        """获取所需的数据字段"""
        pass

# 具体策略实现
class MLPredictionStrategy(PredictionStrategy):
    def __init__(self, model_service: ModelService):
        self.model_service = model_service

    async def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # 调用机器学习模型进行预测
        features = self._extract_features(data)
        prediction = await self.model_service.predict_async(features)
        return {
            "strategy": "ml_model",
            "prediction": prediction,
            "confidence": self.get_confidence_score(data)
        }

    def get_confidence_score(self, data: Dict[str, Any]) -> float:
        # 基于数据质量和模型性能计算置信度
        data_quality = self._calculate_data_quality(data)
        model_performance = self._get_model_performance()
        return min(data_quality * model_performance, 1.0)

class StatisticalPredictionStrategy(PredictionStrategy):
    async def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # 基于历史统计数据预测
        stats = self._calculate_statistical_prediction(data)
        return {
            "strategy": "statistical",
            "prediction": stats,
            "confidence": self.get_confidence_score(data)
        }

# 策略工厂
class PredictionStrategyFactory:
    def __init__(self):
        self._strategies: Dict[PredictionStrategyType, PredictionStrategy] = {}

    def register_strategy(self, strategy_type: PredictionStrategyType, strategy: PredictionStrategy):
        self._strategies[strategy_type] = strategy

    def create_strategy(self, strategy_type: PredictionStrategyType, **kwargs) -> PredictionStrategy:
        if strategy_type not in self._strategies:
            raise ValueError(f"未支持的策略类型: {strategy_type}")

        strategy = self._strategies[strategy_type]

        # 如果策略需要额外参数，可以在这里注入
        if hasattr(strategy, 'configure'):
            strategy.configure(**kwargs)

        return strategy

    async def create_optimal_strategy(self, data: Dict[str, Any]) -> PredictionStrategy:
        """根据数据情况自动选择最优策略"""
        available_strategies = []

        for strategy_type, strategy in self._strategies.items():
            if self._can_use_strategy(strategy, data):
                available_strategies.append((strategy_type, strategy))

        if not available_strategies:
            # 降级到默认策略
            return self._strategies[PredictionStrategyType.RULE_BASED]

        # 选择置信度最高的策略
        best_strategy = max(available_strategies,
                          key=lambda x: x[1].get_confidence_score(data))

        return best_strategy[1]

    def _can_use_strategy(self, strategy: PredictionStrategy, data: Dict[str, Any]) -> bool:
        """检查策略是否可以用于给定数据"""
        required_fields = strategy.get_required_data_fields()
        return all(field in data for field in required_fields)

# 使用示例
class PredictionService:
    def __init__(self, strategy_factory: PredictionStrategyFactory):
        self.strategy_factory = strategy_factory

    async def create_prediction(self, request: PredictionRequest) -> Prediction:
        # 获取数据
        data = await self._collect_prediction_data(request)

        # 选择最优策略
        strategy = await self.strategy_factory.create_optimal_strategy(data)

        # 执行预测
        result = await strategy.predict(data)

        return Prediction.from_dict(result)
```

---

## 🏭 2. 工厂模式 (Factory Pattern)

### 应用场景
各种服务对象的创建，包括数据库连接、缓存实例、外部API客户端等。工厂模式封装了对象的创建逻辑，提供了统一的创建接口。

### 实现示例

```python
from abc import ABC, abstractmethod
from typing import Protocol

class DatabaseConnection(Protocol):
    async def execute(self, query: str, params: Dict = None) -> Any:
        ...

    async def close(self) -> None:
        ...

# 抽象工厂
class DatabaseConnectionFactory(ABC):
    @abstractmethod
    async def create_connection(self, config: Dict[str, Any]) -> DatabaseConnection:
        pass

# 具体工厂
class PostgreSQLConnectionFactory(DatabaseConnectionFactory):
    async def create_connection(self, config: Dict[str, Any]) -> DatabaseConnection:
        return PostgreSQLConnection(config)

class MySQLConnectionFactory(DatabaseConnectionFactory):
    async def create_connection(self, config: Dict[str, Any]) -> DatabaseConnection:
        return MySQLConnection(config)

# 工厂注册器
class ConnectionFactoryRegistry:
    def __init__(self):
        self._factories: Dict[str, DatabaseConnectionFactory] = {}

    def register_factory(self, db_type: str, factory: DatabaseConnectionFactory):
        self._factories[db_type] = factory

    def create_connection(self, db_type: str, config: Dict[str, Any]) -> DatabaseConnection:
        if db_type not in self._factories:
            raise ValueError(f"不支持的数据库类型: {db_type}")

        factory = self._factories[db_type]
        return await factory.create_connection(config)

# 使用示例
class DatabaseManager:
    def __init__(self, registry: ConnectionFactoryRegistry):
        self.registry = registry
        self._connections: Dict[str, DatabaseConnection] = {}

    async def get_connection(self, connection_name: str) -> DatabaseConnection:
        if connection_name not in self._connections:
            config = self._get_connection_config(connection_name)
            self._connections[connection_name] = await self.registry.create_connection(
                config['type'], config
            )
        return self._connections[connection_name]
```

---

## 📦 3. 建造者模式 (Builder Pattern)

### 应用场景
复杂对象的创建，特别是API响应对象、配置对象等。建造者模式提供了灵活的对象构建方式。

### 实现示例

```python
from typing import List, Optional, Any
from dataclasses import dataclass, field

@dataclass
class PredictionResponse:
    """预测响应对象"""
    prediction_id: int
    match_info: Dict[str, Any]
    prediction_result: Dict[str, Any]
    confidence_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_predictions: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

class PredictionResponseBuilder:
    """预测响应建造者"""

    def __init__(self):
        self._prediction_id: Optional[int] = None
        self._match_info: Optional[Dict[str, Any]] = None
        self._prediction_result: Optional[Dict[str, Any]] = None
        self._confidence_score: Optional[float] = None
        self._metadata: Dict[str, Any] = {}
        self._related_predictions: List[Dict[str, Any]] = []
        self._recommendations: List[str] = []

    def set_prediction_id(self, prediction_id: int) -> 'PredictionResponseBuilder':
        self._prediction_id = prediction_id
        return self

    def set_match_info(self, match_info: Dict[str, Any]) -> 'PredictionResponseBuilder':
        self._match_info = match_info
        return self

    def set_prediction_result(self, result: Dict[str, Any]) -> 'PredictionResponseBuilder':
        self._prediction_result = result
        return self

    def set_confidence_score(self, score: float) -> 'PredictionResponseBuilder':
        self._confidence_score = score
        return self

    def add_metadata(self, key: str, value: Any) -> 'PredictionResponseBuilder':
        self._metadata[key] = value
        return self

    def add_related_prediction(self, prediction: Dict[str, Any]) -> 'PredictionResponseBuilder':
        self._related_predictions.append(prediction)
        return self

    def add_recommendation(self, recommendation: str) -> 'PredictionResponseBuilder':
        self._recommendations.append(recommendation)
        return self

    def build(self) -> PredictionResponse:
        if not all([self._prediction_id, self._match_info, self._prediction_result, self._confidence_score]):
            raise ValueError("缺少必需的字段")

        return PredictionResponse(
            prediction_id=self._prediction_id,
            match_info=self._match_info,
            prediction_result=self._prediction_result,
            confidence_score=self._confidence_score,
            metadata=self._metadata,
            related_predictions=self._related_predictions,
            recommendations=self._recommendations
        )

# 使用示例
class PredictionService:
    async def get_prediction_response(self, prediction_id: int) -> PredictionResponse:
        # 获取基础数据
        prediction = await self.repository.find_by_id(prediction_id)
        match = await self.match_repository.find_by_id(prediction.match_id)

        # 构建响应
        builder = PredictionResponseBuilder()

        response = (builder
            .set_prediction_id(prediction.id)
            .set_match_info({
                "home_team": match.home_team.name,
                "away_team": match.away_team.name,
                "match_time": match.match_time,
                "league": match.league.name
            })
            .set_prediction_result(prediction.result)
            .set_confidence_score(prediction.confidence)
            .add_metadata("created_at", prediction.created_at)
            .add_metadata("strategy", prediction.strategy)
            .add_related_prediction(await self._get_similar_predictions(prediction))
            .add_recommendation("查看历史对决记录")
            .add_recommendation("关注球队近期状态")
            .build())

        return response

# 建造者模式的Director类
class PredictionResponseDirector:
    def __init__(self, builder: PredictionResponseBuilder):
        self.builder = builder

    async def construct_full_response(self, prediction_id: int) -> PredictionResponse:
        """构建完整的预测响应"""
        prediction = await self._get_prediction(prediction_id)

        return (self.builder
            .set_prediction_id(prediction.id)
            .set_match_info(await self._get_match_info(prediction.match_id))
            .set_prediction_result(prediction.result)
            .set_confidence_score(prediction.confidence)
            .add_metadata("processing_time", prediction.processing_time)
            .add_related_prediction(await self._get_related_predictions(prediction))
            .add_recommendation("基于历史数据分析")
            .add_recommendation("考虑球队伤病情况")
            .build())
```

---

## 🔗 4. 观察者模式 (Observer Pattern)

### 应用场景
领域事件的发布和订阅，实现系统各模块之间的松耦合通信。

### 实现示例

```python
from abc import ABC, abstractmethod
from typing import List, Callable, Any
from collections import defaultdict
import asyncio
import logging

logger = logging.getLogger(__name__)

# 观察者接口
class EventObserver(ABC):
    @abstractmethod
    async def handle_event(self, event: 'DomainEvent') -> None:
        """处理领域事件"""
        pass

# 被观察者接口
class EventPublisher(ABC):
    @abstractmethod
    def add_observer(self, observer: EventObserver) -> None:
        """添加观察者"""
        pass

    @abstractmethod
    def remove_observer(self, observer: EventObserver) -> None:
        """移除观察者"""
        pass

    @abstractmethod
    async def notify_observers(self, event: 'DomainEvent') -> None:
        """通知观察者"""
        pass

# 领域事件基类
class DomainEvent:
    def __init__(self, aggregate_id: str, event_data: Dict[str, Any] = None):
        self.aggregate_id = aggregate_id
        self.event_data = event_data or {}
        self.occurred_at = datetime.utcnow()
        self.event_id = str(uuid.uuid4())

# 具体事件
class PredictionCreatedEvent(DomainEvent):
    def __init__(self, prediction_id: int, user_id: int, match_id: int):
        super().__init__(f"prediction_{prediction_id}", {
            "prediction_id": prediction_id,
            "user_id": user_id,
            "match_id": match_id
        })

class MatchScoreUpdatedEvent(DomainEvent):
    def __init__(self, match_id: int, old_score: str, new_score: str):
        super().__init__(f"match_{match_id}", {
            "match_id": match_id,
            "old_score": old_score,
            "new_score": new_score
        })

# 事件发布者实现
class EventPublisherImpl(EventPublisher):
    def __init__(self):
        self._observers: Dict[str, List[EventObserver]] = defaultdict(list)

    def add_observer(self, observer: EventObserver, event_types: List[str] = None):
        """添加观察者，可以指定感兴趣的事件类型"""
        if event_types is None:
            # 如果没有指定事件类型，监听所有事件
            event_types = ["*"]

        for event_type in event_types:
            self._observers[event_type].append(observer)
            logger.info(f"添加观察者监听事件类型: {event_type}")

    def remove_observer(self, observer: EventObserver):
        """移除观察者"""
        for event_type, observers in self._observers.items():
            if observer in observers:
                observers.remove(observer)
                logger.info(f"移除观察者对事件类型的监听: {event_type}")

    async def notify_observers(self, event: DomainEvent):
        """通知所有相关观察者"""
        event_type = event.__class__.__name__

        # 通知监听特定事件类型的观察者
        specific_observers = self._observers.get(event_type, [])

        # 通知监听所有事件的观察者
        general_observers = self._observers.get("*", [])

        all_observers = specific_observers + general_observers

        if all_observers:
            logger.info(f"通知 {len(all_observers)} 个观察者处理事件: {event_type}")

            # 并行通知所有观察者
            tasks = []
            for observer in all_observers:
                tasks.append(self._safe_notify_observer(observer, event))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_notify_observer(self, observer: EventObserver, event: DomainEvent):
        """安全地通知观察者，捕获异常"""
        try:
            await observer.handle_event(event)
        except Exception as e:
            logger.error(f"观察者处理事件失败: {e}", exc_info=True)

# 具体观察者实现
class StatisticsObserver(EventObserver):
    """统计信息观察者"""

    async def handle_event(self, event: DomainEvent):
        if isinstance(event, PredictionCreatedEvent):
            await self._update_prediction_statistics(event)
        elif isinstance(event, MatchScoreUpdatedEvent):
            await self._update_match_statistics(event)

    async def _update_prediction_statistics(self, event: PredictionCreatedEvent):
        """更新预测统计信息"""
        # 异步更新用户预测次数
        await increment_user_prediction_count(event.event_data["user_id"])

        # 异步更新比赛预测统计
        await increment_match_prediction_count(event.event_data["match_id"])

class NotificationObserver(EventObserver):
    """通知观察者"""

    async def handle_event(self, event: DomainEvent):
        if isinstance(event, PredictionCreatedEvent):
            await self._send_prediction_notification(event)
        elif isinstance(event, MatchScoreUpdatedEvent):
            await self._send_score_update_notification(event)

    async def _send_prediction_notification(self, event: PredictionCreatedEvent):
        """发送预测创建通知"""
        user_id = event.event_data["user_id"]
        prediction_id = event.event_data["prediction_id"]

        notification = Notification(
            user_id=user_id,
            type="prediction_created",
            title="预测创建成功",
            message=f"您的预测 #{prediction_id} 已创建"
        )

        await notification_service.send_async(notification)

# 使用示例
class PredictionService:
    def __init__(self, event_publisher: EventPublisher):
        self.event_publisher = event_publisher

    async def create_prediction(self, data: PredictionData) -> Prediction:
        # 创建预测
        prediction = Prediction.create(data)
        await self.repository.save(prediction)

        # 发布事件
        event = PredictionCreatedEvent(
            prediction_id=prediction.id,
            user_id=prediction.user_id,
            match_id=prediction.match_id
        )

        await self.event_publisher.notify_observers(event)

        return prediction

# 系统初始化时注册观察者
async def setup_event_system():
    event_publisher = EventPublisherImpl()

    # 创建观察者
    statistics_observer = StatisticsObserver()
    notification_observer = NotificationObserver()
    analytics_observer = AnalyticsObserver()

    # 注册观察者
    event_publisher.add_observer(statistics_observer, ["PredictionCreatedEvent", "MatchScoreUpdatedEvent"])
    event_publisher.add_observer(notification_observer, ["PredictionCreatedEvent"])
    event_publisher.add_observer(analytics_observer, ["*"])  # 监听所有事件

    return event_publisher
```

---

## 🏛️ 5. 仓储模式 (Repository Pattern)

### 应用场景
数据访问层的抽象，将业务逻辑与数据访问技术解耦。

### 实现示例

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Generic, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')

# 仓储接口
class Repository(ABC, Generic[T]):
    @abstractmethod
    async def find_by_id(self, id: Any) -> Optional[T]:
        pass

    @abstractmethod
    async def find_all(self) -> List[T]:
        pass

    @abstractmethod
    async def save(self, entity: T) -> T:
        pass

    @abstractmethod
    async def delete(self, entity: T) -> None:
        pass

# 具体仓储实现
class SqlAlchemyPredictionRepository(Repository[Prediction]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, prediction_id: int) -> Optional[Prediction]:
        result = await self.session.execute(
            select(Prediction).where(Prediction.id == prediction_id)
        )
        return result.scalar_one_or_none()

    async def find_all(self) -> List[Prediction]:
        result = await self.session.execute(select(Prediction))
        return result.scalars().all()

    async def save(self, prediction: Prediction) -> Prediction:
        self.session.add(prediction)
        await self.session.flush()
        await self.session.refresh(prediction)
        return prediction

    async def delete(self, prediction: Prediction) -> None:
        await self.session.delete(prediction)
        await self.session.flush()

    # 自定义查询方法
    async def find_by_user(self, user_id: int, limit: int = 10) -> List[Prediction]:
        result = await self.session.execute(
            select(Prediction)
            .where(Prediction.user_id == user_id)
            .order_by(Prediction.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def find_by_match(self, match_id: int) -> List[Prediction]:
        result = await self.session.execute(
            select(Prediction)
            .where(Prediction.match_id == match_id)
        )
        return result.scalars().all()

# 仓储工厂
class RepositoryFactory:
    def __init__(self):
        self._repositories: Dict[type, Callable] = {}

    def register_repository(self, entity_type: type, repository_factory: Callable):
        self._repositories[entity_type] = repository_factory

    def create_repository(self, entity_type: type, session: AsyncSession) -> Repository:
        if entity_type not in self._repositories:
            raise ValueError(f"未找到实体类型的仓储工厂: {entity_type}")

        factory = self._repositories[entity_type]
        return factory(session)

# 使用示例
class PredictionService:
    def __init__(self, repository_factory: RepositoryFactory, session_factory):
        self.repository_factory = repository_factory
        self.session_factory = session_factory

    async def get_user_predictions(self, user_id: int) -> List[Prediction]:
        async with self.session_factory() as session:
            repository = self.repository_factory.create_repository(Prediction, session)
            return await repository.find_by_user(user_id)

    async def create_prediction(self, data: PredictionData) -> Prediction:
        async with self.session_factory() as session:
            repository = self.repository_factory.create_repository(Prediction, session)

            prediction = Prediction.create(data)
            prediction = await repository.save(prediction)

            await session.commit()
            return prediction
```

---

## 📚 总结

这些设计模式在足球预测系统中的应用：

1. **策略模式**: 提供了灵活的算法选择机制
2. **工厂模式**: 封装了对象创建的复杂性
3. **建造者模式**: 简化了复杂对象的构建过程
4. **观察者模式**: 实现了松耦合的事件驱动架构
5. **仓储模式**: 抽象了数据访问层，提高了可测试性

这些模式共同作用，提高了系统的：
- **可维护性**: 清晰的职责分离和模块化设计
- **可扩展性**: 易于添加新功能而不影响现有代码
- **可测试性**: 依赖注入和接口抽象便于单元测试
- **灵活性**: 运行时的动态行为调整

通过合理使用这些设计模式，系统具备了良好的架构基础，能够应对未来的业务需求变化和技术演进。