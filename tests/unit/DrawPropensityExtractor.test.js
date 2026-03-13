/**
 * DrawPropensityExtractor 单元测试
 * =================================
 *
 * V4.0 平局倾向特征提取器测试套件
 * 专门解决平局预测准确率低的问题
 * @module tests/unit/DrawPropensityExtractor
 * @version V4.0.0
 */

'use strict';

const test = require('node:test');
const assert = require('assert');
const { DrawPropensityExtractor, FEATURE_NAMES } = require('../../src/feature_engine/smelter/components/DrawPropensityExtractor');

// ============================================================================
// 测试辅助函数
// ============================================================================

// 模拟历史比赛数据（包含平局）
const mockDrawMatches = [
    {
        match_id: 'match_1',
        home_team: 'Team A',
        away_team: 'Team B',
        home_score: 1,
        away_score: 1,  // 平局
        match_date: '2026-01-01',
        home_xg: '0.8',
        away_xg: '0.9',
        home_possession: '48',
        away_possession: '52',
        total_xg: '1.7',
        possession_diff: '-4'
    },
    {
        match_id: 'match_2',
        home_team: 'Team C',
        away_team: 'Team A',
        home_score: 0,
        away_score: 0,  // 平局
        match_date: '2026-01-05',
        home_xg: '0.5',
        away_xg: '0.6',
        home_possession: '50',
        away_possession: '50',
        total_xg: '1.1',
        possession_diff: '0'
    },
    {
        match_id: 'match_3',
        home_team: 'Team A',
        away_team: 'Team D',
        home_score: 2,
        away_score: 1,
        match_date: '2026-01-10',
        home_xg: '1.5',
        away_xg: '0.8',
        home_possession: '55',
        away_possession: '45',
        total_xg: '2.3',
        possession_diff: '10'
    },
    {
        match_id: 'match_4',
        home_team: 'Team E',
        away_team: 'Team A',
        home_score: 1,
        away_score: 1,  // 平局
        match_date: '2026-01-12',
        home_xg: '1.0',
        away_xg: '1.1',
        home_possession: '49',
        away_possession: '51',
        total_xg: '2.1',
        possession_diff: '-2'
    },
    {
        match_id: 'match_5',
        home_team: 'Team A',
        away_team: 'Team F',
        home_score: 0,
        away_score: 0,  // 平局
        match_date: '2026-01-14',
        home_xg: '0.6',
        away_xg: '0.5',
        home_possession: '47',
        away_possession: '53',
        total_xg: '1.1',
        possession_diff: '-6'
    }
];

function createMockDbPool(rows) {
    return {
        query: async () => ({ rows: rows || [] })
    };
}

function createExtractor(dbPool, config = {}) {
    const extractor = new DrawPropensityExtractor({
        dbPool,
        config: {
            rollingWindow: 10,
            minSamples: 5,
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

    assert.strictEqual(featureNames.length, 16); // 5+5+6
    assert(featureNames.includes('home_draw_rate'));
    assert(featureNames.includes('combined_draw_probability'));
    assert(featureNames.includes('match_stalemate_index'));
});

test('应该正确返回默认配置', () => {
    const extractor = createExtractor(createMockDbPool());
    const config = extractor.getDefaultConfig();

    assert.strictEqual(config.rollingWindow, 10);
    assert.strictEqual(config.minSamples, 5);
    assert.strictEqual(config.defaults.drawRate, 0.25);
});

// 平局率计算测试
test('应该正确计算历史平局率', async () => {
    const dbPool = createMockDbPool(mockDrawMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-20'
    });

    // Team A: 5场比赛4场平局 = 80%平局率
    assert.strictEqual(result.home_draw_rate, 0.8,
        `平局率应为0.8，实际为 ${result.home_draw_rate}`);
});

// 平局倾向指数测试
test('应该正确计算平局倾向指数', async () => {
    const dbPool = createMockDbPool(mockDrawMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-20'
    });

    // 平局倾向指数应该较高
    assert.ok(result.home_draw_tendency > 0.3,
        `平局倾向应>0.3，实际为 ${result.home_draw_tendency}`);
});

// 低进球率测试
test('应该正确计算低进球率', async () => {
    const dbPool = createMockDbPool(mockDrawMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-20'
    });

    // 5场比赛中有4场总进球<=2 (1-1, 0-0, 2-1不算, 1-1, 0-0)
    // = 80% 低进球率
    assert.ok(result.home_low_scoring_rate >= 0.6,
        `低进球率应>=0.6，实际为 ${result.home_low_scoring_rate}`);
});

// 对局平局指标测试
test('应该计算综合平局概率', async () => {
    const dbPool = createMockDbPool(mockDrawMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-20'
    });

    assert.ok(result.combined_draw_probability > 0.2,
        `综合平局概率应>0.2，实际为 ${result.combined_draw_probability}`);
    assert.ok(result.match_stalemate_index >= 0,
        `胶着指数应>=0，实际为 ${result.match_stalemate_index}`);
});

// 边界条件测试
test('历史数据不足时使用默认值', async () => {
    const dbPool = createMockDbPool(mockDrawMatches.slice(0, 4));
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-20'
    });

    assert.strictEqual(result.home_draw_rate, 0.25);
    assert.strictEqual(result.home_draw_tendency, 0.0);
});

// 字段完整性测试
test('所有特征字段都应该有值', async () => {
    const dbPool = createMockDbPool(mockDrawMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-20'
    });

    // 检查所有 16 个特征都有值
    for (const name of FEATURE_NAMES) {
        assert(result[name] !== undefined, `特征 ${name} 应该存在`);
        assert(typeof result[name] === 'number', `特征 ${name} 应该是数字类型`);
    }
});

// 识别"平局体质"球队
test('应该能识别平局体质球队', async () => {
    // 创建一个平局专家球队
    const drawSpecialistMatches = [
        { ...mockDrawMatches[0], home_score: 1, away_score: 1 },
        { ...mockDrawMatches[1], home_score: 0, away_score: 0 },
        { ...mockDrawMatches[2], home_score: 2, away_score: 2 },
        { ...mockDrawMatches[3], home_score: 1, away_score: 1 },
        { ...mockDrawMatches[4], home_score: 0, away_score: 0 }
    ];

    const dbPool = createMockDbPool(drawSpecialistMatches);
    const extractor = createExtractor(dbPool);

    const result = await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-20'
    });

    // 平局专家应该有极高的平局率
    assert.strictEqual(result.home_draw_rate, 1.0,
        `平局专家平局率应为1.0，实际为 ${result.home_draw_rate}`);
    assert.ok(result.combined_draw_probability > 0.5,
        `平局概率应>0.5，实际为 ${result.combined_draw_probability}`);
});

// 统计追踪
test('应该追踪执行统计', async () => {
    const dbPool = createMockDbPool(mockDrawMatches);
    const extractor = createExtractor(dbPool);

    await extractor.extract({
        match_id: 'test_1',
        home_team: 'Team A',
        away_team: 'Team B',
        match_date: '2026-01-20'
    });

    assert.strictEqual(extractor.stats.totalCalls, 1);
    assert.strictEqual(extractor.stats.successfulCalls, 1);
});

console.log('\n✅ DrawPropensityExtractor 测试套件已加载，共 10 个测试用例');
