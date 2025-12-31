# V51.1 特征库数据架构文档

**版本**: V51.1
**发布日期**: 2025-12-31
**架构状态**: Production Ready

---

## 目录

1. [架构概览](#架构概览)
2. [表结构定义](#表结构定义)
3. [字段说明](#字段说明)
4. [索引策略](#索引策略)
5. [数据流转](#数据流转)
6. [质量保障](#质量保障)

---

## 架构概览

V51.1 特征库采用 **三层分离架构**：

```
┌─────────────────────────────────────────────────────────────────┐
│                    V51.1 特征库架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ feature_snapshots│───▶│ prematch_features│───▶│  ML Models  │ │
│  │   (原始特征)      │    │   (赛前特征)      │    │  (推理)      │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│         │                       │                              │
│         ▼                       ▼                              │
│  ┌─────────────────┐    ┌─────────────────┐                   │
│  │ feature_registry│    │  数据质量监控    │                   │
│  │   (元数据)       │    │  (QA Dashboard) │                   │
│  └─────────────────┘    └─────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 表结构定义

### 1. feature_snapshots (特征快照表)

存储 V51.0 提取的 642 维原始"赛后表现"特征。

```sql
CREATE TABLE feature_snapshots (
    -- 主键
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,

    -- 提取元数据
    feature_version VARCHAR(20) NOT NULL DEFAULT 'V51.1',
    extracted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extractor_config JSONB,

    -- V51.0 原始特征 (JSONB 存储)
    raw_features JSONB NOT NULL,
    feature_count INTEGER NOT NULL,

    -- 质量指标
    extraction_status VARCHAR(20) NOT NULL DEFAULT 'success',
    quality_score FLOAT,
    null_count INTEGER DEFAULT 0,
    blacklist_filtered INTEGER DEFAULT 0,

    -- 错误信息
    error_message TEXT,
    processing_time_ms INTEGER,

    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- 约束
    CONSTRAINT valid_quality_score CHECK (quality_score BETWEEN 0 AND 1),
    CONSTRAINT valid_feature_count CHECK (feature_count >= 0)
);
```

**核心字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `raw_features` | JSONB | 642 维原始特征，使用 GIN 索引加速查询 |
| `feature_count` | INTEGER | 实际提取的特征数量 |
| `quality_score` | FLOAT | 0.0-1.0，特征完整性评分 |
| `extraction_status` | VARCHAR | success/partial/failed |

---

### 2. prematch_features (赛前特征表)

存储计算好的赛前预测信号（滚动统计）。

```sql
CREATE TABLE prematch_features (
    -- 主键
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,

    -- 比赛基础信息
    match_date TIMESTAMP WITH TIME ZONE NOT NULL,
    home_team VARCHAR(200) NOT NULL,
    away_team VARCHAR(200) NOT NULL,
    league_name VARCHAR(100) NOT NULL,
    season VARCHAR(20) NOT NULL,

    -- 第一类: 实力底蕴特征 (Past 10 matches average)
    home_rolling_xg FLOAT,
    home_rolling_xg_std FLOAT,
    home_rolling_shots_on_target FLOAT,
    home_rolling_shots_on_target_std FLOAT,
    home_rolling_possession FLOAT,
    home_rolling_possession_std FLOAT,
    home_rolling_team_rating FLOAT,
    home_rolling_team_rating_std FLOAT,

    away_rolling_xg FLOAT,
    away_rolling_xg_std FLOAT,
    away_rolling_shots_on_target FLOAT,
    away_rolling_shots_on_target_std FLOAT,
    away_rolling_possession FLOAT,
    away_rolling_possession_std FLOAT,
    away_rolling_team_rating FLOAT,
    away_rolling_team_rating_std FLOAT,

    rolling_xg_diff FLOAT,
    rolling_possession_diff FLOAT,

    -- 第二类: 即时状态特征 (Past 3 matches trend)
    home_recent_form_points FLOAT,
    home_recent_goals_scored FLOAT,
    home_recent_goals_conceded FLOAT,
    home_recent_win_rate FLOAT,
    home_recent_trend VARCHAR(10),

    away_recent_form_points FLOAT,
    away_recent_goals_scored FLOAT,
    away_recent_goals_conceded FLOAT,
    away_recent_win_rate FLOAT,
    away_recent_trend VARCHAR(10),

    recent_form_diff FLOAT,
    momentum_gap FLOAT,

    -- 第三类: 主/客场特定特征 (Venue-specific)
    home_home_win_rate FLOAT,
    home_home_goals_scored FLOAT,
    home_home_goals_conceded FLOAT,
    home_home_clean_sheets FLOAT,

    home_away_win_rate FLOAT,
    home_away_goals_scored FLOAT,
    home_away_goals_conceded FLOAT,
    home_away_clean_sheets FLOAT,

    away_home_win_rate FLOAT,
    away_home_goals_scored FLOAT,
    away_home_goals_conceded FLOAT,
    away_home_clean_sheets FLOAT,

    away_away_win_rate FLOAT,
    away_away_goals_scored FLOAT,
    away_away_goals_conceded FLOAT,
    away_away_clean_sheets FLOAT,

    home_advantage FLOAT,
    venue_bias FLOAT,

    -- 第四类: 疲劳度特征 (Match density)
    home_fatigue_index FLOAT,
    away_fatigue_index FLOAT,
    fatigue_diff FLOAT,

    home_rest_days FLOAT,
    away_rest_days FLOAT,
    rest_days_diff FLOAT,

    home_matches_7days INTEGER,
    away_matches_7days INTEGER,
    home_matches_30days INTEGER,
    away_matches_30days INTEGER,

    -- 元数据
    feature_version VARCHAR(20) NOT NULL DEFAULT 'V51.1',
    computed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    computation_window VARCHAR(20) NOT NULL DEFAULT 'past_10_matches',

    home_history_count INTEGER,
    away_history_count INTEGER,
    min_history_required INTEGER DEFAULT 5,
    is_valid BOOLEAN DEFAULT TRUE,

    processing_time_ms INTEGER
);
```

**特征分类说明**:

| 类别 | 特征数量 | 说明 | 时空隔离 |
|------|----------|------|----------|
| 实力底蕴 | 10 | 过去 10 场平均 xG、射正、控球、评分 | ✅ 是 |
| 即时状态 | 10 | 过去 3 场积分、进球、胜率、趋势 | ✅ 是 |
| 主客场 | 10 | 主场/客场特定表现统计 | ✅ 是 |
| 疲劳度 | 10 | 比赛密度、休息天数 | ✅ 是 |
| 积分榜 | 7 | 赛前积分榜位置和积分 | ✅ 是 |
| ELO 评分 | 2 | 动态 ELO 分差 | ✅ 是 |
| **总计** | **49** | - | **100%** |

---

### 3. feature_registry (特征注册表)

记录所有特征的元数据和血缘关系。

```sql
CREATE TABLE feature_registry (
    id SERIAL PRIMARY KEY,

    -- 特征标识
    feature_path VARCHAR(200) UNIQUE NOT NULL,
    feature_name VARCHAR(100) NOT NULL,
    feature_category VARCHAR(50),

    -- 数据类型
    data_type VARCHAR(20) NOT NULL,
    value_range VARCHAR(50),

    -- 来源追溯
    source_path VARCHAR(500),
    source_table VARCHAR(100),

    -- 计算逻辑
    computation_logic TEXT,
    dependencies TEXT[],

    -- 质量指标
    is_active BOOLEAN DEFAULT TRUE,
    null_rate FLOAT DEFAULT 0,
    distribution_stats JSONB,

    -- 版本管理
    feature_version VARCHAR(20) DEFAULT 'V51.1',
    introduced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deprecated_at TIMESTAMP WITH TIME ZONE,

    -- 审计
    created_by VARCHAR(100) DEFAULT 'system',
    last_modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 索引策略

### feature_snapshots 索引

```sql
-- 主查询路径
CREATE INDEX idx_feature_snapshots_match_id
    ON feature_snapshots(match_id);

CREATE INDEX idx_feature_snapshots_extracted_at
    ON feature_snapshots(extracted_at DESC);

-- 质量过滤
CREATE INDEX idx_feature_snapshots_status
    ON feature_snapshots(extraction_status);

CREATE INDEX idx_feature_snapshots_quality
    ON feature_snapshots(quality_score DESC);

-- JSONB GIN 索引
CREATE INDEX idx_feature_snapshots_features_gin
    ON feature_snapshots USING GIN(raw_features);

-- 唯一约束
CREATE UNIQUE INDEX idx_feature_snapshots_unique
    ON feature_snapshots(match_id, feature_version);
```

### prematch_features 索引

```sql
-- 按球队查询 (用于计算滚动特征)
CREATE INDEX idx_prematch_home_team_date
    ON prematch_features(home_team, match_date DESC);

CREATE INDEX idx_prematch_away_team_date
    ON prematch_features(away_team, match_date DESC);

-- 按联赛和赛季查询
CREATE INDEX idx_prematch_league_season
    ON prematch_features(league_name, season, match_date DESC);

-- 按日期范围查询
CREATE INDEX idx_prematch_match_date
    ON prematch_features(match_date DESC);

-- 质量过滤
CREATE INDEX idx_prematch_is_valid
    ON prematch_features(is_valid) WHERE is_valid = TRUE;

-- 唯一约束
CREATE UNIQUE INDEX idx_prematch_unique
    ON prematch_features(match_id, feature_version);
```

---

## 数据流转

```
┌─────────────────────────────────────────────────────────────────┐
│                      V51.1 数据流转                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. L1: FotMob API                                             │
│     └── matches 表 (比分、状态)                                  │
│                                                                 │
│  2. L2: Raw Match Data                                         │
│     └── raw_match_data 表 (stats.xg = [home, away])            │
│                                                                 │
│  3. V51.1: Feature Calculator                                  │
│     ├── get_team_history()    # 时空隔离查询                   │
│     ├── extract_stats_from_raw_data()  # 数组拆包              │
│     ├── calculate_strength_features()   # 实力底蕴              │
│     ├── calculate_recent_form_features() # 即时状态            │
│     ├── calculate_venue_features()      # 主客场特征            │
│     └── calculate_fatigue_features()    # 疲劳度               │
│                                                                 │
│  4. Storage: prematch_features                                 │
│     └── 49 维赛前特征 + 质量标记                                │
│                                                                 │
│  5. ML Inference                                               │
│     └── ModelDispatcher.predict()                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 质量保障

### 时空隔离验证

```sql
-- 验证：所有历史比赛必须早于目标比赛
SELECT
    pf.match_id,
    pf.match_date,
    pf.home_rolling_xg,
    -- 确认计算使用的最晚历史比赛早于目标比赛
    (
        SELECT MAX(m.match_date)
        FROM matches m
        WHERE m.match_date < pf.match_date
          AND m.home_team = pf.home_team
    ) AS latest_history_date,
    pf.match_date - (
        SELECT MAX(m.match_date)
        FROM matches m
        WHERE m.match_date < pf.match_date
          AND m.home_team = pf.home_team
    ) AS time_gap_days
FROM prematch_features pf
WHERE pf.is_valid = TRUE
  AND pf.match_date >= '2025-01-01'
LIMIT 10;
```

### 数据完整性检查

```sql
-- 检查特征覆盖度
SELECT
    COUNT(*) AS total_records,
    COUNT(home_rolling_xg) AS with_xg,
    COUNT(away_rolling_xg) AS with_away_xg,
    ROUND(COUNT(home_rolling_xg) * 100.0 / COUNT(*), 2) AS xg_coverage_pct
FROM prematch_features;
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| V51.1 | 2025-12-31 | 初始版本，三层架构，时空隔离保证 |

---

**文档维护**: ML Platform Team
**最后更新**: 2025-12-31
