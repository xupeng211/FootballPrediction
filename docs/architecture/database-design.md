# 数据库设计文档

## 📋 概述

足球预测系统采用PostgreSQL作为主数据库，设计了符合业务需求的数据模型。数据库设计遵循第三范式（3NF），同时通过适当的反范式化优化查询性能。

---

## 🏗️ 数据库架构

### 核心设计原则
1. **业务驱动**: 数据模型基于足球预测业务需求设计
2. **性能优化**: 合理使用索引和分区策略
3. **扩展性**: 支持水平扩展和数据分片
4. **数据完整性**: 外键约束和业务规则验证
5. **审计追踪**: 关键数据的变更历史记录

### 技术特性
- **版本**: PostgreSQL 13+
- **字符集**: UTF-8
- **时区**: UTC
- **连接池**: 异步连接池管理
- **事务级别**: READ COMMITTED
- **备份策略**: 每日全量备份 + WAL归档

---

## 📊 数据库表结构

### 1. 用户管理模块

#### users (用户表)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    phone VARCHAR(20),
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    is_admin BOOLEAN DEFAULT false,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT users_username_length CHECK (LENGTH(username) >= 3),
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- 索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_users_created_at ON users(created_at);
```

#### user_profiles (用户配置表)
```sql
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    favorite_team_id INTEGER REFERENCES teams(id),
    prediction_preferences JSONB DEFAULT '{}',
    notification_settings JSONB DEFAULT '{}',
    privacy_settings JSONB DEFAULT '{}',
    statistics JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id)
);

-- 索引
CREATE INDEX idx_user_profiles_favorite_team ON user_profiles(favorite_team_id);
```

### 2. 比赛数据模块

#### teams (球队表)
```sql
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    logo_url VARCHAR(500),
    founded_year INTEGER,
    country VARCHAR(100),
    league_id INTEGER REFERENCES leagues(id),
    home_venue VARCHAR(200),
    website VARCHAR(500),
    social_media JSONB DEFAULT '{}',
    statistics JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT teams_name_unique UNIQUE(name, country)
);

-- 索引
CREATE INDEX idx_teams_league ON teams(league_id);
CREATE INDEX idx_teams_country ON teams(country);
CREATE INDEX idx_teams_active ON teams(is_active);
```

#### leagues (联赛表)
```sql
CREATE TABLE leagues (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    country VARCHAR(100),
    tier INTEGER NOT NULL,
    season_start_month INTEGER,
    season_end_month INTEGER,
    logo_url VARCHAR(500),
    website VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT leagues_name_country_unique UNIQUE(name, country),
    CONSTRAINT leagues_tier_positive CHECK (tier > 0)
);

-- 索引
CREATE INDEX idx_leagues_country ON leagues(country);
CREATE INDEX idx_leagues_tier ON leagues(tier);
CREATE INDEX idx_leagues_active ON leagues(is_active);
```

#### matches (比赛表)
```sql
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    home_team_id INTEGER NOT NULL REFERENCES teams(id),
    away_team_id INTEGER NOT NULL REFERENCES teams(id),
    league_id INTEGER NOT NULL REFERENCES leagues(id),
    match_time TIMESTAMP WITH TIME ZONE NOT NULL,
    venue VARCHAR(200),
    status VARCHAR(50) NOT NULL DEFAULT 'SCHEDULED',
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    home_half_score INTEGER,
    away_half_score INTEGER,
    duration_minutes INTEGER,
    attendance INTEGER,
    referee VARCHAR(100),
    weather JSONB DEFAULT '{}',
    odds JSONB DEFAULT '{}',
    statistics JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT matches_different_teams CHECK (home_team_id != away_team_id),
    CONSTRAINT matches_scores_positive CHECK (home_score >= 0 AND away_score >= 0)
);

-- 索引
CREATE INDEX idx_matches_datetime ON matches(match_time);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_home_team ON matches(home_team_id);
CREATE INDEX idx_matches_away_team ON matches(away_team_id);
CREATE INDEX idx_matches_league ON matches(league_id);
CREATE INDEX idx_matches_team_time ON matches(home_team_id, match_time);
CREATE INDEX idx_matches_status_time ON matches(status, match_time);

-- 分区表（按月分区，提高查询性能）
-- CREATE TABLE matches_y2024m01 PARTITION OF matches
-- FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### 3. 预测模块

#### predictions (预测表)
```sql
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    match_id INTEGER NOT NULL REFERENCES matches(id),
    home_score_prediction INTEGER NOT NULL,
    away_score_prediction INTEGER NOT NULL,
    confidence_score DECIMAL(5,4) NOT NULL,
    prediction_type VARCHAR(50) NOT NULL DEFAULT 'EXACT_SCORE',
    strategy_used VARCHAR(100),
    model_version VARCHAR(50),
    input_features JSONB DEFAULT '{}',
    calculation_details JSONB DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    result_status VARCHAR(50),
    accuracy_score DECIMAL(5,4),
    points_earned INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, match_id),
    CONSTRAINT predictions_confidence_range CHECK (confidence_score >= 0 AND confidence_score <= 1),
    CONSTRAINT predictions_accuracy_range CHECK (accuracy_score >= 0 AND accuracy_score <= 1)
);

-- 索引
CREATE INDEX idx_predictions_user ON predictions(user_id);
CREATE INDEX idx_predictions_match ON predictions(match_id);
CREATE INDEX idx_predictions_status ON predictions(status);
CREATE INDEX idx_predictions_created_at ON predictions(created_at);
CREATE INDEX idx_predictions_user_match ON predictions(user_id, match_id);
CREATE INDEX idx_predictions_confidence ON predictions(confidence_score DESC);
```

#### prediction_results (预测结果表)
```sql
CREATE TABLE prediction_results (
    id SERIAL PRIMARY KEY,
    prediction_id INTEGER NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
    actual_home_score INTEGER NOT NULL,
    actual_away_score INTEGER NOT NULL,
    is_correct BOOLEAN NOT NULL,
    points_difference INTEGER,
    result_calculation_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    bonus_points INTEGER DEFAULT 0,
    total_points INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT prediction_results_unique UNIQUE(prediction_id)
);

-- 索引
CREATE INDEX idx_prediction_results_correct ON prediction_results(is_correct);
CREATE INDEX idx_prediction_results_points ON prediction_results(total_points DESC);
```

### 4. 统计和分析模块

#### user_statistics (用户统计表)
```sql
CREATE TABLE user_statistics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_predictions INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0,
    accuracy_rate DECIMAL(5,4) DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    favorite_team_predictions INTEGER DEFAULT 0,
    last_prediction_date TIMESTAMP WITH TIME ZONE,
    ranking_position INTEGER,
    ranking_percentile DECIMAL(5,4),
    statistics_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, statistics_date),
    CONSTRAINT user_statistics_accuracy_rate CHECK (accuracy_rate >= 0 AND accuracy_rate <= 1)
);

-- 索引
CREATE INDEX idx_user_statistics_user_date ON user_statistics(user_id, statistics_date);
CREATE INDEX idx_user_statistics_date ON user_statistics(statistics_date);
CREATE INDEX idx_user_statistics_ranking ON user_statistics(ranking_position);
```

#### match_statistics (比赛统计表)
```sql
CREATE TABLE match_statistics (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    total_predictions INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0,
    average_confidence DECIMAL(5,4) DEFAULT 0,
    prediction_accuracy DECIMAL(5,4) DEFAULT 0,
    popular_prediction JSONB DEFAULT '{}',
    outcome_surprise_score DECIMAL(5,4),
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(match_id),
    CONSTRAINT match_statistics_accuracy CHECK (prediction_accuracy >= 0 AND prediction_accuracy <= 1)
);

-- 索引
CREATE INDEX idx_match_statistics_accuracy ON match_statistics(prediction_accuracy DESC);
CREATE INDEX idx_match_statistics_surprise ON match_statistics(outcome_surprise_score DESC);
```

### 5. 系统管理模块

#### system_logs (系统日志表)
```sql
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    module VARCHAR(100),
    user_id INTEGER REFERENCES users(id),
    request_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    session_id VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX idx_system_logs_module ON system_logs(module);
CREATE INDEX idx_system_logs_user ON system_logs(user_id);

-- 分区表（按日分区）
-- CREATE TABLE system_logs_y2024m01 PARTITION OF system_logs
-- FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

#### audit_logs (审计日志表)
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id INTEGER NOT NULL,
    operation VARCHAR(20) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],
    user_id INTEGER REFERENCES users(id),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_audit_logs_table_record ON audit_logs(table_name, record_id);
CREATE INDEX idx_audit_logs_operation ON audit_logs(operation);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
```

---

## 🔧 数据库优化策略

### 1. 索引优化
```sql
-- 复合索引，优化常用查询
CREATE INDEX idx_predictions_user_match_status ON predictions(user_id, match_id, status);
CREATE INDEX idx_matches_league_status_time ON matches(league_id, status, match_time);

-- 部分索引，优化查询性能
CREATE INDEX idx_users_active_verified ON users(is_active, is_verified) WHERE is_active = true;

-- 函数索引，优化JSON字段查询
CREATE INDEX idx_predictions_features_gml ON predictions USING GIN (input_features);
CREATE INDEX idx_match_statistics_popular_gml ON match_statistics USING GIN (popular_prediction);
```

### 2. 查询优化
```sql
-- 使用CTE优化复杂查询
WITH user_prediction_stats AS (
    SELECT
        user_id,
        COUNT(*) as total_predictions,
        COUNT(*) FILTER (WHERE pr.result_status = 'CORRECT') as correct_predictions,
        AVG(pr.confidence_score) as avg_confidence
    FROM predictions pr
    WHERE pr.created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY user_id
)
SELECT
    u.id,
    u.username,
    stats.total_predictions,
    stats.correct_predictions,
    ROUND(stats.correct_predictions::decimal / NULLIF(stats.total_predictions, 0) * 100, 2) as accuracy_rate,
    ROUND(stats.avg_confidence, 4) as avg_confidence
FROM users u
JOIN user_prediction_stats stats ON u.id = stats.user_id
WHERE stats.total_predictions >= 10
ORDER BY stats.correct_predictions DESC, stats.total_predictions DESC
LIMIT 100;

-- 使用窗口函数进行排名计算
SELECT
    p.user_id,
    u.username,
    COUNT(*) as total_predictions,
    COUNT(*) FILTER (WHERE pr.result_status = 'CORRECT') as correct_predictions,
    ROUND(COUNT(*) FILTER (WHERE pr.result_status = 'CORRECT')::decimal /
          NULLIF(COUNT(*), 0) * 100, 2) as accuracy_rate,
    RANK() OVER (ORDER BY COUNT(*) FILTER (WHERE pr.result_status = 'CORRECT') DESC) as global_rank,
    PERCENT_RANK() OVER (ORDER BY COUNT(*) FILTER (WHERE pr.result_status = 'CORRECT') DESC) as percentile_rank
FROM predictions p
JOIN users u ON p.user_id = u.id
WHERE p.created_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY p.user_id, u.username
HAVING COUNT(*) >= 5
ORDER BY global_rank;
```

### 3. 分区策略
```sql
-- 按时间分区大表
-- 比赛表按月分区
CREATE TABLE matches_partitioned (
    id SERIAL,
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    league_id INTEGER NOT NULL,
    match_time TIMESTAMP WITH TIME ZONE NOT NULL,
    -- 其他字段...
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (match_time);

-- 创建分区
CREATE TABLE matches_2024_q1 PARTITION OF matches_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE matches_2024_q2 PARTITION OF matches_partitioned
    FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

-- 系统日志按日分区
CREATE TABLE system_logs_partitioned (
    id SERIAL,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    -- 其他字段...
) PARTITION BY RANGE (created_at);
```

### 4. 缓存策略
```sql
-- 物化视图，用于缓存复杂查询结果
CREATE MATERIALIZED VIEW user_leaderboard AS
SELECT
    u.id as user_id,
    u.username,
    u.full_name,
    u.avatar_url,
    COALESCE(stats.total_predictions, 0) as total_predictions,
    COALESCE(stats.correct_predictions, 0) as correct_predictions,
    COALESCE(stats.accuracy_rate, 0) as accuracy_rate,
    COALESCE(stats.total_points, 0) as total_points,
    COALESCE(stats.current_streak, 0) as current_streak,
    COALESCE(stats.ranking_position, 999999) as ranking,
    COALESCE(stats.ranking_percentile, 0) as percentile_rank
FROM users u
LEFT JOIN user_statistics stats ON u.id = stats.user_id
    AND stats.statistics_date = CURRENT_DATE
WHERE u.is_active = true
ORDER BY stats.total_points DESC NULLS LAST;

-- 创建唯一索引用于刷新
CREATE UNIQUE INDEX idx_user_leaderboard_user_id ON user_leaderboard(user_id);

-- 定期刷新物化视图的函数
CREATE OR REPLACE FUNCTION refresh_user_leaderboard()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW user_leaderboard;
END;
$$ LANGUAGE plpgsql;

-- 定时任务（每天刷新）
-- SELECT cron.schedule('refresh-leaderboard', '0 2 * * *', 'SELECT refresh_user_leaderboard();');
```

---

## 🔒 数据安全

### 1. 访问控制
```sql
-- 创建只读用户
CREATE ROLE readonly_user;
GRANT CONNECT ON DATABASE football_prediction TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- 创建应用用户
CREATE ROLE app_user;
GRANT CONNECT ON DATABASE football_prediction TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- 创建行级安全策略
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;

-- 用户只能访问自己的预测
CREATE POLICY user_predictions_policy ON predictions
    FOR ALL
    TO app_user
    USING (user_id = current_setting('app.current_user_id')::integer);

-- 管理员可以访问所有数据
CREATE POLICY admin_predictions_policy ON predictions
    FOR ALL
    TO app_user
    USING (EXISTS (
        SELECT 1 FROM users u
        WHERE u.id = predictions.user_id
        AND u.is_admin = true
        AND u.id = current_setting('app.current_user_id')::integer
    ));
```

### 2. 数据加密
```sql
-- 敏感数据加密存储
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 加密用户邮箱
ALTER TABLE users ADD COLUMN email_encrypted BYTEA;
UPDATE users SET email_encrypted = pgp_sym_encrypt(email, current_setting('app.encryption_key'));
ALTER TABLE users DROP COLUMN email;
ALTER TABLE users RENAME COLUMN email_encrypted TO email;

-- 创建解密函数
CREATE OR REPLACE FUNCTION decrypt_email(encrypted_email BYTEA)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(encrypted_email, current_setting('app.encryption_key'));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## 📊 性能监控

### 1. 慢查询监控
```sql
-- 启用慢查询日志
ALTER SYSTEM SET log_min_duration_statement = 1000; -- 1秒
ALTER SYSTEM SET log_statement = 'all';

-- 查询统计视图
CREATE VIEW slow_queries AS
SELECT
    query,
    calls,
    total_time,
    mean_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
WHERE mean_time > 1000  -- 超过1秒的查询
ORDER BY total_time DESC;
```

### 2. 表统计信息
```sql
-- 表大小统计
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) -
                     pg_relation_size(schemaname||'.'||tablename)) as index_size,
    pg_stat_get_num_live_tuples(schemaname||'.'||tablename) as rows
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 索引使用情况
SELECT
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC, idx_tup_read DESC;
```

---

## 🔄 备份和恢复

### 1. 备份策略
```bash
#!/bin/bash
# 每日全量备份脚本
pg_dump -h localhost -U postgres -d football_prediction \
    --format=custom \
    --compress=9 \
    --file="/backup/football_prediction_$(date +%Y%m%d).backup"

# 连续归档WAL
archive_command = 'cp %p /backup/wal_archive/%f'
```

### 2. 恢复操作
```bash
# 恢复数据库
pg_restore -h localhost -U postgres -d football_prediction \
    --clean --if-exists \
    /backup/football_prediction_20241201.backup
```

---

## 📋 数据库变更管理

### 1. 迁移脚本示例
```python
"""Add prediction result tracking

Revision ID: 001_add_prediction_results
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001_add_prediction_results'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 创建预测结果表
    op.create_table('prediction_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('prediction_id', sa.Integer(), nullable=False),
        sa.Column('actual_home_score', sa.Integer(), nullable=False),
        sa.Column('actual_away_score', sa.Integer(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('points_difference', sa.Integer(), nullable=True),
        sa.Column('result_calculation_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('bonus_points', sa.Integer(), nullable=True),
        sa.Column('total_points', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['prediction_id'], ['predictions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uq_prediction_results_prediction_id')
    )

    # 创建索引
    op.create_index('ix_prediction_results_correct', 'prediction_results', ['is_correct'])
    op.create_index('ix_prediction_results_points', 'prediction_results', ['total_points'])

def downgrade():
    op.drop_table('prediction_results')
```

---

这个数据库设计文档为足球预测系统提供了完整的数据存储方案，支持业务需求、性能优化和长期维护。通过合理的数据模型设计、索引策略和优化手段，确保系统能够高效地处理大量并发请求和复杂查询。