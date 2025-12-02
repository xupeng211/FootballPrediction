# 足球预测系统 - 数据库架构文档

## 概述

本系统的数据库采用 PostgreSQL 15，设计遵循足球预测业务需求，支持多种数据源集成和灵活的数据结构扩展。核心设计理念是使用关系型数据存储基础实体，结合 JSONB 字段存储复杂的半结构化数据。

## 核心表结构

### 1. matches 表 - 比赛数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | integer | PRIMARY KEY, NOT NULL | 比赛唯一标识符 |
| `home_team_id` | integer | NOT NULL, FK → teams.id | 主队ID |
| `away_team_id` | integer | NOT NULL, FK → teams.id | 客队ID |
| `home_score` | integer | - | 主队得分 |
| `away_score` | integer | - | 客队得分 |
| `status` | varchar(20) | - | 比赛状态 (scheduled, live, finished, postponed) |
| `match_date` | timestamp | NOT NULL | 比赛时间 |
| `venue` | varchar(255) | - | 比赛场馆 |
| `league_id` | integer | FK → leagues.id | 联赛ID |
| `season` | varchar(20) | - | 赛季信息 |
| `created_at` | timestamp | NOT NULL | 创建时间 |
| `updated_at` | timestamp | NOT NULL | 更新时间 |
| `lineups` | jsonb | - | 阵容信息 |
| `stats` | jsonb | - | 比赛统计数据 |
| `events` | jsonb | - | 比赛事件（进球、换人等） |
| `odds` | jsonb | - | 赔率信息 |
| `match_metadata` | jsonb | - | 比赛元数据 |
| `data_source` | varchar(50) | DEFAULT 'unknown' | 数据来源标识 |
| `data_completeness` | varchar(20) | DEFAULT 'partial' | 数据完整性 (partial, complete) |
| `raw_file_path` | varchar(512) | - | 原始数据文件路径 |

#### JSONB 字段详细结构

##### `stats` 字段 - 比赛统计数据
```json
{
  "xg_home": 1.85,                    // 主队预期进球数
  "xg_away": 0.73,                    // 客队预期进球数
  "possession_home": 62.5,            // 主队控球率 (%)
  "possession_away": 37.5,            // 客队控球率 (%)
  "shots_home": 15,                   // 主队射门次数
  "shots_away": 8,                    // 客队射门次数
  "shots_on_target_home": 7,          // 主队射正次数
  "shots_on_target_away": 3,          // 客队射正次数
  "corners_home": 6,                  // 主队角球数
  "corners_away": 3,                  // 客队角球数
  "fouls_home": 12,                   // 主队犯规次数
  "fouls_away": 9,                    // 客队犯规次数
  "yellow_cards_home": 2,             // 主队黄牌数
  "yellow_cards_away": 1,             // 客队黄牌数
  "red_cards_home": 0,                // 主队红牌数
  "red_cards_away": 1,                // 客队红牌数
  "passes_home": 485,                 // 主队传球次数
  "passes_away": 312,                 // 客队传球次数
  "pass_accuracy_home": 83.2,         // 主队传球成功率 (%)
  "pass_accuracy_away": 76.1          // 客队传球成功率 (%)
}
```

##### `odds` 字段 - 赔率信息
```json
{
  "bookmakers": {
    "bet365": {
      "home_win": 1.85,               // 主胜赔率
      "draw": 3.60,                    // 平局赔率
      "away_win": 4.20,                // 客胜赔率
      "over_2_5": 1.95,               // 大2.5球赔率
      "under_2_5": 1.85,              // 小2.5球赔率
      "updated_at": "2024-01-15T10:30:00Z"
    },
    "william_hill": {
      "home_win": 1.88,
      "draw": 3.55,
      "away_win": 4.15,
      "updated_at": "2024-01-15T10:25:00Z"
    }
  },
  "market_analysis": {
    "average_home_win": 1.86,         // 平均主胜赔率
    "average_draw": 3.58,             // 平均平局赔率
    "average_away_win": 4.18,         // 平均客胜赔率
    "total_volume": 1250000,           // 总交易量
    "home_win_volume": 680000         // 主胜交易量
  }
}
```

##### `lineups` 字段 - 阵容信息
```json
{
  "home_formation": "4-3-3",          // 主队阵型
  "away_formation": "4-4-2",          // 客队阵型
  "home_lineup": [
    {
      "player_id": 12345,
      "player_name": "John Doe",
      "position": "GK",               // 位置: GK, DF, MF, FW
      "shirt_number": 1,
      "captain": true,
      "substituted": false,
      "substitution_time": null
    }
  ],
  "away_lineup": [
    // 类似结构
  ],
  "substitutions": {
    "home": [
      {
        "player_out": 67890,
        "player_in": 67891,
        "minute": 67
      }
    ],
    "away": []
  }
}
```

##### `events` 字段 - 比赛事件
```json
{
  "goals": [
    {
      "minute": 23,
      "team": "home",                 // home, away
      "player_id": 12345,
      "player_name": "John Doe",
      "assist_player_id": 67890,
      "assist_player_name": "Jane Smith",
      "goal_type": "regular",         // regular, penalty, own_goal
      "score_after": "1-0"
    }
  ],
  "cards": [
    {
      "minute": 45,
      "team": "away",
      "player_id": 67892,
      "player_name": "Bob Johnson",
      "card_type": "yellow",          // yellow, red
      "reason": "foul"
    }
  ],
  "substitutions": [
    {
      "minute": 67,
      "team": "home",
      "player_out_id": 67893,
      "player_in_id": 67894,
      "position": "MF"
    }
  ]
}
```

##### `match_metadata` 字段 - 比赛元数据
```json
{
  "referee": {
    "name": "Michael Oliver",
    "nationality": "England"
  },
  "weather": {
    "temperature": 15.5,              // 摄氏度
    "humidity": 65,                   // 百分比
    "wind_speed": 12.3,               // km/h
    "condition": "cloudy"             // sunny, cloudy, rainy, snowy
  },
  "attendance": 45678,                // 观众人数
  "match_week": 15,                   // 联赛轮次
  "importance": "high",               // low, medium, high
  "tv_broadcasters": [
    "Sky Sports",
    "BT Sport"
  ]
}
```

### 2. teams 表 - 球队数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | integer | PRIMARY KEY, NOT NULL | 球队唯一标识符 |
| `name` | varchar(100) | NOT NULL | 球队全名 |
| `short_name` | varchar(50) | - | 球队简称 |
| `country` | varchar(50) | NOT NULL | 球队所属国家 |
| `founded_year` | integer | - | 成立年份 |
| `venue` | varchar(255) | - | 主场场馆 |
| `website` | varchar(255) | - | 官方网站 |
| `created_at` | timestamp | NOT NULL | 创建时间 |
| `updated_at` | timestamp | NOT NULL | 更新时间 |
| `fotmob_external_id` | integer | - | FotMob外部ID |
| `fbref_external_id` | varchar(100) | - | FBref外部ID |
| `fbref_url` | varchar(255) | - | FBref数据源URL |

### 3. leagues 表 - 联赛数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | integer | PRIMARY KEY, NOT NULL | 联赛唯一标识符 |
| `name` | varchar(100) | NOT NULL | 联赛名称 |
| `country` | varchar(50) | NOT NULL | 联赛所属国家 |
| `is_active` | boolean | NOT NULL | 是否活跃 |
| `created_at` | timestamp | NOT NULL | 创建时间 |
| `updated_at` | timestamp | NOT NULL | 更新时间 |
| `fbref_url` | varchar(255) | - | FBref数据源URL |
| `fbref_id` | varchar(50) | - | FBref联赛ID |
| `category` | varchar(50) | - | 联赛类别 (domestic, international, cup) |
| `tier` | varchar(20) | - | 联赛级别 (1, 2, 3...) |
| `gender` | varchar(20) | DEFAULT 'men' | 性别 (men, women) |
| `season` | varchar(20) | - | 当前赛季 |

### 4. features 表 - 特征数据（机器学习用）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | integer | PRIMARY KEY, NOT NULL | 特征唯一标识符 |
| `match_id` | integer | NOT NULL, FK → matches.id | 关联比赛ID |
| `team_id` | integer | FK → teams.id | 关联球队ID |
| `feature_type` | varchar(50) | NOT NULL | 特征类型 (historical, real_time, predicted) |
| `feature_data` | text | - | 序列化的特征数据 |
| `created_at` | timestamp | NOT NULL | 创建时间 |
| `updated_at` | timestamp | NOT NULL | 更新时间 |

## 索引策略

### 主要索引
- **主键索引**: 所有表的 `id` 字段
- **外键索引**: 所有外键字段
- **查询优化索引**:
  ```sql
  -- matches表
  CREATE INDEX idx_matches_date_league ON matches(match_date, league_id);
  CREATE INDEX idx_matches_teams ON matches(home_team_id, away_team_id);
  CREATE INDEX idx_matches_status ON matches(status) WHERE status IN ('live', 'scheduled');

  -- JSONB GIN索引
  CREATE INDEX idx_matches_stats ON matches USING gin(stats);
  CREATE INDEX idx_matches_odds ON matches USING gin(odds);
  CREATE INDEX idx_matches_lineups ON matches USING gin(lineups);

  -- teams表
  CREATE INDEX idx_teams_country ON teams(country);
  CREATE INDEX idx_teams_name ON teams(name);

  -- leagues表
  CREATE INDEX idx_leagues_country_active ON leagues(country, is_active);
  CREATE INDEX idx_leagues_category ON leagues(category);

  -- features表
  CREATE INDEX idx_features_match_type ON features(match_id, feature_type);
  CREATE INDEX idx_features_team_type ON features(team_id, feature_type);
  ```

## 数据迁移指南

### 本地数据备份
```bash
# 备份完整数据库
docker-compose exec db pg_dump -U postgres football_prediction > backup_$(date +%Y%m%d_%H%M%S).sql

# 备份特定表
docker-compose exec db pg_dump -U postgres football_prediction -t matches > matches_backup.sql
docker-compose exec db pg_dump -U postgres football_prediction -t teams > teams_backup.sql
docker-compose exec db pg_dump -U postgres football_prediction -t leagues > leagues_backup.sql

# 仅导数据（不包含结构）
docker-compose exec db pg_dump -U postgres football_prediction --data-only > data_only_backup.sql
```

### 云端服务器恢复
```bash
# 1. 传输备份文件到云端服务器
scp backup_20241202_173000.sql user@cloud-server:/tmp/

# 2. 连接到云端数据库（假设使用相同的Docker环境）
docker-compose exec -T db psql -U postgres football_prediction < /tmp/backup_20241202_173000.sql

# 3. 恢复特定表
docker-compose exec -T db psql -U postgres football_prediction < /tmp/matches_backup.sql

# 4. 验证数据完整性
docker-compose exec db psql -U postgres football_prediction -c "
  SELECT
    (SELECT COUNT(*) FROM matches) as matches_count,
    (SELECT COUNT(*) FROM teams) as teams_count,
    (SELECT COUNT(*) FROM leagues) as leagues_count;
"
```

### 数据一致性检查
```sql
-- 检查外键约束完整性
SELECT
  m.home_team_id,
  COUNT(*) as orphaned_matches
FROM matches m
LEFT JOIN teams t ON m.home_team_id = t.id
WHERE t.id IS NULL
GROUP BY m.home_team_id;

-- 检查JSON字段数据完整性
SELECT
  COUNT(*) as total_matches,
  COUNT(stats) as matches_with_stats,
  COUNT(odds) as matches_with_odds,
  COUNT(lineups) as matches_with_lineups
FROM matches;

-- 检查数据完整性分布
SELECT
  data_completeness,
  COUNT(*) as count
FROM matches
GROUP BY data_completeness;
```

## 性能优化建议

### 1. JSONB 查询优化
```sql
-- 为常用JSON字段创建表达式索引
CREATE INDEX idx_matches_xg_home ON matches USING btree ((stats->>'xg_home')::float);
CREATE INDEX idx_matches_possession_home ON matches USING btree ((stats->>'possession_home')::float);

-- 使用JSONB路径查询优化
SELECT * FROM matches
WHERE stats->>'xg_home'::float > 2.0
  AND match_date >= '2024-01-01';
```

### 2. 分区策略（数据量增长时）
```sql
-- 按时间分区matches表
CREATE TABLE matches_partitioned (
  LIKE matches INCLUDING ALL
) PARTITION BY RANGE (match_date);

-- 创建月度分区
CREATE TABLE matches_2024_01 PARTITION OF matches_partitioned
  FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### 3. 查询缓存策略
- 使用Redis缓存频繁查询的联赛信息、球队信息
- 对实时比赛数据设置短期缓存（1-5分钟）
- 对历史统计数据设置长期缓存（24小时）

## 数据保留策略

### 历史数据归档
```sql
-- 归档超过2年的比赛数据
CREATE TABLE matches_archive AS
SELECT * FROM matches
WHERE match_date < NOW() - INTERVAL '2 years';

-- 删除已归档数据
DELETE FROM matches
WHERE match_date < NOW() - INTERVAL '2 years';
```

### 监控查询
```sql
-- 监控表大小增长
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 监控JSONB字段使用情况
SELECT
  column_name,
  pg_size_pretty(sum(pg_column_size(column_name)::bigint)) as column_size
FROM information_schema.columns
JOIN matches ON true
WHERE table_name = 'matches'
  AND data_type = 'jsonb'
GROUP BY column_name;
```

---

**文档版本**: v1.0.0
**最后更新**: 2024-12-02
**数据库版本**: PostgreSQL 15
**维护者**: 首席文档工程师

此文档与生产数据库结构保持同步，任何结构变更都应及时更新本文档。