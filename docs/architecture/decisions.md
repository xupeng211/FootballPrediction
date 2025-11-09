# 技术决策记录 (Architecture Decision Records)

## 📋 ADR-001: 采用异步架构 (Async Architecture)

**状态**: 已接受
**日期**: 2024-01-15
**决策者**: 架构团队

### 上下文
足球预测系统需要处理大量的并发请求，包括实时数据更新、预测计算和用户交互。传统的同步架构在高并发场景下性能瓶颈明显。

### 决策
采用Python asyncio和async/await语法，构建全异步的Web应用架构。

### 理由
1. **高并发支持**: 单线程事件循环可以处理数千个并发连接
2. **资源效率**: 相比线程池，异步I/O占用更少的系统资源
3. **生态成熟**: FastAPI、SQLAlchemy 2.0等主流框架都支持异步
4. **未来兼容**: 异步架构更适配现代云原生环境

### 后果
- ✅ **性能提升**: 响应时间显著改善，吞吐量大幅提升
- ✅ **资源节约**: 服务器资源使用效率提高
- ⚠️ **学习曲线**: 开发团队需要适应异步编程模式
- ⚠️ **调试复杂性**: 异步代码的调试和测试相对复杂

### 实施细节
```python
# 异步Web服务示例
@app.post("/predictions")
async def create_prediction(request: PredictionRequest):
    # 异步数据库操作
    async with get_async_session() as session:
        prediction = await prediction_service.create_async(session, request)

    # 异步缓存更新
    await cache.set_async(f"prediction:{prediction.id}", prediction)

    # 异步事件发布
    await event_bus.publish_async(PredictionCreatedEvent(prediction))

    return prediction
```

---

## 📋 ADR-002: 选择CQRS架构模式 (CQRS Pattern)

**状态**: 已接受
**日期**: 2024-01-20
**决策者**: 架构团队

### 上下文
系统需要同时支持复杂的业务写操作和高性能的读操作。传统的CRUD模式难以优化读写性能，且业务逻辑和数据查询逻辑混合在一起。

### 决策
实施命令查询责任分离（CQRS）模式，将读操作和写操作分离处理。

### 理由
1. **性能优化**: 读操作和写操作可以独立优化和扩展
2. **业务清晰**: 命令处理业务逻辑，查询专注数据获取
3. **扩展性**: 可以使用不同的数据存储技术处理读写
4. **事件溯源**: 为实现事件溯源架构奠定基础

### 后果
- ✅ **查询性能**: 专门优化的查询处理，响应时间更快
- ✅ **业务一致性**: 命令处理保证业务规则和数据一致性
- ✅ **团队协作**: 读写的开发可以并行进行
- ⚠️ **复杂度增加**: 系统架构更加复杂，需要更多的代码
- ⚠️ **数据同步**: 读写模型的数据同步需要额外处理

### 实施细节
```python
# 命令处理器
class CreatePredictionCommandHandler:
    async def handle(self, command: CreatePredictionCommand) -> Prediction:
        # 业务规则验证
        if not self.validate_business_rules(command):
            raise BusinessException("业务规则验证失败")

        # 创建领域对象
        prediction = Prediction.create(command.data)

        # 持久化
        await self.repository.save_async(prediction)

        # 发布事件
        await self.event_bus.publish_async(PredictionCreatedEvent(prediction))

        return prediction

# 查询处理器
class GetPredictionQueryHandler:
    async def handle(self, query: GetPredictionQuery) -> Prediction:
        # 从缓存获取
        cached = await self.cache.get_async(f"prediction:{query.id}")
        if cached:
            return cached

        # 从数据库查询
        prediction = await self.read_repository.find_by_id_async(query.id)

        # 缓存结果
        await self.cache.set_async(f"prediction:{query.id}", prediction, ttl=300)

        return prediction
```

---

## 📋 ADR-003: 使用Redis作为分布式缓存 (Redis Distributed Cache)

**状态**: 已接受
**日期**: 2024-02-01
**决策者**: 架构团队

### 上下文
系统需要频繁访问预测结果、比赛数据和用户信息。每次请求都访问数据库会导致性能瓶颈，且数据库成为系统的单点故障。

### 决策
采用Redis作为分布式缓存层，实现多级缓存策略。

### 理由
1. **高性能**: Redis内存数据库提供毫秒级响应时间
2. **数据结构丰富**: 支持字符串、哈希、列表、集合等多种数据结构
3. **持久化**: 支持RDB和AOF两种持久化方式
4. **集群支持**: Redis Cluster提供高可用和水平扩展
5. **生态成熟**: Python有成熟的Redis客户端库

### 后果
- ✅ **性能提升**: 缓存命中时响应时间从毫秒级降低到微秒级
- ✅ **可用性**: 缓存层降低了数据库压力，提高系统整体可用性
- ✅ **扩展性**: Redis集群支持水平扩展
- ⚠️ **数据一致性**: 需要处理缓存与数据库的数据一致性问题
- ⚠️ **运维复杂**: Redis集群的运维和监控需要额外工作

### 实施细节
```python
# 缓存管理器
class CacheManager:
    def __init__(self, redis_pool):
        self.redis = redis_pool
        self.default_ttl = 3600  # 1小时

    async def get_async(self, key: str) -> Optional[Any]:
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"缓存获取失败: {e}")
            return None

    async def set_async(self, key: str, value: Any, ttl: Optional[int] = None):
        try:
            ttl = ttl or self.default_ttl
            data = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, data)
        except Exception as e:
            logger.error(f"缓存设置失败: {e}")

    # 缓存失效策略
    async def invalidate_pattern(self, pattern: str):
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

# 缓存装饰器
@cache_result(ttl=1800)  # 30分钟
async def get_prediction_stats(match_id: int) -> Dict:
    # 复杂的统计计算
    stats = await calculate_complex_stats(match_id)
    return stats
```

---

## 📋 ADR-004: 实现领域驱动设计 (Domain-Driven Design)

**状态**: 已接受
**日期**: 2024-02-15
**决策者**: 架构团队

### 上下文
足球预测系统的业务逻辑复杂，涉及多个业务概念和规则。传统的三层架构中，业务逻辑分散在服务层和数据访问层，难以维护和扩展。

### 决策
采用领域驱动设计（DDD），建立清晰的领域模型和业务边界。

### 理由
1. **业务中心**: 以业务领域为中心，技术为业务服务
2. **知识共享**: 统一的领域语言便于团队沟通
3. **复杂度管理**: 通过聚合根和领域服务管理业务复杂度
4. **可测试性**: 领域逻辑独立于基础设施，易于单元测试

### 后果
- ✅ **业务清晰**: 领域模型清晰表达业务概念和规则
- ✅ **可维护性**: 业务逻辑集中，易于理解和修改
- ✅ **团队协作**: 统一的语言和模型促进团队协作
- ⚠️ **学习成本**: DDD概念和模式需要团队学习
- ⚠️ **过度设计**: 简单业务可能存在过度设计风险

### 实施细节
```python
# 领域模型 - 比赛聚合根
class Match(AggregateRoot):
    def __init__(self, id: int, home_team: Team, away_team: Team, match_time: datetime):
        super().__init__(id)
        self.home_team = home_team
        self.away_team = away_team
        self.match_time = match_time
        self.status = MatchStatus.SCHEDULED
        self.score = MatchScore(0, 0)
        self.prediction_deadline = match_time - timedelta(hours=1)

    def update_score(self, home_score: int, away_score: int) -> None:
        """更新比分"""
        if self.status != MatchStatus.IN_PROGRESS:
            raise DomainException("比赛未进行中，无法更新比分")

        old_score = self.score
        self.score = MatchScore(home_score, away_score)

        # 发布领域事件
        self.add_domain_event(MatchScoreUpdatedEvent(
            match_id=self.id,
            old_score=old_score,
            new_score=self.score
        ))

    def can_predict(self) -> bool:
        """检查是否可以预测"""
        return datetime.now() < self.prediction_deadline

# 领域服务
class PredictionService:
    def __init__(self, match_repository: MatchRepository):
        self.match_repository = match_repository

    async def create_prediction(self, user_id: int, match_id: int, prediction: PredictionData) -> Prediction:
        # 获取比赛聚合
        match = await self.match_repository.find_by_id(match_id)

        # 业务规则验证
        if not match.can_predict():
            raise DomainException("已过预测截止时间")

        if await self.has_user_predicted(user_id, match_id):
            raise DomainException("用户已对此比赛进行预测")

        # 创建预测聚合
        prediction = Prediction.create(user_id, match_id, prediction)

        return prediction

# 仓储接口
class MatchRepository(ABC):
    @abstractmethod
    async def find_by_id(self, match_id: int) -> Match:
        pass

    @abstractmethod
    async def save(self, match: Match) -> None:
        pass
```

---

## 📋 ADR-005: 使用PostgreSQL作为主数据库 (PostgreSQL Database)

**状态**: 已接受
**日期**: 2024-03-01
**决策者**: 架构团队

### 上下文
系统需要一个可靠的关系型数据库来存储业务数据，包括用户信息、比赛数据、预测结果等。需要在性能、功能、可靠性等方面进行权衡。

### 决策
选择PostgreSQL作为主数据库，配合使用SQLAlchemy 2.0 ORM。

### 理由
1. **ACID特性**: 完整的事务支持，保证数据一致性
2. **JSON支持**: 原生支持JSON数据类型，适合存储复杂业务数据
3. **性能优秀**: 在复杂查询和大数据量场景下性能优异
4. **扩展性**: 支持多种扩展，如PostGIS、pg_stat_statements等
5. **开源生态**: 活跃的开源社区和丰富的工具支持

### 后果
- ✅ **数据一致性**: ACID事务保证数据完整性
- ✅ **查询能力**: 强大的SQL查询和分析能力
- ✅ **扩展性**: 丰富的扩展和插件生态
- ✅ **工具支持**: 成熟的开发和管理工具
- ⚠️ **运维复杂**: 相比NoSQL数据库，运维相对复杂
- ⚠️ **成本**: 在云环境中成本相对较高

### 实施细节
```python
# 数据库模型
class Base(DeclarativeBase):
    """数据库模型基类"""
    pass

class Match(Base):
    __tablename__ = "matches"

    id = mapped_column(Integer, primary_key=True)
    home_team_id = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    league_id = mapped_column(Integer, ForeignKey("leagues.id"), nullable=False)
    match_time = mapped_column(DateTime, nullable=False)
    status = mapped_column(Enum(MatchStatus), nullable=False, default=MatchStatus.SCHEDULED)

    # JSON字段存储复杂数据
    metadata = mapped_column(JSON, default=dict)
    statistics = mapped_column(JSON, default=dict)

    # 关系定义
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    league = relationship("League")
    predictions = relationship("Prediction", back_populates="match")

    # 索引定义
    __table_args__ = (
        Index("idx_match_time_status", "match_time", "status"),
        Index("idx_team_match", "home_team_id", "away_team_id"),
        Index("idx_league_matches", "league_id", "match_time"),
    )

# 异步数据库会话
async def get_async_session() -> AsyncSession:
    """获取异步数据库会话"""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# 仓储实现
class SqlAlchemyMatchRepository(MatchRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, match_id: int) -> Match:
        result = await self.session.execute(
            select(Match).where(Match.id == match_id).options(
                selectinload(Match.home_team),
                selectinload(Match.away_team),
                selectinload(Match.league)
            )
        )
        match = result.scalar_one_or_none()
        if not match:
            raise NotFoundException(f"比赛 {match_id} 不存在")
        return match

    async def save(self, match: Match) -> None:
        self.session.add(match)
        await self.session.flush()
        await self.session.refresh(match)
```

---

## 📋 ADR-006: 采用事件驱动架构 (Event-Driven Architecture)

**状态**: 已接受
**日期**: 2024-03-15
**决策者**: 架构团队

### 上下文
系统中有多个业务场景需要异步处理，如预测结果的计算、用户通知的发送、统计数据的更新等。同步处理会导致响应时间变长，且不同服务之间的耦合度高。

### 决策
实现事件驱动架构，通过领域事件实现系统的松耦合和异步处理。

### 理由
1. **解耦合**: 发布者和订阅者之间松耦合
2. **异步处理**: 提高系统响应时间和吞吐量
3. **可扩展性**: 新的事件处理器可以轻松添加
4. **最终一致性**: 适合分布式系统的一致性要求

### 后果
- ✅ **系统解耦**: 各模块之间通过事件通信，降低耦合度
- ✅ **性能提升**: 主流程异步处理，响应时间更快
- ✅ **可扩展性**: 新功能可以通过添加事件处理器实现
- ⚠️ **复杂性**: 事件流追踪和调试相对复杂
- ⚠️ **一致性**: 最终一致性需要额外的处理机制

### 实施细节
```python
# 领域事件基类
class DomainEvent:
    def __init__(self, aggregate_id: str, occurred_at: datetime = None):
        self.aggregate_id = aggregate_id
        self.occurred_at = occurred_at or datetime.utcnow()
        self.event_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "aggregate_id": self.aggregate_id,
            "occurred_at": self.occurred_at.isoformat(),
            "event_type": self.__class__.__name__,
            "data": self.__dict__
        }

# 具体事件
class PredictionCreatedEvent(DomainEvent):
    def __init__(self, prediction_id: int, user_id: int, match_id: int, prediction_data: Dict):
        super().__init__(f"prediction_{prediction_id}")
        self.prediction_id = prediction_id
        self.user_id = user_id
        self.match_id = match_id
        self.prediction_data = prediction_data

class MatchScoreUpdatedEvent(DomainEvent):
    def __init__(self, match_id: int, old_score: MatchScore, new_score: MatchScore):
        super().__init__(f"match_{match_id}")
        self.match_id = match_id
        self.old_score = old_score
        self.new_score = new_score

# 事件总线
class EventBus:
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent):
        event_type = event.__class__.__name__
        if event_type in self.handlers:
            tasks = []
            for handler in self.handlers[event_type]:
                tasks.append(self._handle_event(handler, event))
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_event(self, handler: Callable, event: DomainEvent):
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.error(f"事件处理失败: {e}", exc_info=True)

# 事件处理器
class PredictionStatisticsHandler:
    async def handle(self, event: PredictionCreatedEvent):
        """处理预测创建事件，更新统计信息"""
        # 异步更新用户预测统计
        await update_user_prediction_stats(event.user_id)

        # 异步更新比赛预测统计
        await update_match_prediction_stats(event.match_id)

        # 异步发送通知
        await send_prediction_notification(event.user_id, event.prediction_id)

class PredictionAccuracyHandler:
    async def handle(self, event: MatchScoreUpdatedEvent):
        """处理比分更新事件，计算预测准确率"""
        # 获取该比赛的所有预测
        predictions = await get_predictions_by_match(event.match_id)

        # 计算预测准确率
        for prediction in predictions:
            accuracy = calculate_prediction_accuracy(prediction, event.new_score)
            await update_prediction_accuracy(prediction.id, accuracy)

            # 如果准确率有显著变化，发送通知
            if accuracy.is_significant_change():
                await send_accuracy_notification(prediction.user_id, accuracy)

# 领域服务中使用事件
class PredictionService:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def create_prediction(self, data: PredictionData) -> Prediction:
        # 业务逻辑处理
        prediction = Prediction.create(data)

        # 保存到数据库
        await self.repository.save(prediction)

        # 发布领域事件
        event = PredictionCreatedEvent(
            prediction_id=prediction.id,
            user_id=prediction.user_id,
            match_id=prediction.match_id,
            prediction_data=data.dict()
        )
        await self.event_bus.publish(event)

        return prediction
```

---

## 📋 总结

这些技术决策共同构建了足球预测系统的技术架构基础：

1. **异步架构**提供了高性能的处理能力
2. **CQRS模式**优化了读写性能和业务逻辑分离
3. **Redis缓存**显著提升了系统响应速度
4. **DDD设计**确保了业务逻辑的清晰和可维护性
5. **PostgreSQL**提供了可靠的数据存储和查询能力
6. **事件驱动**实现了系统的解耦和异步处理

每个决策都有其权衡和后果，但整体上为系统提供了良好的技术基础，支持系统的长期发展和演进。