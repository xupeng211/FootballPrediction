-- 中文ML优化数据库Schema验证脚本 (修正版)
-- 验证表结构语法和JSONB查询功能

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

-- 插入测试数据
INSERT INTO test_比赛高级统计 (
    比赛ID, 主队期望进球, 客队期望进球,
    主队控球率, 客队控球率, 主队射门数, 客队射门数,
    主队射正数, 客队射正数, 裁判, 球场,
    射门地图, 压力指数, 阵容信息, 球员统计, 比赛事件,
    数据质量评分, 数据来源可靠性
) VALUES (
    'test_002',
    2.15, 1.32,
    58, 42, 18, 14,
    12, 8, '迈克·迪恩', '老特拉福德球场',
    '[{"id": 1, "x": 81.7, "y": 39.5, "expectedGoals": 0.85, "shotType": "RightFoot", "shotQuality": 85.0, "angle": 25.5, "distance": 12.3}]'::jsonb,
    '{"home_team": [{"minute": 2, "pressure": 45.5}], "away_team": [{"minute": 2, "pressure": 54.5}], "key_moments": [{"minute": 25, "type": "momentum_shift"}]}'::jsonb,
    '{"home": {"team_name": "曼联", "formation": "4-3-3"}, "away": {"team_name": "曼城", "formation": "4-2-3-1"}}'::jsonb,
    '{"115591": {"name": "拉什福德", "goals": 1, "rating": 8.5}}'::jsonb,
    '[{"id": 1, "minute": 25, "type": "goal", "player_name": "拉什福德", "team_id": 8603}]'::jsonb,
    0.92, 'high'
) ON CONFLICT (比赛ID) DO NOTHING;

-- 验证基础数据插入
SELECT
    '=== 基础数据验证 ===' AS 验证类型,
    比赛ID,
    主队期望进球 + 客队期望进球 AS 总期望进球,
    主队控球率 - 客队控球率 AS 控球率差值,
    主队射门数 + 客队射门数 AS 总射门数,
    数据质量评分,
    数据来源可靠性
FROM test_比赛高级统计
WHERE 比赛ID = 'test_002';

-- 验证JSONB查询功能 (修正语法)
SELECT
    '=== JSONB深度学习特征验证 ===' AS 验证类型,
    比赛ID,
    (射门地图->0->>'expectedGoals')::DECIMAL(5,2) AS 首个射门xG值,
    (射门地图->0->>'shotQuality')::FLOAT AS 首个射门质量,
    (射门地图->0->>'angle')::FLOAT AS 首个射门角度,
    (阵容信息->'home'->>'team_name') AS 主队名称,
    jsonb_array_length(比赛事件) AS 比赛事件数量,
    jsonb_array_length(压力指数->'home_team') AS 主队压力数据点数量
FROM test_比赛高级统计
WHERE 比赛ID = 'test_002';

-- 验证ML特征查询视图
SELECT
    '=== ML特征查询验证 ===' AS 验证类型,
    比赛ID,
    主队期望进球,
    客队期望进球,
    (主队期望进球 + 客队期望进球) AS 总期望进球,
    (主队期望进球 - 客队期望进球) AS 期望进球差值,
    (主队期望进球 * 1.5 + 主队控球率 * 0.5) AS 主队强度评分,
    (客队期望进球 * 1.5 + 客队控球率 * 0.5) AS 客队强度评分,
    jsonb_array_length(射门地图) AS 射门地图总射门数
FROM test_比赛高级统计
WHERE 比赛ID = 'test_002';

-- 验证高级JSONB查询 - 提取关键转折点
SELECT
    '=== 关键转折点验证 ===' AS 验证类型,
    比赛ID,
    (压力指数->'key_moments'->0->>'minute')::INTEGER AS 首个转折点分钟,
    压力指数->'key_moments'->0->>'type' AS 转折点类型,
    (阵容信息->'home'->>'formation') AS 主队阵型,
    (球员统计->'115591'->>'rating')::FLOAT AS 球员评分
FROM test_比赛高级统计
WHERE 比赛ID = 'test_002';

-- 测试ML特征函数 (如果有)
SELECT
    '=== 测试结果总结 ===' AS 验证类型,
    '中文ML优化Schema验证成功!' AS 状态,
    COUNT(*) AS 测试记录数,
    AVG(主队期望进球 + 客队期望进球) AS 平均总期望进球,
    AVG(jsonb_array_length(射门地图)) AS 平均射门数量
FROM test_比赛高级统计;

-- 清理测试表
DROP TABLE test_比赛高级统计;