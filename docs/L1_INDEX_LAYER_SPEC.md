# V171 L1 索引层规范 (Index Layer Specification)

**版本**: V171.100
**最后更新**: 2026-02-25
**维护者**: V171 Architecture Team

---

## 1. 概述

L1 索引层是 FootballPrediction 系统的数据采集入口，负责从 FotMob API 获取比赛元数据并存储到 PostgreSQL 数据库。

### 1.1 核心职责

| 职责 | 说明 |
|------|------|
| **比赛发现** | 从 FotMob API 获取联赛赛季的完整比赛列表 |
| **元数据持久化** | 存储比赛基础信息到 `matches` 表 |
| **全量快照** | 保存完整数据到 `metrics_multi_source_data` 表 |
| **幂等性保证** | 支持重复执行，不产生重复记录 |

### 1.2 数据流向

```
FotMob API → v171_l1_api_fetch.js → PostgreSQL (matches + metrics_multi_source_data)
     ↓
https://www.fotmob.com/api/leagues?id={league_id}&season={season}
```

---

## 2. 字段定义

### 2.1 matches 表字段

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| `match_id` | VARCHAR(50) | 主键，格式: `{LEAGUE}_{DATE}_{HOME}_{AWAY}` | 计算生成 |
| `external_id` | VARCHAR(100) | FotMob 原始比赛 ID | `match.id` |
| `home_team` | VARCHAR(200) | 主队名称 | `match.home.name` |
| `away_team` | VARCHAR(200) | 客队名称 | `match.away.name` |
| `home_score` | INTEGER | 主队进球 | `match.status.scoreStr` |
| `away_score` | INTEGER | 客队进球 | `match.status.scoreStr` |
| `ht_score` | VARCHAR(10) | 半场比分，格式: `1-0` | `match.status.htScoreStr` |
| `utc_time` | TIMESTAMP | 开球时间 (UTC) | `match.status.utcTime` |
| `match_status` | VARCHAR(20) | 比赛状态 | `finished/started/scheduled/cancelled` |
| `round_number` | INTEGER | 联赛轮次 | `match.round` |
| `is_live` | BOOLEAN | 是否正在直播 | `started && !finished` |
| `is_finished` | BOOLEAN | 是否已完赛 | `match.status.finished` |
| `league_name` | VARCHAR(100) | 联赛名称 | 配置映射 |
| `season` | VARCHAR(20) | 赛季 | `2024-2025` |
| `data_source` | VARCHAR(50) | 数据来源 | 固定: `FotMob` |

### 2.2 metrics_multi_source_data 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `match_id` | VARCHAR(100) | 外键 |
| `source` | VARCHAR(50) | 数据源，固定: `FotMob` |
| `metric_type` | VARCHAR(50) | 指标类型，固定: `l1_full_snapshot` |
| `metric_value` | JSONB | 全量快照 JSON |
| `collected_at` | TIMESTAMP | 采集时间 |

---

## 3. 采集频率限制

### 3.1 API 请求限制

| 场景 | 限制 | 处理方式 |
|------|------|----------|
| **正常请求** | 2 秒间隔 | `setTimeout(2000)` |
| **429 Too Many Requests** | 指数退避 | 1s → 2s → 4s → 放弃 |
| **403 Forbidden** | 不重试 | 直接报错 |
| **网络超时** | 30 秒超时 | 抛出 TimeoutError |

### 3.2 联赛配置

```javascript
const LEAGUES = [
    { id: 47, name: 'Premier League', code: 'EPL' },
    { id: 87, name: 'La Liga', code: 'LALIGA' },
    { id: 54, name: 'Bundesliga', code: 'BL' },
    { id: 55, name: 'Serie A', code: 'SA' },
    { id: 53, name: 'Ligue 1', code: 'L1' }
];
```

---

## 4. 数据库表关联

### 4.1 表关系

```
┌─────────────────────┐
│      matches        │
│─────────────────────│
│ PK: match_id        │
│ FK: league_name     │
└──────────┬──────────┘
           │
           │ 1:1
           ▼
┌─────────────────────┐
│ metrics_multi_source_data │
│─────────────────────│
│ FK: match_id        │
│    source           │
│    metric_type      │
└─────────────────────┘
```

### 4.2 索引策略

| 表 | 索引 | 用途 |
|----|------|------|
| `matches` | `idx_matches_utc_time` | 按时间查询 |
| `matches` | `idx_matches_match_status` | 按状态筛选 |
| `matches` | `idx_matches_round_number` | 按轮次查询 |
| `metrics_multi_source_data` | `match_id, source, metric_type` | 唯一约束 |

---

## 5. 幂等性设计

### 5.1 UPSERT 逻辑

```sql
INSERT INTO matches (match_id, home_team, away_team, ...)
VALUES ($1, $2, $3, ...)
ON CONFLICT (match_id) DO UPDATE SET
    home_score = EXCLUDED.home_score,
    away_score = EXCLUDED.away_score,
    updated_at = NOW();
```

### 5.2 external_id 保留

```sql
-- 更新时保留已存在的 external_id
external_id = COALESCE(matches.external_id, EXCLUDED.external_id)
```

---

## 6. 使用示例

### 6.1 运行采集

```bash
# 在 Docker 容器内执行
docker-compose exec dev node scripts/ops/v171_l1_api_fetch.js
```

### 6.2 查询数据

```sql
-- 查询最近 5 场已完赛比赛
SELECT match_id, home_team, away_team, home_score, away_score, utc_time
FROM matches
WHERE is_finished = true
ORDER BY utc_time DESC
LIMIT 5;

-- 查询某场比赛的全量快照
SELECT match_id, jsonb_pretty(metric_value)
FROM metrics_multi_source_data
WHERE match_id = 'EPL_20250215_ARS_CHE';
```

---

## 7. 故障排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 429 错误 | 请求频率过高 | 增加请求间隔 |
| 字段为 NULL | API 返回缺失 | 正常行为，无需处理 |
| 重复记录 | match_id 生成不一致 | 检查队名标准化 |

---

## 8. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| V171.100 | 2026-02-25 | 全量快照策略，新增 5 个字段 |
| V172.000 | 2026-02-25 | 统一数据库配置，消除硬编码密码 |

---

**维护者**: V171 Architecture Team
**许可证**: 内部使用
