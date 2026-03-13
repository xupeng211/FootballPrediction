/**
 * EfficiencyFeatureExtractor 单元测试
 * ===================================
 *
 * V4.0 效率特征提取器测试套件
 * 测试射门转化率、终结效率等关键指标
 * @module tests/unit/EfficiencyExtractor
 * @version V4.0.0
 */

'use strict';

const test = require('node:test');
const assert = require('assert');
const { EfficiencyFeatureExtractor, FEATURE_NAMES } = require('../../src/feature_engine/smelter/components/EfficiencyFeatureExtractor');

// ============================================================================
// 测试辅助函数
// ============================================================================

// 模拟历史比赛数据（包含射门统计）
const mockEfficiencyMatches = [
    {
        match_id: 'match_1',
        home_team: 'Team A',
        away_team: 'Team B',
        home_score: 2,
        away_score: 1,
        match_date: '2026-01-01',
        home_shots: '15',
        away_shots: '8',
        home_shots_on_target: '6',
        away_shots_on_target: '3',
        home_xg: '1.8',
        away_xg: '0.9',
        home_big_chances: '3',
        away_big_chances: '1',
        home_possession: '55',
        away_possession: '45',
        home_ppda: '8',
        away_ppda: '12'
    },
    {
        match_id: 'match_2',
        home_team: 'Team C',
        away_team: 'Team A',
        home_score: 0,
        away_score: 2,
        match_date: '2026-01-05',
        home_shots: '10',
        away_shots: '14',
        home_shots_on_target: '3',
        away_shots_on_target: '7',
        home_xg: '0.8',
        away_xg: '1.5',
        home_big_chances: '2',
        away_big_chances: '4',
        home_possession: '48',
        away_possession: '52',
        home_ppda: '15',
        away_ppda: '6'
    },
    {
        match_id: 'match_3',
        home_team: 'Team A',
        away_team: 'Team D',
        home_score: 3,
        away_score: 0,
        match_date: '2026-01-10',
        home_shots: '18',
        away_shots: '6',
        home_shots_on_target: '9',
        away_shots_on_target: '2',
        home_xg: '2.5',
        away_xg: '0.5',
        home_big_chances: '5',
        away_big_chances: '0',
        home_possession: '60',
        away_possession: '40',
        home_ppda: '7',
        away_ppda: '18'
    }
];

function createMockDbPool(rows) {
    return {
        query: async () => ({ rows: rows || [] })
    };
}

function createExtractor(dbPool, config = {}) {
    const extractor = new EfficiencyFeatureExtractor({
        dbPool,
        config: {
            rollingWindow: 5,
            minSamples: 3,
            ...config
        }
    });

    // 禁用日志
    extractor.logger = {
        info: () => {},
        debug: () => {},
        warn: () => {},
        error: () => {}
    };

    return extractor;
}

// ============================================================================
// 测试套件
// ============================================================================

// 基础接口测试
test('应该正确返回特征名列表', () => {
    const extractor = createExtractor(createMockDbPool());
    const featureNames = extractor.getFeatureNames();

    assert.strictEqual(featureNames.length, 14); // 5+5+4
    assert(featureNames.includes('home_shot_conversion'));
    assert(featureNames.includes('away_finishing_efficiency'));
    assert(featureNames.includes('shot_conversion_diff'));
});

test('应该正确返回默认配置', () => {
    const extractor = createExtractor(createMockDbPool());
    const config = extractor.getDefaultConfig();

    assert.strictEqual(config.rollingWindow, 5);
    assert.strictEqual(config.minSamples, 3);
    assert.strictEqual(config.defaults.shotConversion, 0.33);
});

// 射门转化率测试
test('应该正确计算射门转化率', async () => {
    const dbPool = createMockDbPool(mockEfficiencyMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    // Team A: (6+7+9)/(15+14+18) = 22/47 = 0.468
    assert.ok(result.home_shot_conversion >= 0.4 && result.home_shot_conversion <= 0.5,
        `射门转化率应在0.4-0.5之间，实际为 ${result.home_shot_conversion}`);
});

// 终结效率测试
test('应该正确计算终结效率', async () => {
    const dbPool = createMockDbPool(mockEfficiencyMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    // Team A: goals/xG = (2+2+3)/(1.8+1.5+2.5) = 7/5.8 = 1.21
    // 表示把握机会能力超过预期
    assert.ok(result.home_finishing_efficiency > 1.0,
        `终结效率应>1.0（超常发挥），实际为 ${result.home_finishing_efficiency}`);
});

// 防守稳固性测试
test('应该正确计算防守稳固性', async () => {
    const dbPool = createMockDbPool(mockEfficiencyMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    // 防守稳固性应该存在且在合理范围
    assert.ok(result.home_defensive_solidity >= 0.5 && result.home_defensive_solidity <= 2.0,
        `防守稳固性应在0.5-2.0之间，实际为 ${result.home_defensive_solidity}`);
});

// 压迫效率测试
test('应该正确计算压迫效率', async () => {
    const dbPool = createMockDbPool(mockEfficiencyMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    // Team A: PPDA = (8+6+7)/3 = 7.0 -> 效率 = (25-7)/20 = 0.9
    assert.ok(result.home_press_efficiency >= 0.5 && result.home_press_efficiency <= 1.0,
        `压迫效率应在0.5-1.0之间（高压），实际为 ${result.home_press_efficiency}`);
});

// 对比特征测试
test('应该计算射门转化率差', async () => {
    const dbPool = createMockDbPool(mockEfficiencyMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    assert(typeof result.shot_conversion_diff === 'number');
    assert(typeof result.offensive_quality_index === 'number');
    assert(typeof result.defensive_quality_index === 'number');
});

// 边界条件测试
test('历史数据不足时使用默认值', async () => {
    const dbPool = createMockDbPool(mockEfficiencyMatches.slice(0, 2));
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    assert.strictEqual(result.home_shot_conversion, 0.33);
    assert.strictEqual(result.home_finishing_efficiency, 1.0);
});

test('无历史数据时使用默认值', async () => {
    const dbPool = createMockDbPool([]);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    assert.strictEqual(result.home_shot_conversion, 0.33);
    assert.strictEqual(result.away_defensive_solidity, 1.0);
});

// 缺少数据库连接
test('缺少数据库连接时返回错误特征', async () => {
    const extractor = new EfficiencyFeatureExtractor({ dbPool: null });
    extractor.logger = { info: () => {}, debug: () => {}, warn: () => {}, error: () => {} };

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    assert(result._error);
});

// 统计追踪
test('应该追踪执行统计', async () => {
    const dbPool = createMockDbPool(mockEfficiencyMatches);
    const extractor = createExtractor(dbPool);

    await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    assert.strictEqual(extractor.stats.totalCalls, 1);
    assert.strictEqual(extractor.stats.successfulCalls, 1);
});

// 字段完整性测试
test('所有特征字段都应该有值', async () => {
    const dbPool = createMockDbPool(mockEfficiencyMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    // 检查所有 14 个特征都有值
    for (const name of FEATURE_NAMES) {
        assert(result[name] !== undefined, `特征 ${name} 应该存在`);
        assert(typeof result[name] === 'number', `特征 ${name} 应该是数字类型`);
    }
});

// 识别高效杀手与浪射王
test('应该能区分高效杀手和浪射王', async () => {
    // 高效杀手：射门少但进球多
    const efficientMatches = [
        {
            ...mockEfficiencyMatches[0],
            home_shots: '8',
            home_shots_on_target: '5',
            home_score: '3',
            home_xg: '1.5'
        },
        {
            ...mockEfficiencyMatches[1],
            away_shots: '6',
            away_shots_on_target: '4',
            away_score: '2',
            away_xg: '1.0'
        },
        {
            ...mockEfficiencyMatches[2],
            home_shots: '10',
            home_shots_on_target: '6',
            home_score: '4',
            home_xg: '2.0'
        }
    ];

    const dbPool = createMockDbPool(efficientMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    // 高效杀手应该有高射门转化率和高终结效率
    assert.ok(result.home_shot_conversion > 0.5,
        `高效杀手射门转化率应>0.5，实际为 ${result.home_shot_conversion}`);
    assert.ok(result.home_finishing_efficiency > 1.5,
        `高效杀手终结效率应>1.5，实际为 ${result.home_finishing_efficiency}`);
});

console.log('\n✅ EfficiencyFeatureExtractor 测试套件已加载，共 14 个测试用例');
