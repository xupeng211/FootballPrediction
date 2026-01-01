-- ============================================================
-- V51.2: prematch_features 表 - 添加赔率字段
-- ============================================================
-- 用途: 为赛前特征表添加初赔和终赔字段
-- 日期: 2025-12-31
-- ============================================================

-- 1. 添加初赔字段 (Opening Odds)
ALTER TABLE prematch_features
    ADD COLUMN IF NOT EXISTS opening_home_odds FLOAT,
    ADD COLUMN IF NOT EXISTS opening_draw_odds FLOAT,
    ADD COLUMN IF NOT EXISTS opening_away_odds FLOAT;

-- 2. 添加终赔字段 (Closing Odds)
ALTER TABLE prematch_features
    ADD COLUMN IF NOT EXISTS closing_home_odds FLOAT,
    ADD COLUMN IF NOT EXISTS closing_draw_odds FLOAT,
    ADD COLUMN IF NOT EXISTS closing_away_odds FLOAT;

-- 3. 添加赔率相关特征字段
ALTER TABLE prematch_features
    ADD COLUMN IF NOT EXISTS market_implied_prob_home FLOAT,
    ADD COLUMN IF NOT EXISTS market_implied_prob_draw FLOAT,
    ADD COLUMN IF NOT EXISTS market_implied_prob_away FLOAT,
    ADD COLUMN IF NOT EXISTS odds_movement_home FLOAT,
    ADD COLUMN IF NOT EXISTS odds_movement_draw FLOAT,
    ADD COLUMN IF NOT EXISTS odds_movement_away FLOAT;

-- 4. 添加价值投注字段 (用于后续 ROI 计算)
ALTER TABLE prematch_features
    ADD COLUMN IF NOT EXISTS ev_home FLOAT,
    ADD COLUMN IF NOT EXISTS ev_draw FLOAT,
    ADD COLUMN IF NOT EXISTS ev_away FLOAT,
    ADD COLUMN IF NOT EXISTS kelly_home FLOAT,
    ADD COLUMN IF NOT EXISTS kelly_draw FLOAT,
    ADD COLUMN IF NOT EXISTS kelly_away FLOAT,
    ADD COLUMN IF NOT EXISTS value_bet_outcome VARCHAR(10),
    ADD COLUMN IF NOT EXISTS value_level VARCHAR(20);

-- 5. 添加注释
COMMENT ON COLUMN prematch_features.opening_home_odds IS 'V51.2: 初盘主胜赔率';
COMMENT ON COLUMN prematch_features.opening_draw_odds IS 'V51.2: 初盘平局赔率';
COMMENT ON COLUMN prematch_features.opening_away_odds IS 'V51.2: 初盘客胜赔率';
COMMENT ON COLUMN prematch_features.closing_home_odds IS 'V51.2: 终盘主胜赔率';
COMMENT ON COLUMN prematch_features.closing_draw_odds IS 'V51.2: 终盘平局赔率';
COMMENT ON COLUMN prematch_features.closing_away_odds IS 'V51.2: 终盘客胜赔率';

COMMENT ON COLUMN prematch_features.market_implied_prob_home IS 'V51.2: 市场隐含概率 (主胜)';
COMMENT ON COLUMN prematch_features.market_implied_prob_draw IS 'V51.2: 市场隐含概率 (平局)';
COMMENT ON COLUMN prematch_features.market_implied_prob_away IS 'V51.2: 市场隐含概率 (客胜)';
COMMENT ON COLUMN prematch_features.odds_movement_home IS 'V51.2: 赔率变动 (主胜)';
COMMENT ON COLUMN prematch_features.odds_movement_draw IS 'V51.2: 赔率变动 (平局)';
COMMENT ON COLUMN prematch_features.odds_movement_away IS 'V51.2: 赔率变动 (客胜)';

COMMENT ON COLUMN prematch_features.ev_home IS 'V51.2: 期望值 (主胜)';
COMMENT ON COLUMN prematch_features.ev_draw IS 'V51.2: 期望值 (平局)';
COMMENT ON COLUMN prematch_features.ev_away IS 'V51.2: 期望值 (客胜)';
COMMENT ON COLUMN prematch_features.kelly_home IS 'V51.2: Kelly Criterion (主胜)';
COMMENT ON COLUMN prematch_features.kelly_draw IS 'V51.2: Kelly Criterion (平局)';
COMMENT ON COLUMN prematch_features.kelly_away IS 'V51.2: Kelly Criterion (客胜)';
COMMENT ON COLUMN prematch_features.value_bet_outcome IS 'V51.2: 推荐投注结果 (home/draw/away/null)';
COMMENT ON COLUMN prematch_features.value_level IS 'V51.2: 价值等级 (negative/low/moderate/high/excellent)';

-- 6. 创建索引
CREATE INDEX IF NOT EXISTS idx_prematch_odds_opening
    ON prematch_features(opening_home_odds) WHERE opening_home_odds IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_prematch_odds_closing
    ON prematch_features(closing_home_odds) WHERE closing_home_odds IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_prematch_ev
    ON prematch_features(ev_home, ev_draw, ev_away) WHERE ev_home IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_prematch_value_bet
    ON prematch_features(value_level, value_bet_outcome) WHERE value_bet_outcome IS NOT NULL;

-- 7. 添加约束 (确保赔率值合法)
ALTER TABLE prematch_features
    ADD CONSTRAINT chk_opening_home_odds_positive
    CHECK (opening_home_odds IS NULL OR opening_home_odds > 1.0),
    ADD CONSTRAINT chk_opening_draw_odds_positive
    CHECK (opening_draw_odds IS NULL OR opening_draw_odds > 1.0),
    ADD CONSTRAINT chk_opening_away_odds_positive
    CHECK (opening_away_odds IS NULL OR opening_away_odds > 1.0),
    ADD CONSTRAINT chk_closing_home_odds_positive
    CHECK (closing_home_odds IS NULL OR closing_home_odds > 1.0),
    ADD CONSTRAINT chk_closing_draw_odds_positive
    CHECK (closing_draw_odds IS NULL OR closing_draw_odds > 1.0),
    ADD CONSTRAINT chk_closing_away_odds_positive
    CHECK (closing_away_odds IS NULL OR closing_away_odds > 1.0);

-- 8. 添加检查约束 (价值等级枚举)
ALTER TABLE prematch_features
    ADD CONSTRAINT chk_value_level
    CHECK (value_level IS NULL OR value_level IN (
        'negative', 'low', 'moderate', 'high', 'excellent'
    ));

-- 9. 添加检查约束 (投注结果枚举)
ALTER TABLE prematch_features
    ADD CONSTRAINT chk_value_bet_outcome
    CHECK (value_bet_outcome IS NULL OR value_bet_outcome IN (
        'home', 'draw', 'away'
    ));

-- ============================================================
-- 迁移完成
-- ============================================================
-- 注释: 此脚本为 prematch_features 表添加了 20 个赔率相关字段
-- 后续步骤:
--   1. 运行 scripts/ml/v51_2_team_mapping_generator.py 生成球队映射
--   2. 启动 odds_scraper 服务采集赔率数据
--   3. 运行赔率数据填充脚本更新 prematch_features 表
-- ============================================================
