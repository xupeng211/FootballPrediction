# Data Engineering Skill

## 技能概述
专业的数据工程技能模块，专注于高性能数据管道设计、数据库优化和缓存策略。

## 核心能力
- **数据库优化**: PostgreSQL性能调优、连接池管理、查询优化
- **缓存策略**: Redis多级缓存、缓存预热、缓存失效策略
- **数据管道**: ETL/ELT流水线、实时数据处理、数据质量监控
- **连接管理**: 异步连接池、连接健康检查、故障恢复
- **数据建模**: 数据库设计优化、索引策略、分区方案
- **监控运维**: 数据库监控、性能分析、容量规划

## 当前应用场景：足球预测系统数据层
- **数据库**: PostgreSQL (主数据库)
- **缓存**: Redis (缓存和队列)
- **连接池**: asyncpg + SQLAlchemy
- **数据源**: FotMob API (外部数据)
- **数据处理**: 特征工程和模型训练数据

## 工具和库
- **asyncpg**: 高性能异步PostgreSQL驱动
- **SQLAlchemy**: 异步ORM和查询构建
- **Redis**: 异步Redis客户端
- **Alembic**: 数据库迁移管理
- **Pandas**: 数据处理和分析
- **Apache Airflow**: 数据工作流调度
- **Prometheus**: 数据库指标监控

## 快速开始（第一层）
```python
import asyncpg
import aioredis
import asyncio

async def create_optimized_connections():
    """创建优化的数据库连接"""

    # PostgreSQL连接池
    pg_pool = await asyncpg.create_pool(
        "postgresql://user:pass@localhost/db",
        min_size=10,
        max_size=20,
        command_timeout=60
    )

    # Redis连接池
    redis_pool = await aioredis.from_url(
        "redis://localhost:6379",
        max_connections=20
    )

    return pg_pool, redis_pool

# 使用连接池
async def fetch_data(pool):
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM matches LIMIT 100")
```

## 深入优化（第二层）
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, text
import asyncio

class DatabaseManager:
    """数据库管理器"""

    def __init__(self, database_url: str):
        self.engine = create_async_engine(
            database_url,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def optimized_query(self):
        """优化查询示例"""
        async with self.SessionLocal() as session:
            # 使用索引优化查询
            stmt = select(Match).options(
                selectinload(Match.home_team),
                selectinload(Match.away_team)
            ).where(
                Match.date >= datetime.now() - timedelta(days=30)
            ).order_by(Match.date.desc()).limit(100)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def batch_insert(self, data: List[dict]):
        """批量插入优化"""
        async with self.SessionLocal() as session:
            try:
                # 批量插入
                await session.execute(
                    insert(Match).values(data)
                )
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise
```

## 高级应用（第三层）
```python
import asyncio
from typing import Any, Dict, List
from dataclasses import dataclass
import json

@dataclass
class CacheStrategy:
    """缓存策略配置"""
    ttl: int = 3600          # 默认1小时
    max_size: int = 1000     # 最大缓存条目
    prefix: str = ""         # 缓存键前缀
    serialize: bool = True   # 是否序列化

class AdvancedCacheManager:
    """高级缓存管理器"""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.local_cache = {}  # L1缓存
        self.strategies = {}   # 不同数据类型的缓存策略
        self.stats = {
            'hits': 0,
            'misses': 0,
            'l1_hits': 0,
            'l2_hits': 0,
            'errors': 0
        }

    async def get(self, key: str, strategy: CacheStrategy = None) -> Any:
        """多层缓存获取"""
        # L1缓存 (内存)
        if key in self.local_cache:
            self.stats['hits'] += 1
            self.stats['l1_hits'] += 1
            return self.local_cache[key]

        # L2缓存 (Redis)
        try:
            async with aioredis.from_url(self.redis_url) as redis:
                value = await redis.get(key)
                if value:
                    self.stats['hits'] += 1
                    self.stats['l2_hits'] += 1
                    data = json.loads(value) if strategy and strategy.serialize else value

                    # 回填L1缓存
                    self._update_l1_cache(key, data, strategy)
                    return data
        except Exception as e:
            self.stats['errors'] += 1

        # 缓存未命中
        self.stats['misses'] += 1
        return None

    async def set(self, key: str, value: Any, strategy: CacheStrategy = None):
        """多层缓存设置"""
        # 更新L1缓存
        self._update_l1_cache(key, value, strategy)

        # 更新L2缓存
        try:
            async with aioredis.from_url(self.redis_url) as redis:
                ttl = strategy.ttl if strategy else 3600
                serialized_value = json.dumps(value, default=str) if strategy and strategy.serialize else value
                await redis.setex(key, ttl, serialized_value)
        except Exception as e:
            self.stats['errors'] += 1

    def _update_l1_cache(self, key: str, value: Any, strategy: CacheStrategy):
        """更新L1缓存"""
        max_size = strategy.max_size if strategy else 1000

        if len(self.local_cache) >= max_size:
            # LRU淘汰策略
            oldest_key = next(iter(self.local_cache))
            del self.local_cache[oldest_key]

        self.local_cache[key] = value
```

## 数据库性能优化

### 1. 索引策略
```python
# 创建优化索引
async def create_optimized_indexes():
    """创建数据库索引"""
    indexes = [
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_date ON matches(date)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_teams ON matches(home_team_id, away_team_id)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_league ON matches(league_id, date)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_features_match_id ON match_features(match_id)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_features_composite ON match_features(match_id, feature_type, created_at)"
    ]

    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            for index_sql in indexes:
                await conn.execute(index_sql)
```

### 2. 查询优化
```python
async def optimized_feature_query(match_ids: List[int]):
    """优化的特征查询"""
    # 使用数组查询避免多次查询
    query = """
    SELECT
        mf.match_id,
        mf.feature_type,
        mf.feature_value,
        m.date,
        ht.name as home_team,
        at.name as away_team
    FROM match_features mf
    JOIN matches m ON mf.match_id = m.id
    JOIN teams ht ON m.home_team_id = ht.id
    JOIN teams at ON m.away_team_id = at.id
    WHERE mf.match_id = ANY($1::int[])
    ORDER BY mf.match_id, mf.feature_type
    """

    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            return await conn.fetch(query, match_ids)
```

### 3. 分区表设计
```python
async def create_partitioned_table():
    """创建分区表"""
    # 按年份分区matches表
    partition_sql = """
    CREATE TABLE IF NOT EXISTS matches (
        id SERIAL,
        home_team_id INTEGER REFERENCES teams(id),
        away_team_id INTEGER REFERENCES teams(id),
        home_score INTEGER,
        away_score INTEGER,
        date TIMESTAMP NOT NULL,
        league_id INTEGER REFERENCES leagues(id),
        created_at TIMESTAMP DEFAULT NOW(),
        PRIMARY KEY (id, date)
    ) PARTITION BY RANGE (date);

    -- 创建年度分区
    CREATE TABLE IF NOT EXISTS matches_2024 PARTITION OF matches
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

    CREATE TABLE IF NOT EXISTS matches_2025 PARTITION OF matches
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
    """

    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            await conn.execute(partition_sql)
```

## Redis缓存策略

### 1. 缓存模式
```python
class CachePatterns:
    """常见缓存模式"""

    @staticmethod
    async def cache_aside(cache_manager: AdvancedCacheManager, key: str, fetch_func, ttl: int = 3600):
        """Cache-Aside模式"""
        # 尝试从缓存获取
        cached_data = await cache_manager.get(key)
        if cached_data:
            return cached_data

        # 缓存未命中，从数据库获取
        data = await fetch_func()

        # 写入缓存
        await cache_manager.set(key, data, CacheStrategy(ttl=ttl))

        return data

    @staticmethod
    async def write_through(cache_manager: AdvancedCacheManager, key: str, data: Any, db_func):
        """Write-Through模式"""
        # 同时写入数据库和缓存
        await db_func(data)
        await cache_manager.set(key, data)

    @staticmethod
    async def write_behind(cache_manager: AdvancedCacheManager, key: str, data: Any, db_func):
        """Write-Behind模式"""
        # 立即更新缓存
        await cache_manager.set(key, data)

        # 异步写入数据库
        asyncio.create_task(db_func(data))
```

### 2. 缓存预热
```python
async def warm_up_cache(cache_manager: AdvancedCacheManager):
    """缓存预热"""
    # 预加载热门数据
    common_queries = [
        "upcoming_matches",
        "team_rankings",
        "league_standings",
        "recent_form"
    ]

    for query_key in common_queries:
        try:
            data = await fetch_common_data(query_key)
            await cache_manager.set(
                f"common:{query_key}",
                data,
                CacheStrategy(ttl=1800)  # 30分钟
            )
        except Exception as e:
            print(f"预热失败 {query_key}: {e}")
```

### 3. 缓存失效策略
```python
class CacheInvalidation:
    """缓存失效策略"""

    @staticmethod
    async def invalidate_by_pattern(cache_manager: AdvancedCacheManager, pattern: str):
        """按模式失效缓存"""
        async with aioredis.from_url(cache_manager.redis_url) as redis:
            keys = await redis.keys(pattern)
            if keys:
                await redis.delete(*keys)

    @staticmethod
    async def smart_invalidation(cache_manager: AdvancedCacheManager, table: str, record_id: int):
        """智能缓存失效"""
        # 失效相关缓存
        patterns = [
            f"*:{table}:{record_id}:*",
            f"*:{table}:list:*",
            f"*:{record_id}:*"
        ]

        for pattern in patterns:
            await CacheInvalidation.invalidate_by_pattern(cache_manager, pattern)
```

## 数据质量监控

### 1. 数据完整性检查
```python
async def data_quality_checks():
    """数据质量检查"""
    checks = {
        'matches_with_null_teams': """
            SELECT COUNT(*) FROM matches
            WHERE home_team_id IS NULL OR away_team_id IS NULL
        """,
        'invalid_scores': """
            SELECT COUNT(*) FROM matches
            WHERE home_score < 0 OR away_score < 0
        """,
        'orphaned_features': """
            SELECT COUNT(*) FROM match_features mf
            LEFT JOIN matches m ON mf.match_id = m.id
            WHERE m.id IS NULL
        """,
        'duplicate_matches': """
            SELECT home_team_id, away_team_id, date, COUNT(*) as cnt
            FROM matches
            GROUP BY home_team_id, away_team_id, date
            HAVING COUNT(*) > 1
        """
    }

    results = {}
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            for check_name, query in checks.items():
                result = await conn.fetchval(query)
                results[check_name] = result

    return results
```

### 2. 性能监控
```python
async def monitor_database_performance():
    """数据库性能监控"""
    metrics = {
        'connection_count': "SELECT count(*) FROM pg_stat_activity",
        'slow_queries': """
            SELECT query, mean_time, calls
            FROM pg_stat_statements
            WHERE mean_time > 1000
            ORDER BY mean_time DESC
            LIMIT 10
        """,
        'table_sizes': """
            SELECT schemaname, tablename,
                   pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """,
        'index_usage': """
            SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
            FROM pg_stat_user_indexes
            ORDER BY idx_scan DESC
        """
    }

    performance_data = {}
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            for metric_name, query in metrics.items():
                if metric_name == 'connection_count':
                    result = await conn.fetchval(query)
                else:
                    result = await conn.fetch(query)
                performance_data[metric_name] = result

    return performance_data
```

## ETL流水线

### 1. 数据抽取
```python
class DataExtractor:
    """数据抽取器"""

    async def extract_from_api(self, api_url: str, params: dict = None):
        """从API抽取数据"""
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params) as response:
                return await response.json()

    async def extract_from_database(self, query: str, params: dict = None):
        """从数据库抽取数据"""
        async with asyncpg.create_pool(DATABASE_URL) as pool:
            async with pool.acquire() as conn:
                return await conn.fetch(query, *params.values() if params else [])
```

### 2. 数据转换
```python
class DataTransformer:
    """数据转换器"""

    @staticmethod
    def normalize_team_data(raw_data: dict) -> dict:
        """标准化球队数据"""
        return {
            'team_id': raw_data.get('id'),
            'name': raw_data.get('name'),
            'league_id': raw_data.get('leagueId'),
            'normalized_name': raw_data.get('name').lower().strip(),
            'created_at': datetime.now()
        }

    @staticmethod
    def calculate_features(match_data: dict) -> List[dict]:
        """计算比赛特征"""
        features = []

        # 基础特征
        features.append({
            'match_id': match_data['id'],
            'feature_type': 'basic',
            'feature_value': {
                'home_advantage': 0.15,
                'team_form_difference': 0.0
            }
        })

        # 历史交锋特征
        features.append({
            'match_id': match_data['id'],
            'feature_type': 'h2h',
            'feature_value': {
                'h2h_home_wins': 0,
                'h2h_away_wins': 0,
                'h2h_draws': 0
            }
        })

        return features
```

### 3. 数据加载
```python
class DataLoader:
    """数据加载器"""

    async def load_batch(self, table: str, data: List[dict], batch_size: int = 1000):
        """批量加载数据"""
        async with asyncpg.create_pool(DATABASE_URL) as pool:
            async with pool.acquire() as conn:
                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]
                    await conn.execute(
                        f"""
                        INSERT INTO {table} ({','.join(batch[0].keys())})
                        VALUES ({','.join([f'${i+1}' for i in range(len(batch[0]))])})
                        """,
                        *[value for item in batch for value in item.values()]
                    )
```

## 监控和告警

### 1. 连接池监控
```python
async def monitor_connection_pools():
    """监控连接池状态"""
    pg_pool = await asyncpg.create_pool(DATABASE_URL)

    pool_stats = {
        'pool_size': pg_pool.get_size(),
        'pool_idle': pg_pool.get_idle_size(),
        'pool_used': pg_pool.get_size() - pg_pool.get_idle_size(),
        'max_connections': pg_pool.get_max_size(),
        'min_connections': pg_pool.get_min_size()
    }

    return pool_stats
```

### 2. 缓存性能监控
```python
def get_cache_performance_report(cache_manager: AdvancedCacheManager) -> dict:
    """获取缓存性能报告"""
    stats = cache_manager.stats
    total_requests = stats['hits'] + stats['misses']

    return {
        'hit_rate': stats['hits'] / total_requests if total_requests > 0 else 0,
        'l1_hit_rate': stats['l1_hits'] / total_requests if total_requests > 0 else 0,
        'l2_hit_rate': stats['l2_hits'] / total_requests if total_requests > 0 else 0,
        'error_rate': stats['errors'] / total_requests if total_requests > 0 else 0,
        'local_cache_size': len(cache_manager.local_cache),
        **stats
    }
```

## 最佳实践

1. **连接池优化**: 合理配置连接池大小，避免连接泄露
2. **缓存策略**: 根据数据访问模式选择合适的缓存策略
3. **查询优化**: 使用索引、分区、批量操作优化性能
4. **数据质量**: 建立数据质量检查和监控机制
5. **故障恢复**: 实现重试机制和降级策略
6. **容量规划**: 监控数据增长趋势，提前规划容量

---
*Last updated: 2025-12-18*
*Target: 足球预测系统数据层优化*