-- 简化的中文ML优化数据库Schema验证
-- 验证表结构语法

-- 创建测试表
CREATE TABLE IF NOT EXISTS test_比赛高级统计 (
    比赛ID VARCHAR(100) PRIMARY KEY,
    主队期望进球 DECIMAL(5,2) NOT NULL DEFAULT 0.0,
    客队期望进球 DECIMAL(5,2) NOT NULL DEFAULT 0.0,
    主队控球率 INTEGER NOT NULL DEFAULT 0,
    客队控球率 INTEGER NOT NULL DEFAULT 0,
    主队射门数 INTEGER NOT NULL DEFAULT 0,
    客队射门数 INTEGER NOT NULL DEFAULT 0,
    主队射正数 INTEGER NOT NULL DEFAULT 0,
    客队射正数 INTEGER NOT NULL DEFAULT 0,
    主队犯规数 INTEGER NOT NULL DEFAULT 0,
    客队犯规数 INTEGER NOT NULL DEFAULT 0,
    主队黄牌数 INTEGER NOT NULL DEFAULT 0,
    客队黄牌数 INTEGER NOT NULL DEFAULT 0,
    主队红牌数 INTEGER NOT NULL DEFAULT 0,
    客队红牌数 INTEGER NOT NULL DEFAULT 0,
    主队角球数 INTEGER NOT NULL DEFAULT 0,
    客队角球数 INTEGER NOT NULL DEFAULT 0,
    主队越位数 INTEGER NOT NULL DEFAULT 0,
    客队越位数 INTEGER NOT NULL DEFAULT 0,
    裁判 VARCHAR(200),
    球场 VARCHAR(200),
    观众人数 INTEGER,
    天气 VARCHAR(100),
    比赛日 VARCHAR(50),
    轮次 VARCHAR(100),
    阶段 VARCHAR(100),
    射门地图 JSONB NOT NULL DEFAULT '[]',
    压力指数 JSONB NOT NULL DEFAULT '{}',
    阵容信息 JSONB NOT NULL DEFAULT '{}',
    球员统计 JSONB NOT NULL DEFAULT '{}',
    比赛事件 JSONB NOT NULL DEFAULT '[]',
    数据质量评分 DECIMAL(3,2) NOT NULL DEFAULT 0.5,
    数据来源可靠性 VARCHAR(20) NOT NULL DEFAULT 'medium',
    采集时间 TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    更新时间 TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建JSONB索引
CREATE INDEX IF NOT EXISTS idx_test_射门地图 ON test_比赛高级统计 USING GIN (射门地图);
CREATE INDEX IF NOT EXISTS idx_test_压力指数 ON test_比赛高级统计 USING GIN (压力指数);
CREATE INDEX IF NOT EXISTS idx_test_阵容信息 ON test_比赛高级统计 USING GIN (阵容信息);
CREATE INDEX IF NOT EXISTS idx_test_球员统计 ON test_比赛高级统计 USING GIN (球员统计);
CREATE INDEX IF NOT EXISTS idx_test_比赛事件 ON test_比赛高级统计 USING GIN (比赛事件);

-- 创建ML特征索引
CREATE INDEX IF NOT EXISTS idx_test_主队期望进球 ON test_比赛高级统计(主队期望进球);
CREATE INDEX IF NOT EXISTS idx_test_客队期望进球 ON test_比赛高级统计(客队期望进球);
CREATE INDEX IF NOT EXISTS idx_test_总期望进球 ON test_比赛高级统计((主队期望进球 + 客队期望进球));

-- 插入测试数据
INSERT INTO test_比赛高级统计 (
    比赛ID, 主队期望进球, 客队期望进球,
    主队控球率, 客队控球率, 主队射门数, 客队射门数,
    主队射正数, 客队射正数, 裁判, 球场,
    射门地图, 压力指数, 阵容信息, 球员统计, 比赛事件,
    数据质量评分, 数据来源可靠性
) VALUES (
    'test_001',
    2.15, 1.32,
    58, 42, 18, 14,
    12, 8, 'Mike Dean', 'Old Trafford',
    '[{"id": 1, "x": 81.7, "y": 39.5, "expectedGoals": 0.85, "shotType": "RightFoot"}]'::jsonb,
    '{"home": [45, 48, 52], "away": [55, 52, 48]}'::jsonb,
    '{"home": {"team_name": "曼联"}, "away": {"team_name": "曼城"}}'::jsonb,
    '{"115591": {"name": "拉什福德", "goals": 1}}'::jsonb,
    '[{"minute": 25, "type": "goal", "player_name": "拉什福德"}]'::jsonb,
    0.92, 'high'
) ON CONFLICT (比赛ID) DO NOTHING;

-- 验证数据插入
SELECT
    比赛ID,
    主队期望进球 + 客队期望进球 AS 总期望进球,
    jsonb_array_length(射门地图) AS 射门数量,
    数据质量评分,
    数据来源可靠性
FROM test_比赛高级统计
WHERE 比赛ID = 'test_001';

-- 验证JSONB查询功能
SELECT
    比赛ID,
    射门地图->0->>'expectedGoals' AS 首个射门xG值,
    阵容信息->>'home'->>'team_name' AS 主队名称,
    jsonb_array_length(比赛事件) AS 比赛事件数量
FROM test_比赛高级统计
WHERE 比赛ID = 'test_001';

-- 清理测试表
DROP TABLE IF EXISTS test_比赛高级统计;