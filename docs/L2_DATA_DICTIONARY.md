# V37.1 L2 数据资产字典（Data Dictionary）

> **用途**: L2 数据 → L3 特征工程的"契约"
>
> **目标**: 明确定义 `raw_match_data.raw_data` (JSONB) 中的字段位置，供模型开发者使用

---

## 📋 概述

`raw_match_data` 表存储来自 FotMob API 的原始 L2 比赛详情数据，数据格式为 JSONB。

**表结构**:
```sql
CREATE TABLE raw_match_data (
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id),
    raw_data JSONB NOT NULL,           -- ← 核心数据字段
    source VARCHAR(50) DEFAULT 'fotmob',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(match_id)
);
```

---

## 🔍 JSONB 字段路径映射

### A. 统计数据（核心预测特征）

FotMob API 路径: `content.stats.Period[0]`

| JSON 路径 | 字段名称 | 类型 | 说明 | L3 用途 |
|----------|---------|------|------|---------|
| `raw_data->'content'->'stats'->'Period'->0->'xG'->'home'` | `xg_home` | float | 主队预期进球 | **核心特征** |
| `raw_data->'content'->'stats'->'Period'->0->'xG'->'away'` | `xg_away` | float | 客队预期进球 | **核心特征** |
| `raw_data->'content'->'stats'->'Period'->0->'shotsOnTarget'->'home'` | `shots_on_target_home` | int | 主队射正数 | **核心特征** |
| `raw_data->'content'->'stats'->'Period'->0->'shotsOnTarget'->'away'` | `shots_on_target_away` | int | 客队射正数 | **核心特征** |
| `raw_data->'content'->'stats'->'Period'->0->'possession'->'home'` | `possession_home` | float | 主队控球率 (%) | **核心特征** |
| `raw_data->'content'->'stats'->'Period'->0->'possession'->'away'` | `possession_away` | float | 客队控球率 (%) | **核心特征** |
| `raw_data->'content'->'stats'->'Period'->0->'teamRating'->'home'` | `team_rating_home` | float | 主队评分 | 高级特征 |
| `raw_data->'content'->'stats'->'Period'->0->'teamRating'->'away'` | `team_rating_away` | float | 客队评分 | 高级特征 |

**SQL 提取示例**:
```sql
-- 提取 xG 数据（完整比赛）
SELECT
    match_id,
    raw_data->'content'->'stats'->'Period'->0->'xG'->>'home' as xg_home,
    raw_data->'content'->'stats'->'Period'->0->'xG'->>'away' as xg_away
FROM raw_match_data
WHERE raw_data->'content'->'stats'->'Period' IS NOT NULL;
```

**Python 提取示例**:
```python
import asyncpg

async def extract_xg_features(match_id: str) -> dict:
    conn = await asyncpg.connect(...)
    row = await conn.fetchrow("""
        SELECT
            raw_data->'content'->'stats'->'Period'->0->'xG'->>'home' as xg_home,
            raw_data->'content'->'stats'->'Period'->0->'xG'->>'away' as xg_away
        FROM raw_match_data
        WHERE match_id = $1
    """, match_id)
    return dict(row)
```

---

### B. 阵容信息（Lineup）

FotMob API 路径: `content.lineup`

| JSON 路径 | 字段名称 | 类型 | 说明 |
|----------|---------|------|------|
| `raw_data->'content'->'lineup'->'home'` | `lineup_home` | jsonb | 主队阵容 |
| `raw_data->'content'->'lineup'->'away'` | `lineup_away` | jsonb | 客队阵容 |
| `raw_data->'content'->'lineup'->'home'->0->'name'` | `player_name` | str | 球员姓名 |
| `raw_data->'content'->'lineup'->'home'->0->'position'` | `player_position` | str | 位置 (GK, DF, MF, FW) |
| `raw_data->'content'->'lineup'->'home'->0->'shirtNumber'` | `shirt_number` | int | 球衣号码 |
| `raw_data->'content'->'lineup'->'home'->0->'isHomeTeam'` | `is_home_team` | bool | 是否主队 |

**提取示例**:
```sql
-- 检查是否有阵容数据
SELECT
    match_id,
    raw_data->'content' ? 'lineup' as has_lineup
FROM raw_match_data;
```

---

### C. 射门图数据（Shotmap）

FotMob API 路径: `content.shotmap`

| JSON 路径 | 字段名称 | 类型 | 说明 |
|----------|---------|------|------|
| `raw_data->'content'->'shotmap'->'shots'` | `shots` | jsonb | 所有射门事件 |
| `raw_data->'content'->'shotmap'->'shots'->0->'xg'` | `shot_xg` | float | 单次射门 xG |
| `raw_data->'content'->'shotmap'->'shots'->0->'isGoal'` | `is_goal` | bool | 是否进球 |
| `raw_data->'content'->'shotmap'->'shots'->0->'situation'->'type'` | `situation_type` | str | 射门类型 |
| `raw_data->'content'->'shotmap'->'shots'->0->'playerName'` | `player_name` | str | 射门球员 |

---

### D. 元数据（Metadata）

FotMob API 路径: `general`

| JSON 路径 | 字段名称 | 类型 | 说明 |
|----------|---------|------|------|
| `raw_data->'general'->'leagueName'` | `league_name` | str | 联赛名称 |
| `raw_data->'general'->'matchID'` | `match_id_original` | str | FotMob 原始 ID |
| `raw_data->'general'->'matchTime'` | `match_time_utc` | str | UTC 时间戳 |
| `raw_data->'general'->'teamColors'` | `team_colors` | jsonb | 球队颜色（嵌套结构） |

---

### E. 数据质量标记

| 字段路径 | 说明 |
|---------|------|
| `raw_data->'data_quality'` | 质量分级 (full/partial/warning) |
| `raw_data->'stats'->'xg'` | 提取后的 xG 数据 (简化路径) |
| `raw_data->'fetched_at'` | 采集时间戳 |

---

## 📊 完整提取示例

### V26.7/V26.8 特征工程映射

```sql
-- L3 特征工程所需的完整特征提取
WITH l2_features AS (
    SELECT
        match_id,
        -- 统计数据
        raw_data->'content'->'stats'->'Period'->0->'xG'->>'home' as xg_home,
        raw_data->'content'->'stats'->'Period'->0->'xG'->>'away' as xg_away,
        raw_data->'content'->'stats'->'Period'->0->'shotsOnTarget'->>'home' as shots_on_target_home,
        raw_data->'content'->'stats'->'Period'->0->'shotsOnTarget'->>'away' as shots_on_target_away,
        raw_data->'content'->'stats'->'Period'->0->'possession'->>'home' as possession_home,
        raw_data->'content'->'stats'->'Period'->0->'possession'->>'away' as possession_away,
        raw_data->'content'->'stats'->'Period'->0->'teamRating'->>'home' as team_rating_home,
        raw_data->'content'->'stats'->'Period'->0->'teamRating'->>'away' as team_rating_away,

        -- 元数据
        raw_data->'general'->'matchTime' as match_time_utc,
        raw_data->'data_quality' as data_quality,

        -- 完整性检查
        raw_data->'content' ? 'lineup' as has_lineup,
        raw_data->'content' ? 'shotmap' as has_shotmap

    FROM raw_match_data
)
SELECT * FROM l2_features
WHERE xg_home IS NOT NULL
ORDER BY match_time_utc DESC;
```

---

## 🔧 数据质量过滤

### FULL 质量数据（推荐用于训练）

```sql
-- 只选择 FULL 质量的比赛（xG 完整）
SELECT
    match_id,
    raw_data->'content'->'stats'->'Period'->0->'xG'->>'home' as xg_home
FROM raw_match_data
WHERE raw_data->>'data_quality' = 'full';
```

### PARTIAL 质量数据（降级使用）

```sql
-- 选择 PARTIAL 质量（xG 缺失，但其他特征存在）
SELECT
    match_id,
    raw_data->'content'->'stats'->'Period'->0->'shotsOnTarget'->>'home' as shots_home
FROM raw_match_data
WHERE raw_data->>'data_quality' = 'partial';
```

---

## 📝 契约示例

### 1. 从 L2 提取 xG 特征

```python
import asyncpg

async def get_xg_features(pool: asyncpg.Pool, match_id: str) -> dict:
    """
    从 raw_match_data 提取 xG 特征

    契约: 确保 match_id 的 raw_data->>'data_quality' = 'full'
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                raw_data->'content'->'stats'->'Period'->0->'xG'->>'home' as xg_home,
                raw_data->'content'->'stats'->'Period'->0->'xG'->>'away' as xg_away,
                raw_data->'content'->'stats'->'Period'->0->'possession'->>'home' as possession_home
            FROM raw_match_data
            WHERE match_id = $1
              AND raw_data->>'data_quality' = 'full'
        """, match_id)

        if row is None:
            raise ValueError(f"Match {match_id} 数据质量不符合要求")

        return {
            "xg_home": float(row["xg_home"]) if row["xg_home"] else None,
            "xg_away": float(row["xg_away"]) if row["xg_away"] else None,
            "possession_home": float(row["possession_home"]) if row["possession_home"] else None,
        }
```

### 2. 批量提取训练数据

```python
async def extract_training_dataset(pool: asyncpg.Pool, min_quality: str = "partial"):
    """
    批量提取训练数据集

    Args:
        min_quality: 最低质量要求 (full/partial/warning)
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                match_id,
                raw_data->'content'->'stats'->'Period'->0 as stats
            FROM raw_match_data
            WHERE raw_data->>'data_quality' = $1
            ORDER BY match_id
        """, min_quality)

    return [dict(row) for row in rows]
```

---

## ⚠️ 重要注意事项

### 1. 数据结构变化

FotMob API 可能随时调整数据结构，如：
- `Period[0]` → `Period[1]`（如果是上半场/下半场）
- `xG.home` → `xG.homeTeam`
- 字段完全移除

**应对方案**:
- 定期运行 `pre_harvest_final_check.py` 验证 Pydantic Schema
- 查看 `logs/auto_harvest.log` 中的校验错误

### 2. NULL 值处理

```sql
-- 正确的 NULL 处理方式
SELECT
    match_id,
    -- 使用 COALESCE 提供默认值
    COALESCE(
        raw_data->'content'->'stats'->'Period'->0->'xG'->>'home',
        0.0
    ) as xg_home_safe
FROM raw_match_data;
```

### 3. 性能优化

```sql
-- 使用 GIN 索引加速 JSONB 查询
CREATE INDEX IF NOT EXISTS idx_raw_data_gin
    ON raw_match_data USING GIN(raw_data);

-- 查询时使用 @> 检查 JSON 包含
SELECT match_id
FROM raw_match_data
WHERE raw_data @> '{"content": {"stats": {"Period": [...]}}}';
```

---

## 📚 相关文档

- **L2 采集器**: `src/api/collectors/production_l2_collector.py`
- **Pydantic Schema**: `src/api/collectors/schemas/l2_match_schema.py`
- **断点续传 Runbook**: `docs/RESUMABLE_HARVEST_RUNBOOK.md`
- **API 参考**: `scripts/collectors/README.md`

---

**最后更新**: 2025-12-29 | **版本**: V37.1 | **维护者**: ML Architect
