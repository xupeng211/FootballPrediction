/**
 * GoldenFeatureExtractor 单元测试 - V3.0-PRO
 * ==========================================
 *
 * 测试覆盖：
 * 1. 标准输入：验证身价单位转换（× 1e6）
 * 2. 残缺输入：验证返回空特征
 * 3. 四层回退逻辑：验证优先级
 *
 * 运行方式:
 *   node tests/extractors/GoldenFeatureExtractor.test.js
 *   npm test tests/extractors/GoldenFeatureExtractor.test.js
 *
 * @module tests/extractors/GoldenFeatureExtractor.test
 * @version V3.0.0-PRO
 */

'use strict';

const assert = require('assert');

// 动态导入，支持不同环境
let GoldenFeatureExtractor;
try {
    GoldenFeatureExtractor = require('../../src/feature_engine/extractors/GoldenFeatureExtractor');
} catch (e) {
    // 尝试备用路径
    try {
        GoldenFeatureExtractor = require('../../../src/feature_engine/extractors/GoldenFeatureExtractor');
    } catch (e2) {
        console.error('无法导入 GoldenFeatureExtractor:', e.message);
        process.exit(1);
    }
}

const {
    extractGoldenFeatures,
    extractTeamFeatures,
    extractMarketValueFeatures,
    createEmptyFeatures,
    DEFAULT_CONFIG
} = GoldenFeatureExtractor;

// ============================================================================
// 测试数据 Fixtures
// ============================================================================

/**
 * 标准 FotMob JSON 数据（完整版）
 */
const STANDARD_FOTMOB_DATA = {
    content: {
        lineup: {
            homeTeam: {
                totalStarterMarketValue: 850.5,  // 百万欧元
                starters: [
                    { name: 'Player 1', marketValue: 120, age: 25, performance: { rating: 7.2 } },
                    { name: 'Player 2', marketValue: 80, age: 28, performance: { rating: 6.8 } },
                    { name: 'Player 3', marketValue: 65, age: 23, performance: { rating: 7.0 } }
                ],
                subs: [
                    { name: 'Sub 1', marketValue: 30, age: 21 }
                ],
                unavailable: [
                    { name: 'Injured 1', unavailability: { type: 'injury' } }
                ]
            },
            awayTeam: {
                totalStarterMarketValue: 420.3,  // 百万欧元
                starters: [
                    { name: 'Player A', marketValue: 90, age: 27, performance: { rating: 6.5 } },
                    { name: 'Player B', marketValue: 55, age: 24, performance: { rating: 6.2 } }
                ],
                unavailable: [
                    { name: 'Injured A', unavailability: { type: 'suspension' } },
                    { name: 'Injured B', unavailability: { type: 'injury' } }
                ]
            }
        }
    },
    header: {
        homeMarketValue: 850.5,
        awayMarketValue: 420.3
    }
};

/**
 * 残缺数据 - 只有 starters 数组
 */
const PARTIAL_DATA_STARTERS_ONLY = {
    content: {
        lineup: {
            homeTeam: {
                starters: [
                    { name: 'Player 1', marketValue: 100 },
                    { name: 'Player 2', marketValue: 50 }
                ]
            },
            awayTeam: {
                starters: [
                    { name: 'Player A', marketValue: 80 }
                ]
            }
        }
    }
};

/**
 * 残缺数据 - 只有 subs 数组
 */
const PARTIAL_DATA_SUBS_ONLY = {
    content: {
        lineup: {
            homeTeam: {
                subs: [
                    { name: 'Sub 1', marketValue: 30 },
                    { name: 'Sub 2', marketValue: 20 }
                ]
            },
            awayTeam: {
                subs: [
                    { name: 'Sub A', marketValue: 25 }
                ]
            }
        }
    }
};

/**
 * 残缺数据 - 需要深度搜索
 */
const PARTIAL_DATA_DEEP_SEARCH = {
    content: {
        table: {
            all: [
                { name: 'Player 1', marketValue: 50, isHome: true },
                { name: 'Player 2', marketValue: 40, isHome: true },
                { name: 'Player A', marketValue: 60, isHome: false }
            ]
        },
        players: [
            { marketValue: 100, teamRole: 'home' },
            { marketValue: 80, teamRole: 'away' }
        ]
    }
};

/**
 * 完全无效的数据
 */
const INVALID_DATA = {
    content: {}
};

/**
 * null 数据
 */
const NULL_DATA = null;

// ============================================================================
// 测试套件
// ============================================================================

describe('GoldenFeatureExtractor V3.0-PRO', function() {

    // ========================================================================
    // 测试 1: 标准输入 - 身价单位转换验证
    // ========================================================================
    describe('Case 1: 标准输入 - 身价单位转换', function() {

        it('应该正确将百万欧元转换为欧元（× 1e6）', function() {
            const features = extractGoldenFeatures(STANDARD_FOTMOB_DATA);

            // 主队身价: 850.5M × 1e6 = 850,500,000 欧元
            assert.strictEqual(
                features.home_market_value_total,
                850500000,
                `主队身价应为 850,500,000 欧元，实际为 ${features.home_market_value_total}`
            );

            // 客队身价: 420.3M × 1e6 = 420,300,000 欧元
            assert.strictEqual(
                features.away_market_value_total,
                420300000,
                `客队身价应为 420,300,000 欧元，实际为 ${features.away_market_value_total}`
            );
        });

        it('应该正确计算身价差', function() {
            const features = extractGoldenFeatures(STANDARD_FOTMOB_DATA);

            // 身价差: 850,500,000 - 420,300,000 = 430,200,000
            assert.strictEqual(
                features.market_value_gap,
                430200000,
                `身价差应为 430,200,000 欧元，实际为 ${features.market_value_gap}`
            );
        });

        it('应该标记数据来源为 totalStarterMarketValue', function() {
            const features = extractGoldenFeatures(STANDARD_FOTMOB_DATA);

            assert.strictEqual(
                features.home_market_value_source,
                'totalStarterMarketValue',
                `主队数据来源应为 totalStarterMarketValue，实际为 ${features.home_market_value_source}`
            );

            assert.strictEqual(
                features.away_market_value_source,
                'totalStarterMarketValue',
                `客队数据来源应为 totalStarterMarketValue，实际为 ${features.away_market_value_source}`
            );
        });

        it('应该正确提取伤病数据', function() {
            const features = extractGoldenFeatures(STANDARD_FOTMOB_DATA);

            assert.strictEqual(features.home_injury_count, 1, '主队应有 1 名伤员');
            assert.strictEqual(features.away_injury_count, 2, '客队应有 2 名伤员');
            assert.strictEqual(features.injury_count_gap, -1, '伤病差应为 -1');
        });

        it('应该包含元数据', function() {
            const features = extractGoldenFeatures(STANDARD_FOTMOB_DATA);

            assert.ok(features._extractedAt, '应包含 _extractedAt');
            assert.strictEqual(features._version, 'V3.0.0-PRO', '版本应为 V3.0.0-PRO');
            assert.strictEqual(features._source, 'FotMob', '数据源应为 FotMob');
        });
    });

    // ========================================================================
    // 测试 2: 残缺输入 - 返回空特征验证
    // ========================================================================
    describe('Case 2: 残缺输入 - 空特征返回', function() {

        it('null 输入应返回空特征', function() {
            const features = extractGoldenFeatures(NULL_DATA);

            assert.strictEqual(features.home_market_value_total, 0, 'null 输入应返回 0');
            assert.strictEqual(features.away_market_value_total, 0, 'null 输入应返回 0');
            assert.ok(features._error, '应包含错误信息');
        });

        it('空对象输入应返回空特征', function() {
            const features = extractGoldenFeatures({});

            assert.strictEqual(features.home_market_value_total, 0);
            assert.strictEqual(features.away_market_value_total, 0);
        });

        it('无效内容输入应返回空特征', function() {
            const features = extractGoldenFeatures(INVALID_DATA);

            assert.strictEqual(features.home_market_value_total, 0);
            assert.strictEqual(features.away_market_value_total, 0);
            assert.strictEqual(features.home_market_value_source, 'not_found');
        });

        it('createEmptyFeatures 应返回正确结构', function() {
            const emptyFeatures = createEmptyFeatures('测试原因');

            assert.strictEqual(emptyFeatures.home_market_value_total, 0);
            assert.strictEqual(emptyFeatures.away_market_value_total, 0);
            assert.strictEqual(emptyFeatures.market_value_gap, 0);
            assert.strictEqual(emptyFeatures._error, '测试原因');
        });
    });

    // ========================================================================
    // 测试 3: 四层回退逻辑 - 优先级验证
    // ========================================================================
    describe('Case 3: 四层回退逻辑 - 优先级验证', function() {

        it('策略 1 (totalStarterMarketValue) 应优先于策略 2 (starters)', function() {
            // 当同时存在 totalStarterMarketValue 和 starters 时，应使用前者
            const features = extractGoldenFeatures(STANDARD_FOTMOB_DATA);

            assert.strictEqual(
                features.home_market_value_source,
                'totalStarterMarketValue',
                '应优先使用 totalStarterMarketValue'
            );
        });

        it('策略 2 (starters) 应在无 totalStarterMarketValue 时生效', function() {
            const features = extractGoldenFeatures(PARTIAL_DATA_STARTERS_ONLY);

            // 主队: 100 + 50 = 150M × 1e6 = 150,000,000
            assert.strictEqual(
                features.home_market_value_total,
                150000000,
                `starters 求和应为 150,000,000，实际为 ${features.home_market_value_total}`
            );
            assert.strictEqual(
                features.home_market_value_source,
                'starters',
                `数据来源应为 starters，实际为 ${features.home_market_value_source}`
            );
        });

        it('策略 3 (subs) 应在无 starters 时生效', function() {
            const features = extractGoldenFeatures(PARTIAL_DATA_SUBS_ONLY);

            // 主队: 30 + 20 = 50M × 1e6 = 50,000,000
            assert.strictEqual(
                features.home_market_value_total,
                50000000,
                `subs 求和应为 50,000,000，实际为 ${features.home_market_value_total}`
            );
            assert.strictEqual(
                features.home_market_value_source,
                'subs',
                `数据来源应为 subs，实际为 ${features.home_market_value_source}`
            );
        });

        it('策略 4 (deep_search) 应在无其他来源时生效', function() {
            const features = extractGoldenFeatures(PARTIAL_DATA_DEEP_SEARCH);

            // 应该能从 content.table.all 或 content.players 中提取
            assert.ok(
                features.home_market_value_total > 0 || features.home_market_value_source === 'deep_search',
                `应该通过深度搜索找到身价，实际为 ${features.home_market_value_source}: ${features.home_market_value_total}`
            );
        });

        it('所有策略失败时应标记为 not_found', function() {
            const features = extractGoldenFeatures(INVALID_DATA);

            assert.strictEqual(
                features.home_market_value_source,
                'not_found',
                '无数据时应标记为 not_found'
            );
        });
    });

    // ========================================================================
    // 测试 4: 边界情况
    // ========================================================================
    describe('Case 4: 边界情况', function() {

        it('应正确处理 marketValue 为 0 的球员', function() {
            const data = {
                content: {
                    lineup: {
                        homeTeam: {
                            starters: [
                                { name: 'Player 1', marketValue: 100 },
                                { name: 'Player 2', marketValue: 0 },  // 无效
                                { name: 'Player 3', marketValue: 50 }
                            ]
                        },
                        awayTeam: {
                            starters: []
                        }
                    }
                }
            };

            const features = extractGoldenFeatures(data);

            // 只应计算有效值: 100 + 50 = 150M
            assert.strictEqual(features.home_market_value_total, 150000000);
        });

        it('应正确处理负数 marketValue（视为无效）', function() {
            const data = {
                content: {
                    lineup: {
                        homeTeam: {
                            starters: [
                                { name: 'Player 1', marketValue: -10 }  // 无效
                            ]
                        },
                        awayTeam: {
                            starters: []
                        }
                    }
                }
            };

            const features = extractGoldenFeatures(data);

            assert.strictEqual(features.home_market_value_total, 0);
            assert.strictEqual(features.home_market_value_source, 'not_found');
        });

        it('应正确处理超大身价值', function() {
            const data = {
                content: {
                    lineup: {
                        homeTeam: {
                            totalStarterMarketValue: 1500  // 15 亿欧元
                        },
                        awayTeam: {
                            totalStarterMarketValue: 800
                        }
                    }
                }
            };

            const features = extractGoldenFeatures(data);

            // 1500M × 1e6 = 1,500,000,000
            assert.strictEqual(features.home_market_value_total, 1500000000);
            assert.strictEqual(features.away_market_value_total, 800000000);
        });
    });

    // ========================================================================
    // 测试 5: 纯函数特性
    // ========================================================================
    describe('Case 5: 纯函数特性', function() {

        it('相同输入应产生相同输出（幂等性）', function() {
            const features1 = extractGoldenFeatures(STANDARD_FOTMOB_DATA);
            const features2 = extractGoldenFeatures(STANDARD_FOTMOB_DATA);

            // 排除时间戳后比较
            delete features1._extractedAt;
            delete features2._extractedAt;

            assert.deepStrictEqual(features1, features2, '相同输入应产生相同输出');
        });

        it('不应修改输入对象（无副作用）', function() {
            const originalData = JSON.parse(JSON.stringify(STANDARD_FOTMOB_DATA));
            const originalJson = JSON.stringify(originalData);

            extractGoldenFeatures(originalData);

            assert.strictEqual(
                JSON.stringify(originalData),
                originalJson,
                '输入对象不应被修改'
            );
        });
    });
});

// ============================================================================
// 运行测试
// ============================================================================

// 如果直接运行此文件
if (require.main === module) {
    console.log('运行 GoldenFeatureExtractor 测试...\n');

    // 简单的测试运行器
    let passed = 0;
    let failed = 0;

    const runTest = (name, fn) => {
        try {
            fn();
            console.log(`✅ ${name}`);
            passed++;
        } catch (error) {
            console.log(`❌ ${name}`);
            console.log(`   Error: ${error.message}`);
            failed++;
        }
    };

    // 运行关键测试
    runTest('Case 1.1: 身价单位转换', () => {
        const features = extractGoldenFeatures(STANDARD_FOTMOB_DATA);
        assert.strictEqual(features.home_market_value_total, 850500000);
        assert.strictEqual(features.away_market_value_total, 420300000);
    });

    runTest('Case 1.2: 身价差计算', () => {
        const features = extractGoldenFeatures(STANDARD_FOTMOB_DATA);
        assert.strictEqual(features.market_value_gap, 430200000);
    });

    runTest('Case 2.1: null 输入处理', () => {
        const features = extractGoldenFeatures(null);
        assert.strictEqual(features.home_market_value_total, 0);
        assert.ok(features._error);
    });

    runTest('Case 3.1: 策略优先级 - totalStarterMarketValue', () => {
        const features = extractGoldenFeatures(STANDARD_FOTMOB_DATA);
        assert.strictEqual(features.home_market_value_source, 'totalStarterMarketValue');
    });

    runTest('Case 3.2: 策略优先级 - starters 回退', () => {
        const features = extractGoldenFeatures(PARTIAL_DATA_STARTERS_ONLY);
        assert.strictEqual(features.home_market_value_source, 'starters');
        assert.strictEqual(features.home_market_value_total, 150000000);
    });

    runTest('Case 5.1: 幂等性', () => {
        const f1 = extractGoldenFeatures(STANDARD_FOTMOB_DATA);
        const f2 = extractGoldenFeatures(STANDARD_FOTMOB_DATA);
        assert.strictEqual(f1.home_market_value_total, f2.home_market_value_total);
    });

    console.log(`\n结果: ${passed} 通过, ${failed} 失败`);
    process.exit(failed > 0 ? 1 : 0);
}
