# 未来数据架构设计 - xG与阵容数据存储方案

## 📋 技术债务备忘录

基于数据考古发现，当前FotMob API仅提供基础比赛信息。为支持高级机器学习模型，需要设计扩展的数据库架构来存储xG、阵容、技术统计等深度数据。

## 🏗️ 扩展表结构设计

### 1. `match_details` 表 - 比赛详细信息

```sql
CREATE TABLE match_details (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id) ON DELETE CASCADE,

    -- 期望进球数据
    home_xg DECIMAL(5,2),
    away_xg DECIMAL(5,2),
    total_xg DECIMAL(5,2),

    -- 技术统计数据
    home_possession DECIMAL(5,2),      -- 主队控球率
    away_possession DECIMAL(5,2),      -- 客队控球率
    home_shots INTEGER,               -- 主队射门数
    away_shots INTEGER,               -- 客队射门数
    home_shots_on_target INTEGER,     -- 主队射正数
    away_shots_on_target INTEGER,     -- 客队射正数
    home_corners INTEGER,             -- 主队角球数
    away_corners INTEGER,             -- 客队角球数
    home_fouls INTEGER,              -- 主队犯规数
    away_fouls INTEGER,              -- 客队犯规数
    home_yellow_cards INTEGER,       -- 主队黄牌数
    away_yellow_cards INTEGER,       -- 客队黄牌数
    home_red_cards INTEGER,          -- 主队红牌数
    away_red_cards INTEGER,          -- 客队红牌数

    -- 数据源和完整性标记
    data_source VARCHAR(50) DEFAULT 'fotmob',
    data_quality_score INTEGER DEFAULT 1,  -- 1-5 数据完整性评分

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_match_details_match_id ON match_details(match_id);
CREATE INDEX idx_match_details_xg ON match_details(home_xg, away_xg);
```

### 2. `match_lineups` 表 - 阵容信息

```sql
CREATE TABLE match_lineups (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id) ON DELETE CASCADE,

    -- 球队信息
    team_id INTEGER REFERENCES teams(id),
    team_side VARCHAR(10),              -- 'home' 或 'away'
    formation VARCHAR(10),             -- 阵形如 '4-3-3'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_match_lineups_match_id ON match_lineups(match_id);
CREATE INDEX idx_match_lineups_team_id ON match_lineups(team_id);
```

### 3. `match_players` 表 - 球员表现数据

```sql
CREATE TABLE match_players (
    id SERIAL PRIMARY KEY,
    match_lineup_id INTEGER REFERENCES match_lineups(id) ON DELETE CASCADE,

    -- 球员基础信息
    player_external_id VARCHAR(50),   -- 外部球员ID
    player_name VARCHAR(100),
    player_number INTEGER,            -- 球衣号码
    player_position VARCHAR(20),       -- 位置 (GK, DEF, MID, FWD)

    -- 比赛表现数据
    is_starter BOOLEAN DEFAULT FALSE,  -- 是否首发
    minutes_played INTEGER,           -- 出场时间(分钟)
    goals_scored INTEGER DEFAULT 0,   -- 进球数
    assists INTEGER DEFAULT 0,         -- 助攻数
    yellow_cards INTEGER DEFAULT 0,    -- 黄牌数
    red_cards INTEGER DEFAULT 0,      -- 红牌数
    own_goals INTEGER DEFAULT 0,       -- 乌龙球

    -- 高级统计数据
    shots INTEGER DEFAULT 0,          -- 射门数
    shots_on_target INTEGER DEFAULT 0, -- 射正数
    passes INTEGER DEFAULT 0,         -- 传球数
    pass_accuracy DECIMAL(5,2),       -- 传球成功率
    duels_won INTEGER DEFAULT 0,      -- 对抗胜利数
    tackles INTEGER DEFAULT 0,       -- 抢断数
    interceptions INTEGER DEFAULT 0, -- 拦截数

    -- 评分数据
    player_rating DECIMAL(3,1),       -- 球员评分 (0.0-10.0)
    xg DECIMAL(5,2),                 -- 期望进球
    xa DECIMAL(5,2),                 -- 期望助攻

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_match_players_lineup_id ON match_players(match_lineup_id);
CREATE INDEX idx_match_players_external_id ON match_players(player_external_id);
CREATE INDEX idx_match_players_rating ON match_players(player_rating);
```

### 4. `match_events` 表 - 比赛事件

```sql
CREATE TABLE match_events (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id) ON DELETE CASCADE,

    -- 事件基础信息
    event_type VARCHAR(20),            -- 事件类型 (goal, card, substitution 等)
    event_time INTEGER,               -- 事件时间(分钟)
    period VARCHAR(10),               -- 上半场/下半场 (H1, H2)

    -- 球员信息
    player_id VARCHAR(50),            -- 事件球员ID
    player_name VARCHAR(100),         -- 事件球员姓名
    team_id INTEGER REFERENCES teams(id),

    -- 详细信息
    event_description TEXT,           -- 事件描述
    event_sub_type VARCHAR(20),       -- 子类型 (yellow_card, red_card, penalty 等)

    -- xG信息 (适用于进球事件)
    xg_value DECIMAL(5,2),           -- 该进球的期望进球值
    xg_assist_value DECIMAL(5,2),    -- 期望助攻值

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_match_events_match_id ON match_events(match_id);
CREATE INDEX idx_match_events_type ON match_events(event_type);
CREATE INDEX idx_match_events_time ON match_events(event_time);
```

### 5. `betting_odds` 表 - 博彩数据

```sql
CREATE TABLE betting_odds (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id) ON DELETE CASCADE,

    -- 赔率来源
    bookmaker VARCHAR(50),            -- 博彩公司
    odds_type VARCHAR(20),            -- 赔率类型 (1X2, Over/Under, Handicap)

    -- 主胜/平/客胜赔率
    home_win_odds DECIMAL(8,4),
    draw_odds DECIMAL(8,4),
    away_win_odds DECIMAL(8,4),

    -- 让球盘
    handicap_line DECIMAL(4,2),      -- 让球数
    home_handicap_odds DECIMAL(8,4),
    away_handicap_odds DECIMAL(8,4),

    -- 大小球盘
    over_under_line DECIMAL(4,2),    -- 盘口线
    over_odds DECIMAL(8,4),         -- 大球赔率
    under_odds DECIMAL(8,4),        -- 小球赔率

    -- 数据时间戳
    odds_timestamp TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_betting_odds_match_id ON betting_odds(match_id);
CREATE INDEX idx_betting_odds_bookmaker ON betting_odds(bookmaker);
CREATE INDEX idx_betting_odds_type ON betting_odds(odds_type);
```

## 🔗 数据关联关系图

```
matches (1) -----> (1) match_details
    |
    +-----> (1) match_lineups (1..11) -----> (1..25) match_players
    |
    +-----> (1..N) match_events
    |
    +-----> (1..N) betting_odds
```

## 🚀 实施路线图

### Phase 1: 基础架构 (1-2周)
- [ ] 创建上述扩展表结构
- [ ] 更新数据模型 (SQLAlchemy Models)
- [ ] 修改ETL流程支持新表

### Phase 2: 数据源集成 (2-4周)
- [ ] 探索FotMob详情API
- [ ] 集成xG数据源 (可能需要Understat等)
- [ ] 开发阵容数据采集器

### Phase 3: 特征工程增强 (1-2周)
- [ ] 基于新数据设计高级特征
- [ ] 更新特征生成脚本
- [ ] 重新训练机器学习模型

## 📊 数据质量监控

### 数据完整性指标
- xG数据覆盖率 > 80%
- 阵容数据完整性 > 90%
- 事件数据时序性验证
- 赔率数据时效性检查

### 数据质量评分系统
```python
QUALITY_SCORES = {
    'complete_xg_data': 5,
    'partial_xg_data': 3,
    'lineup_complete': 5,
    'lineup_partial': 2,
    'events_detailed': 4,
    'events_basic': 2
}
```

## 💡 关键技术考虑

1. **数据源多样性**: 需要支持多个API源 (FotMob, Understat, Opta等)
2. **实时性考虑**: 某些数据需要实时更新 (比分、事件)
3. **存储优化**: 时间序列数据考虑分区策略
4. **API限流处理**: 多数据源的并发访问管理
5. **数据一致性**: 跨表引用的完整性约束

这个设计为未来3-6个月的数据架构升级提供了清晰的路线图。