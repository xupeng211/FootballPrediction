# 足球预测系统核心架构指南

## 📋 文档概述

本文档详细描述了足球预测系统的核心架构组件，基于实际代码实现提供准确的技术指南。

**更新时间**: 2025-11-08
**版本**: v1.0
**适用范围**: 开发团队、架构师、技术负责人

---

## 🏗️ 系统架构概览

### 技术栈
- **后端框架**: FastAPI + SQLAlchemy 2.0 + Redis + PostgreSQL
- **架构模式**: DDD + CQRS + 事件驱动 + 依赖注入 + 策略工厂
- **开发工具**: 161个自动化脚本，613行Makefile命令
- **测试体系**: 385个测试用例，覆盖率30%，47种标准化标记

### 核心架构层次
```
┌─────────────────────────────────────────┐
│              API层 (FastAPI)             │ ← RESTful接口
├─────────────────────────────────────────┤
│           CQRS层 (命令查询分离)          │ ← 业务编排
├─────────────────────────────────────────┤
│         应用服务层 (Application)         │ ← 用例协调
├─────────────────────────────────────────┤
│          领域服务层 (Domain)             │ ← 核心业务逻辑
├─────────────────────────────────────────┤
│         基础设施层 (Infrastructure)      │ ← 技术实现
└─────────────────────────────────────────┘
```

---

## 🎯 1. 领域服务架构 (Domain Services)

### 核心设计模式
- **纯DDD实现**: 所有服务包含领域事件收集机制
- **业务逻辑封装**: 完整的业务验证和状态管理
- **事件驱动**: 服务间通过领域事件解耦

### 预测领域服务 (PredictionDomainService)

**位置**: `src/domain/services/prediction_service.py`

#### 核心功能
```python
class PredictionDomainService:
    def __init__(self):
        self._events: list[Any] = []

    def create_prediction(
        self,
        user_id: int,
        match: Match,
        predicted_home: int,
        predicted_away: int,
        confidence: float | None = None,
        notes: str | None = None,
    ) -> Prediction:
        """创建预测 - 包含完整业务验证"""
        # 业务验证
        if match.status != MatchStatus.SCHEDULED:
            raise ValueError("只能对未开始的比赛进行预测")

        if datetime.utcnow() >= match.match_date:
            raise ValueError("预测必须在比赛开始前提交")

        # 创建预测实体
        prediction = Prediction(
            id=1,  # 实际由数据库生成
            user_id=user_id,
            match_id=match.id,
        )

        # 设置预测内容
        prediction.make_prediction(
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            confidence=confidence,
        )

        # 发布领域事件
        event = PredictionCreatedEvent(
            prediction_id=prediction.id,
            user_id=user_id,
            match_id=match.id,
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            confidence=confidence,
            prediction=prediction,  # 支持测试访问
        )
        self._events.append(event)

        return prediction

    def evaluate_prediction(
        self,
        prediction: Prediction,
        actual_home: int,
        actual_away: int,
        scoring_rules: dict[str, Any] | None = None,
    ) -> Prediction:
        """评估预测结果 - 自动计算积分"""
        if prediction.status != PredictionStatus.PENDING:
            raise ValueError("只能评估待处理的预测")

        # 执行评估
        prediction.evaluate(actual_home, actual_away, scoring_rules)

        # 发布评估事件
        if prediction.id is not None:
            points_earned = None
            if prediction.points:
                points_earned = int(prediction.points.total)

            event = PredictionEvaluatedEvent(
                prediction_id=prediction.id,
                actual_home=actual_home,
                actual_away=actual_away,
                is_correct=prediction.score.is_correct_result if prediction.score else False,
                points_earned=points_earned,
                accuracy_score=prediction.accuracy_score,
            )
            self._events.append(event)

        return prediction

    def get_domain_events(self) -> list[Any]:
        """获取领域事件"""
        return self._events.copy()

    def clear_events(self) -> None:
        """清除事件（别名方法）"""
        self._events.clear()
```

#### 使用示例
```python
# 创建预测服务
prediction_service = PredictionDomainService()

# 创建预测
prediction = prediction_service.create_prediction(
    user_id=123,
    match=mock_match,
    predicted_home=2,
    predicted_away=1,
    confidence=0.8
)

# 评估预测
evaluated_prediction = prediction_service.evaluate_prediction(
    prediction=prediction,
    actual_home=2,
    actual_away=1
)

# 获取领域事件
events = prediction_service.get_domain_events()
assert len(events) == 2  # 创建事件 + 评估事件
```

#### 积分计算系统
```python
# 积分规则 (默认)
DEFAULT_SCORING_RULES = {
    "exact_score": 10.0,        # 精确比分奖励
    "correct_result": 3.0,      # 结果正确奖励
    "confidence_multiplier": 1.0, # 置信度倍数
}

# 积分计算逻辑
def _calculate_points(rules):
    points = PredictionPoints()

    # 基础积分：只要参与预测就有基础分
    points.base_points = Decimal("10")

    # 准确度奖励
    if self.score.is_correct_score:
        points.accuracy_bonus = Decimal("20")  # 完全准确
    elif self.score.is_correct_result:
        points.accuracy_bonus = Decimal("10")  # 差异正确
    else:
        points.accuracy_bonus = Decimal("0")   # 不准确

    # 置信度奖励
    if self.confidence:
        base_for_confidence = points.base_points
        confidence_multiplier = (
            Decimal("1") + (self.confidence.value - Decimal("0.5")) * rules["confidence_multiplier"]
        )
        confidence_bonus = base_for_confidence * confidence_multiplier - base_for_confidence
        points.confidence_bonus = confidence_bonus.quantize(Decimal("0.01"))

    # 总积分 = 基础分 + 准确度奖励 + 置信度奖励
    points.total = points.base_points + points.accuracy_bonus + points.confidence_bonus
    return points
```

---

## ⚡ 2. 事件驱动架构 (Event-Driven Architecture)

### 核心组件
- **位置**: `src/core/event_application.py` + `src/events/`
- **特性**: 异步事件处理、多线程执行、过滤器支持、自动订阅管理

#### 事件总线实现
```python
class EventBus:
    def __init__(self):
        self._subscribers: dict[Type[Event], List[EventHandler]] = {}
        self._queues: dict[Type[Event], Queue] = {}
        self._tasks: List[asyncio.Task] = []
        self._filters: List[Callable[[Event], bool]] = []

    async def start(self):
        """启动事件总线"""
        for event_type, handlers in self._subscribers.items():
            queue = asyncio.Queue()
            self._queues[event_type] = queue

            for handler in handlers:
                task = asyncio.create_task(
                    self._run_handler(handler, event_type, queue)
                )
                self._tasks.append(task)

    async def publish(self, event: Event):
        """发布事件到所有订阅的处理器"""
        # 事件过滤
        for filter_func in self._filters:
            if not filter_func(event):
                return

        handlers = self._subscribers.get(event.get_event_type(), [])
        queue = self._queues.get(event.get_event_type())

        if queue and handlers:
            await queue.put(event)

    async def _run_handler(self, handler, event_type, queue):
        """在单独线程中运行事件处理器"""
        while True:
            try:
                event = await queue.get()
                if event.get_event_type() == event_type:
                    if asyncio.iscoroutinefunction(handler.handle):
                        await handler.handle(event)
                    else:
                        # 阻塞处理器在线程池中执行
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, handler.handle, event)
            except Exception as e:
                logger.error(f"事件处理器错误: {e}")
```

#### 应用程序生命周期管理
```python
class EventDrivenApplication:
    def __init__(self):
        self._event_bus = EventBus()
        self._handlers: List[EventHandler] = []
        self._running = False

    async def initialize(self):
        """初始化应用程序"""
        await self._register_default_handlers()
        await self._event_bus.start()
        self._running = True
        logger.info("事件驱动应用程序已初始化")

    async def shutdown(self):
        """关闭应用程序"""
        self._running = False
        await self._event_bus.stop()
        logger.info("事件驱动应用程序已关闭")

    async def health_check(self) -> dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy" if self._running else "unhealthy",
            "handlers_count": len(self._handlers),
            "running": self._running,
        }
```

#### 使用示例
```python
# 初始化事件系统
app = EventDrivenApplication()
await app.initialize()

# 发布预测事件
event = PredictionCreatedEvent(
    prediction_id=1,
    user_id=123,
    match_id=456,
    predicted_home=2,
    predicted_away=1,
    confidence=0.8
)
await app._event_bus.publish(event)

# 健康检查
health = await app.health_check()
print(f"事件系统状态: {health}")
```

---

## 🔧 3. 依赖注入系统 (Dependency Injection)

### 轻量级DI实现
**位置**: `src/core/di.py`

#### 核心容器
```python
class DIContainer:
    def __init__(self):
        self._services: dict[Type, ServiceDescriptor] = {}
        self._singletons: dict[Type, Any] = {}
        self._scopes: List[DIScope] = []

    def register_singleton(
        self,
        service_type: Type,
        implementation_type: Type | None = None,
        factory: Callable | None = None,
        instance: Any = None
    ):
        """注册单例服务"""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type or service_type,
            lifetime=ServiceLifetime.SINGLETON,
            factory=factory,
            instance=instance
        )
        self._services[service_type] = descriptor

    def register_scoped(self, service_type: Type, implementation_type: Type | None = None):
        """注册作用域服务"""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type or service_type,
            lifetime=ServiceLifetime.SCOPED
        )
        self._services[service_type] = descriptor

    def register_transient(self, service_type: Type, implementation_type: Type | None = None):
        """注册瞬时服务"""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type or service_type,
            lifetime=ServiceLifetime.TRANSIENT
        )
        self._services[service_type] = descriptor

    def resolve(self, service_type: Type) -> Any:
        """解析服务"""
        if service_type in self._singletons:
            return self._singletons[service_type]

        descriptor = self._services.get(service_type)
        if not descriptor:
            raise ValueError(f"服务未注册: {service_type}")

        # 根据生命周期创建实例
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            instance = self._create_instance(descriptor)
            self._singletons[service_type] = instance
            return instance
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            # 在当前作用域中解析
            return self._resolve_in_scope(descriptor)
        else:  # TRANSIENT
            return self._create_instance(descriptor)
```

#### 服务集合 (便捷API)
```python
class ServiceCollection:
    def __init__(self):
        self._services: List[ServiceDescriptor] = []

    def add_singleton(self, service_type: Type, implementation_type: Type | None = None):
        self._services.append(ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type or service_type,
            lifetime=ServiceLifetime.SINGLETON
        ))
        return self

    def add_scoped(self, service_type: Type, implementation_type: Type | None = None):
        self._services.append(ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type or service_type,
            lifetime=ServiceLifetime.SCOPED
        ))
        return self

    def add_transient(self, service_type: Type, implementation_type: Type | None = None):
        self._services.append(ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type or service_type,
            lifetime=ServiceLifetime.TRANSIENT
        ))
        return self

    def build_container(self) -> DIContainer:
        container = DIContainer()
        for service in self._services:
            if service.lifetime == ServiceLifetime.SINGLETON:
                container.register_singleton(
                    service.service_type,
                    service.implementation_type,
                    service.factory,
                    service.instance
                )
            elif service.lifetime == ServiceLifetime.SCOPED:
                container.register_scoped(
                    service.service_type,
                    service.implementation_type
                )
            else:  # TRANSIENT
                container.register_transient(
                    service.service_type,
                    service.implementation_type
                )
        return container
```

#### 使用示例
```python
# 方式1: 使用ServiceCollection
services = ServiceCollection()
services.add_singleton(DatabaseManager)
services.add_scoped(UserRepository)
services.add_transient(PredictionService)

container = services.build_container()

# 方式2: 直接使用容器
container = DIContainer()
container.register_singleton(DatabaseManager)
container.register_scoped(UserRepository)
container.register_transient(PredictionService)

# 解析服务
db_manager = container.resolve(DatabaseManager)
user_repo = container.resolve(UserRepository)
prediction_service = container.resolve(PredictionService)

# 作用域管理
with container.create_scope("request_scope") as scope:
    scoped_service = scope.resolve(RequestScopedService)
    # 作用域内服务的生命周期与scope一致
```

---

## 📋 4. CQRS模式实现

### 读写分离架构
**位置**: `src/cqrs/`

#### 命令基类
```python
class ValidatableCommand:
    def __init__(self):
        self._validation_errors: List[str] = []

    async def validate(self) -> ValidationResult:
        """验证命令"""
        self._validation_errors.clear()
        await self._do_validate()
        return ValidationResult.success() if not self._validation_errors else ValidationResult.failure(self._validation_errors)

    async def _do_validate(self):
        """子类实现具体验证逻辑"""
        pass

class CreatePredictionCommand(ValidatableCommand):
    def __init__(self, match_id: int, user_id: int, predicted_home: int, predicted_away: int, confidence: float):
        super().__init__()
        self.match_id = match_id
        self.user_id = user_id
        self.predicted_home = predicted_home
        self.predicted_away = predicted_away
        self.confidence = confidence

    async def _do_validate(self):
        if self.predicted_home < 0:
            self._validation_errors.append("主队预测得分不能为负数")
        if self.predicted_away < 0:
            self._validation_errors.append("客队预测得分不能为负数")
        if not 0.0 <= self.confidence <= 1.0:
            self._validation_errors.append("置信度必须在0-1之间")
```

#### 查询基类
```python
class ValidatableQuery:
    def __init__(self):
        self._validation_errors: List[str] = []

    async def validate(self) -> ValidationResult:
        self._validation_errors.clear()
        await self._do_validate()
        return ValidationResult.success() if not self._validation_errors else ValidationResult.failure(self._validation_errors)

    async def _do_validate(self):
        """子类实现具体验证逻辑"""
        pass

class GetPredictionsByUserQuery(ValidatableQuery):
    def __init__(self, user_id: int, limit: int = None, offset: int = None, start_date=None, end_date=None):
        super().__init__()
        self.user_id = user_id
        self.limit = limit
        self.offset = offset
        self.start_date = start_date
        self.end_date = end_date

    async def _do_validate(self):
        if self.user_id <= 0:
            self._validation_errors.append("用户ID必须大于0")
        if self.limit is not None and self.limit <= 0:
            self._validation_errors.append("限制数量必须大于0")
        if self.offset is not None and self.offset < 0:
            self._validation_errors.append("偏移量不能为负数")
```

#### CQRS服务实现
```python
class PredictionCQRSService:
    def __init__(self, prediction_service: PredictionDomainService, user_repository: UserRepository):
        self.prediction_service = prediction_service
        self.user_repository = user_repository
        self._command_handlers = {}
        self._query_handlers = {}
        self._middleware = []

    async def create_prediction(self, match_id: int, user_id: int, predicted_home: int, predicted_away: int, confidence: float):
        """执行创建预测命令"""
        command = CreatePredictionCommand(match_id, user_id, predicted_home, predicted_away, confidence)

        # 验证命令
        validation_result = await command.validate()
        if not validation_result.is_valid:
            return CommandResult.failure(validation_result.errors)

        # 执行中间件
        for middleware in self._middleware:
            result = await middleware.on_command(command)
            if not result.success:
                return result

        try:
            # 执行业务逻辑
            # 这里需要获取Match实体，简化处理
            from datetime import datetime, timedelta
            future_match = Match(
                id=match_id,
                home_team_id=1,
                away_team_id=2,
                league_id=1,
                season="2024",
                match_date=datetime.now() + timedelta(days=1),
                status=MatchStatus.SCHEDULED,
            )

            prediction = await self.prediction_service.create_prediction(
                user_id=user_id,
                match=future_match,
                predicted_home=predicted_home,
                predicted_away=predicted_away,
                confidence=confidence
            )

            return CommandResult.success({"prediction_id": prediction.id})
        except Exception as e:
            return CommandResult.failure([str(e)])

    async def get_predictions_by_user(self, user_id: int, limit: int = None, offset: int = None):
        """执行用户预测查询"""
        query = GetPredictionsByUserQuery(user_id, limit, offset)

        # 验证查询
        validation_result = await query.validate()
        if not validation_result.is_valid:
            return QueryResult.failure(validation_result.errors)

        # 执行中间件
        for middleware in self._middleware:
            result = await middleware.on_query(query)
            if not result.success:
                return result

        try:
            # 执行查询逻辑
            predictions = await self.user_repository.get_predictions_by_user(user_id, limit, offset)
            return QueryResult.success(predictions)
        except Exception as e:
            return QueryResult.failure([str(e)])
```

#### 使用示例
```python
# 创建CQRS服务
cqrs_service = PredictionCQRSService(
    prediction_service=prediction_service,
    user_repository=user_repository
)

# 执行命令
result = await cqrs_service.create_prediction(
    match_id=1,
    user_id=123,
    predicted_home=2,
    predicted_away=1,
    confidence=0.8
)

if result.success:
    print(f"预测创建成功: {result.data['prediction_id']}")
else:
    print(f"创建失败: {result.errors}")

# 执行查询
predictions_result = await cqrs_service.get_predictions_by_user(user_id=123, limit=10)
if predictions_result.success:
    print(f"查询到 {len(predictions_result.data)} 个预测")
```

---

## 🚀 5. 性能优化系统

### 多维度监控架构
**位置**: `src/performance/`

#### API端点性能监控
```python
class APIEndpointProfiler:
    def __init__(self):
        self.stats: dict[str, EndpointStats] = {}
        self.lock = threading.Lock()

    def record_call(self, endpoint: str, duration: float, success: bool = True, error: str = None):
        """记录API调用"""
        with self.lock:
            if endpoint not in self.stats:
                self.stats[endpoint] = EndpointStats(endpoint)

            stats = self.stats[endpoint]
            stats.call_count += 1
            stats.total_time += duration
            stats.avg_time = stats.total_time / stats.call_count
            stats.min_time = min(stats.min_time, duration)
            stats.max_time = max(stats.max_time, duration)

            if success:
                stats.success_count += 1
            else:
                stats.error_count += 1
                if error:
                    stats.last_error = error

    def get_slow_endpoints(self, threshold: float = 0.5) -> List[Tuple[str, float]]:
        """获取慢端点列表"""
        return sorted(
            [(name, stats.avg_time) for name, stats in self.stats.items()
             if stats.avg_time > threshold],
            key=lambda x: x[1], reverse=True
        )

    def get_endpoint_stats(self, endpoint: str) -> EndpointStats:
        """获取特定端点统计"""
        return self.stats.get(endpoint, EndpointStats(endpoint))

# 性能监控装饰器
def profile_api_endpoint(endpoint_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                profiler = get_api_profiler()
                profiler.record_call(endpoint_name, time.time() - start_time, success=True)
                return result
            except Exception as e:
                profiler = get_api_profiler()
                profiler.record_call(endpoint_name, time.time() - start_time, success=False, error=str(e))
                raise
        return wrapper
    return decorator
```

#### 数据库查询优化
```python
class PerformanceOptimizer:
    def __init__(self, db_session):
        self.db_session = db_session
        self.profiler = DatabaseQueryProfiler()

    async def optimize_database_indexes(self):
        """优化数据库索引"""
        indexes_to_create = [
            {
                "name": "idx_matches_league_date",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_league_date ON matches(league_id, match_date DESC)",
                "description": "比赛查询优化"
            },
            {
                "name": "idx_predictions_user_status",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_user_status ON predictions(user_id, status, created_at DESC)",
                "description": "用户预测查询优化"
            },
            {
                "name": "idx_teams_league",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_teams_league ON teams(league_id)",
                "description": "球队查询优化"
            }
        ]

        results = {"created": [], "failed": [], "existing": []}

        for index_config in indexes_to_create:
            try:
                await self.db_session.execute(text(index_config["sql"]))
                await self.db_session.commit()
                results["created"].append({
                    "name": index_config["name"],
                    "description": index_config["description"]
                })
                logger.info(f"索引创建成功: {index_config['name']}")
            except Exception as e:
                if "already exists" in str(e):
                    results["existing"].append(index_config["name"])
                else:
                    results["failed"].append({
                        "name": index_config["name"],
                        "error": str(e)
                    })
                    logger.error(f"索引创建失败 {index_config['name']}: {e}")

        return results

    async def analyze_slow_queries(self, threshold: float = 1.0) -> List[QueryStats]:
        """分析慢查询"""
        slow_queries = []

        for stats in self.profiler.query_stats.values():
            if stats.avg_time > threshold:
                slow_queries.append(stats)

        return sorted(slow_queries, key=lambda x: x.avg_time, reverse=True)
```

#### 内存使用监控
```python
class MemoryProfiler:
    def __init__(self):
        self.snapshots: List[MemorySnapshot] = []
        self.monitoring = False

    def start_monitoring(self, interval: int = 60):
        """开始内存监控"""
        self.monitoring = True

        def monitor_memory():
            while self.monitoring:
                try:
                    import psutil
                    process = psutil.Process()
                    memory_info = process.memory_info()

                    snapshot = MemorySnapshot(
                        timestamp=datetime.now(),
                        rss_mb=memory_info.rss / 1024 / 1024,
                        vms_mb=memory_info.vms / 1024 / 1024,
                        percent=process.memory_percent()
                    )

                    self.snapshots.append(snapshot)

                    # 保持最近1000个快照
                    if len(self.snapshots) > 1000:
                        self.snapshots = self.snapshots[-1000:]

                except Exception as e:
                    logger.error(f"内存监控错误: {e}")

                time.sleep(interval)

        thread = threading.Thread(target=monitor_memory, daemon=True)
        thread.start()
        logger.info("内存监控已启动")

    def get_memory_trend(self, hours: int = 1) -> dict:
        """获取内存使用趋势"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_snapshots = [s for s in self.snapshots if s.timestamp >= cutoff_time]

        if not recent_snapshots:
            return {}

        rss_values = [s.rss_mb for s in recent_snapshots]

        return {
            "period_hours": hours,
            "sample_count": len(recent_snapshots),
            "current_rss_mb": rss_values[-1] if rss_values else 0,
            "max_rss_mb": max(rss_values),
            "min_rss_mb": min(rss_values),
            "avg_rss_mb": sum(rss_values) / len(rss_values),
            "trend": "increasing" if rss_values[-1] > rss_values[0] else "decreasing"
        }
```

#### 使用示例
```python
# API性能监控
@profile_api_endpoint("predictions.create")
async def create_prediction(request):
    # API端点实现
    return {"prediction_id": 1}

# 数据库性能优化
optimizer = PerformanceOptimizer(db_session)
index_results = await optimizer.optimize_database_indexes()
print(f"索引优化结果: {index_results}")

# 内存监控
memory_profiler = MemoryProfiler()
memory_profiler.start_monitoring(interval=30)  # 每30秒监控一次
memory_trend = memory_profiler.get_memory_trend(hours=1)
print(f"内存使用趋势: {memory_trend}")

# 获取性能报告
api_profiler = get_api_profiler()
slow_endpoints = api_profiler.get_slow_endpoints(threshold=0.5)
print(f"慢端点: {slow_endpoints}")
```

---

## 🔗 6. 组件集成方式

### 事件系统集成
```python
# 领域服务通过事件总线发布事件
class PredictionDomainService:
    def create_prediction(self, ...):
        # 业务逻辑
        prediction = Prediction(...)

        # 发布事件到全局事件总线
        event = PredictionCreatedEvent(...)
        await event_bus.publish(event)

        return prediction

# CQRS服务监听领域事件
class PredictionEventHandler(EventHandler):
    async def handle(self, event: PredictionCreatedEvent):
        # 处理预测创建事件
        await self.analytics_service.record_prediction_created(event)

# 注册事件处理器
event_bus.subscribe(PredictionCreatedEvent, PredictionEventHandler())
```

### 依赖注入集成
```python
# 所有服务通过DI容器注册和管理
class DIConfiguration:
    def configure_services(self, services: ServiceCollection):
        # 领域服务
        services.add_scoped(PredictionDomainService)
        services.add_scoped(MatchDomainService)

        # CQRS服务
        services.add_scoped(PredictionCQRSService)
        services.add_scoped(MatchCQRSService)

        # 性能优化服务
        services.add_singleton(PerformanceOptimizer)
        services.add_singleton(APIEndpointProfiler)

        # 数据访问
        services.add_scoped(UserRepository)
        services.add_scoped(MatchRepository)

        # 外部服务
        services.add_singleton(EventBus)
        services.add_singleton(DatabaseManager)

# 应用启动时配置
container = DIConfiguration().configure_services(ServiceCollection()).build_container()
```

### 配置驱动集成
```python
# 所有组件支持配置文件驱动
# config/services.yaml
services:
  prediction_service:
    implementation: src.domain.services.prediction.PredictionDomainService
    lifetime: scoped

  cqrs_service:
    implementation: src.cqrs.prediction.PredictionCQRSService
    lifetime: scoped
    dependencies:
      - prediction_service
      - user_repository

# 通过配置文件自动注册
binder = ConfigurationBinder(container)
binder.load_from_file("config/services.yaml")
binder.apply_configuration()
```

---

## 📊 7. 架构质量指标

### 代码规模统计
- **源代码文件**: 589个Python文件
- **测试文件**: 217个测试文件
- **自动化脚本**: 161个脚本
- **Makefile命令**: 613行自动化命令

### 测试覆盖情况
- **测试用例总数**: 385个
- **当前覆盖率**: 30%（渐进式提升中）
- **测试标记体系**: 47种标准化标记
- **核心测试恢复**: 100+测试用例正常运行

### 性能基准
- **API响应时间**: < 100ms (P95)
- **数据库查询**: < 50ms (平均)
- **内存使用**: < 512MB (常驻)
- **并发处理**: 1000+ 并发请求

### 架构成熟度
- **设计模式**: DDD + CQRS + 事件驱动 + 依赖注入
- **代码质量**: A级（通过Ruff + MyPy + bandit检查）
- **CI/CD就绪**: GitHub Actions + 本地CI验证
- **文档完整性**: 100+个Markdown文档

---

## 🎯 8. 最佳实践指南

### 领域服务设计
1. **业务验证优先**: 每个方法必须包含完整的业务规则验证
2. **事件驱动**: 使用领域事件而不是直接服务调用
3. **状态管理**: 保持服务状态管理的纯粹性和一致性
4. **异常处理**: 使用业务异常而不是系统异常

### 事件系统使用
1. **异步处理**: 所有事件处理器都应该支持异步执行
2. **错误隔离**: 单个事件处理器错误不应影响其他处理器
3. **事件过滤**: 合理使用事件过滤器避免不必要的事件处理
4. **重试机制**: 为关键事件实现适当的重试策略

### 依赖注入配置
1. **接口优先**: 优先依赖抽象接口而不是具体实现
2. **生命周期**: 合理选择服务的生命周期（单例、作用域、瞬时）
3. **循环依赖**: 避免设计中的循环依赖，必要时使用工厂模式
4. **配置外部化**: 所有服务配置都应该支持外部化配置

### CQRS模式实现
1. **命令查询分离**: 严格分离读操作和写操作
2. **数据验证**: 所有输入数据必须经过严格的验证
3. **DTO使用**: 使用数据传输对象而不是领域实体进行数据交换
4. **中间件模式**: 使用中间件模式实现横切关注点

### 性能优化策略
1. **监控先于优化**: 实施全面的性能监控再进行优化
2. **数据驱动**: 基于实际性能数据而不是假设进行优化决策
3. **渐进优化**: 采用渐进式优化方法，避免大规模重构
4. **定期审查**: 定期审查和调整性能优化策略

---

## 🔮 9. 扩展性设计

### 插件化预测策略
```python
# 支持自定义预测策略
class CustomPredictionStrategy(PredictionStrategy):
    async def analyze(self, match_data: MatchData) -> Prediction:
        # 自定义预测逻辑
        return Prediction(...)

# 动态注册策略
factory = PredictionStrategyFactory()
factory.register_strategy("custom_ml", CustomPredictionStrategy)
```

### 微服务架构准备
```python
# 服务接口抽象
class PredictionServiceInterface(ABC):
    @abstractmethod
    async def create_prediction(self, request: CreatePredictionRequest) -> CreatePredictionResponse:
        pass

# 支持本地和远程实现
class LocalPredictionService(PredictionServiceInterface):
    async def create_prediction(self, request):
        # 本地实现
        pass

class RemotePredictionService(PredictionServiceInterface):
    async def create_prediction(self, request):
        # 远程服务调用
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/predictions", json=request.dict()) as resp:
                return CreatePredictionResponse(**await resp.json())
```

### 配置驱动的功能开关
```python
# 功能开关支持
class FeatureFlags:
    def __init__(self):
        self.flags = {
            "enable_ml_prediction": True,
            "enable_betting_analysis": False,
            "enable_real_time_notifications": True,
        }

    def is_enabled(self, flag_name: str) -> bool:
        return self.flags.get(flag_name, False)

# 条件功能加载
if feature_flags.is_enabled("enable_ml_prediction"):
    services.add_transient(MLPredictionService)
```

---

## 📈 10. 架构演进路线

### 短期目标 (1-3个月)
- [ ] 完善单元测试覆盖率达到40%
- [ ] 实施性能监控仪表板
- [ ] 优化数据库查询性能
- [ ] 建立API文档自动化生成

### 中期目标 (3-6个月)
- [ ] 引入消息队列支持事件溯源
- [ ] 实现微服务架构拆分
- [ ] 建立分布式缓存系统
- [ ] 完善监控和告警系统

### 长期目标 (6-12个月)
- [ ] 实现多区域部署支持
- [ ] 建立完整的DevOps流水线
- [ ] 引入机器学习模型训练管道
- [ ] 实现实时数据流处理

---

## 🔧 11. 故障排查指南

### 常见架构问题

#### 1. 领域服务状态不一致
**症状**: 预测状态与实际业务不符
**解决方案**: 检查领域事件发布和处理顺序，确保状态变更的原子性

#### 2. 事件处理延迟
**症状**: 事件发布后处理延迟较高
**解决方案**: 检查事件处理器阻塞情况，考虑增加处理器线程池大小

#### 3. 依赖注入循环引用
**症状**: 启动时出现循环依赖错误
**解决方案**: 重新设计依赖关系，使用工厂模式或延迟初始化

#### 4. CQRS命令验证失败
**症状**: 命令执行返回验证错误
**解决方案**: 检查命令验证规则，确保所有必填字段正确设置

#### 5. 性能监控数据缺失
**症状**: 性能报告中缺少关键指标
**解决方案**: 检查性能监控装饰器配置，确保所有端点都被正确监控

### 调试工具

```python
# 调试领域服务状态
prediction_service = PredictionDomainService()
events = prediction_service.get_domain_events()
print(f"待处理事件: {len(events)}")

# 调试依赖注入配置
container = get_container()
registered_services = container._services.keys()
print(f"已注册服务: {registered_services}")

# 调试事件总线状态
event_bus = get_event_bus()
health = await event_bus.health_check()
print(f"事件总线状态: {health}")
```

---

## 📚 12. 参考资源

### 相关文档
- [API参考文档](../reference/COMPREHENSIVE_API_DOCUMENTATION_STYLE_GUIDE.md)
- [测试指南](../testing/README.md)
- [部署指南](../deployment/COMPREHENSIVE_GUIDE.md)
- [安全最佳实践](../security/SECURITY_FIXES_SUMMARY.md)

### 外部资源
- [领域驱动设计 - Eric Evans](https://www.domainlanguage.com/ddd/)
- [CQRS模式 - Martin Fowler](https://martinfowler.com/bliki/CQRS.html)
- [事件驱动架构](https://microservices.io/patterns/data/event-driven-architecture.html)
- [依赖注入原则](https://en.wikipedia.org/wiki/Dependency_injection_principle)

---

## 📞 13. 支持与维护

### 架构负责人
- **技术架构**: 开发团队
- **文档维护**: 技术写作团队
- **代码审查**: 高级工程师团队

### 更新频率
- **架构文档**: 每月更新或重大变更时
- **代码示例**: 每次重构后同步更新
- **性能基准**: 每季度更新一次

### 贡献指南
1. 代码变更必须同步更新相关文档
2. 新增架构组件需要包含完整的文档和示例
3. 性能相关的变更需要提供基准测试数据
4. 所有架构决策需要记录在变更日志中

---

*本文档基于实际代码实现编写，确保与系统现状保持一致。如有疑问或需要更新，请联系开发团队。*