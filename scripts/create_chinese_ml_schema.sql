-- =====================================================
-- 中文ML优化高级比赛统计数据表 - PostgreSQL混合存储方案
-- 主键设计：可索引核心字段 + JSONB深度学习特征
-- =====================================================

-- 删除旧表
DROP TABLE IF EXISTS 比赛高级统计 CASCADE;

-- 创建新的ML优化表
CREATE TABLE 比赛高级统计 (
    -- 主键标识
    比赛ID VARCHAR(100) PRIMARY KEY,

    -- === 可索引的核心业务指标 (ML模型特征) ===
    -- 期望进球xG (Expected Goals) - 机器学习核心特征
    主队期望进球 DECIMAL(5,2) NOT NULL DEFAULT 0.0,
    客队期望进球 DECIMAL(5,2) NOT NULL DEFAULT 0.0,

    -- 基础技术统计
    主队控球率 INTEGER NOT NULL DEFAULT 0,      -- 百分比存储，如58表示58%
    客队控球率 INTEGER NOT NULL DEFAULT 0,
    主队射门数 INTEGER NOT NULL DEFAULT 0,
    客队射门数 INTEGER NOT NULL DEFAULT 0,
    主队射正数 INTEGER NOT NULL DEFAULT 0,
    客队射正数 INTEGER NOT NULL DEFAULT 0,

    -- 犯规统计
    主队犯规数 INTEGER NOT NULL DEFAULT 0,
    客队犯规数 INTEGER NOT NULL DEFAULT 0,
    主队黄牌数 INTEGER NOT NULL DEFAULT 0,
    客队黄牌数 INTEGER NOT NULL DEFAULT 0,
    主队红牌数 INTEGER NOT NULL DEFAULT 0,
    客队红牌数 INTEGER NOT NULL DEFAULT 0,

    -- 定位球统计
    主队角球数 INTEGER NOT NULL DEFAULT 0,
    客队角球数 INTEGER NOT NULL DEFAULT 0,
    主队越位数 INTEGER NOT NULL DEFAULT 0,
    客队越位数 INTEGER NOT NULL DEFAULT 0,

    -- === 比赛元数据 (字符串字段，便于搜索和筛选) ===
    裁判 VARCHAR(200),                      -- 比赛裁判姓名
    球场 VARCHAR(200),                      -- 比赛球场名称
    观众人数 INTEGER,                          -- 现场观众数量
    天气 VARCHAR(100),                          -- 比赛当天天气情况
    比赛日 VARCHAR(50),                       -- 比赛日期描述
    轮次 VARCHAR(100),                       -- 比赛轮次信息
    阶段 VARCHAR(100),                      -- 比赛阶段(小组赛/淘汰赛等)

    -- === JSONB深度学习特征存储 (复杂数据结构) ===
    -- 射门图数据 (包含坐标、xG值、射门类型的深度学习特征)
    射门地图 JSONB NOT NULL DEFAULT '[]',

    -- 全场压力指数时间序列 (用于momentum分析和比赛走势预测)
    压力指数 JSONB NOT NULL DEFAULT '{}',

    -- 完整阵容数据 (首发+替补，含球员评分、位置信息)
    阵容信息 JSONB NOT NULL DEFAULT '{}',

    -- 详细的球员技术统计 (评分、传球、对抗等个人表现数据)
    球员统计 JSONB NOT NULL DEFAULT '{}',

    -- 比赛事件时间轴 (进球、换人、卡牌、VAR等完整事件流)
    比赛事件 JSONB NOT NULL DEFAULT '[]',

    -- === 数据质量和来源追踪 ===
    数据质量评分 DECIMAL(3,2) NOT NULL DEFAULT 0.5,
    数据来源可靠性 VARCHAR(20) NOT NULL DEFAULT 'medium',

    -- 时间戳
    采集时间 TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    更新时间 TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- 数据完整性约束
    CONSTRAINT 射门地图必须是数组 CHECK (jsonb_typeof(射门地图) = 'array'::text),
    CONSTRAINT 压力指数必须是对象 CHECK (jsonb_typeof(压力指数) = 'object'::text),
    CONSTRAINT 阵容信息必须是对象 CHECK (jsonb_typeof(阵容信息) = 'object'::text),
    CONSTRAINT 球员统计必须是对象 CHECK (jsonb_typeof(球员统计) = 'object'::text),
    CONSTRAINT 比赛事件必须是数组 CHECK (jsonb_typeof(比赛事件) = 'array'::text)
);

-- =====================================================
-- 索引策略优化 - 平衡查询性能和存储效率
-- =====================================================

-- JSONB字段专用索引 (支持GIN索引，加速JSONB查询)
CREATE INDEX idx_比赛高级统计_射门地图 ON 比赛高级统计 USING GIN (射门地图);
CREATE INDEX idx_比赛高级统计_压力指数 ON 比赛高级统计 USING GIN (压力指数);
CREATE INDEX idx_比赛高级统计_阵容信息 ON 比赛高级统计 USING GIN (阵容信息);
CREATE INDEX idx_比赛高级统计_球员统计 ON 比赛高级统计 USING GIN (球员统计);
CREATE INDEX idx_比赛高级统计_比赛事件 ON 比赛高级统计 USING GIN (比赛事件);

-- 常用查询索引 (加速筛选和排序)
CREATE INDEX idx_比赛高级统计_裁判 ON 比赛高级统计(裁判);
CREATE INDEX idx_比赛高级统计_球场 ON 比赛高级统计(球场);
CREATE INDEX idx_比赛高级统计_观众 ON 比赛高级统计(观众人数);
CREATE INDEX idx_比赛高级统计_天气 ON 比赛高级统计(天气);

-- 机器学习特征索引 (ML模型训练和预测优化)
CREATE INDEX idx_比赛高级统计_主队期望进球 ON 比赛高级统计(主队期望进球);
CREATE INDEX idx_比赛高级统计_客队期望进球 ON 比赛高级统计(客队期望进球);
CREATE INDEX idx_比赛高级统计_控球率 ON 比赛高级统计(主队控球率, 客队控球率);
CREATE INDEX idx_比赛高级统计_射门数 ON 比赛高级统计(主队射门数, 客队射门数);

-- 综合性能指标索引
CREATE INDEX idx_比赛高级统计_总期望进球 ON 比赛高级统计((主队期望进球 + 客队期望进球));
CREATE INDEX idx_比赛高级统计_总射门数 ON 比赛高级统计((主队射门数 + 客队射门数));
CREATE INDEX idx_比赛高级统计_期望进球控球率 ON 比赛高级统计(主队期望进球, 客队期望进球, 主队控球率, 客队控球率);

-- 时间戳索引 (按时间范围查询优化)
CREATE INDEX idx_比赛高级统计_采集时间 ON 比赛高级统计(采集时间);
CREATE INDEX idx_比赛高级统计_更新时间 ON 比赛高级统计(更新时间);

-- =====================================================
-- 表和字段注释 (数据字典)
-- =====================================================

COMMENT ON TABLE 比赛高级统计 IS 'ML/DL优化的比赛高级统计数据表 - PostgreSQL混合存储设计：可索引业务字段 + JSONB深度学习特征，适用于机器学习模型训练和足球数据分析';

COMMENT ON COLUMN 比赛高级统计.比赛ID IS '主键：FotMob比赛唯一标识符';
COMMENT ON COLUMN 比赛高级统计.主队期望进球 IS '主队期望进球数(xG)：基于射门数据的期望进球值，机器学习核心特征';
COMMENT ON COLUMN 比赛高级统计.客队期望进球 IS '客队期望进球数(xG)：基于射门数据的期望进球值，机器学习核心特征';
COMMENT ON COLUMN 比赛高级统计.主队控球率 IS '主队控球率(整数)：比赛期间主队控球百分比，如58表示58%';
COMMENT ON COLUMN 比赛高级统计.客队控球率 IS '客队控球率(整数)：比赛期间客队控球百分比';
COMMENT ON COLUMN 比赛高级统计.裁判 IS '裁判姓名：比赛主裁判的完整姓名';
COMMENT ON COLUMN 比赛高级统计.球场 IS '球场名称：比赛举办球场的完整名称';
COMMENT ON COLUMN 比赛高级统计.观众人数 IS '观众人数：现场观看比赛的总观众数量';
COMMENT ON COLUMN 比赛高级统计.射门地图 IS '射门地图(JSONB)：包含每个射门的位置坐标(x,y)、期望进球值、射门类型、时间戳等深度学习特征';
COMMENT ON COLUMN 比赛高级统计.压力指数 IS '压力指数(JSONB)：全场比赛压力指数的时间序列数据，用于momentum分析和比赛走势预测';
COMMENT ON COLUMN 比赛高级统计.阵容信息 IS '阵容信息(JSONB)：主客队完整阵容数据，包含首发名单、替补球员、阵型、球员评分等';
COMMENT ON COLUMN 比赛高级统计.球员统计 IS '球员统计(JSONB)：详细的个人技术统计数据，包含评分、传球、对抗、射门等各项指标';
COMMENT ON COLUMN 比赛高级统计.比赛事件 IS '比赛事件(JSONB)：完整的事件时间轴，包含进球、换人、黄红牌、VAR等所有关键事件';
COMMENT ON COLUMN 比赛高级统计.数据质量评分 IS '数据质量评分(0-1)：基于数据完整性、一致性的自动评估指标';
COMMENT ON COLUMN 比赛高级统计.数据来源可靠性 IS '数据来源可靠性：high/medium/low三级可靠性评估';

-- =====================================================
-- 机器学习特征提取函数
-- =====================================================

-- 提取射门特征函数 (从JSONB射门地图中计算统计指标)
CREATE OR REPLACE FUNCTION 提取射门特征(射门数据 JSONB)
RETURNS JSONB AS $$
BEGIN
    RETURN jsonb_build_object(
        '总射门数', jsonb_array_length(射门数据),
        '总期望进球', COALESCE((
            SELECT SUM((elem->>'expectedGoals')::NUMERIC)
            FROM jsonb_array_elements(射门数据) AS elem
        ), 0),
        '平均期望进球', COALESCE((
            SELECT AVG((elem->>'expectedGoals')::NUMERIC)
            FROM jsonb_array_elements(射门数据) AS elem
        ), 0),
        '高质量射门数', COALESCE((
            SELECT COUNT(*)
            FROM jsonb_array_elements(射门数据) AS elem
            WHERE (elem->>'expectedGoals')::NUMERIC > 0.5  -- 高质量射门阈值
        ), 0),
        '主队高质量射门', COALESCE((
            SELECT COUNT(*)
            FROM jsonb_array_elements(射门数据) AS elem
            WHERE (elem->>'expectedGoals')::NUMERIC > 0.5
            AND (elem->>'teamId')::TEXT = (elem->>'teamId')::TEXT  -- 确保是同一队
        ), 0),
        '射门位置分布', (
            SELECT jsonb_object_agg(
                '位置区域', CASE
                    WHEN elem->>'y'::NUMERIC < 33.3 THEN '前场'
                    WHEN elem->>'y'::NUMERIC < 66.7 THEN '中场'
                    ELSE '后场'
                END,
                '射门数', COUNT(*)
            )
            FROM jsonb_array_elements(射门数据) AS elem
        ),
        '射门类型统计', (
            SELECT jsonb_object_agg(
                '射门类型', CASE
                    WHEN elem->>'shotType' = 'RightFoot' THEN '右脚'
                    WHEN elem->>'shotType' = 'LeftFoot' THEN '左脚'
                    WHEN elem->>'shotType' = 'Header' THEN '头球'
                    ELSE '其他'
                END,
                '射门数', COUNT(*)
            )
            FROM jsonb_array_elements(射门数据) AS elem
            WHERE elem->>'shotType' IS NOT NULL
        )
    );
END;
$$ LANGUAGE plpgsql;

-- 提取比赛压力特征函数 (从JSONB压力指数中计算momentum指标)
CREATE OR REPLACE FUNCTION 提取压力特征(压力数据 JSONB)
RETURNS JSONB AS $$
BEGIN
    RETURN jsonb_build_object(
        '压力变化次数', jsonb_array_length(压力数据),
        '平均压力值', COALESCE((
            SELECT AVG((elem->>'pressure')::NUMERIC)
            FROM jsonb_array_elements(压力数据) AS elem
            WHERE elem->>'pressure' IS NOT NULL
        ), 0),
        '最大压力时刻', (
            SELECT jsonb_build_object(
                '分钟', elem->>'minute',
                '压力值', elem->>'pressure',
                '压力变化', CASE
                    WHEN (elem->>'pressureChange')::NUMERIC > 0.1 THEN '上升'
                    WHEN (elem->>'pressureChange')::NUMERIC < -0.1 THEN '下降'
                    ELSE '稳定'
                END
            )
            FROM jsonb_array_elements(压力数据) AS elem
            WHERE elem->>'pressure' IS NOT NULL
            ORDER BY (elem->>'pressure')::NUMERIC DESC
            LIMIT 1
        ),
        '关键转折点', (
            SELECT jsonb_agg(
                '分钟', elem->>'minute',
                '事件', CASE
                    WHEN (elem->>'pressureChange')::NUMERIC > 0.1 THEN '压力陡升'
                    WHEN (elem->>'pressureChange')::NUMERIC < -0.1 THEN '压力陡降'
                    WHEN ABS((elem->>'pressureChange')::NUMERIC) > 0.05 THEN '压力波动'
                    ELSE '平稳期'
                END
            )
            FROM jsonb_array_elements(压力数据) AS elem
            WHERE elem->>'pressureChange' IS NOT NULL
        )
    );
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 机器学习查询视图 (预计算特征，简化ML管道)
-- =====================================================

-- 比赛机器学习特征视图 (整合所有ML特征)
CREATE OR REPLACE VIEW 比赛机器学习特征 AS
SELECT
    -- 基础标识
    比赛ID,

    -- 核心xG特征
    主队期望进球,
    客队期望进球,
    (主队期望进球 + 客队期望进球) AS 总期望进球,
    (主队期望进球 - 客队期望进球) AS 期望进球差值,

    -- 技术统计
    主队控球率,
    客队控球率,
    (主队控球率 - 客队控球率) AS 控球率差值,
    主队射门数,
    客队射门数,
    (主队射门数 + 客队射门数) AS 总射门数,
    (主队射正数::FLOAT / NULLIF(主队射门数, 0)) * 100 AS 主队射正率,
    (客队射正数::FLOAT / NULLIF(客队射门数, 0)) * 100 AS 客队射正率,

    -- 犯规统计
    (主队犯规数 + 客队犯规数) AS 总犯规数,
    (主队黄牌数 + 客队黄牌数) AS 总黄牌数,
    (主队红牌数 + 客队红牌数) AS 总红牌数,
    (主队角球数 + 客队角球数) AS 总角球数,

    -- 计算特征指标
    (主队期望进球 * 1.5 + 主队控球率 * 0.5) AS 主队强度评分,
    (客队期望进球 * 1.5 + 客队控球率 * 0.5) AS 客队强度评分,
    (主队期望进球 / NULLIF(主队射门数 + 客队射门数, 0)) AS 主队进攻效率,
    (客队期望进球 / NULLIF(主队射门数 + 客队射门数, 0)) AS 客队进攻效率,

    -- JSONB特征提取
    jsonb_array_length(射门地图) AS 射门地图总射门数,
    提取射门特征(射门地图)->>'总射门数' AS 射门特征统计射门数,
    提取射门特征(射门地图)->>'总期望进球' AS 射门特征统计期望进球,
    提取射门特征(射门地图)->>'平均期望进球' AS 射门特征平均期望进球,
    提取压力特征(压力指数)->>'压力变化次数' AS 压力变化频率,
    提取压力特征(压力指数)->>'平均压力值' AS 平均压力水平,

    -- 阵容数据特征
    (阵容信息->'home'->>'team_name') AS 主队名称,
    (阵容信息->'away'->>'team_name') AS 客队名称,
    (阵容信息->'home'->>'formation') AS 主队阵型,
    (阵容信息->'away'->>'formation') AS 客队阵型,
    jsonb_array_length(阵容信息->'home'->'players') AS 主队上场球员数,
    jsonb_array_length(阵容信息->'away'->'players') AS 客队上场球员数,

    -- 比赛事件统计
    jsonb_array_length(比赛事件) AS 总事件数,
    (
        SELECT COUNT(*)
        FROM jsonb_array_elements(比赛事件) AS elem
        WHERE elem->>'type' = 'goal'
    ) AS 总进球事件数,
    (
        SELECT COUNT(*)
        FROM jsonb_array_elements(比赛事件) AS elem
        WHERE elem->>'type' IN ('yellow_card', 'red_card')
    ) AS 总卡牌事件数,
    (
        SELECT COUNT(*)
        FROM jsonb_array_elements(比赛事件) AS elem
        WHERE elem->>'type' = 'substitution'
    ) AS 总换人事件数,

    -- 数据质量评估
    数据质量评分,
    数据来源可靠性,
    采集时间,
    更新时间

FROM 比赛高级统计;

-- =====================================================
-- 测试数据插入 (验证JSONB存储和特征提取)
-- =====================================================

INSERT INTO 比赛高级统计 (
    比赛ID, 主队期望进球, 客队期望进球,
    主队控球率, 客队控球率, 主队射门数, 客队射门数,
    主队射正数, 客队射正数, 主队犯规数, 客队犯规数,
    主队黄牌数, 客队黄牌数, 主队红牌数, 客队红牌数,
    主队角球数, 客队角球数, 主队越位数, 客队越位数,
    裁判, 球场, 观众人数, 天气, 比赛日, 轮次, 阶段,

    -- 射门地图JSONB数据
    '[{"id": 2840199951, "x": 81.7, "y": 39.5, "expectedGoals": 0.85, "shotType": "RightFoot", "isOnTarget": true, "minute": 16, "teamId": 8603, "situation": "RegularPlay", "period": "FirstHalf", "isOwnGoal": false, "goalCrossedY": 27.7, "goalCrossedZ": 2.0}, {"id": 2840199952, "x": 120.3, "y": 25.8, "expectedGoals": 1.32, "shotType": "LeftFoot", "isOnTarget": false, "minute": 34, "teamId": 5421, "situation": "CounterAttack", "period": "SecondHalf", "isOwnGoal": false, "goalCrossedY": 25.0, "goalCrossedZ": 1.8}]'::jsonb,

    -- 压力指数JSONB数据
    '{
        "pressure_65": 0.65,
        "pressure_70": 0.82,
        "pressure_75": 0.48,
        "pressure_80": 0.93,
        "pressure_85": 1.15,
        "pressure_90": 0.77
    }'::jsonb,

    -- 阵容信息JSONB数据
    '{
        "home": {
            "team_name": "曼联",
            "formation": "4-3-3",
            "players": [
                {
                    "name": "拉什福德",
                    "position": "ST",
                    "shirt_number": 10,
                    "rating": 8.2,
                    "is_starter": true,
                    "minutes_played": 90
                },
                {
                    "name": "布鲁诺·费尔南德斯",
                    "position": "CAM",
                    "shirt_number": 8,
                    "rating": 7.9,
                    "is_starter": true,
                    "minutes_played": 90
                },
                {
                    "name": "马库斯·拉什福德",
                    "position": "CF",
                    "shirt_number": 9,
                    "rating": 7.5,
                    "is_starter": true,
                    "minutes_played": 78
                }
            ]
        },
        "away": {
            "team_name": "曼城",
            "formation": "4-2-3-1",
            "players": [
                {
                    "name": "埃尔林·哈兰德",
                    "position": "ST",
                    "shirt_number": 9,
                    "rating": 8.8,
                    "is_starter": true,
                    "minutes_played": 90
                },
                {
                    "name": "凯文·德布劳内",
                    "position": "LW",
                    "shirt_number": 20,
                    "rating": 8.1,
                    "is_starter": true,
                    "minutes_played": 90
                },
                {
                    "name": "菲尔·福登",
                    "position": "CF",
                    "shirt_number": 47,
                    "rating": 6.8,
                    "is_starter": false,
                    "minutes_played": 12
                }
            ]
        }
    }'::jsonb,

    -- 比赛事件JSONB数据
    '[
        {
            "id": 2840199991,
            "minute": 25,
            "type": "goal",
            "team_id": 8603,
            "player_id": 115591,
            "player_name": "拉什福德",
            "is_home_team": true,
            "assist_player_id": 123456,
            "assist_player_name": "布鲁诺·费尔南德斯"
        },
        {
            "id": 2840199992,
            "minute": 67,
            "type": "yellow_card",
            "team_id": 5421,
            "player_id": 987654,
            "player_name": "凯文·德布劳内",
            "is_home_team": false,
            "reason": "战术犯规"
        },
        {
            "id": 2840199993,
            "minute": 78,
            "type": "substitution",
            "team_id": 8603,
            "player_out_id": 115591,
            "player_out_name": "马库斯·拉什福德",
            "player_in_id": 111222,
            "player_in_name": "菲尔·福登"
        }
    ]'::jsonb,

    0.92,  # 数据质量评分
    'high'    # 数据来源可靠性
) VALUES (
    '4837167',
    2.15, 1.32,
    58, 42,
    18, 14,
    12, 8,
    12, 9,
    5, 4,
    2, 3,
    3, 2,
    6, 3,
    '迈克·迪恩',
    '老特拉福德球场',
    75000,
    '晴朗',
    '2024年8月24日',
    '英超第3轮',
    '小组赛',
    0.92,  # 数据质量评分
    'high'    # 数据来源可靠性
) ON CONFLICT (比赛ID) DO NOTHING;