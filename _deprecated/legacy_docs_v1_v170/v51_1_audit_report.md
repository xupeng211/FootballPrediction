# V51.1 架构审计与特征方案建议书

**审计日期**: 2025-12-31
**审计范围**: L1→L2→V51 全链路连通性 + 特征存储架构设计
**审计人员**: 首席系统架构师 & ML 平台专家

---

## 执行摘要

本次审计针对 FootballPrediction 系统的 L1→L2→V51 数据流进行全面审查，核心发现：

| 审计项 | 状态 | 风险等级 | 关键发现 |
|--------|------|----------|----------|
| **ID 一致性** | ⚠️ 部分兼容 | 中 | match_id 与 external_id 存在命名不一致，需统一 |
| **自愈链路** | ✅ 兼容 | 低 | V51.1 自愈机制与 V51.0 特征提取完全兼容 |
| **I/O 性能** | ⚠️ 有瓶颈 | 中 | 单进程顺序提取，9,000 场数据耗时较长 |
| **特征存储** | ❌ 缺失 | 高 | 无特征快照表，使用 CSV 存储不符合生产标准 |
| **赛前特征** | ❌ 未实现 | 高 | V51 提取的是赛后统计，非赛前预测信号 |

---

## 第一部分：全链路连通性审计

### 1.1 ID 一致性审查

#### 1.1.1 L1 索引层 (v50_rich_l1_scanner.py)

**位置**: `src/api/collectors/v50_rich_l1_scanner.py:387-389`

```python
rich_match = RichL1Match(
    match_id=match_id,  # ← FotMob 原始 ID (int)
    league_id=league_id,
    ...
)
```

**关键字段**:
- `match_id`: FotMob 原始比赛 ID (int)，如 `4041683`
- `home_team_id`, `away_team_id`: FotMob 球队 ID (int)

#### 1.1.2 L2 原始数据层 (v51_incremental_collector.py)

**位置**: `src/api/collectors/v51_incremental_collector.py:557-559`

```python
batch_data.append((
    str(match_id),      # match_id (主键，VARCHAR(50))
    str(match_id),      # external_id (用于 UPSERT 冲突检测)
    ...
))
```

**关键发现**:
- `match_id` 作为主键存储为 VARCHAR(50)
- `external_id` 与 `match_id` 使用**相同值**（冗余设计）
- 这与 schema_manager.py 中的设计不一致

#### 1.1.3 matches 表结构 (init_db.sql:21-46)

```sql
CREATE TABLE IF NOT EXISTS matches (
    match_id VARCHAR(50) PRIMARY KEY,      -- 主键
    external_id VARCHAR(100),              -- 冗余字段！
    ...
);
```

**不一致点**:
1. **命名冲突**: `external_id` 在代码中有两种用途
   - V51 采集器: `external_id` = `match_id` (相同值)
   - schema_manager.py: `external_id` 用于旧版 ID 映射

2. **字段冲突风险**:
   ```python
   # schema_manager.py:271-298 使用 external_id 作为主键
   external_id VARCHAR(50) NOT NULL UNIQUE,  -- 旧设计
   ```
   而 init_db.sql 使用 `match_id` 作为主键。

#### 1.1.4 V51 特征提取层 (v51_feature_refiner.py)

**位置**: `src/processors/v51_feature_refiner.py:623-630`

```python
query = """
    SELECT m.match_id, m.external_id, m.league_name, ...
    FROM matches m
    INNER JOIN raw_match_data r ON m.match_id = r.match_id
    WHERE m.status = 'finished'
"""
```

**连通性验证**:
- ✅ JOIN 条件使用 `m.match_id = r.match_id`，正确
- ✅ 查询条件 `m.status = 'finished'` 确保只提取已完赛数据
- ⚠️ 返回 `external_id` 但未实际使用（冗余查询）

#### 1.1.5 ID 一致性结论

| 层级 | ID 字段 | 类型 | 是否一致 |
|------|---------|------|----------|
| L1 (FotMob) | `match_id` | int | ✅ 原始来源 |
| matches 表 | `match_id` | VARCHAR(50) | ✅ 主键 |
| matches 表 | `external_id` | VARCHAR(100) | ⚠️ 与 match_id 冗余 |
| raw_match_data | `match_id` | VARCHAR(50) | ✅ 外键关联 |
| V51 提取 | `match_id` | VARCHAR(50) | ✅ 连通 |

**建议修复方案**:
```sql
-- 统一 ID 字段，移除冗余 external_id
ALTER TABLE matches DROP COLUMN IF EXISTS external_id;
-- 或重命名以避免歧义
ALTER TABLE matches RENAME COLUMN external_id TO legacy_id;
```

---

### 1.2 自愈链路兼容性验证

#### 1.2.1 V51.1 自愈机制 (v51_incremental_collector.py)

**位置**: `src/api/collectors/v51_incremental_collector.py:544-554`

```python
# ===== V51.1 核心逻辑: 比分驱动状态自愈 =====
has_valid_score = (
    home_score is not None
    and away_score is not None
    and isinstance(home_score, int)
    and isinstance(away_score, int)
)

final_status = "finished" if has_valid_score else match_data.get("status", "scheduled")
```

**自愈逻辑**:
1. 当 L1 返回有效比分 → 强制 `status = 'finished'`
2. 当 L1 比分为空 → 保持原状态
3. 使用 UPSERT 实现自动更新

#### 1.2.2 V51.0 特征提取兼容性

**位置**: `src/processors/v51_feature_refiner.py:631-632`

```python
WHERE m.status = 'finished'
  AND m.home_score IS NOT NULL
  AND m.away_score IS NOT NULL
```

**兼容性验证**:
- ✅ V51.1 自愈后 `status = 'finished'`，满足 V51.0 查询条件
- ✅ 自愈同时写入比分，满足 `home_score IS NOT NULL` 条件
- ✅ UPSERT 机制确保数据原子性

**时序分析**:
```
Step 1: V51.1 _import_matches_to_db()
  └─> 9000 场僵尸比赛被唤醒 (status: scheduled → finished)

Step 2: V51.0 extract_features_from_db()
  └─> WHERE status = 'finished' 自动包含新唤醒的比赛
  └─> 提取 raw_match_data.raw_data (已同步完成)
```

#### 1.2.3 自愈链路结论

**兼容性**: ✅ **完全兼容**

| 检查项 | V51.1 自愈 | V51.0 提取 | 结果 |
|--------|-----------|-----------|------|
| 状态字段 | status = 'finished' | WHERE status = 'finished' | ✅ 匹配 |
| 比分字段 | home_score/away_score | WHERE scores IS NOT NULL | ✅ 匹配 |
| 原始数据 | raw_data 同步写入 | 从 raw_match_data 读取 | ✅ 匹配 |

**统计报告**:
```
╔════════════════════════════════════════════════════════════╗
║           V51.1 系统自愈报告 (比分驱动状态修复)              ║
╚════════════════════════════════════════════════════════════╝
🔄 本次运行共修复/唤醒: 9000 场僵尸比赛
   这些比赛从 'scheduled'/'ongoing' 被修正为 'finished'
╚════════════════════════════════════════════════════════════╝
```

---

### 1.3 I/O 性能瓶颈评估

#### 1.3.1 当前 I/O 模式

**位置**: `src/processors/v51_feature_refiner.py:586-683`

```python
def extract_features_from_db(...):
    # 1. 单次 SQL 查询 (有索引优化)
    cur.execute(query, params)
    rows = cur.fetchall()  # ← 一次性加载到内存

    # 2. 单进程顺序提取
    for match_id, raw_data in iterator:
        features = refiner.extract_single_match(raw_data, match_id)
```

**性能分析**:
- **SQL 查询**: ✅ 使用索引，毫秒级
- **数据传输**: ⚠️ 50GB L2 数据 → 内存，可能 OOM
- **特征提取**: ⚠️ 单进程，9000 场 × ~50ms = 7.5 分钟

#### 1.3.2 瓶颈定位

| 阶段 | 耗时估算 | 瓶颈等级 |
|------|----------|----------|
| SQL 查询 | ~2秒 | 🟢 低 |
| 数据传输 | ~10秒 (9000 × 5MB) | 🟡 中 |
| JSON 解析 | ~60秒 | 🟡 中 |
| 特征提取 | ~450秒 (单进程) | 🔴 高 |
| DataFrame 构建 | ~30秒 | 🟢 低 |

**总耗时**: ~8-10 分钟（9000 场）

#### 1.3.3 优化建议

**方案 1: 多进程并行提取**
```python
from multiprocessing import Pool

def extract_single_wrapper(args):
    match_id, raw_data = args
    refiner = V51FeatureRefiner()
    return refiner.extract_single_match(raw_data, match_id)

with Pool(processes=8) as pool:
    results = pool.map(extract_single_wrapper, raw_data_list)
```
**预期提升**: 8 倍加速（~1 分钟）

**方案 2: 分批查询 + 流式处理**
```python
# 每次只查询 1000 场
cur.execute(query + " LIMIT 1000 OFFSET %s", (offset,))
```
**预期效果**: 降低内存峰值，避免 OOM

**方案 3: 使用数据库连接池**
```python
from src.database.db_pool import get_pool

pool = get_pool(minconn=4, maxconn=20)
# 多连接并发查询
```

---

## 第二部分：特征存储方案设计

### 2.1 现状分析

#### 2.1.1 当前存储方式

**位置**: `scripts/ml/generate_v51_training_set.py:91-97`

```python
# 保存为 CSV 文件
output_path = output_dir / "v51_features_all.csv"
df.to_csv(output_path, index=False)

output_path_features = output_dir / "v51_features_all_numeric.csv"
df_features.to_csv(output_path_features, index=False)
```

**问题分析**:
1. ❌ **不可追溯**: 无法查到特征是怎么算出来的
2. ❌ **不可复现**: CSV 文件是静态快照，重新提取可能不同
3. ❌ **不可观测**: 计算出错无法报警
4. ❌ **无版本管理**: 无法追踪特征演进历史
5. ❌ **查询低效**: 无法按 team_id 和 match_date 快速查询

#### 2.1.2 数据库现有表结构

**match_features_training 表** (`init_db.sql:76-133`):
- 存储 V17.0/V18.0/V19.0 的**手工特征** (约 40 维)
- 有 `adaptive_features` JSONB 字段，但 V51 未使用
- 设计适合赛前特征，但被 V51 忽略

### 2.2 V51.1 特征存储架构设计

#### 2.2.1 设计原则

1. **可追溯性**: 每个特征记录其来源 JSON 路径
2. **可复现性**: 相同输入 → 相同输出（确定性计算）
3. **可观测性**: 计算失败时记录详细错误信息
4. **性能优先**: 支持按 team_id 和 match_date 快速查询
5. **版本管理**: 特征定义可演进而不破坏历史

#### 2.2.2 表结构设计

##### 表 1: 特征快照表 (feature_snapshots)

```sql
-- ============================================
-- V51.1 特征快照表 (Feature Snapshot Table)
-- 用途: 存储 V51 提取的 642 维原始指标
-- ============================================
CREATE TABLE IF NOT EXISTS feature_snapshots (
    -- 主键
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,

    -- 提取元数据
    feature_version VARCHAR(20) NOT NULL DEFAULT 'V51.1',
    extracted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extractor_config JSONB,  -- 提取器配置快照

    -- V51.0 原始特征 (JSONB 存储，支持 642 维)
    raw_features JSONB NOT NULL,  -- {feature_path: value}
    feature_count INTEGER NOT NULL,  -- 特征数量

    -- 质量指标
    extraction_status VARCHAR(20) NOT NULL DEFAULT 'success',  -- success/partial/failed
    quality_score FLOAT,  -- 0.0-1.0，特征完整性评分
    null_count INTEGER DEFAULT 0,  -- NULL 值数量
    blacklist_filtered INTEGER DEFAULT 0,  -- 黑名单过滤数量

    -- 错误信息
    error_message TEXT,
    processing_time_ms INTEGER,

    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- 约束
    CONSTRAINT valid_quality_score CHECK (quality_score BETWEEN 0 AND 1),
    CONSTRAINT valid_feature_count CHECK (feature_count >= 0)
);

-- 性能索引
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_match_id
    ON feature_snapshots(match_id);
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_extracted_at
    ON feature_snapshots(extracted_at DESC);
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_status
    ON feature_snapshots(extraction_status);
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_quality
    ON feature_snapshots(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_version
    ON feature_snapshots(feature_version);

-- JSONB GIN 索引 (支持特征查询)
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_features_gin
    ON feature_snapshots USING GIN(raw_features);

-- 唯一约束 (同一 match_id + version 只保留最新)
CREATE UNIQUE INDEX IF NOT EXISTS idx_feature_snapshots_unique
    ON feature_snapshots(match_id, feature_version);
```

**设计说明**:
1. **raw_features JSONB**: 存储 V51 提取的完整 642 维特征
2. **feature_version**: 支持多版本特征共存 (V51.0, V51.1, ...)
3. **extraction_status**: 支持部分成功场景
4. **quality_score**: 特征完整性评分，用于过滤低质量数据
5. **processing_time_ms**: 性能监控

##### 表 2: 赛前特征表 (prematch_features)

```sql
-- ============================================
-- V51.1 赛前特征表 (Pre-match Feature Table)
-- 用途: 存储计算好的赛前预测信号 (滚动统计)
-- ============================================
CREATE TABLE IF NOT EXISTS prematch_features (
    -- 主键
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,

    -- 比赛基础信息 (用于快速查询)
    match_date TIMESTAMP WITH TIME ZONE NOT NULL,
    home_team VARCHAR(200) NOT NULL,
    away_team VARCHAR(200) NOT NULL,
    league_name VARCHAR(100) NOT NULL,
    season VARCHAR(20) NOT NULL,

    -- ============================================
    -- 第一类: 实力底蕴特征 (Past 10 matches average)
    -- ============================================
    -- 主队实力 (过去 10 场平均)
    home_rolling_xg FLOAT,              -- xG 平均值
    home_rolling_xg_std FLOAT,          -- xG 标准差
    home_rolling_shots_on_target FLOAT, -- 射正平均
    home_rolling_shots_on_target_std FLOAT,
    home_rolling_possession FLOAT,      -- 控球率平均
    home_rolling_possession_std FLOAT,
    home_rolling_team_rating FLOAT,     -- 评分平均
    home_rolling_team_rating_std FLOAT,

    -- 客队实力 (过去 10 场平均)
    away_rolling_xg FLOAT,
    away_rolling_xg_std FLOAT,
    away_rolling_shots_on_target FLOAT,
    away_rolling_shots_on_target_std FLOAT,
    away_rolling_possession FLOAT,
    away_rolling_possession_std FLOAT,
    away_rolling_team_rating FLOAT,
    away_rolling_team_rating_std FLOAT,

    -- 实力差值
    rolling_xg_diff FLOAT,              -- 主队 xG - 客队 xG
    rolling_possession_diff FLOAT,      -- 主队控球 - 客队控球
    rolling_rating_diff FLOAT,          -- 主队评分 - 客队评分

    -- ============================================
    -- 第二类: 即时状态特征 (Past 3 matches trend)
    -- ============================================
    -- 主队近期状态 (过去 3 场)
    home_recent_form_points FLOAT,     -- 积分: 3分/胜, 1分/平, 0分/负
    home_recent_goals_scored FLOAT,    -- 进球数
    home_recent_goals_conceded FLOAT,  -- 失球数
    home_recent_win_rate FLOAT,        -- 胜率
    home_recent_trend VARCHAR(10),      -- 'ascending'/'descending'/'stable'

    -- 客队近期状态 (过去 3 场)
    away_recent_form_points FLOAT,
    away_recent_goals_scored FLOAT,
    away_recent_goals_conceded FLOAT,
    away_recent_win_rate FLOAT,
    away_recent_trend VARCHAR(10),

    -- 状态对比
    recent_form_diff FLOAT,             -- 主队积分 - 客队积分
    momentum_gap FLOAT,                 -- 势能差值

    -- ============================================
    -- 第三类: 主/客场特定偏见特征 (Venue-specific)
    -- ============================================
    -- 主队主场表现 (过去 10 场主场)
    home_home_win_rate FLOAT,          -- 主场胜率
    home_home_goals_scored FLOAT,      -- 主场进球
    home_home_goals_conceded FLOAT,    -- 主场失球
    home_home_clean_sheets FLOAT,      -- 主场零封

    -- 主队客场表现 (过去 10 场客场)
    home_away_win_rate FLOAT,
    home_away_goals_scored FLOAT,
    home_away_goals_conceded FLOAT,
    home_away_clean_sheets FLOAT,

    -- 客队主场表现 (过去 10 场主场)
    away_home_win_rate FLOAT,
    away_home_goals_scored FLOAT,
    away_home_goals_conceded FLOAT,
    away_home_clean_sheets FLOAT,

    -- 客队客场表现 (过去 10 场客场)
    away_away_win_rate FLOAT,
    away_away_goals_scored FLOAT,
    away_away_goals_conceded FLOAT,
    away_away_clean_sheets FLOAT,

    -- 主客场优势
    home_advantage FLOAT,              -- 主队主场胜率 - 客队客场胜率
    venue_bias FLOAT,                  -- 主场偏向度

    -- ============================================
    -- 第四类: 竞技压力特征 (Match density/Rest days)
    -- ============================================
    -- 疲劳度指数
    home_fatigue_index FLOAT,          -- 过去 7 天比赛密度
    away_fatigue_index FLOAT,
    fatigue_diff FLOAT,                -- 主队疲劳 - 客队疲劳

    -- 休息天数
    home_rest_days FLOAT,              -- 距离上一场休息天数
    away_rest_days FLOAT,
    rest_days_diff FLOAT,              -- 休息天数差

    -- 赛程密度
    home_matches_7days INTEGER,        -- 过去 7 天比赛数
    away_matches_7days INTEGER,
    home_matches_30days INTEGER,       -- 过去 30 天比赛数
    away_matches_30days INTEGER,

    -- ============================================
    -- 第五类: 积分榜特征 (来自 schema_manager.py)
    -- ============================================
    home_table_position INTEGER,
    away_table_position INTEGER,
    table_position_diff INTEGER,
    home_points FLOAT,
    away_points FLOAT,
    points_diff FLOAT,
    home_recent_form_points FLOAT,
    away_recent_form_points FLOAT,

    -- ============================================
    -- 第六类: ELO 评分特征
    -- ============================================
    raw_elo_gap FLOAT,
    adjusted_elo_gap FLOAT,            -- 调整主场优势

    -- ============================================
    -- 元数据与审计
    -- ============================================
    feature_version VARCHAR(20) NOT NULL DEFAULT 'V51.1',
    computed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    computation_window VARCHAR(20) NOT NULL DEFAULT 'past_10_matches',

    -- 质量指标
    home_history_count INTEGER,        -- 主队历史比赛数
    away_history_count INTEGER,        -- 客队历史比赛数
    min_history_required INTEGER DEFAULT 5,  -- 最低历史要求
    is_valid BOOLEAN DEFAULT TRUE,     -- 是否满足最低历史要求

    -- 计算性能
    processing_time_ms INTEGER,

    -- 约束
    CONSTRAINT valid_win_rate CHECK (
        home_home_win_rate BETWEEN 0 AND 1 AND
        away_away_win_rate BETWEEN 0 AND 1
    ),
    CONSTRAINT valid_fatigue_index CHECK (
        home_fatigue_index BETWEEN 0 AND 1 AND
        away_fatigue_index BETWEEN 0 AND 1
    )
);

-- ============================================
-- 性能优化索引 (关键查询路径)
-- ============================================

-- 按球队查询 (用于计算滚动特征)
CREATE INDEX IF NOT EXISTS idx_prematch_home_team_date
    ON prematch_features(home_team, match_date DESC);
CREATE INDEX IF NOT EXISTS idx_prematch_away_team_date
    ON prematch_features(away_team, match_date DESC);

-- 按联赛和赛季查询
CREATE INDEX IF NOT EXISTS idx_prematch_league_season
    ON prematch_features(league_name, season, match_date DESC);

-- 按日期范围查询
CREATE INDEX IF NOT EXISTS idx_prematch_match_date
    ON prematch_features(match_date DESC);

-- 质量过滤
CREATE INDEX IF NOT EXISTS idx_prematch_is_valid
    ON prematch_features(is_valid) WHERE is_valid = TRUE;

-- 版本管理
CREATE INDEX IF NOT EXISTS idx_prematch_version
    ON prematch_features(feature_version);

-- 唯一约束
CREATE UNIQUE INDEX IF NOT EXISTS idx_prematch_unique
    ON prematch_features(match_id, feature_version);
```

**设计说明**:
1. **60+ 维赛前特征**: 覆盖实力、状态、主客场、疲劳度等
2. **快速查询索引**: 支持按 `team_id` 和 `match_date` 高效查询历史
3. **质量约束**: 确保数据有效性 (如 win_rate ∈ [0, 1])
4. **版本管理**: 支持特征演进
5. **is_valid 标记**: 快速过滤满足最低历史要求的比赛

##### 表 3: 特征注册表 (feature_registry)

```sql
-- ============================================
-- V51.1 特征注册表 (Feature Registry)
-- 用途: 记录所有特征的元数据和血缘关系
-- ============================================
CREATE TABLE IF NOT EXISTS feature_registry (
    id SERIAL PRIMARY KEY,

    -- 特征标识
    feature_path VARCHAR(200) UNIQUE NOT NULL,  -- 例如: "header_content__stats__xg"
    feature_name VARCHAR(100) NOT NULL,         -- 例如: "rolling_xg_home"
    feature_category VARCHAR(50),               -- 'raw'/'derived'/'prematch'

    -- 数据类型
    data_type VARCHAR(20) NOT NULL,             -- 'int'/'float'/'bool'/'percentage'
    value_range VARCHAR(50),                    -- 例如: "0.0-1.0" 或 "0-100"

    -- 来源追溯
    source_path VARCHAR(500),                   -- JSON 源路径
    source_table VARCHAR(100),                  -- 'feature_snapshots'/'prematch_features'

    -- 计算逻辑
    computation_logic TEXT,                     -- SQL/Python 伪代码
    dependencies TEXT[],                        -- 依赖的其他特征

    -- 质量指标
    is_active BOOLEAN DEFAULT TRUE,
    null_rate FLOAT DEFAULT 0,                 -- NULL 值比例
    distribution_stats JSONB,                  -- {mean, std, min, max, median}

    -- 版本管理
    feature_version VARCHAR(20) DEFAULT 'V51.1',
    introduced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deprecated_at TIMESTAMP WITH TIME ZONE,

    -- 审计
    created_by VARCHAR(100) DEFAULT 'system',
    last_modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_feature_registry_path
    ON feature_registry(feature_path);
CREATE INDEX IF NOT EXISTS idx_feature_registry_category
    ON feature_registry(feature_category);
CREATE INDEX IF NOT EXISTS idx_feature_registry_active
    ON feature_registry(is_active) WHERE is_active = TRUE;
```

**设计说明**:
1. **血缘追溯**: 记录每个特征的来源和计算逻辑
2. **质量监控**: 统计 NULL 值比例和分布
3. **版本管理**: 支持特征演进和弃用

#### 2.2.3 特征计算 SQL 模板

##### 实力底蕴特征 (Past 10 matches average)

```sql
-- ============================================
-- V51.1 特征计算模板: 实力底蕴特征
-- 用途: 计算球队过去 N 场的滚动统计
-- ============================================

-- 为主队 match_id = '12345' 计算主队实力特征
WITH home_team_matches AS (
    SELECT
        m.match_id,
        m.match_date,
        m.home_team,
        m.away_team,
        m.home_score,
        m.away_score,
        r.raw_data
    FROM matches m
    INNER JOIN raw_match_data r ON m.match_id = r.match_id
    WHERE m.home_team = 'Arsenal'  -- 目标球队
       OR m.away_team = 'Arsenal'
       AND m.match_date < '2024-01-15 15:00:00'  -- 比赛时间（时空隔离）
       AND m.status = 'finished'
    ORDER BY m.match_date DESC
    LIMIT 10  -- 过去 10 场
),
home_team_stats AS (
    SELECT
        -- 提取 xG (需要从 JSONB 解析)
        CASE
            WHEN home_team = 'Arsenal'
            THEN (raw_data->'header'->'stats'->'xg'->'home')::FLOAT
            ELSE (raw_data->'header'->'stats'->'xg'->'away')::FLOAT
        END as xg,
        -- 提取射正
        CASE
            WHEN home_team = 'Arsenal'
            THEN (raw_data->'header'->'stats'->'shotsOnTarget'->'home')::FLOAT
            ELSE (raw_data->'header'->'stats'->'shotsOnTarget'->'away')::FLOAT
        END as shots_on_target,
        -- 提取控球率
        CASE
            WHEN home_team = 'Arsenal'
            THEN (raw_data->'header'->'stats'->'possession'->'home')::FLOAT
            ELSE (raw_data->'header'->'stats'->'possession'->'away')::FLOAT
        END as possession,
        -- 提取评分
        CASE
            WHEN home_team = 'Arsenal'
            THEN (raw_data->'content'->'matchStats'->'stats'->'rating'->'home')::FLOAT
            ELSE (raw_data->'content'->'matchStats'->'stats'->'rating'->'away')::FLOAT
        END as team_rating
    FROM home_team_matches
    WHERE raw_data IS NOT NULL
)
INSERT INTO prematch_features (
    match_id,
    home_rolling_xg,
    home_rolling_xg_std,
    home_rolling_shots_on_target,
    home_rolling_possession,
    home_rolling_team_rating,
    home_history_count,
    feature_version
)
SELECT
    '12345',  -- 当前比赛 match_id
    AVG(xg),                           -- 平均 xG
    STDDEV_SAMP(xg),                   -- xG 标准差
    AVG(shots_on_target),              -- 平均射正
    AVG(possession),                   -- 平均控球
    AVG(team_rating),                  -- 平均评分
    COUNT(*),                          -- 历史比赛数
    'V51.1'
FROM home_team_stats;
```

##### 即时状态特征 (Past 3 matches trend)

```sql
-- ============================================
-- V51.1 特征计算模板: 即时状态特征
-- 用途: 计算球队过去 3 场的趋势
-- ============================================

WITH home_recent_matches AS (
    SELECT
        m.match_id,
        m.match_date,
        m.home_team,
        m.away_team,
        m.home_score,
        m.away_score,
        r.raw_data
    FROM matches m
    INNER JOIN raw_match_data r ON m.match_id = r.match_id
    WHERE (m.home_team = 'Arsenal' OR m.away_team = 'Arsenal')
       AND m.match_date < '2024-01-15 15:00:00'  -- 时空隔离
       AND m.status = 'finished'
    ORDER BY m.match_date DESC
    LIMIT 3  -- 过去 3 场
),
home_recent_stats AS (
    SELECT
        -- 计算积分 (胜=3, 平=1, 负=0)
        CASE
            WHEN home_team = 'Arsenal' AND home_score > away_score THEN 3
            WHEN away_team = 'Arsenal' AND away_score > home_score THEN 3
            WHEN home_score = away_score THEN 1
            ELSE 0
        END as points,
        -- 计算进球
        CASE
            WHEN home_team = 'Arsenal' THEN home_score
            ELSE away_score
        END as goals_scored,
        -- 计算失球
        CASE
            WHEN home_team = 'Arsenal' THEN away_score
            ELSE home_score
        END as goals_conceded
    FROM home_recent_matches
)
INSERT INTO prematch_features (
    match_id,
    home_recent_form_points,
    home_recent_goals_scored,
    home_recent_goals_conceded,
    home_recent_win_rate,
    home_recent_trend,
    feature_version
)
SELECT
    '12345',
    SUM(points),                          -- 总积分
    SUM(goals_scored),                    -- 总进球
    SUM(goals_conceded),                  -- 总失球
    AVG(CASE WHEN points = 3 THEN 1 ELSE 0 END),  -- 胜率
    CASE
        WHEN LAG(SUM(points), 1) OVER (ORDER BY SUM(points)) IS NULL THEN 'stable'
        WHEN SUM(points) > LAG(SUM(points), 1) OVER (ORDER BY SUM(points)) THEN 'ascending'
        WHEN SUM(points) < LAG(SUM(points), 1) OVER (ORDER BY SUM(points)) THEN 'descending'
        ELSE 'stable'
    END as trend,  -- 趋势判断
    'V51.1'
FROM home_recent_stats;
```

##### 主客场特定特征 (Venue-specific)

```sql
-- ============================================
-- V51.1 特征计算模板: 主客场特定特征
-- 用途: 计算球队在主/客场的特定表现
-- ============================================

WITH home_venue_stats AS (
    SELECT
        COUNT(*) as total_matches,
        SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) as wins,
        SUM(home_score) as goals_scored,
        SUM(away_score) as goals_conceded,
        SUM(CASE WHEN away_score = 0 THEN 1 ELSE 0 END) as clean_sheets
    FROM matches m
    WHERE m.home_team = 'Arsenal'  -- 主队主场
       AND m.match_date < '2024-01-15 15:00:00'  -- 时空隔离
       AND m.status = 'finished'
    ORDER BY m.match_date DESC
    LIMIT 10  -- 过去 10 场主场
),
away_venue_stats AS (
    SELECT
        COUNT(*) as total_matches,
        SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) as wins,
        SUM(away_score) as goals_scored,
        SUM(home_score) as goals_conceded,
        SUM(CASE WHEN home_score = 0 THEN 1 ELSE 0 END) as clean_sheets
    FROM matches m
    WHERE m.away_team = 'Arsenal'  -- 主队客场
       AND m.match_date < '2024-01-15 15:00:00'  -- 时空隔离
       AND m.status = 'finished'
    ORDER BY m.match_date DESC
    LIMIT 10  -- 过去 10 场客场
)
INSERT INTO prematch_features (
    match_id,
    home_home_win_rate,
    home_home_goals_scored,
    home_home_goals_conceded,
    home_home_clean_sheets,
    home_away_win_rate,
    home_away_goals_scored,
    home_away_goals_conceded,
    home_away_clean_sheets,
    feature_version
)
SELECT
    '12345',
    (wins::FLOAT / NULLIF(total_matches, 0)),  -- 主场胜率
    AVG(goals_scored),                          -- 主场进球
    AVG(goals_conceded),                        -- 主场失球
    (clean_sheets::FLOAT / NULLIF(total_matches, 0)),  -- 主场零封率
    (away_venue_stats.wins::FLOAT / NULLIF(away_venue_stats.total_matches, 0)),
    AVG(away_venue_stats.goals_scored),
    AVG(away_venue_stats.goals_conceded),
    (away_venue_stats.clean_sheets::FLOAT / NULLIF(away_venue_stats.total_matches, 0)),
    'V51.1'
FROM home_venue_stats, away_venue_stats;
```

##### 疲劳度特征 (Match density/Rest days)

```sql
-- ============================================
-- V51.1 特征计算模板: 疲劳度特征
-- 用途: 计算比赛密度和休息天数
-- ============================================

WITH home_match_calendar AS (
    SELECT
        match_id,
        match_date,
        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - match_date)) / 86400 as days_since_match
    FROM matches m
    WHERE (m.home_team = 'Arsenal' OR m.away_team = 'Arsenal')
       AND m.match_date < '2024-01-15 15:00:00'  -- 时空隔离
       AND m.status = 'finished'
    ORDER BY m.match_date DESC
),
home_fatigue_calc AS (
    SELECT
        -- 过去 7 天比赛密度
        COUNT(*) FILTER (
            WHERE days_since_match <= 7
        ) as matches_7days,
        -- 过去 30 天比赛密度
        COUNT(*) FILTER (
            WHERE days_since_match <= 30
        ) as matches_30days,
        -- 休息天数 (距离上一场)
        MIN(days_since_match) as rest_days
    FROM home_match_calendar
)
INSERT INTO prematch_features (
    match_id,
    home_fatigue_index,
    home_rest_days,
    home_matches_7days,
    home_matches_30days,
    feature_version
)
SELECT
    '12345',
    -- 疲劳度指数 = 7天内比赛数 / 7
    LEAST(matches_7days::FLOAT / 7.0, 1.0),
    rest_days,
    matches_7days,
    matches_30days,
    'V51.1'
FROM home_fatigue_calc;
```

### 2.3 特征计算伪代码

#### 2.3.1 完整特征计算流程

```python
#!/usr/bin/env python3
"""
V51.1 赛前特征计算引擎 (Pre-match Feature Calculator)
====================================================
核心功能:
1. 从 feature_snapshots 提取 V51.0 原始特征
2. 计算赛前滚动统计 (实力底蕴、即时状态、主客场、疲劳度)
3. 存储到 prematch_features 表
4. 确保时空隔离 (before_match_time 约束)

Author: ML Platform Team
Version: V51.1
Date: 2025-12-31
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PreMatchFeatures:
    """赛前特征数据类"""

    # 比赛基础信息
    match_id: str
    match_date: datetime
    home_team: str
    away_team: str

    # 实力底蕴特征 (10 维)
    home_rolling_xg: float | None = None
    home_rolling_xg_std: float | None = None
    home_rolling_shots_on_target: float | None = None
    home_rolling_shots_on_target_std: float | None = None
    home_rolling_possession: float | None = None
    home_rolling_possession_std: float | None = None
    home_rolling_team_rating: float | None = None
    home_rolling_team_rating_std: float | None = None
    rolling_xg_diff: float | None = None
    rolling_possession_diff: float | None = None

    # 即时状态特征 (6 维)
    home_recent_form_points: float | None = None
    home_recent_goals_scored: float | None = None
    home_recent_goals_conceded: float | None = None
    home_recent_win_rate: float | None = None
    home_recent_trend: str | None = None  # 'ascending'/'descending'/'stable'
    momentum_gap: float | None = None

    # 主客场特征 (10 维)
    home_home_win_rate: float | None = None
    home_home_goals_scored: float | None = None
    home_home_goals_conceded: float | None = None
    home_away_win_rate: float | None = None
    home_away_goals_scored: float | None = None
    home_away_goals_conceded: float | None = None
    home_advantage: float | None = None
    away_away_win_rate: float | None = None
    away_away_goals_scored: float | None = None
    away_away_goals_conceded: float | None = None
    venue_bias: float | None = None

    # 疲劳度特征 (8 维)
    home_fatigue_index: float | None = None
    away_fatigue_index: float | None = None
    fatigue_diff: float | None = None
    home_rest_days: float | None = None
    away_rest_days: float | None = None
    rest_days_diff: float | None = None
    home_matches_7days: int | None = None
    away_matches_7days: int | None = None

    # 积分榜特征 (8 维)
    home_table_position: int | None = None
    away_table_position: int | None = None
    table_position_diff: int | None = None
    home_points: float | None = None
    away_points: float | None = None
    points_diff: float | None = None
    home_recent_form_points: float | None = None
    away_recent_form_points: float | None = None

    # ELO 评分特征 (2 维)
    raw_elo_gap: float | None = None
    adjusted_elo_gap: float | None = None

    # 质量指标
    home_history_count: int = 0
    away_history_count: int = 0
    is_valid: bool = False

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }


class PreMatchFeatureCalculator:
    """
    V51.1 赛前特征计算引擎

    核心特性:
    1. 严格时空隔离 (before_match_time 约束)
    2. 可追溯计算 (记录所有中间结果)
    3. 质量自检 (history_count 检查)
    4. 高性能查询 (使用连接池 + 批量处理)
    """

    def __init__(
        self,
        rolling_window: int = 10,
        recent_window: int = 3,
        min_history: int = 5,
        feature_version: str = "V51.1",
    ):
        """
        初始化计算引擎

        Args:
            rolling_window: 滚动窗口大小 (默认 10 场)
            recent_window: 近期窗口大小 (默认 3 场)
            min_history: 最低历史比赛要求
            feature_version: 特征版本
        """
        self.rolling_window = rolling_window
        self.recent_window = recent_window
        self.min_history = min_history
        self.feature_version = feature_version

        # 数据库连接
        settings = get_settings()
        self.conn_params = {
            "host": settings.database.host,
            "port": settings.database.port,
            "database": settings.database.name,
            "user": settings.database.user,
            "password": settings.database.password.get_secret_value(),
        }

        logger.info(
            "V51.1 赛前特征计算器已初始化",
            rolling_window=rolling_window,
            recent_window=recent_window,
            min_history=min_history,
        )

    def get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.conn_params)

    def calculate_team_history(
        self,
        team_name: str,
        before_match_time: datetime,
        venue: str | None = None,  # 'home'/'away'/None(全部)
    ) -> pd.DataFrame:
        """
        获取球队历史比赛（时空隔离）

        Args:
            team_name: 球队名称
            before_match_time: 时空隔离时间点
            venue: 场地过滤 ('home'/'away'/None)

        Returns:
            历史比赛 DataFrame
        """
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 基础查询
                query = """
                    SELECT
                        m.match_id,
                        m.match_date,
                        m.home_team,
                        m.away_team,
                        m.home_score,
                        m.away_score,
                        m.status,
                        s.raw_features
                    FROM matches m
                    INNER JOIN feature_snapshots s
                        ON m.match_id = s.match_id
                    WHERE m.status = 'finished'
                      AND m.home_score IS NOT NULL
                      AND m.away_score IS NOT NULL
                      AND m.match_date < %s
                """

                params = [before_match_time]

                # 场地过滤
                if venue == "home":
                    query += " AND m.home_team = %s"
                    params.append(team_name)
                elif venue == "away":
                    query += " AND m.away_team = %s"
                    params.append(team_name)
                else:
                    query += " AND (m.home_team = %s OR m.away_team = %s)"
                    params.extend([team_name, team_name])

                # 排序和限制
                query += " ORDER BY m.match_date DESC LIMIT %s"
                params.append(self.rolling_window * 2)  # 多取一些，后续过滤

                cur.execute(query, params)
                rows = cur.fetchall()

                if not rows:
                    logger.warning(
                        "未找到球队历史记录",
                        team=team_name,
                        before_time=before_match_time,
                        venue=venue,
                    )
                    return pd.DataFrame()

                # 转换为 DataFrame
                df = pd.DataFrame([dict(row) for row in rows])

                # 提取球队数据（区分主客场）
                df["is_home"] = df["home_team"] == team_name

                # 提取统计指标
                df["team_score"] = df.apply(
                    lambda row: row["home_score"] if row["is_home"] else row["away_score"],
                    axis=1,
                )
                df["opponent_score"] = df.apply(
                    lambda row: row["away_score"] if row["is_home"] else row["home_score"],
                    axis=1,
                )

                # 计算积分
                df["points"] = df.apply(
                    lambda row: (
                        3 if row["team_score"] > row["opponent_score"]
                        else 1 if row["team_score"] == row["opponent_score"]
                        else 0
                    ),
                    axis=1,
                )

                logger.info(
                    "球队历史查询完成",
                    team=team_name,
                    venue=venue,
                    matches_found=len(df),
                )

                return df

        finally:
            conn.close()

    def extract_stats_from_snapshot(
        self,
        raw_features: dict,
        is_home: bool,
    ) -> dict[str, float]:
        """
        从 feature_snapshots.raw_features 提取统计指标

        Args:
            raw_features: V51.0 原始特征 (JSONB)
            is_home: 是否为主队

        Returns:
            统计指标字典
        """
        # V51.0 特征路径模式
        prefix = "home" if is_home else "away"

        # 尝试多种可能的路径
        stats = {}

        # xG (预期进球)
        for path in [
            f"header_content_stats_{prefix}_xg",
            f"content_stats_{prefix}_xg",
            f"{prefix}_xg",
        ]:
            if path in raw_features:
                stats["xg"] = float(raw_features[path])
                break

        # 射正
        for path in [
            f"header_content_stats_{prefix}_shotsOnTarget",
            f"content_stats_{prefix}_shots_on_target",
            f"{prefix}_shots_on_target",
        ]:
            if path in raw_features:
                stats["shots_on_target"] = float(raw_features[path])
                break

        # 控球率
        for path in [
            f"header_content_stats_{prefix}_possession",
            f"content_stats_{prefix}_possession",
            f"{prefix}_possession",
        ]:
            if path in raw_features:
                stats["possession"] = float(raw_features[path])
                break

        # 评分
        for path in [
            f"content_matchStats_stats_rating_{prefix}",
            f"{prefix}_team_rating",
            f"rating_{prefix}",
        ]:
            if path in raw_features:
                stats["team_rating"] = float(raw_features[path])
                break

        return stats

    def calculate_strength_features(
        self,
        history_df: pd.DataFrame,
        is_home: bool,
    ) -> dict[str, float]:
        """
        计算实力底蕴特征 (Past 10 matches average)

        Args:
            history_df: 历史比赛数据
            is_home: 是否为主队

        Returns:
            实力特征字典
        """
        if history_df.empty:
            return {}

        features = {}

        # 提取统计指标
        stats_list = []
        for _, row in history_df.iterrows():
            raw_features = row.get("raw_features", {})
            stats = self.extract_stats_from_snapshot(raw_features, row["is_home"])
            stats_list.append(stats)

        stats_df = pd.DataFrame(stats_list)

        # 计算滚动平均和标准差
        for metric in ["xg", "shots_on_target", "possession", "team_rating"]:
            if metric in stats_df.columns:
                values = stats_df[metric].dropna()
                if len(values) > 0:
                    prefix = "home" if is_home else "away"
                    features[f"{prefix}_rolling_{metric}"] = float(values.mean())
                    features[f"{prefix}_rolling_{metric}_std"] = float(values.std()) if len(values) > 1 else 0.0

        return features

    def calculate_recent_form_features(
        self,
        history_df: pd.DataFrame,
        is_home: bool,
    ) -> dict[str, float]:
        """
        计算即时状态特征 (Past 3 matches trend)

        Args:
            history_df: 历史比赛数据
            is_home: 是否为主队

        Returns:
            状态特征字典
        """
        if history_df.empty:
            return {}

        # 取最近 N 场
        recent_df = history_df.head(self.recent_window)

        features = {}

        prefix = "home" if is_home else "away"

        # 积分
        features[f"{prefix}_recent_form_points"] = float(recent_df["points"].sum())

        # 进球/失球
        features[f"{prefix}_recent_goals_scored"] = float(recent_df["team_score"].sum())
        features[f"{prefix}_recent_goals_conceded"] = float(recent_df["opponent_score"].sum())

        # 胜率
        wins = (recent_df["points"] == 3).sum()
        features[f"{prefix}_recent_win_rate"] = float(wins / len(recent_df))

        # 趋势判断
        if len(recent_df) >= 2:
            recent_points = recent_df["points"].tolist()
            if recent_points[0] > recent_points[-1]:
                features[f"{prefix}_recent_trend"] = "ascending"
            elif recent_points[0] < recent_points[-1]:
                features[f"{prefix}_recent_trend"] = "descending"
            else:
                features[f"{prefix}_recent_trend"] = "stable"
        else:
            features[f"{prefix}_recent_trend"] = "stable"

        return features

    def calculate_venue_features(
        self,
        team_name: str,
        before_match_time: datetime,
    ) -> dict[str, float]:
        """
        计算主客场特定特征

        Args:
            team_name: 球队名称
            before_match_time: 时空隔离时间点

        Returns:
            主客场特征字典
        """
        features = {}

        # 主场数据
        home_df = self.get_team_history(team_name, before_match_time, venue="home")
        if not home_df.empty:
            features["home_home_win_rate"] = float((home_df["points"] == 3).sum() / len(home_df))
            features["home_home_goals_scored"] = float(home_df["team_score"].mean())
            features["home_home_goals_conceded"] = float(home_df["opponent_score"].mean())
            features["home_home_clean_sheets"] = float((home_df["opponent_score"] == 0).sum() / len(home_df))

        # 客场数据
        away_df = self.get_team_history(team_name, before_match_time, venue="away")
        if not away_df.empty:
            features["home_away_win_rate"] = float((away_df["points"] == 3).sum() / len(away_df))
            features["home_away_goals_scored"] = float(away_df["team_score"].mean())
            features["home_away_goals_conceded"] = float(away_df["opponent_score"].mean())
            features["home_away_clean_sheets"] = float((away_df["opponent_score"] == 0).sum() / len(away_df))

        # 主客场优势
        if "home_home_win_rate" in features and "home_away_win_rate" in features:
            features["home_advantage"] = features["home_home_win_rate"] - features["home_away_win_rate"]

        return features

    def calculate_fatigue_features(
        self,
        team_name: str,
        before_match_time: datetime,
    ) -> dict[str, float]:
        """
        计算疲劳度特征

        Args:
            team_name: 球队名称
            before_match_time: 时空隔离时间点

        Returns:
            疲劳度特征字典
        """
        # 获取历史比赛（不限场地）
        history_df = self.get_team_history(team_name, before_match_time)

        if history_df.empty:
            return {}

        features = {}

        # 计算比赛密度
        now = before_match_time
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        # 7 天内比赛数
        matches_7days = history_df[history_df["match_date"] >= seven_days_ago]
        features[f"{team_name}_matches_7days"] = len(matches_7days)

        # 30 天内比赛数
        matches_30days = history_df[history_df["match_date"] >= thirty_days_ago]
        features[f"{team_name}_matches_30days"] = len(matches_30days)

        # 疲劳度指数 (7 天内比赛数 / 7)
        features[f"{team_name}_fatigue_index"] = min(len(matches_7days) / 7.0, 1.0)

        # 休息天数 (距离上一场)
        if len(history_df) > 0:
            last_match_date = history_df.iloc[0]["match_date"]
            rest_days = (now - last_match_date).days
            features[f"{team_name}_rest_days"] = float(rest_days)
        else:
            features[f"{team_name}_rest_days"] = 999.0  # 无历史，视为充分休息

        return features

    def calculate_prematch_features(
        self,
        match_id: str,
        match_date: datetime,
        home_team: str,
        away_team: str,
    ) -> PreMatchFeatures:
        """
        计算单场比赛的完整赛前特征

        Args:
            match_id: 比赛 ID
            match_date: 比赛时间
            home_team: 主队
            away_team: 客队

        Returns:
            赛前特征对象
        """
        features = PreMatchFeatures(
            match_id=match_id,
            match_date=match_date,
            home_team=home_team,
            away_team=away_team,
        )

        # ===== 时空隔离协议 =====
        # 确保只查询 match_date 之前的比赛
        before_match_time = match_date

        # ===== 主队历史 =====
        home_history = self.get_team_history(home_team, before_match_time)
        features.home_history_count = len(home_history)

        if len(home_history) >= self.min_history:
            # 实力特征
            strength = self.calculate_strength_features(home_history, is_home=True)
            for k, v in strength.items():
                setattr(features, k, v)

            # 状态特征
            recent = self.calculate_recent_form_features(home_history, is_home=True)
            for k, v in recent.items():
                setattr(features, k, v)

            # 主客场特征
            venue = self.calculate_venue_features(home_team, before_match_time)
            for k, v in venue.items():
                setattr(features, k, v)

            # 疲劳度特征
            fatigue = self.calculate_fatigue_features(home_team, before_match_time)
            for k, v in fatigue.items():
                if k.startswith("home_"):
                    setattr(features, k, v)

        # ===== 客队历史 =====
        away_history = self.get_team_history(away_team, before_match_time)
        features.away_history_count = len(away_history)

        if len(away_history) >= self.min_history:
            # 实力特征
            strength = self.calculate_strength_features(away_history, is_home=False)
            for k, v in strength.items():
                setattr(features, k, v)

            # 状态特征
            recent = self.calculate_recent_form_features(away_history, is_home=False)
            for k, v in recent.items():
                setattr(features, k, v)

            # 主客场特征
            venue = self.calculate_venue_features(away_team, before_match_time)
            for k, v in venue.items():
                if k.startswith("home_"):
                    # 重命名: away_home_*
                    k = k.replace("home_", "away_home_", 1)
                elif k.startswith("home_away_"):
                    # 重命名: away_away_*
                    k = k.replace("home_", "away_", 1)
                setattr(features, k, v)

            # 疲劳度特征
            fatigue = self.calculate_fatigue_features(away_team, before_match_time)
            for k, v in fatigue.items():
                if k.startswith("away_"):
                    setattr(features, k, v)

        # ===== 差值特征 =====
        if hasattr(features, "home_rolling_xg") and hasattr(features, "away_rolling_xg"):
            features.rolling_xg_diff = features.home_rolling_xg - features.away_rolling_xg

        if hasattr(features, "home_rolling_possession") and hasattr(features, "away_rolling_possession"):
            features.rolling_possession_diff = features.home_rolling_possession - features.away_rolling_possession

        if hasattr(features, "home_recent_form_points") and hasattr(features, "away_recent_form_points"):
            features.recent_form_diff = features.home_recent_form_points - features.away_recent_form_points

        if hasattr(features, "home_fatigue_index") and hasattr(features, "away_fatigue_index"):
            features.fatigue_diff = features.home_fatigue_index - features.away_fatigue_index

        if hasattr(features, "home_rest_days") and hasattr(features, "away_rest_days"):
            features.rest_days_diff = features.home_rest_days - features.away_rest_days

        # ===== 质量检查 =====
        features.is_valid = (
            features.home_history_count >= self.min_history
            and features.away_history_count >= self.min_history
        )

        return features

    def save_to_database(self, features: PreMatchFeatures) -> bool:
        """
        保存赛前特征到数据库

        Args:
            features: 赛前特征对象

        Returns:
            是否保存成功
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # 构建插入 SQL
                columns = [
                    "match_id", "match_date", "home_team", "away_team",
                    "home_history_count", "away_history_count", "is_valid",
                    "feature_version",
                ]

                # 添加所有特征列
                for k, v in features.to_dict().items():
                    if k not in columns and v is not None:
                        columns.append(k)

                # 构建值列表
                values = []
                placeholders = []
                for col in columns:
                    value = getattr(features, col, None)
                    values.append(value)
                    placeholders.append("%s")

                # 插入数据
                query = f"""
                    INSERT INTO prematch_features ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                    ON CONFLICT (match_id, feature_version)
                    DO UPDATE SET
                        computed_at = CURRENT_TIMESTAMP,
                        is_valid = EXCLUDED.is_valid
                """

                cur.execute(query, values)
                conn.commit()

                logger.info(
                    "赛前特征已保存",
                    match_id=features.match_id,
                    is_valid=features.is_valid,
                )

                return True

        except Exception as e:
            logger.error(
                "保存赛前特征失败",
                match_id=features.match_id,
                error=str(e),
            )
            conn.rollback()
            return False

        finally:
            conn.close()

    def batch_calculate(
        self,
        match_ids: list[str] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        批量计算赛前特征

        Args:
            match_ids: 指定比赛 ID 列表
            limit: 限制数量

        Returns:
            统计信息字典
        """
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 查询比赛列表
                query = """
                    SELECT match_id, match_date, home_team, away_team
                    FROM matches
                    WHERE status = 'finished'
                      AND home_score IS NOT NULL
                      AND away_score IS NOT NULL
                """

                params = []

                if match_ids:
                    query += " AND match_id = ANY(%s)"
                    params.append(match_ids)

                query += " ORDER BY match_date DESC"

                if limit:
                    query += " LIMIT %s"
                    params.append(limit)

                cur.execute(query, params)
                matches = cur.fetchall()

                logger.info(f"开始批量计算 {len(matches)} 场比赛的赛前特征")

                success_count = 0
                failed_count = 0
                invalid_count = 0

                for match in matches:
                    try:
                        features = self.calculate_prematch_features(
                            match_id=match["match_id"],
                            match_date=match["match_date"],
                            home_team=match["home_team"],
                            away_team=match["away_team"],
                        )

                        if self.save_to_database(features):
                            success_count += 1
                            if not features.is_valid:
                                invalid_count += 1
                        else:
                            failed_count += 1

                    except Exception as e:
                        logger.error(
                            "计算赛前特征失败",
                            match_id=match["match_id"],
                            error=str(e),
                        )
                        failed_count += 1

                logger.info(
                    "批量计算完成",
                    total=len(matches),
                    success=success_count,
                    failed=failed_count,
                    invalid=invalid_count,
                )

                return {
                    "total": len(matches),
                    "success": success_count,
                    "failed": failed_count,
                    "invalid": invalid_count,
                }

        finally:
            conn.close()


# ============================================
# 使用示例
# ============================================

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V51.1 赛前特征计算引擎",
    )
    parser.add_argument("--limit", type=int, default=100, help="计算比赛数量")
    parser.add_argument("--match-ids", nargs="+", help="指定比赛 ID")

    args = parser.parse_args()

    calculator = PreMatchFeatureCalculator(
        rolling_window=10,
        recent_window=3,
        min_history=5,
    )

    stats = calculator.batch_calculate(
        match_ids=args.match_ids,
        limit=args.limit,
    )

    print("\n" + "=" * 60)
    print("V51.1 赛前特征计算摘要")
    print("=" * 60)
    print(f"总计: {stats['total']} 场")
    print(f"成功: {stats['success']} 场")
    print(f"失败: {stats['failed']} 场")
    print(f"无效: {stats['invalid']} 场 (历史不足)")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

---

## 第三部分：交付标准检查

### 3.1 可追溯性 (Traceability)

| 检查项 | V51.0 现状 | V51.1 改进 |
|--------|-----------|-----------|
| **特征来源** | ❌ CSV 文件，无来源记录 | ✅ feature_snapshots.raw_features 存储 JSON 源路径 |
| **计算逻辑** | ❌ 代码逻辑，无文档 | ✅ feature_registry.computation_logic 记录 SQL/Python 伪代码 |
| **参数追踪** | ❌ 无参数记录 | ✅ feature_snapshots.extractor_config 存储提取器配置快照 |
| **血缘关系** | ❌ 无法追溯特征依赖 | ✅ feature_registry.dependencies 记录特征依赖链 |

### 3.2 可复现性 (Reproducibility)

| 检查项 | V51.0 现状 | V51.1 改进 |
|--------|-----------|-----------|
| **确定性计算** | ⚠️ 依赖代码逻辑 | ✅ SQL 计算保证确定性（相同输入 → 相同输出） |
| **版本管理** | ❌ CSV 无版本信息 | ✅ feature_version 字段支持多版本共存 |
| **快照机制** | ❌ 无数据快照 | ✅ feature_snapshots 存储原始数据快照 |
| **验证机制** | ❌ 无验证 | ✅ quality_score + null_count 质量指标 |

### 3.3 可观测性 (Observability)

| 检查项 | V51.0 现状 | V51.1 改进 |
|--------|-----------|-----------|
| **错误捕获** | ⚠️ 异常被捕获但未记录 | ✅ extraction_status + error_message 详细记录 |
| **性能监控** | ❌ 无性能数据 | ✅ processing_time_ms 性能指标 |
| **质量监控** | ❌ 无质量检查 | ✅ quality_score + null_count + is_valid 质量门禁 |
| **告警机制** | ❌ 无告警 | ✅ 可基于 extraction_status = 'failed' 设置告警 |

---

## 第四部分：关键问题与修复建议

### 4.1 L1→L2→V51 "不合拍" 代码点

#### 问题 1: match_id vs external_id 不一致

**位置**: `src/api/collectors/v51_incremental_collector.py:557-559`

```python
# ❌ 当前代码：冗余字段
batch_data.append((
    str(match_id),      # match_id (主键)
    str(match_id),      # external_id (与 match_id 相同值!)
    ...
))
```

**修复方案**:
```python
# ✅ 修复后：移除 external_id，统一使用 match_id
batch_data.append((
    str(match_id),      # match_id (主键)
    ...
))
```

#### 问题 2: V51 查询冗余字段

**位置**: `src/processors/v51_feature_refiner.py:624`

```python
# ❌ 当前代码：查询未使用的 external_id
SELECT m.match_id, m.external_id, ...
```

**修复方案**:
```python
# ✅ 修复后：移除 external_id
SELECT m.match_id, ...
```

#### 问题 3: 无赛前特征提取

**位置**: `src/processors/v51_feature_refiner.py:全文`

**问题**: V51.0 提取的是**赛后统计** (xG, 射正, 控球等)，不是**赛前预测信号**

**修复方案**: 实现上述 `PreMatchFeatureCalculator`，计算滚动统计特征

### 4.2 数据库修复脚本

```sql
-- ============================================
-- V51.1 数据库修复脚本
-- ============================================

-- 1. 移除冗余 external_id 字段
ALTER TABLE matches DROP COLUMN IF EXISTS external_id;

-- 2. 创建特征快照表
-- (见上文表结构设计)

-- 3. 创建赛前特征表
-- (见上文表结构设计)

-- 4. 创建特征注册表
-- (见上文表结构设计)

-- 5. 迁移现有 V51 CSV 数据到 feature_snapshots
-- (需要 Python 脚本辅助)

-- 6. 验证数据完整性
SELECT
    COUNT(*) as total_matches,
    COUNT(CASE WHEN raw_features IS NOT NULL THEN 1 END) as with_features,
    COUNT(CASE WHEN extraction_status = 'success' THEN 1 END) as success_count
FROM feature_snapshots;
```

---

## 第五部分：实施路线图

### Phase 1: 数据库重构 (P0 - 紧急)

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 创建 feature_snapshots 表 | 2h | P0 |
| 创建 prematch_features 表 | 2h | P0 |
| 创建 feature_registry 表 | 1h | P0 |
| 修复 match_id/external_id 不一致 | 1h | P0 |
| 迁移现有 V51 数据 | 4h | P0 |

**预计完成**: 1-2 个工作日

### Phase 2: 特征计算引擎 (P0 - 紧急)

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 实现 PreMatchFeatureCalculator | 8h | P0 |
| 实现多进程并行提取 | 4h | P1 |
| 实现质量检查机制 | 2h | P0 |
| 单元测试覆盖 | 4h | P0 |

**预计完成**: 3-4 个工作日

### Phase 3: 监控与告警 (P1 - 重要)

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 接入 Prometheus 指标 | 4h | P1 |
| 配置告警规则 | 2h | P1 |
| 创建 Grafana 仪表盘 | 4h | P2 |

**预计完成**: 2-3 个工作日

### Phase 4: 性能优化 (P2 - 可选)

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 实现数据库连接池 | 2h | P2 |
| 优化 JSONB 查询 | 4h | P2 |
| 实现特征缓存 | 4h | P2 |

**预计完成**: 2-3 个工作日

---

## 附录

### A. 关键文件清单

| 文件 | 作用 | 优先级 |
|------|------|--------|
| `src/api/collectors/v51_incremental_collector.py` | L1→L2 采集，自愈机制 | P0 |
| `src/processors/v51_feature_refiner.py` | V51 特征提取 (赛后) | P0 |
| `src/database/schema_manager.py` | 数据库 Schema 管理 | P0 |
| `deploy/docker/init_db.sql` | 数据库初始化脚本 | P0 |
| `scripts/ml/generate_v51_training_set.py` | CSV 存储逻辑 (待重构) | P1 |

### B. 术语表

| 术语 | 定义 |
|------|------|
| L1 索引 | Rich L1 数据，包含 match_id, 比分, 状态, 时间 |
| L2 原始数据 | FotMob API 完整 JSON，存储在 raw_match_data.raw_data |
| V51.0 特征 | 从 L2 提取的 642 维赛后统计指标 |
| V51.1 赛前特征 | 从历史 V51.0 特征计算的滚动统计信号 |
| 时空隔离 | 确保计算特征时只使用 before_match_time 之前的数据 |
| 自愈机制 | V51.1 自动修复僵尸比赛状态 (scheduled → finished) |

---

**审计报告生成时间**: 2025-12-31
**版本**: V51.1 Audit Report (Final)
**状态**: 待批准实施

---

## 签署

**审计人员**: Claude (首席系统架构师 & ML 平台专家)
**审核状态**: ✅ 完成
**建议行动**: 立即启动 Phase 1 (数据库重构)
