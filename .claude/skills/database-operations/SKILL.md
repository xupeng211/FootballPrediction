---
name: database-operations
description: Manage PostgreSQL database operations including migrations, query optimization, connection pooling, and data backup/restore. Use when handling database tasks, optimizing queries, or managing database connections.
---

# Database Operations Skill

## 概述
专业的数据库操作管理技能，专注于PostgreSQL数据库的优化、迁移、连接管理和数据处理。

## 核心功能

### 1. 数据库连接管理
- **异步连接池**: 高性能连接池管理
- **连接健康检查**: 自动检测和恢复连接
- **负载均衡**: 读写分离和负载分发
- **故障转移**: 主从切换和故障恢复

### 2. 查询优化
- **查询分析**: EXPLAIN ANALYZE查询分析
- **索引优化**: 索引创建和性能调优
- **慢查询监控**: 识别和优化慢查询
- **查询缓存**: 查询结果缓存机制

### 3. 数据迁移
- **Schema迁移**: 数据库结构变更
- **数据迁移**: 大批量数据迁移
- **版本控制**: 数据库版本管理
- **回滚机制**: 迁移失败回滚

### 4. 备份与恢复
- **自动备份**: 定时数据备份
- **增量备份**: 增量备份策略
- **快速恢复**: 快速数据恢复
- **备份验证**: 备份完整性验证

## 数据库架构

### 连接架构
```
应用 → 连接池 → PostgreSQL主库
 ↓      ↓           ↓
连接   连接复用     读写
管理   负载均衡     分离
```

### 数据分层
- **热数据**: Redis缓存层
- **温数据**: PostgreSQL主库
- **冷数据**: 历史数据归档

## 使用方法

### 数据库连接
```python
# 异步数据库连接
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine

class DatabaseManager:
    def __init__(self):
        self.engine = create_async_engine(
            DATABASE_URL,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600
        )

    async def get_connection(self):
        return await self.engine.acquire()
```

### 查询优化
```python
# 查询分析
async def analyze_query(query: str):
    """分析查询性能"""
    explain_query = f"EXPLAIN (ANALYZE, BUFFERS) {query}"
    result = await conn.fetch(explain_query)
    return parse_explain_result(result)

# 索引优化
async def create_optimal_index():
    """创建优化索引"""
    indexes = [
        "CREATE INDEX CONCURRENTLY idx_matches_date ON matches(date)",
        "CREATE INDEX CONCURRENTLY idx_teams_name ON teams(name)",
        "CREATE INDEX CONCURRENTLY idx_predictions_created ON predictions(created_at)"
    ]
    for index in indexes:
        await conn.execute(index)
```

### 数据迁移
```python
# 迁移脚本示例
class Migration_001_AddPredictionConfidence:
    async def up(self):
        """升级数据库"""
        await conn.execute("""
            ALTER TABLE predictions
            ADD COLUMN confidence_score FLOAT,
            ADD COLUMN model_version VARCHAR(50)
        """)

    async def down(self):
        """降级数据库"""
        await conn.execute("""
            ALTER TABLE predictions
            DROP COLUMN confidence_score,
            DROP COLUMN model_version
        """)
```

## 数据库设计

### 核心表结构
```sql
-- 比赛表
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    match_date TIMESTAMP NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    competition_id INTEGER,
    status VARCHAR(20) DEFAULT 'scheduled',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 预测结果表
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    model_version VARCHAR(50),
    predicted_outcome VARCHAR(20),
    home_win_prob FLOAT,
    draw_prob FLOAT,
    away_win_prob FLOAT,
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引优化
CREATE INDEX idx_matches_date ON matches(match_date);
CREATE INDEX idx_matches_teams ON matches(home_team_id, away_team_id);
CREATE INDEX idx_predictions_match ON predictions(match_id);
CREATE INDEX idx_predictions_created ON predictions(created_at);
```

### 分区策略
```sql
-- 按时间分区比赛表
CREATE TABLE matches_y2024m01 PARTITION OF matches
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE matches_y2024m02 PARTITION OF matches
FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
```

## 查询优化技巧

### 1. 索引使用
```sql
-- 复合索引优化
CREATE INDEX idx_matches_team_date ON matches(home_team_id, match_date DESC);

-- 部分索引
CREATE INDEX idx_recent_predictions ON predictions(created_at)
WHERE created_at > NOW() - INTERVAL '30 days';
```

### 2. 查询重写
```sql
-- 原查询（慢）
SELECT * FROM matches
WHERE date_trunc('day', match_date) = '2024-01-15';

-- 优化后（快）
SELECT * FROM matches
WHERE match_date >= '2024-01-15' AND match_date < '2024-01-16';
```

### 3. CTE优化
```sql
-- 使用CTE提高可读性和性能
WITH recent_matches AS (
    SELECT * FROM matches
    WHERE match_date > NOW() - INTERVAL '7 days'
),
team_stats AS (
    SELECT
        home_team_id,
        AVG(home_score) as avg_home_score
    FROM recent_matches
    GROUP BY home_team_id
)
SELECT t.name, ts.avg_home_score
FROM team_stats ts
JOIN teams t ON t.id = ts.home_team_id;
```

## 连接池配置

### SQLAlchemy配置
```python
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)
```

### AsyncPG连接池
```python
import asyncpg

class AsyncPGPool:
    def __init__(self):
        self.pool = None

    async def init_pool(self):
        self.pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=10,
            max_size=20,
            command_timeout=60
        )

    async def execute_query(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
```

## 性能监控

### 查询性能指标
```python
# 查询时间监控
import time
from functools import wraps

def monitor_query_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start_time

        # 记录慢查询
        if duration > 1.0:  # 超过1秒的查询
            logger.warning(f"Slow query detected: {duration:.2f}s - {func.__name__}")

        return result
    return wrapper

@monitor_query_performance
async def get_team_predictions(team_id: int):
    query = """
        SELECT * FROM predictions p
        JOIN matches m ON p.match_id = m.id
        WHERE m.home_team_id = $1 OR m.away_team_id = $1
        ORDER BY m.match_date DESC
        LIMIT 100
    """
    return await conn.fetch(query, team_id)
```

### 数据库指标
```sql
-- 查看活跃连接
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;

-- 查看慢查询
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- 查看索引使用情况
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## 备份策略

### 自动备份脚本
```python
#!/usr/bin/env python3
# scripts/backup_database.py

import subprocess
import datetime
import os

class DatabaseBackup:
    def __init__(self):
        self.db_name = "football_prediction"
        self.backup_dir = "/backups"

    def create_backup(self):
        """创建数据库备份"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{self.backup_dir}/backup_{timestamp}.sql"

        cmd = [
            "pg_dump",
            "-h", "localhost",
            "-U", "football_user",
            "-d", self.db_name,
            "-f", backup_file,
            "--verbose",
            "--no-password"
        ]

        subprocess.run(cmd, check=True)
        return backup_file

    def restore_backup(self, backup_file):
        """恢复数据库备份"""
        cmd = [
            "psql",
            "-h", "localhost",
            "-U", "football_user",
            "-d", self.db_name,
            "-f", backup_file
        ]

        subprocess.run(cmd, check=True)
```

### 定时备份配置
```bash
# crontab -e
# 每天凌晨2点备份
0 2 * * * /usr/bin/python3 /app/scripts/backup_database.py

# 每周日进行完整备份
0 3 * * 0 /usr/bin/python3 /app/scripts/full_backup.py
```

## 数据迁移管理

### 迁移版本控制
```python
# migrations/migration_manager.py
class MigrationManager:
    def __init__(self):
        self.migrations_dir = "migrations"
        self.migrations_table = "schema_migrations"

    async def get_current_version(self):
        """获取当前数据库版本"""
        query = f"SELECT version FROM {self.migrations_table} ORDER BY version DESC LIMIT 1"
        result = await conn.fetchval(query)
        return result or 0

    async def migrate_up(self):
        """执行数据库迁移"""
        current_version = await self.get_current_version()

        for migration_file in self.get_pending_migrations(current_version):
            migration = self.load_migration(migration_file)
            await migration.up()
            await self.record_migration(migration.version)

    async def migrate_down(self, target_version):
        """回滚数据库到指定版本"""
        current_version = await self.get_current_version()

        while current_version > target_version:
            migration = self.load_migration(current_version)
            await migration.down()
            current_version -= 1
```

### 迁移脚本示例
```python
# migrations/002_add_feature_importance.py
class Migration_002_AddFeatureImportance:
    version = 2

    async def up(self):
        """添加特征重要性表"""
        await conn.execute("""
            CREATE TABLE feature_importance (
                id SERIAL PRIMARY KEY,
                model_version VARCHAR(50),
                feature_name VARCHAR(100),
                importance_score FLOAT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

    async def down(self):
        """删除特征重要性表"""
        await conn.execute("DROP TABLE feature_importance")
```

## 故障排查

### 常见问题解决

1. **连接池耗尽**
   ```python
   # 增加连接池大小
   pool_size = 30
   max_overflow = 50

   # 或使用连接池监控
   if pool.status().checkedin == 0:
       logger.warning("Connection pool exhausted")
   ```

2. **死锁检测**
   ```sql
   -- 查看死锁信息
   SELECT blocked_locks.pid AS blocked_pid,
          blocked_activity.usename AS blocked_user,
          blocking_locks.pid AS blocking_pid,
          blocking_activity.usename AS blocking_user,
          blocked_activity.query AS blocked_statement,
          blocking_activity.query AS current_statement_in_blocking_process
   FROM pg_catalog.pg_locks blocked_locks
   JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
   JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
   JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
   WHERE NOT blocked_locks.granted;
   ```

3. **查询优化**
   ```sql
   -- 查看查询执行计划
   EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM matches WHERE date > '2024-01-01';
   ```

## 最佳实践

### 1. 连接管理
- **合理配置**: 根据应用负载配置连接池
- **连接复用**: 避免频繁创建和销毁连接
- **健康检查**: 定期检查连接健康状态
- **优雅关闭**: 应用退出时正确关闭连接

### 2. 查询优化
- **索引策略**: 为常用查询创建合适索引
- **避免全表扫描**: 使用WHERE限制查询范围
- **批量操作**: 减少数据库往返次数
- **查询缓存**: 缓存频繁查询结果

### 3. 数据安全
- **权限最小化**: 应用只使用必要权限
- **SQL注入防护**: 使用参数化查询
- **敏感数据加密**: 敏感字段加密存储
- **审计日志**: 记录重要操作日志

## 相关配置

### PostgreSQL配置
```ini
# postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
max_connections = 200
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

### 应用配置
```python
# src/config.py
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "pool_size": int(os.getenv("DB_POOL_SIZE", 20)),
    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", 30))
}
```

## 监控指标

- **连接数**: 当前活跃连接数
- **查询时间**: 平均查询响应时间
- **慢查询数**: 慢查询统计
- **缓存命中率**: 查询缓存效果
- **数据库大小**: 数据库存储使用情况