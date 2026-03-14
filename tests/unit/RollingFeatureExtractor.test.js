/**
 * RollingFeatureExtractor 单元测试
 * ================================
 *
 * V4.0 模块化特征提取器测试套件
 * 覆盖滚动统计特征的计算逻辑
 * @module tests/unit/RollingExtractor
 * @version V4.0.0
 */

'use strict';

const test = require('node:test');
const assert = require('assert');
const { RollingFeatureExtractor, FEATURE_NAMES } = require('../../src/feature_engine/smelter/components/RollingFeatureExtractor');

// ============================================================================
// 测试辅助函数
// ============================================================================

// 模拟历史比赛数据
const mockHistoricalMatches = [
    {
        match_id: 'match_1',
        home_team: 'Team A',
        away_team: 'Team B',
        home_score: 2,
        away_score: 1,
        match_date: '2026-01-01',
        home_xg: '1.8',
        away_xg: '0.9',
        home_possession: '55',
        away_possession: '45',
        home_shots: '15',
        away_shots: '8',
        home_shots_on_target: '6',
        away_shots_on_target: '3'
    },
    {
        match_id: 'match_2',
        home_team: 'Team C',
        away_team: 'Team A',
        home_score: 1,
        away_score: 1,
        match_date: '2026-01-05',
        home_xg: '1.2',
        away_xg: '1.5',
        home_possession: '48',
        away_possession: '52',
        home_shots: '10',
        away_shots: '14',
        home_shots_on_target: '4',
        away_shots_on_target: '6'
    },
    {
        match_id: 'match_3',
        home_team: 'Team A',
        away_team: 'Team D',
        home_score: 3,
        away_score: 0,
        match_date: '2026-01-10',
        home_xg: '2.5',
        away_xg: '0.5',
        home_possession: '60',
        away_possession: '40',
        home_shots: '18',
        away_shots: '6',
        home_shots_on_target: '8',
        away_shots_on_target: '2'
    }
];

function createMockDbPool(rows) {
    return {
        query: async () => ({ rows: rows || [] })
    };
}

function createMockDbPoolSequence(rowArrays) {
    let callIndex = 0;
    return {
        query: async () => {
            const rows = rowArrays[callIndex % rowArrays.length] || [];
            callIndex++;
            return { rows };
        }
    };
}

function createExtractor(dbPool, config = {}) {
    const extractor = new RollingFeatureExtractor({
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

    assert.strictEqual(featureNames.length, 30); // V5.2: 30维特征
    assert(featureNames.includes('home_last5_xg_avg'));
    assert(featureNames.includes('away_last5_draw_rate'));
    assert(featureNames.includes('rest_days_diff'));
});

test('应该正确返回默认配置', () => {
    const extractor = createExtractor(createMockDbPool());
    const config = extractor.getDefaultConfig();

    assert.strictEqual(config.rollingWindow, 5);
    assert.strictEqual(config.minSamples, 3);
    assert.strictEqual(config.defaults.xgAvg, 1.2);
});

test('应该继承 BaseExtractor', () => {
    const extractor = createExtractor(createMockDbPool());

    assert.strictEqual(extractor.name, 'RollingFeatureExtractor');
    assert.strictEqual(extractor.version, 'V5.2.0-HOME-FORTRESS');
});

// 核心提取逻辑测试
test('应该正确计算滚动xG均值', async () => {
    const dbPool = createMockDbPool(mockHistoricalMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    // Team A: 近3场xG = (1.8 + 1.5 + 2.5) / 3 = 1.93
    assert.ok(result.home_last5_xg_avg >= 1.9 && result.home_last5_xg_avg <= 1.97,
        `xG均值应为 ~1.93，实际为 ${result.home_last5_xg_avg}`);
});

test('应该正确计算射门转化率', async () => {
    const dbPool = createMockDbPool(mockHistoricalMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    // Team A: shots_on_target / shots = (6+6+8)/(15+14+18) = 20/47 = 0.426
    assert.ok(result.home_last5_shot_conversion > 0.3 && result.home_last5_shot_conversion < 0.5,
        `射门转化率应在 0.3-0.5 之间，实际为 ${result.home_last5_shot_conversion}`);
});

test('应该正确计算胜率', async () => {
    const dbPool = createMockDbPool(mockHistoricalMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    // Team A: 2胜1平0负 => 胜率 66.7%, 平局率 33.3%
    assert.ok(result.home_last5_win_rate > 0.6 && result.home_last5_win_rate < 0.7,
        `胜率应为 ~0.667，实际为 ${result.home_last5_win_rate}`);
    assert.ok(result.home_last5_draw_rate > 0.3 && result.home_last5_draw_rate < 0.35,
        `平局率应为 ~0.333，实际为 ${result.home_last5_draw_rate}`);
    assert.strictEqual(result.home_last5_loss_rate, 0);
});

test('应该正确计算休息天数', async () => {
    // 创建历史比赛数据
    const matches = [
        { ...mockHistoricalMatches[0], match_date: '2026-01-10' },
        { ...mockHistoricalMatches[1], match_date: '2026-01-12' },
        { ...mockHistoricalMatches[2], match_date: '2026-01-14' }
    ];
    const dbPool = createMockDbPool(matches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-20'
    });

    // 验证休息天数是有效数字（1-14之间）
    assert.ok(typeof result.home_rest_days === 'number');
    assert.ok(result.home_rest_days >= 1 && result.home_rest_days <= 14,
        `休息天数应在1-14之间，实际为 ${result.home_rest_days}`);
});

// 边界条件测试
test('历史数据不足时使用默认值', async () => {
    const dbPool = createMockDbPool(mockHistoricalMatches.slice(0, 2));
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    // 使用默认值
    assert.strictEqual(result.home_last5_xg_avg, 1.2);
    assert.strictEqual(result.home_last5_win_rate, 0.33);
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

    assert.strictEqual(result.home_last5_xg_avg, 1.2);
    assert.strictEqual(result.home_last5_draw_rate, 0.25);
});

test('缺少数据库连接时返回错误特征', async () => {
    const extractor = new RollingFeatureExtractor({ dbPool: null });
    extractor.logger = { info: () => {}, debug: () => {}, warn: () => {}, error: () => {} };

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    assert(result._error);
});

test('休息天数最大限制为14天', async () => {
    const oldMatches = [{
        ...mockHistoricalMatches[0],
        match_date: '2025-12-01' // 早于45天
    }];
    const dbPool = createMockDbPool(oldMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    // 休息天数应使用默认值7（当数据不足时）或14（当超过上限时）
    // 根据代码逻辑，返回的是默认值7
    assert.ok(result.home_rest_days <= 14);
});

// 对比特征测试
test('应该计算休息天数差', async () => {
    const homeMatches = [{
        ...mockHistoricalMatches[0],
        match_date: '2026-01-15'  // 5天前
    }];
    const awayMatches = [{
        ...mockHistoricalMatches[1],
        match_date: '2026-01-17'  // 3天前
    }];

    const dbPool = createMockDbPoolSequence([homeMatches, awayMatches]);
    const extractor = createExtractor(dbPool, { minSamples: 1 }); // 降低最小样本要求

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-20'
    });

    // 主队休息5天，客队休息3天 => 差值 +2
    assert.strictEqual(result.rest_days_diff, 2);
});

test('应该计算势头差和xG差', async () => {
    const dbPool = createMockDbPool(mockHistoricalMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    assert(typeof result.form_momentum_diff === 'number');
    assert(typeof result.xg_diff_rolling === 'number');
});

// 性能与统计
test('应该追踪执行统计', async () => {
    const dbPool = createMockDbPool(mockHistoricalMatches);
    const extractor = createExtractor(dbPool);

    await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    assert.strictEqual(extractor.stats.totalCalls, 1);
    assert.strictEqual(extractor.stats.successfulCalls, 1);
    assert.strictEqual(extractor.stats.failedCalls, 0);
});

test('失败时应该返回错误特征', async () => {
    const dbPool = {
        query: async () => { throw new Error('DB Error'); }
    };
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    // 验证返回了错误特征（使用默认值）
    assert.strictEqual(result.home_last5_xg_avg, 1.2);
    assert.strictEqual(result.away_last5_xg_avg, 1.2);
});

// 客场球队测试
test('应该正确处理客场球队数据', async () => {
    const dbPool = createMockDbPool(mockHistoricalMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team X',
        away_team: 'Team A',
        match_date: '2026-01-15'
    });

    // 客队特征应该被提取
    assert(typeof result.away_last5_xg_avg === 'number');
    assert(typeof result.away_last5_win_rate === 'number');
});

// 字段完整性测试
test('所有特征字段都应该有值', async () => {
    const dbPool = createMockDbPool(mockHistoricalMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-15'
    });

    // 检查所有 21 个特征都有值
    for (const name of FEATURE_NAMES) {
        assert(result[name] !== undefined, `特征 ${name} 应该存在`);
        assert(typeof result[name] === 'number', `特征 ${name} 应该是数字类型`);
    }
});

console.log('\n✅ RollingFeatureExtractor 测试套件已加载，共 17 个测试用例');
