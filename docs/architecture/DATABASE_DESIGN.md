# 数据库架构设计

## 📊 数据库选型

### 主数据库：PostgreSQL 15

- **版本**: PostgreSQL 15+
- **优势**:
  - 强大的JSON支持
  - 优秀的并发性能
  - 丰富的地理空间数据类型
  - 强一致性保证

### 缓存层：Redis 7

- **版本**: Redis 7+
- **用途**:
  - 查询结果缓存
  - 会话存储
  - 实时数据缓存
  - 分布式锁

## 🗄️ 核心表结构

### 比赛相关表

```sql
-- 比赛基础信息表
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    league_id INTEGER REFERENCES leagues(id),
    season VARCHAR(10),
    match_date TIMESTAMP,
    venue VARCHAR(100),
    status VARCHAR(20) DEFAULT 'scheduled',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 比赛结果表
CREATE TABLE match_results (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    home_score INTEGER,
    away_score INTEGER,
    home_halftime_score INTEGER,
    away_halftime_score INTEGER,
    match_events JSONB,
    statistics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 球队和联赛表

```sql
-- 球队表
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    logo_url VARCHAR(255),
    founded_year INTEGER,
    stadium VARCHAR(100),
    capacity INTEGER,
    league_id INTEGER REFERENCES leagues(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 联赛表
CREATE TABLE leagues (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    country VARCHAR(50),
    tier INTEGER,
    logo_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 预测相关表

```sql
-- 预测表
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    model_name VARCHAR(50),
    predicted_home_score DECIMAL(3,1),
    predicted_away_score DECIMAL(3,1),
    home_win_probability DECIMAL(5,4),
    draw_probability DECIMAL(5,4),
    away_win_probability DECIMAL(5,4),
    confidence_score DECIMAL(5,4),
    features_used JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 📈 性能优化

### 索引策略

```sql
-- 时间查询优化
CREATE INDEX idx_matches_date ON matches(match_date);
CREATE INDEX idx_matches_season ON matches(season);

-- 关联查询优化
CREATE INDEX idx_matches_teams ON matches(home_team_id, away_team_id);
CREATE INDEX idx_predictions_match ON predictions(match_id);

-- JSONB字段索引
CREATE INDEX idx_match_results_events ON match_results USING GIN(match_events);
CREATE INDEX idx_predictions_features ON predictions USING GIN(features_used);
```

### 分区策略

```sql
-- 按年份分区比赛表
CREATE TABLE matches_2024 PARTITION OF matches
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE matches_2025 PARTITION OF matches
FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

## 🔍 查询优化

### 常用查询模式

```sql
-- 获取球队最近表现
SELECT
    m.match_date,
    mr.home_score,
    mr.away_score,
    CASE
        WHEN mr.home_score > mr.away_score THEN 'win'
        WHEN mr.home_score = mr.away_score THEN 'draw'
        ELSE 'lose'
    END as result
FROM matches m
JOIN match_results mr ON m.id = mr.match_id
WHERE (m.home_team_id = ? OR m.away_team_id = ?)
AND m.match_date >= NOW() - INTERVAL '30 days'
ORDER BY m.match_date DESC;

-- 获取预测准确率
SELECT
    model_name,
    COUNT(*) as total_predictions,
    AVG(
        CASE
            WHEN ABS(predicted_home_score - actual_home_score) <= 1
            AND ABS(predicted_away_score - actual_away_score) <= 1
            THEN 1 ELSE 0 END
    ) * 100 as accuracy_percentage
FROM predictions p
JOIN match_results mr ON p.match_id = mr.match_id
WHERE p.created_at >= NOW() - INTERVAL '30 days'
GROUP BY model_name;
```

## 🗃️ 数据备份策略

### 定期备份

```bash
# 每日全量备份
pg_dump -h localhost -U postgres -d football_prediction \
    > backup_$(date +%Y%m%d).sql

# 增量备份（WAL归档）
archive_command = 'cp %p /backup/wal/%f'
```

### 数据恢复

```bash
# 从备份恢复
psql -h localhost -U postgres -d football_prediction \
    < backup_20231101.sql
```

## 📊 缓存设计

### Redis缓存结构

```
football_prediction:matches:{match_id}     # 比赛详情缓存
football_prediction:teams:{team_id}       # 球队信息缓存
football_prediction:predictions:latest     # 最新预测缓存
football_prediction:statistics:daily      # 每日统计缓存
```

### 缓存过期策略

- 比赛数据：15分钟
- 球队信息：1小时
- 预测结果：30分钟
- 统计数据：6小时

## 🔗 连接池配置

```python
# SQLAlchemy连接池
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600,
    echo=False
)
```

更多详细信息请参考：
- [数据库查询优化指南](../database/query_optimization_guide.md)
- [性能监控配置](../monitoring.md)