# 完整架构说明

本文档详细介绍FootballPrediction项目的完整架构设计，包括DDD、CQRS、策略工厂、依赖注入和事件驱动模式的实现。

---

## 📋 目录

- [🏗️ 整体架构概览](#️-整体架构概览)
- [🎯 DDD领域驱动设计](#-ddd领域驱动设计)
- [📡 CQRS命令查询分离](#-cqrs命令查询分离)
- [🏭 策略工厂模式](#-策略工厂模式)
- [💉 依赖注入容器](#-依赖注入容器)
- [⚡ 事件驱动架构](#-事件驱动架构)
- [🔗 适配器模式](#-适配器模式)
- [📊 数据访问层](#-数据访问层)
- [🎮 核心基础设施](#-核心基础设施)

---

## 🏗️ 整体架构概览

### 技术栈
- **后端框架**: FastAPI
- **ORM**: SQLAlchemy 2.0
- **数据库**: PostgreSQL
- **缓存**: Redis
- **架构模式**: DDD + CQRS + 策略工厂 + 依赖注入 + 事件驱动

### 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   FastAPI   │  │   Health    │  │     Predictions     │  │
│  │   Routes    │  │   Checks    │  │        APIs         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                Application Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   CQRS      │  │  Services   │  │      Events          │  │
│  │    Bus      │  │   Layer     │  │      System          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  Domain Layer                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Entities   │  │ Strategies  │  │   Domain Services   │  │
│  │             │  │   Factory   │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                Infrastructure Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Database   │  │    Cache    │  │   DI Container      │  │
│  │  Repository │  │  Managers   │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 DDD领域驱动设计

### 核心实体（Entities）

**Match实体** - 比赛核心业务对象
```python
# src/domain/entities.py
class Match:
    def __init__(self, id: str, home_team: Team, away_team: Team,
                 league: League, match_date: datetime, venue: str):
        self.id = id
        self.home_team = home_team
        self.away_team = away_team
        self.league = league
        self.match_date = match_date
        self.venue = venue
        self.home_score = None
        self.away_score = None
        self.status = MatchStatus.SCHEDULED

    def finalize_match(self, home_score: int, away_score: int):
        """完成比赛并记录最终比分"""
        self.home_score = home_score
        self.away_score = away_score
        self.status = MatchStatus.COMPLETED

    def is_completed(self) -> bool:
        """检查比赛是否已完成"""
        return self.status == MatchStatus.COMPLETED
```

**Team实体** - 球队核心业务对象
```python
class Team:
    def __init__(self, id: str, name: str, league: League):
        self.id = id
        self.name = name
        self.league = league
        self.home_venue = None
        self.founded_date = None

    def update_venue(self, venue: str):
        """更新球队主场"""
        self.home_venue = venue
```

**Prediction实体** - 预测核心业务对象
```python
class Prediction:
    def __init__(self, id: str, match: Match, strategy_type: str,
                 prediction_data: dict, created_at: datetime):
        self.id = id
        self.match = match
        self.strategy_type = strategy_type
        self.prediction_data = prediction_data
        self.created_at = created_at
        self.confidence_score = 0.0

    def calculate_confidence(self, historical_accuracy: float) -> float:
        """基于历史准确率计算预测置信度"""
        # 根据策略类型和历史表现计算置信度
        base_confidence = self.get_base_confidence()
        adjusted_confidence = base_confidence * historical_accuracy
        self.confidence_score = min(adjusted_confidence, 1.0)
        return self.confidence_score
```

### 值对象（Value Objects）

**MatchResult值对象**
```python
class MatchResult:
    def __init__(self, home_score: int, away_score: int):
        self.home_score = home_score
        self.away_score = away_score

    @property
    def outcome(self) -> str:
        """计算比赛结果：home_win/draw/away_win"""
        if self.home_score > self.away_score:
            return "home_win"
        elif self.home_score < self.away_score:
            return "away_win"
        else:
            return "draw"

    def __eq__(self, other) -> bool:
        return (self.home_score == other.home_score and
                self.away_score == other.away_score)
```

### 领域服务（Domain Services）

**PredictionService**
```python
# src/domain/services/prediction_service.py
class PredictionService:
    def __init__(self, strategy_factory: PredictionStrategyFactory):
        self.strategy_factory = strategy_factory

    async def create_prediction(self, match: Match, strategy_type: str) -> Prediction:
        """创建比赛预测"""
        strategy = await self.strategy_factory.create_strategy(strategy_type, strategy_type)
        prediction_data = await strategy.predict(match)

        prediction = Prediction(
            id=str(uuid.uuid4()),
            match=match,
            strategy_type=strategy_type,
            prediction_data=prediction_data,
            created_at=datetime.utcnow()
        )

        return prediction
```

**TeamStatisticsService**
```python
class TeamStatisticsService:
    async def calculate_team_form(self, team: Team, last_n_matches: int = 5) -> dict:
        """计算球队近期状态"""
        # 计算最近N场比赛的表现
        pass

    async def get_head_to_head(self, team1: Team, team2: Team) -> dict:
        """获取两队历史交锋记录"""
        pass
```

### 领域事件（Domain Events）

**PredictionCreatedEvent**
```python
# src/domain/events/prediction_events.py
class PredictionCreatedEvent:
    def __init__(self, prediction_id: str, match_data: dict,
                 strategy_type: str, timestamp: datetime):
        self.prediction_id = prediction_id
        self.match_data = match_data
        self.strategy_type = strategy_type
        self.timestamp = timestamp
```

**MatchCompletedEvent**
```python
class MatchCompletedEvent:
    def __init__(self, match_id: str, final_score: MatchResult, timestamp: datetime):
        self.match_id = match_id
        self.final_score = final_score
        self.timestamp = timestamp
```

---

## 📡 CQRS命令查询分离

### 基础消息类

**BaseMessage抽象基类**
```python
# src/cqrs/base.py
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any
import uuid

class BaseMessage(ABC):
    def __init__(self, message_id: str, timestamp: datetime,
                 metadata: Dict[str, Any] = None):
        self.message_id = message_id
        self.timestamp = timestamp
        self.metadata = metadata or {}

class BaseCommand(BaseMessage):
    def __init__(self, **kwargs):
        super().__init__(
            message_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            metadata={"type": "command"}
        )
        self.__dict__.update(kwargs)

class BaseQuery(BaseMessage):
    def __init__(self, **kwargs):
        super().__init__(
            message_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            metadata={"type": "query"}
        )
        self.__dict__.update(kwargs)
```

### 命令实现

**CreatePredictionCommand**
```python
# src/cqrs/commands.py
class CreatePredictionCommand(BaseCommand):
    def __init__(self, match_id: str, strategy_type: str):
        super().__init__()
        self.match_id = match_id
        self.strategy_type = strategy_type
```

**UpdateMatchResultCommand**
```python
class UpdateMatchResultCommand(BaseCommand):
    def __init__(self, match_id: str, home_score: int, away_score: int):
        super().__init__()
        self.match_id = match_id
        self.home_score = home_score
        self.away_score = away_score
```

### 查询实现

**GetPredictionQuery**
```python
# src/cqrs/queries.py
class GetPredictionQuery(BaseQuery):
    def __init__(self, prediction_id: str):
        super().__init__()
        self.prediction_id = prediction_id
```

**GetPredictionsByMatchQuery**
```python
class GetPredictionsByMatchQuery(BaseQuery):
    def __init__(self, match_id: str, strategy_types: List[str] = None):
        super().__init__()
        self.match_id = match_id
        self.strategy_types = strategy_types
```

### 命令总线实现

**CommandBus**
```python
# src/cqrs/bus.py
from typing import Type, Dict, Callable
import asyncio

class CommandBus:
    def __init__(self):
        self._handlers: Dict[Type[BaseCommand], Callable] = {}

    def register_handler(self, command_type: Type[BaseCommand], handler: Callable):
        """注册命令处理器"""
        self._handlers[command_type] = handler

    async def execute(self, command: BaseCommand) -> Any:
        """执行命令"""
        command_type = type(command)
        if command_type not in self._handlers:
            raise ValueError(f"No handler registered for {command_type}")

        handler = self._handlers[command_type]
        return await handler(command)
```

### 查询总线实现

**QueryBus**
```python
class QueryBus:
    def __init__(self):
        self._handlers: Dict[Type[BaseQuery], Callable] = {}

    def register_handler(self, query_type: Type[BaseQuery], handler: Callable):
        """注册查询处理器"""
        self._handlers[query_type] = handler

    async def execute(self, query: BaseQuery) -> Any:
        """执行查询"""
        query_type = type(query)
        if query_type not in self._handlers:
            raise ValueError(f"No handler registered for {query_type}")

        handler = self._handlers[query_type]
        return await handler(query)
```

### 处理器基类

**CommandHandler**
```python
# src/cqrs/handlers.py
from abc import ABC, abstractmethod

class CommandHandler(ABC):
    @abstractmethod
    async def handle(self, command: BaseCommand) -> Any:
        """处理命令"""
        pass
```

**QueryHandler**
```python
class QueryHandler(ABC):
    @abstractmethod
    async def handle(self, query: BaseQuery) -> Any:
        """处理查询"""
        pass
```

---

## 🏭 策略工厂模式

### 策略接口定义

**PredictionStrategy抽象基类**
```python
# src/domain/strategies/base.py
from abc import ABC, abstractmethod
from src.domain.entities import Match

class PredictionStrategy(ABC):
    @abstractmethod
    async def predict(self, match: Match) -> dict:
        """预测比赛结果"""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        pass

    @abstractmethod
    def get_confidence_weight(self) -> float:
        """获取策略置信度权重"""
        pass
```

### 具体策略实现

**ML模型策略**
```python
# src/domain/strategies/ml_strategy.py
class MLModelStrategy(PredictionStrategy):
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None

    async def predict(self, match: Match) -> dict:
        """使用机器学习模型预测比赛结果"""
        # 提取特征
        features = self._extract_features(match)

        # 加载模型（如果未加载）
        if self.model is None:
            self.model = await self._load_model()

        # 进行预测
        prediction = await self.model.predict(features)

        return {
            "home_win_prob": prediction[0],
            "draw_prob": prediction[1],
            "away_win_prob": prediction[2],
            "recommended_bet": self._get_recommendation(prediction)
        }

    def get_strategy_name(self) -> str:
        return "ml_model"

    def get_confidence_weight(self) -> float:
        return 0.8
```

**历史数据分析策略**
```python
# src/domain/strategies/historical_strategy.py
class HistoricalAnalysisStrategy(PredictionStrategy):
    def __init__(self, historical_data_repository):
        self.historical_data_repository = historical_data_repository

    async def predict(self, match: Match) -> dict:
        """基于历史数据分析预测"""
        # 获取历史交锋记录
        head_to_head = await self.historical_data_repository.get_head_to_head(
            match.home_team, match.away_team
        )

        # 获取近期状态
        home_form = await self.historical_data_repository.get_team_form(
            match.home_team, last_n=5
        )
        away_form = await self.historical_data_repository.get_team_form(
            match.away_team, last_n=5
        )

        # 基于历史数据计算概率
        probabilities = self._calculate_probabilities(head_to_head, home_form, away_form)

        return {
            "home_win_prob": probabilities["home"],
            "draw_prob": probabilities["draw"],
            "away_win_prob": probabilities["away"],
            "data_points": len(head_to_head),
            "recommendation_strength": self._get_recommendation_strength(probabilities)
        }

    def get_strategy_name(self) -> str:
        return "historical_analysis"

    def get_confidence_weight(self) -> float:
        return 0.6
```

**统计分析策略**
```python
# src/domain/strategies/statistical_strategy.py
class StatisticalAnalysisStrategy(PredictionStrategy):
    async def predict(self, match: Match) -> dict:
        """基于统计分析预测"""
        # 使用统计学方法（如泊松分布）计算概率
        home_goals_expected = await self._calculate_expected_goals(match.home_team, match)
        away_goals_expected = await self._calculate_expected_goals(match.away_team, match)

        # 使用泊松分布计算各种比分概率
        probabilities = self._poisson_distribution(home_goals_expected, away_goals_expected)

        return {
            "home_win_prob": probabilities["home_win"],
            "draw_prob": probabilities["draw"],
            "away_win_prob": probabilities["away_win"],
            "expected_goals": {
                "home": home_goals_expected,
                "away": away_goals_expected
            },
            "methodology": "poisson_distribution"
        }

    def get_strategy_name(self) -> str:
        return "statistical_analysis"

    def get_confidence_weight(self) -> float:
        return 0.7
```

### 策略工厂实现

**PredictionStrategyFactory**
```python
# src/domain/strategies/factory.py
from typing import Dict, Type
import importlib

class PredictionStrategyFactory:
    def __init__(self):
        self._strategies: Dict[str, Type[PredictionStrategy]] = {}
        self._register_default_strategies()

    def _register_default_strategies(self):
        """注册默认策略"""
        self.register_strategy("ml_model", MLModelStrategy)
        self.register_strategy("historical", HistoricalAnalysisStrategy)
        self.register_strategy("statistical", StatisticalAnalysisStrategy)

    def register_strategy(self, name: str, strategy_class: Type[PredictionStrategy]):
        """注册策略类"""
        self._strategies[name] = strategy_class

    async def create_strategy(self, strategy_type: str, config: dict = None) -> PredictionStrategy:
        """创建策略实例"""
        if strategy_type not in self._strategies:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

        strategy_class = self._strategies[strategy_type]

        # 根据配置创建实例
        if config:
            strategy = strategy_class(**config)
        else:
            strategy = strategy_class()

        return strategy

    def get_available_strategies(self) -> List[str]:
        """获取所有可用策略"""
        return list(self._strategies.keys())
```

---

## 💉 依赖注入容器

### 服务生命周期枚举

**ServiceLifetime**
```python
# src/core/di.py
from enum import Enum

class ServiceLifetime(Enum):
    SINGLETON = "singleton"    # 单例模式 - 整个容器生命周期内只创建一次
    SCOPED = "scoped"          # 作用域模式 - 每个作用域内创建一次
    TRANSIENT = "transient"    # 瞬时模式 - 每次请求都创建新实例
```

### 服务描述符

**ServiceDescriptor**
```python
class ServiceDescriptor:
    def __init__(self, service_type: type, implementation_type: type = None,
                 instance: object = None, factory: callable = None,
                 lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT):
        self.service_type = service_type
        self.implementation_type = implementation_type or service_type
        self.instance = instance
        self.factory = factory
        self.lifetime = lifetime
```

### 服务集合

**ServiceCollection**
```python
class ServiceCollection:
    def __init__(self):
        self._services: List[ServiceDescriptor] = []

    def add_singleton(self, service_type: type, implementation_type: type = None) -> 'ServiceCollection':
        """注册单例服务"""
        self._services.append(ServiceDescriptor(
            service_type, implementation_type, lifetime=ServiceLifetime.SINGLETON
        ))
        return self

    def add_scoped(self, service_type: type, implementation_type: type = None) -> 'ServiceCollection':
        """注册作用域服务"""
        self._services.append(ServiceDescriptor(
            service_type, implementation_type, lifetime=ServiceLifetime.SCOPED
        ))
        return self

    def add_transient(self, service_type: type, implementation_type: type = None) -> 'ServiceCollection':
        """注册瞬时服务"""
        self._services.append(ServiceDescriptor(
            service_type, implementation_type, lifetime=ServiceLifetime.TRANSIENT
        ))
        return self

    def add_instance(self, service_type: type, instance: object) -> 'ServiceCollection':
        """注册实例服务"""
        self._services.append(ServiceDescriptor(
            service_type, instance=instance, lifetime=ServiceLifetime.SINGLETON
        ))
        return self

    def add_factory(self, service_type: type, factory: callable,
                   lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT) -> 'ServiceCollection':
        """注册工厂服务"""
        self._services.append(ServiceDescriptor(
            service_type, factory=factory, lifetime=lifetime
        ))
        return self

    def build_container(self) -> 'DIContainer':
        """构建依赖注入容器"""
        return DIContainer(self._services)
```

### 依赖注入容器

**DIContainer**
```python
class DIContainer:
    def __init__(self, service_descriptors: List[ServiceDescriptor]):
        self._services = {}
        self._singletons = {}
        self._scoped_instances = {}

        # 构建服务映射
        for descriptor in service_descriptors:
            service_name = descriptor.service_type.__name__
            self._services[service_name] = descriptor

    def resolve(self, service_type: type) -> object:
        """解析服务"""
        service_name = service_type.__name__

        if service_name not in self._services:
            raise ValueError(f"Service {service_name} is not registered")

        descriptor = self._services[service_name]

        # 根据生命周期创建实例
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return self._resolve_singleton(descriptor)
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            return self._resolve_scoped(descriptor)
        else:  # TRANSIENT
            return self._resolve_transient(descriptor)

    def _resolve_singleton(self, descriptor: ServiceDescriptor) -> object:
        """解析单例服务"""
        service_name = descriptor.service_type.__name__

        if service_name in self._singletons:
            return self._singletons[service_name]

        instance = self._create_instance(descriptor)
        self._singletons[service_name] = instance
        return instance

    def _resolve_scoped(self, descriptor: ServiceDescriptor) -> object:
        """解析作用域服务"""
        # 简化实现，这里可以使用线程本地存储或其他作用域管理机制
        return self._resolve_transient(descriptor)

    def _resolve_transient(self, descriptor: ServiceDescriptor) -> object:
        """解析瞬时服务"""
        return self._create_instance(descriptor)

    def _create_instance(self, descriptor: ServiceDescriptor) -> object:
        """创建服务实例"""
        if descriptor.instance:
            return descriptor.instance

        if descriptor.factory:
            return descriptor.factory(self)

        # 使用构造函数注入创建实例
        implementation_type = descriptor.implementation_type
        constructor_params = self._get_constructor_parameters(implementation_type)

        # 递归解析依赖
        dependencies = {}
        for param_name, param_type in constructor_params.items():
            if param_type != object:  # 跳过self参数
                dependencies[param_name] = self.resolve(param_type)

        return implementation_type(**dependencies)

    def _get_constructor_parameters(self, cls: type) -> Dict[str, type]:
        """获取构造函数参数类型"""
        import inspect

        sig = inspect.signature(cls.__init__)
        parameters = {}

        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            if param.annotation != inspect.Parameter.empty:
                parameters[param_name] = param.annotation

        return parameters
```

---

## ⚡ 事件驱动架构

### 事件总线接口

**EventBus**
```python
# src/core/event_bus.py
from typing import List, Callable, Dict, Any
import asyncio
from collections import defaultdict

class EventBus:
    def __init__(self):
        self._handlers: Dict[type, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable):
        """订阅事件"""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: Callable):
        """取消订阅"""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def publish(self, event):
        """发布事件"""
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        # 并发处理所有事件处理器
        tasks = [handler(event) for handler in handlers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
```

### 事件处理器

**PredictionEventHandler**
```python
# src/domain/events/prediction_event_handlers.py
class PredictionEventHandler:
    def __init__(self, notification_service, analytics_service):
        self.notification_service = notification_service
        self.analytics_service = analytics_service

    async def handle_prediction_created(self, event: PredictionCreatedEvent):
        """处理预测创建事件"""
        # 发送通知
        await self.notification_service.send_prediction_notification(event)

        # 记录分析数据
        await self.analytics_service.record_prediction_created(event)

    async def handle_match_completed(self, event: MatchCompletedEvent):
        """处理比赛完成事件"""
        # 评估预测准确性
        await self.analytics_service.evaluate_predictions(event.match_id)

        # 更新模型数据
        await self.analytics_service.update_training_data(event)
```

### 事件驱动应用

**EventDrivenApplication**
```python
# src/core/event_application.py
class EventDrivenApplication:
    def __init__(self):
        self.event_bus = EventBus()
        self._initialized = False

    async def initialize(self):
        """初始化事件驱动应用"""
        if self._initialized:
            return

        # 注册事件处理器
        self._register_event_handlers()

        self._initialized = True

    def _register_event_handlers(self):
        """注册事件处理器"""
        # 从依赖注入容器获取事件处理器
        prediction_handler = self._get_service(PredictionEventHandler)

        # 订阅事件
        self.event_bus.subscribe(PredictionCreatedEvent,
                               prediction_handler.handle_prediction_created)
        self.event_bus.subscribe(MatchCompletedEvent,
                               prediction_handler.handle_match_completed)

    async def publish_event(self, event):
        """发布事件"""
        await self.event_bus.publish(event)
```

---

## 🔗 适配器模式

### 数据库适配器

**DatabaseAdapter**
```python
# src/adapters/database_adapter.py
from abc import ABC, abstractmethod

class DatabaseAdapter(ABC):
    @abstractmethod
    async def connect(self):
        """连接数据库"""
        pass

    @abstractmethod
    async def disconnect(self):
        """断开数据库连接"""
        pass

    @abstractmethod
    async def execute_query(self, query: str, params: dict = None):
        """执行查询"""
        pass
```

**PostgreSQLAdapter**
```python
class PostgreSQLAdapter(DatabaseAdapter):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None

    async def connect(self):
        """连接PostgreSQL数据库"""
        # 使用asyncpg连接池
        import asyncpg
        self.pool = await asyncpg.create_pool(self.connection_string)

    async def disconnect(self):
        """断开连接"""
        if self.pool:
            await self.pool.close()

    async def execute_query(self, query: str, params: dict = None):
        """执行SQL查询"""
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, **params or {})
```

### 外部API适配器

**FootballDataAPAdapter**
```python
# src/adapters/football_api_adapter.py
class FootballDataAPAdapter:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session = None

    async def connect(self):
        """初始化HTTP会话"""
        import aiohttp
        self.session = aiohttp.ClientSession(
            headers={'X-Auth-Token': self.api_key}
        )

    async def disconnect(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.close()

    async def get_matches(self, league_id: int, date_from: str, date_to: str):
        """获取比赛数据"""
        url = f"{self.base_url}/competitions/{league_id}/matches"
        params = {
            'dateFrom': date_from,
            'dateTo': date_to
        }

        async with self.session.get(url, params=params) as response:
            return await response.json()
```

---

## 📊 数据访问层

### 仓储模式

**BaseRepository**
```python
# src/database/repository.py
from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar, Generic

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    @abstractmethod
    async def create(self, entity: T) -> T:
        """创建实体"""
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """根据ID获取实体"""
        pass

    @abstractmethod
    async def get_all(self) -> List[T]:
        """获取所有实体"""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """更新实体"""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """删除实体"""
        pass
```

**PredictionRepository**
```python
class PredictionRepository(BaseRepository[Prediction]):
    def __init__(self, database_adapter: DatabaseAdapter):
        self.db_adapter = database_adapter

    async def create(self, prediction: Prediction) -> Prediction:
        """创建预测记录"""
        query = """
        INSERT INTO predictions (id, match_id, strategy_type, prediction_data, created_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """

        result = await self.db_adapter.execute_query(
            query,
            {
                'id': prediction.id,
                'match_id': prediction.match.id,
                'strategy_type': prediction.strategy_type,
                'prediction_data': json.dumps(prediction.prediction_data),
                'created_at': prediction.created_at
            }
        )

        return self._map_to_entity(result[0])

    async def get_by_id(self, prediction_id: str) -> Optional[Prediction]:
        """根据ID获取预测"""
        query = "SELECT * FROM predictions WHERE id = $1"
        result = await self.db_adapter.execute_query(query, {'id': prediction_id})

        return self._map_to_entity(result[0]) if result else None

    async def get_by_match_id(self, match_id: str) -> List[Prediction]:
        """获取比赛的所有预测"""
        query = "SELECT * FROM predictions WHERE match_id = $1 ORDER BY created_at DESC"
        result = await self.db_adapter.execute_query(query, {'match_id': match_id})

        return [self._map_to_entity(row) for row in result]

    def _map_to_entity(self, row) -> Prediction:
        """将数据库行映射为Prediction实体"""
        # 映射逻辑
        pass
```

### 工作单元模式

**UnitOfWork**
```python
# src/database/unit_of_work.py
class UnitOfWork:
    def __init__(self, database_adapter: DatabaseAdapter):
        self.db_adapter = database_adapter
        self.repositories = {}
        self._transaction = None

    async def __aenter__(self):
        """开始事务"""
        self._transaction = await self.db_adapter.begin_transaction()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """结束事务"""
        if exc_type:
            await self._transaction.rollback()
        else:
            await self._transaction.commit()

    def get_repository(self, repository_type: type) -> BaseRepository:
        """获取仓储实例"""
        if repository_type not in self.repositories:
            self.repositories[repository_type] = repository_type(self.db_adapter)

        return self.repositories[repository_type]
```

---

## 🎮 核心基础设施

### 配置管理

**ConfigurationManager**
```python
# src/core/config/configuration_manager.py
class ConfigurationManager:
    def __init__(self, config_file: str = None):
        self._config = {}
        self._load_config(config_file)

    def _load_config(self, config_file: str = None):
        """加载配置"""
        # 默认配置
        self._config = {
            'database': {
                'url': os.getenv('DATABASE_URL', 'postgresql://localhost/football_prediction'),
                'pool_size': int(os.getenv('DB_POOL_SIZE', 10))
            },
            'redis': {
                'url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
                'max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', 10))
            },
            'api': {
                'host': os.getenv('API_HOST', '0.0.0.0'),
                'port': int(os.getenv('API_PORT', 8000))
            }
        }

        # 从文件加载配置
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                self._deep_merge(self._config, file_config)

    def get(self, key: str, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value
```

### 异常处理

**CustomExceptions**
```python
# src/core/exceptions.py
class FootballPredictionException(Exception):
    """基础异常类"""
    pass

class PredictionServiceException(FootballPredictionException):
    """预测服务异常"""
    pass

class DataAccessException(FootballPredictionException):
    """数据访问异常"""
    pass

class ConfigurationException(FootballPredictionException):
    """配置异常"""
    pass

class ValidationException(FootballPredictionException):
    """验证异常"""
    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or []
```

### 日志管理

**LoggerManager**
```python
# src/core/logging/logger_manager.py
import logging
import sys
from typing import Optional

class LoggerManager:
    _loggers = {}

    @classmethod
    def get_logger(cls, name: str, level: str = None) -> logging.Logger:
        """获取或创建日志器"""
        if name not in cls._loggers:
            logger = logging.getLogger(name)

            # 设置日志级别
            log_level = getattr(logging, (level or 'INFO').upper())
            logger.setLevel(log_level)

            # 创建处理器
            if not logger.handlers:
                handler = logging.StreamHandler(sys.stdout)
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                logger.addHandler(handler)

            cls._loggers[name] = logger

        return cls._loggers[name]
```

---

## 📋 架构最佳实践

### 1. 模块解耦
- 使用依赖注入管理对象生命周期
- 通过接口定义而非具体实现进行编程
- 采用事件驱动实现模块间松耦合

### 2. 可测试性
- 所有组件都支持依赖注入，便于单元测试
- 使用Mock对象隔离外部依赖
- 事务边界清晰，便于集成测试

### 3. 可扩展性
- 策略模式支持新预测算法的添加
- 适配器模式支持新数据源的接入
- 事件系统支持新业务逻辑的集成

### 4. 性能优化
- 数据库连接池管理
- Redis缓存热点数据
- 异步I/O处理高并发

### 5. 错误处理
- 分层异常处理机制
- 事务回滚保证数据一致性
- 优雅降级和故障恢复

---

*文档版本: v1.0 | 更新时间: 2025-11-16*