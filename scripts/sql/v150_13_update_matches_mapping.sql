-- V150.13: 更新 matches_mapping 表
-- 来源: OddsHarvester 复刻版 - 23/24 赛季 380 场比赛

-- 1. 确保 matches_mapping 表存在
CREATE TABLE IF NOT EXISTS matches_mapping (
    match_id VARCHAR(50) PRIMARY KEY,
    url TEXT NOT NULL,
    hash VARCHAR(8) NOT NULL,
    season VARCHAR(20) NOT NULL,
    league_name VARCHAR(255) NOT NULL DEFAULT 'Premier League',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 创建临时表存储新数据
CREATE TEMP TABLE v150_13_temp_matches (
    url TEXT NOT NULL,
    hash VARCHAR(8) NOT NULL
);

-- 3. 插入 380 场比赛数据（从脚本输出中提取）
-- 注意：实际数据将通过 Python 脚本插入

-- 4. 更新 matches_mapping 表
-- 使用 INSERT ON CONFLICT 更新现有记录或插入新记录

-- 5. 验证数据完整性
-- SELECT COUNT(*) as total_matches FROM matches_mapping WHERE season = '2023-2024';
-- 预期结果: 380

-- 6. 查找揭幕战
-- SELECT * FROM matches_mapping WHERE hash = 'Q7TUjsot';
