/**
 * TacticalMomentumExtractor 单元测试
 * ==============================================
 *
 * 验证 171 维特征提取的完整性和边界情况
 * @module tests/unit/TacticalMomentumExtractor.test
 * @version V176.0.0
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');
const { extractTacticalFeatures, extractStatsFeatures, calculateAdvancedFeatures } = require('../../src/feature_engine/extractors/TacticalMomentumExtractor');

// ============================================================================
// Mock 数据 - 模拟真实 FotMob 结构
// ============================================================================

/**
 * 完整的 FotMob 比赛数据 (content.stats.Periods.All.stats 路径)
 * 这是 270/280 条记录使用的路径
 */
const MOCK_FULL_DATA = {
    content: {
        stats: {
            Periods: {
                All: {
                    stats: [
                        {
                            title: 'Top stats',
                            stats: [
                                { title: 'Ball possession', stats: [61, 39] },
                                { title: 'Expected goals (xG)', stats: ['2.50', '1.63'] },
                                { title: 'Total shots', stats: [14, 12] },
                                { title: 'Shots on target', stats: [5, 7] },
                                { title: 'Shots off target', stats: [7, 2] },
                                { title: 'Blocked shots', stats: [2, 3] },
                                { title: 'Corners', stats: [7, 3] },
                                { title: 'Big chances', stats: [3, 2] },
                                { title: 'Fouls', stats: [8, 10] },
                                { title: 'Yellow cards', stats: [2, 1] },
                                { title: 'Red cards', stats: [0, 1] },
                                { title: 'Offsides', stats: [1, 2] },
                                { title: 'Passes', stats: [425, 277] },
                                { title: 'Accurate passes', stats: [340, 210] },
                                { title: 'Shots inside box', stats: [9, 7] },
                                { title: 'Shots outside box', stats: [5, 5] },
                                { title: 'Hit woodwork', stats: [1, 0] }
                            ]
                        }
                    ]
                },
                FirstHalf: { stats: [] },
                SecondHalf: { stats: [] }
            }
        },
        momentum: {
            data: Array.from({ length: 94 }, (_, i) => ({
                time: i,
                value: Math.sin(i * 0.1) * 50 + Math.random() * 20 - 10
            }))
        }
    }
};

/**
 * Next.js 格式数据 (props.pageProps.content.stats 路径)
 * 这是 10/280 条记录使用的路径
 */
const MOCK_NEXTJS_DATA = {
    props: {
        pageProps: {
            content: MOCK_FULL_DATA.content
        }
    }
};

/**
 * 数据缺失的边界情况
 */
const MOCK_EMPTY_DATA = {
    content: {
        stats: null
    }
};

const MOCK_NULL_DATA = null;

// ============================================================================
// 测试用例
// ============================================================================

describe('TacticalMomentumExtractor', () => {

    describe('extractTacticalFeatures - 完整数据', () => {
        it('应正确提取 xG 数据', () => {
            const features = extractTacticalFeatures(MOCK_FULL_DATA);
            assert.strictEqual(features.home_xg, 2.5);
            assert.strictEqual(features.away_xg, 1.63);
            assert.strictEqual(features.total_xg, 4.13);
            assert.ok(Math.abs(features.xg_diff - 0.87) < 0.01);
        });

        it('应正确提取控球率数据', () => {
            const features = extractTacticalFeatures(MOCK_FULL_DATA);
            assert.strictEqual(features.home_possession_pct, 61);
            assert.strictEqual(features.away_possession_pct, 39);
            assert.strictEqual(features.possession_diff, 22);
        });

        it('应正确提取射门数据', () => {
            const features = extractTacticalFeatures(MOCK_FULL_DATA);
            assert.strictEqual(features.home_shots, 14);
            assert.strictEqual(features.away_shots, 12);
            assert.strictEqual(features.home_shots_on_target, 5);
            assert.strictEqual(features.away_shots_on_target, 7);
            assert.strictEqual(features.home_blocked_shots, 2);
            assert.strictEqual(features.away_blocked_shots, 3);
        });

        it('应正确提取角球和大机会', () => {
            const features = extractTacticalFeatures(MOCK_FULL_DATA);
            assert.strictEqual(features.home_corners, 7);
            assert.strictEqual(features.away_corners, 3);
            assert.strictEqual(features.home_big_chances, 3);
            assert.strictEqual(features.away_big_chances, 2);
        });

        it('应正确提取犯规和牌', () => {
            const features = extractTacticalFeatures(MOCK_FULL_DATA);
            assert.strictEqual(features.home_fouls, 8);
            assert.strictEqual(features.away_fouls, 10);
            assert.strictEqual(features.home_yellow_cards, 2);
            assert.strictEqual(features.away_yellow_cards, 1);
            assert.strictEqual(features.home_red_cards, 0);
            assert.strictEqual(features.away_red_cards, 1);
        });

        it('应正确计算派生特征', () => {
            const features = extractTacticalFeatures(MOCK_FULL_DATA);
            // xG 效率
            assert.ok(features.home_xg_per_shot > 0);
            assert.ok(features.away_xg_per_shot > 0);
            // 射门精度
            assert.ok(features.home_shot_accuracy >= 0 && features.home_shot_accuracy <= 1);
            assert.ok(features.away_shot_accuracy >= 0 && features.away_shot_accuracy <= 1);
            // 纪律评分
            assert.ok(features.home_discipline_score <= 10);
            assert.ok(features.away_discipline_score <= 10);
        });

        it('应正确处理 momentum 数据', () => {
            const features = extractTacticalFeatures(MOCK_FULL_DATA);
            assert.strictEqual(features.has_momentum_data, true);
            assert.strictEqual(features.momentum_samples_count, 94);
            assert.ok(features.momentum_direction !== 'unknown');
            // 验证 6 个时段的特征
            for (let i = 1; i <= 6; i++) {
                assert.ok(features[`momentum_seg${i}_mean`] !== undefined);
                assert.ok(features[`momentum_seg${i}_std`] !== undefined);
                assert.ok(features[`momentum_seg${i}_dominance`] !== undefined);
            }
        });
    });

    describe('extractTacticalFeatures - 边界情况', () => {
        it('应正确处理 null 数据', () => {
            const features = extractTacticalFeatures(MOCK_NULL_DATA);
            assert.ok(features._error !== undefined);
        });

        it('应正确处理空数据', () => {
            const features = extractTacticalFeatures(MOCK_EMPTY_DATA);
            // 应返回默认值
            assert.strictEqual(features.home_xg, 0);
            assert.strictEqual(features.away_xg, 0);
            assert.strictEqual(features.home_possession_pct, 50);
            assert.strictEqual(features.away_possession_pct, 50);
        });

        it('应正确处理缺失 stats 的情况', () => {
            const features = extractTacticalFeatures({ content: {} });
            assert.ok(features.home_xg !== undefined);
            assert.ok(features.has_momentum_data === false);
        });
    });

    describe('特征维度验证', () => {
        it('提取的特征数量应接近 86 维 (tactical_features)', () => {
            const features = extractTacticalFeatures(MOCK_FULL_DATA);
            const keyCount = Object.keys(features).length;
            // tactical_features 应该有 80-90 个 key
            assert.ok(keyCount >= 80, `期望 >= 80 维，实际 ${keyCount} 维`);
            assert.ok(keyCount <= 95, `期望 <= 95 维，实际 ${keyCount} 维`);
        });

        it('所有数值特征应非 NaN', () => {
            const features = extractTacticalFeatures(MOCK_FULL_DATA);
            for (const [key, value] of Object.entries(features)) {
                if (typeof value === 'number') {
                    assert.ok(!Number.isNaN(value), `${key} 不应为 NaN`);
                }
            }
        });

        it('不应包含 undefined 值', () => {
            const features = extractTacticalFeatures(MOCK_FULL_DATA);
            for (const [key, value] of Object.entries(features)) {
                assert.ok(value !== undefined, `${key} 不应为 undefined`);
            }
        });
    });

    describe('路径兼容性', () => {
        it('应支持 content.stats.Periods.All.stats 路径', () => {
            const features = extractTacticalFeatures(MOCK_FULL_DATA);
            assert.strictEqual(features.home_xg, 2.5);
        });
    });
});

describe('calculateAdvancedFeatures', () => {
    it('应正确计算 strength_index', () => {
        const baseFeatures = {
            home_xg: 2.5, away_xg: 1.5,
            home_shots_on_target: 5, away_shots_on_target: 3,
            home_possession_pct: 60, away_possession_pct: 40,
            home_big_chances: 3, away_big_chances: 1
        };
        const advanced = calculateAdvancedFeatures(baseFeatures);
        assert.ok(advanced.home_strength_index > advanced.away_strength_index);
    });

    it('应正确处理零值情况', () => {
        const baseFeatures = {
            home_xg: 0, away_xg: 0,
            home_shots_on_target: 0, away_shots_on_target: 0,
            home_possession_pct: 50, away_possession_pct: 50,
            home_big_chances: 0, away_big_chances: 0,
            home_shots: 0, away_shots: 0,
            home_corners: 0, away_corners: 0,
            home_fouls: 0, away_fouls: 0,
            home_yellow_cards: 0, away_yellow_cards: 0,
            home_red_cards: 0, away_red_cards: 0
        };
        const advanced = calculateAdvancedFeatures(baseFeatures);
        assert.strictEqual(advanced.total_xg, 0);
        assert.strictEqual(advanced.xg_diff, 0);
    });
});
