# `matches` 表数据字典 (V36.0)

**版本**: V36.0 Production-Grade
**生成日期**: 2025-12-28
**来源**: `src/api/collectors/schemas/l1_match_schema.py:L1MatchData`

---

## 表概览

| 属性 | 值 |
|------|-----|
| **表名** | `matches` |
| **用途** | 存储足球比赛的基础信息（L1 数据层） |
| **主键** | `match_id` |
| **生命周期** | 数据从采集到永久存储，保留历史记录 |

---

## 字段定义

### 1. 核心标识字段

| 字段名 | 数据类型 | 约束 | 业务含义 | 示例值 |
|--------|----------|------|----------|--------|
| `match_id` | VARCHAR(50) | PRIMARY KEY, NOT NULL | FotMob 比赛唯一标识 | `"4813374"` |
| `league_id` | INTEGER | NOT NULL | FotMob 联赛 ID（白名单限制） | `47` (Premier League) |
| `league_name` | VARCHAR(100) | NOT NULL | 联赛名称（与 ID 强一致性校验） | `"Premier League"` |

**League ID 白名单** (V36.0 强制校验):
- `47` → Premier League
- `55` → La Liga
- `54` → Bundesliga
- `61` → Ligue 1
- `135` → Serie A
- `42` → Champions League

---

### 2. 赛季信息字段

| 字段名 | 数据类型 | 约束 | 业务含义 | 示例值 |
|--------|----------|------|----------|--------|
| `season_id` | VARCHAR(10) | NOT NULL | 赛季代码（FotMob 格式） | `"2324"` |
| `season_name` | VARCHAR(20) | NOT NULL | 赛季显示名称 | `"23/24"` |

**赛季代码对照**:
| Season Name | Season Code | 说明 |
|-------------|-------------|------|
| 20/21 | 2021 | 2020-2021 赛季 |
| 21/22 | 2122 | 2021-2022 赛季 |
| 22/23 | 2223 | 2022-2023 赛季 |
| 23/24 | 2324 | 2023-2024 赛季 |
| 24/25 | 2425 | 2024-2025 赛季 |

---

### 3. 球队信息字段

| 字段名 | 数据类型 | 约束 | 业务含义 | 示例值 |
|--------|----------|------|----------|--------|
| `home_team` | VARCHAR(200) | NOT NULL | 主队名称 | `"Manchester United"` |
| `away_team` | VARCHAR(200) | NOT NULL | 客队名称 | `"Liverpool"` |
| `home_team_id` | INTEGER | NOT NULL, >= 1 | FotMob 主队 ID | `19` |
| `away_team_id` | INTEGER | NOT NULL, >= 1 | FotMob 客队 ID | `22` |

---

### 4. 比赛状态字段

| 字段名 | 数据类型 | 约束 | 业务含义 | 示例值 |
|--------|----------|------|----------|--------|
| `status` | VARCHAR(20) | NOT NULL | 比赛状态 | `"finished"` |
| `match_date` | TIMESTAMP WITH TIME ZONE | NULL | 比赛时间（UTC） | `2024-12-26 15:00:00+00` |
| `home_score` | INTEGER | NULL | 主队得分（finished 必填） | `2` |
| `away_score` | INTEGER | NULL | 客队得分（finished 必填） | `1` |

**Status 枚举值**:
| 值 | 含义 | Score 要求 |
|----|------|------------|
| `scheduled` | 未开始 | 必须为 NULL |
| `ongoing` | 进行中 | 可选 |
| `finished` | 已结束 | 必须 NOT NULL |

**业务逻辑校验** (V36.0 Pydantic 强制执行):
```python
# finished 状态必须有比分
if status == "finished" and (home_score is None or away_score is None):
    raise ValidationError("finished 状态必须有比分")

# scheduled 状态不能有比分
if status == "scheduled" and (home_score is not None or away_score is not None):
    raise ValidationError("scheduled 状态不能有比分")
```

---

### 5. 采集元数据字段

| 字段名 | 数据类型 | 约束 | 业务含义 | 示例值 |
|--------|----------|------|----------|--------|
| `fetched_at` | TIMESTAMP WITH TIME ZONE | NULL | 数据采集时间 | `2024-12-28 10:30:00+00` |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | 记录创建时间 | `2024-12-28 10:30:00+00` |
| `updated_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | 记录更新时间 | `2024-12-28 10:30:00+00` |

---

## 索引定义

| 索引名 | 字段 | 类型 | 用途 |
|--------|------|------|------|
| `matches_pkey` | `match_id` | PRIMARY KEY | 主键约束 |
| `idx_matches_date` | `match_date DESC` | B-tree | 按时间查询（最新优先） |
| `idx_matches_season` | `season_id` | B-tree | 按赛季过滤 |
| `idx_matches_status` | `status` | B-tree (WHERE finished=true) | 查询已完场比赛 |
| `idx_matches_teams` | `home_team`, `away_team` | B-tree | 按球队查询 |

---

## 外键关系

| 字段 | 引用表 | 引用字段 | 级联规则 |
|------|--------|----------|----------|
| `match_id` | `match_features_training` | `match_id` | ON DELETE CASCADE |
| `match_id` | `raw_match_data` | `match_id` | ON DELETE CASCADE |

---

## 数据完整性约束

### 1. Pydantic Schema 校验（应用层）

**League ID 白名单校验**:
```python
# V36.0 核心防御：只有白名单中的 League ID 才能通过校验
VALID_LEAGUE_IDS = {47, 55, 54, 61, 135, 42}
if league_id not in VALID_LEAGUE_IDS:
    raise ValueError(f"拒绝非法 League ID: {league_id}")
```

**League Name 与 ID 一致性校验**:
```python
# V36.0 核心防御：确保 league_name 与 league_id 匹配
expected_name = LeagueId.get_league_name(league_id)
if league_name not in allowed_variants:
    raise ValueError(
        f"League Name 与 ID 不匹配！\n"
        f"league_id={league_id} 期望: '{expected_name}'\n"
        f"实际收到: league_name='{league_name}'"
    )
```

**比分一致性校验**:
```python
# finished 状态必须有比分
if status == "finished" and (home_score is None or away_score is None):
    raise ValueError(f"finished 状态必须有比分: match_id={match_id}")

# scheduled 状态不能有比分
if status == "scheduled" and (home_score is not None or away_score is not None):
    raise ValueError(f"scheduled 状态不能有比分: match_id={match_id}")
```

### 2. 数据库约束（存储层）

- **主键约束**: `match_id` 唯一且非空
- **外键约束**: 关联 `match_features_training` 和 `raw_match_data`
- **级联删除**: 删除比赛时自动删除关联的特征和原始数据

---

## 数据质量指标

### 采集成功率计算
```python
success_rate = (total_success / total_attempted) × 100%
```

### 联赛覆盖率计算
```python
coverage = (collected_matches / expected_matches) × 100%

# 各联赛预期比赛数
EXPECTED_MATCHES = {
    47: 380,   # Premier League
    55: 380,   # La Liga
    54: 306,   # Bundesliga (18队 × 17轮 × 2)
    61: 380,   # Ligue 1
    135: 380,  # Serie A
}
```

### 元数据纯度指标
```python
# 检查是否存在 "Premier League" 标签污染
purity_rate = (
    正确 league_name 的记录数 / 总记录数
) × 100%

# 例如：Bundesliga (ID=54) 的比赛中，league_name="Bundesliga" 的比例
```

---

## 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| V36.0 | 2025-12-28 | 新增 Pydantic Schema 校验、League ID 白名单、Name-ID 一致性校验 |
| V35.4 | 2025-12-28 | 修正 League ID 配置（La Liga: 87→55, Bundesliga: 53→54） |
| V35.3 | 2025-12-27 | 初始版本 |

---

**维护责任**: ML Architect / DevOps Team
**审核状态**: ✅ Production Ready
