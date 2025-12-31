# V51.0 特征字典
## Feature Dictionary - V51.0 Feature Refiner

**版本**: V51.0 (深度脱水版)
**生成日期**: 2025-12-31
**总特征数**: 642 维
**数据来源**: FotMob L2 API (raw_match_data 表)

---

## 特征分类概览

| 类别 | 特征数 | 占比 | 说明 |
|------|--------|------|------|
| **Header 基础** | 8 | 1.2% | 比赛基础信息、比分 |
| **Header 事件聚合** | 12 | 1.9% | 事件统计 (count/ratio/diff) |
| **Header 事件详情** | 81 | 12.6% | 前 5 个事件的详细属性 |
| **Content 统计** | 481 | 74.9% | FotMob 统计数据 (打平) |
| **Content 射门地图** | 46 | 7.2% | 射门位置坐标、xG |
| **元数据** | 14 | 2.2% | match_id 等 |
| **总计** | **642** | **100%** | - |

---

## 1. Header 基础特征 (8 维)

比赛基础信息，包含比分、队伍统计。

| 特征名 | 数据类型 | 取值范围 | 说明 |
|--------|----------|----------|------|
| `header_teams_total_count` | int64 | [2, 2] | 队伍总数 (固定=2) |
| `header_teams_home_count` | int64 | [1, 1] | 主队数量 |
| `header_teams_away_count` | int64 | [1, 1] | 客队数量 |
| `header_teams_home_away_diff` | int64 | [0, 0] | 主客差异 (固定=0) |
| `header_teams_home_ratio` | float64 | [0.5, 0.5] | 主队占比 |
| `header_teams_away_ratio` | float64 | [0.5, 0.5] | 客队占比 |
| `header_teams_0_score` | float64 | [0, 10+] | 主队比分 |
| `header_teams_1_score` | float64 | [0, 10+] | 客队比分 |

**用途**: 标签特征，用于监督学习

---

## 2. Header 事件聚合特征 (12 维)

对事件列表 (goals, cards, substitutions 等) 的统计聚合。

| 特征模式 | 数据类型 | 说明 |
|----------|----------|------|
| `header_events_{eventType}_total_count` | float64 | 该类型事件总数 |
| `header_events_{eventType}_home_count` | float64 | 主队该类型事件数 |
| `header_events_{eventType}_away_count` | float64 | 客队该类型事件数 |
| `header_events_{eventType}_home_away_diff` | float64 | 主客差值 |
| `header_events_{eventType}_home_ratio` | float64 | [0, 1] 主队占比 |
| `header_events_{eventType}_away_ratio` | float64 | [0, 1] 客队占比 |

**事件类型示例**:
- `awayTeamGoals_Olmo` - 客队进球事件
- `awayTeamGoals_Lewandowski` - 特定球员进球

**用途**: 捕捉比赛事件分布，辅助判断比赛走势

---

## 3. Header 事件详情特征 (81 维)

前 5 个关键事件的详细属性 (列表压减: 50 → 5)。

### 3.1 事件基础属性

| 特征模式 | 数据类型 | 说明 |
|----------|----------|------|
| `header_events_{type}_{i}_time` | float64 | 事件发生时间 (分钟) |
| `header_events_{type}_{i}_isHome` | float64 | 是否为主队 (0/1) |
| `header_events_{type}_{i}_timeStr` | float64 | 时间字符串 (编码后) |
| `header_events_{type}_{i}_eventType` | float64 | 事件类型编码 |

### 3.2 比分相关属性

| 特征模式 | 数据类型 | 说明 |
|----------|----------|------|
| `header_events_{type}_{i}_awayScore` | float64 | 当时客队比分 |
| `header_events_{type}_{i}_homeScore` | float64 | 当时主队比分 |
| `header_events_{type}_{i}_newScore_mean` | float64 | 新比分统计量 |
| `header_events_{type}_{i}_newScore_std` | float64 | 新比分标准差 |

### 3.3 射门事件属性 (shotmapEvent)

| 特征模式 | 数据类型 | 取值范围 | 说明 |
|----------|----------|----------|------|
| `..._shotmapEvent_x` | float64 | [0, 1] | 射门 X 坐标 (标准化) |
| `..._shotmapEvent_y` | float64 | [0, 1] | 射门 Y 坐标 (标准化) |
| `..._shotmapEvent_min` | float64 | [0, 90+] | 射门时间 |
| `..._shotmapEvent_isBlocked` | float64 | {0, 1} | 是否被封堵 |
| `..._shotmapEvent_isOwnGoal` | float64 | {0, 1} | 是否乌龙球 |
| `..._shotmapEvent_isOnTarget` | float64 | {0, 1} | 是否射正 |
| `..._shotmapEvent_expectedGoals` | float64 | [0, 1+] | xG 值 |
| `..._shotmapEvent_isFromInsideBox` | float64 | {0, 1} | 是否来自禁区 |

**用途**: 高频事件特征，捕捉关键时刻信息

---

## 4. Content 统计特征 (481 维)

FotMob API `content.stats` 字段的递归打平结果。

### 4.1 球队统计

| 特征模式示例 | 数据类型 | 说明 |
|--------------|----------|------|
| `content_stats_shots_total_0_shots` | float64 | 某队射门数 |
| `content_stats_shots_total_0_xg` | float64 | 某队 xG |
| `content_stats_possession_home` | float64 | 主队控球率 |

### 4.2 比赛事实

| 特征模式示例 | 数据类型 | 说明 |
|--------------|----------|------|
| `content_matchFacts_attendance` | float64 | 现场观众数 |
| `content_matchFacts_formations_0_formation` | float64 | 阵型编码 |

### 4.3 球员统计 (Player Stats)

| 特征模式示例 | 数据类型 | 说明 |
|--------------|----------|------|
| `content_playerStats_0_rating` | float64 | 球员评分 |
| `content_playerStats_0_goals` | float64 | 进球数 |

**注意**: 由于列表压减，只保留前 5 个球员/项的统计

---

## 5. Content 射门地图特征 (46 维)

FotMob `content.shotmap` 字段，包含所有射门事件的详细信息。

| 特征模式 | 数据类型 | 取值范围 | 说明 |
|----------|----------|----------|------|
| `content_shotmap_{i}_x` | float64 | [0, 1] | 射门 X 坐标 |
| `content_shotmap_{i}_y` | float64 | [0, 1] | 射门 Y 坐标 |
| `content_shotmap_{i}_xg` | float64 | [0, 1+] | 该射门的 xG |
| `content_shotmap_{i}_isHome` | float64 | {0, 1} | 是否主队射门 |
| `content_shotmap_{i}_isBlocked` | float64 | {0, 1} | 是否被封堵 |
| `content_shotmap_{i}_isOnTarget` | float64 | {0, 1} | 是否射正 |
| `content_shotmap_{i}_isGoal` | float64 | {0, 1} | 是否进球 |

**列表压减**: 原 50+ 个射门 → 保留前 5 个

**用途**: 空间特征，捕捉射门位置分布

---

## 6. 元数据特征 (14 维)

用于数据追踪和关联。

| 特征名 | 数据类型 | 说明 |
|--------|----------|------|
| `match_id` | str | 比赛唯一标识 |

---

## 特征质量说明

### 过滤规则 (黑名单)

以下特征已被**完全过滤**，不会出现在输出中:

| 规则 | 示例 |
|------|------|
| `_id$`, `Id$` | `playerId`, `teamId`, `eventId` |
| `color` | `teamColors`, `shirtColor` |
| `text` | `firstName`, `lastName`, `commentary` |
| `description` | `matchDescription` |

### 保留规则 (白名单)

以下特征**强制保留**:

| 模式 | 示例 |
|------|------|
| `rolling_xg_` | 滚动 xG 特征 |
| `elo_gap` | ELO 分差 |
| `table_position` | 积分榜排名 |
| `possession` | 控球率 |
| `\.xg$` | xG 字段 |
| `home_score` | 主队比分 |
| `away_score` | 客队比分 |

---

## 数据类型标准化

| 输入类型 | 输出类型 | 说明 |
|----------|----------|------|
| `bool` | `int64` | 0/1 |
| `int` | `float64` | 数值特征 |
| `float` | `float64` | 数值特征 |
| `str` (数字) | `float64` | 解析后转为浮点 |
| `None` | `float64` (填充 0) | 缺失值填充 |

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| V51.0 | 2025-12-31 | 初始版本，深度脱水版 (12,061 → 642 维) |

---

**文档维护**: ML Engineering Team
**联系**: 请通过项目 Issue 反馈特征相关问题
