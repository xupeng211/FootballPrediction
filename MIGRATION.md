# V175 数据库迁移指南

> **版本**: V175.0.0 | **更新日期**: 2026-03-01

---

## 概述

本文档记录 V175 版本新增的所有数据库列及字段含义，确保团队成员对数据库结构有清晰的理解。

---

## 1. matches 表新增列

V175 为 `matches` 表添加了核心统计指标列，用于存储从 FotMob 提取的 xG、控球率等数据。

### 1.1 xG (期望进球) 列

| 列名 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| `xg_home` | `NUMERIC(5,2)` | 主队期望进球 | `2.35` |
| `xg_away` | `NUMERIC(5,2)` | 客队期望进球 | `1.12` |

**数据来源**: FotMob API `content.stats.Periods.All.stats` 中 `expected_goals` 字段

### 1.2 控球率列

| 列名 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| `possession_home` | `NUMERIC(5,2)` | 主队控球率 (0-1) | `0.65` |
| `possession_away` | `NUMERIC(5,2)` | 客队控球率 (0-1) | `0.35` |

**数据来源**: FotMob API `content.stats` 中 `possession` 字段

### 1.3 射门统计列

| 列名 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| `shots_home` | `INTEGER` | 主队射门次数 | `15` |
| `shots_away` | `INTEGER` | 客队射门次数 | `8` |
| `shots_on_target_home` | `INTEGER` | 主队射正次数 | `6` |
| `shots_on_target_away` | `INTEGER` | 客队射正次数 | `3` |

### 1.4 其他统计列

| 列名 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| `corners_home` | `INTEGER` | 主队角球数 | `7` |
| `corners_away` | `INTEGER` | 客队角球数 | `4` |
| `fouls_home` | `INTEGER` | 主队犯规数 | `12` |
| `fouls_away` | `INTEGER` | 客队犯规数 | `8` |

---

## 2. raw_match_data 表字段对齐

### 2.1 字段名统一

| 旧字段名 | 新字段名 | 说明 |
|---------|---------|------|
| `l2_raw_json` | `raw_data` | 统一使用 `raw_data` 作为原始数据存储字段 |

**影响范围**:

- `src/models/RawDataQueries.js`
- `src/core/scheduler/TaskPool.js`
- `src/infrastructure/repositories/FactoryQueries.js`
- `src/domain/services/harvesting/MatchDetailEngine.js`

---

## 3. 新增索引

为优化查询性能，V175 添加了以下索引：

```sql
-- xG 查询优化
CREATE INDEX idx_matches_xg ON matches(xg_home, xg_away) WHERE xg_home IS NOT NULL;

-- 控球率查询优化
CREATE INDEX idx_matches_possession ON matches(possession_home) WHERE possession_home IS NOT NULL;
```

---

## 4. 迁移 SQL 脚本

### 4.1 完整迁移脚本

```sql
-- V175 Schema 迁移脚本
-- 执行前请备份数据库

BEGIN;

-- 添加统计列
ALTER TABLE matches
ADD COLUMN IF NOT EXISTS xg_home NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS xg_away NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS possession_home NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS possession_away NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS shots_home INTEGER,
ADD COLUMN IF NOT EXISTS shots_away INTEGER,
ADD COLUMN IF NOT EXISTS shots_on_target_home INTEGER,
ADD COLUMN IF NOT EXISTS shots_on_target_away INTEGER,
ADD COLUMN IF NOT EXISTS corners_home INTEGER,
ADD COLUMN IF NOT EXISTS corners_away INTEGER,
ADD COLUMN IF NOT EXISTS fouls_home INTEGER,
ADD COLUMN IF NOT EXISTS fouls_away INTEGER;

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_matches_xg ON matches(xg_home, xg_away) WHERE xg_home IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_matches_possession ON matches(possession_home) WHERE possession_home IS NOT NULL;

COMMIT;
```

### 4.2 回滚脚本

```sql
-- V175 回滚脚本 (谨慎使用)

BEGIN;

ALTER TABLE matches
DROP COLUMN IF EXISTS xg_home,
DROP COLUMN IF EXISTS xg_away,
DROP COLUMN IF EXISTS possession_home,
DROP COLUMN IF EXISTS possession_away,
DROP COLUMN IF EXISTS shots_home,
DROP COLUMN IF EXISTS shots_away,
DROP COLUMN IF EXISTS shots_on_target_home,
DROP COLUMN IF EXISTS shots_on_target_away,
DROP COLUMN IF EXISTS corners_home,
DROP COLUMN IF EXISTS corners_away,
DROP COLUMN IF EXISTS fouls_home,
DROP COLUMN IF EXISTS fouls_away;

DROP INDEX IF EXISTS idx_matches_xg;
DROP INDEX IF EXISTS idx_matches_possession;

COMMIT;
```

---

## 5. 数据提取流程

V175 数据提取流程：

```
raw_match_data.raw_data (JSONB)
         │
         ▼
    XGExtractor.js
         │
         ├── extractXG() → xg_home, xg_away
         ├── extractPossession() → possession_home, possession_away
         └── extractAllStats() → 所有统计数据
         │
         ▼
    matches 表 (结构化列)
```

---

## 6. 注意事项

1. **字段名统一**: 所有代码中使用 `raw_data`，不再使用 `l2_raw_json`
2. **数据类型**: xG 使用 `NUMERIC(5,2)` 保留两位小数精度
3. **控球率**: 存储为 0-1 之间的小数，而非百分比
4. **NULL 处理**: 未提取或无数据时保持 `NULL`，不使用默认值

---

*最后更新: 2026-03-01 | V175 Engineering Team*
