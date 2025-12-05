-- 添加S-Tier特征列到matches表
-- S-Tier Features Migration Script

-- 红黄牌数据
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_yellow_cards INTEGER DEFAULT 0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_yellow_cards INTEGER DEFAULT 0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_red_cards INTEGER DEFAULT 0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_red_cards INTEGER DEFAULT 0;

-- 球队评分数据
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_team_rating DECIMAL(3,1) DEFAULT 0.0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_team_rating DECIMAL(3,1) DEFAULT 0.0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_avg_player_rating DECIMAL(4,2) DEFAULT 0.0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_avg_player_rating DECIMAL(4,2) DEFAULT 0.0;

-- 绝佳机会数据
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_big_chances INTEGER DEFAULT 0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_big_chances INTEGER DEFAULT 0;

-- 环境数据
ALTER TABLE matches ADD COLUMN IF NOT EXISTS stadium_name VARCHAR(255) DEFAULT '';
ALTER TABLE matches ADD COLUMN IF NOT EXISTS attendance INTEGER DEFAULT 0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS referee_name VARCHAR(255) DEFAULT '';
ALTER TABLE matches ADD COLUMN IF NOT EXISTS weather VARCHAR(100) DEFAULT '';

-- 添加索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_matches_home_score ON matches(home_score);
CREATE INDEX IF NOT EXISTS idx_matches_away_score ON matches(away_score);
CREATE INDEX IF NOT EXISTS idx_matches_stadium_name ON matches(stadium_name);
CREATE INDEX IF NOT EXISTS idx_matches_referee_name ON matches(referee_name);

-- 显示表结构确认
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'matches'
    AND column_name IN (
        'home_yellow_cards', 'away_yellow_cards', 'home_red_cards', 'away_red_cards',
        'home_team_rating', 'away_team_rating', 'home_avg_player_rating', 'away_avg_player_rating',
        'home_big_chances', 'away_big_chances', 'stadium_name', 'attendance', 'referee_name', 'weather'
    )
ORDER BY column_name;