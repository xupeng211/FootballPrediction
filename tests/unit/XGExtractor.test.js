/**
 * XGExtractor 单元测试
 * ==============================================
 *
 * 测试 xG 数据提取的完整性和边界情况
 *
 * @module tests/unit/XGExtractor.test
 */

'use strict';

const { describe, it, beforeEach } = require('node:test');
const assert = require('node:assert');
const { extractXG, extractPossession, extractAllStats, validateXG } = require('../../src/parsers/fotmob/XGExtractor');

describe('XGExtractor', () => {
    describe('extractXG', () => {
        it('应正确提取 xG 数据 (方式1: 直接值)', () => {
            const apiData = {
                content: {
                    stats: {
                        Periods: {
                            All: {
                                stats: [{
                                    title: 'Expected Goals',
                                    stats: [2.5, 1.3]
                                }]
                            }
                        }
                    }
                }
            };

            const result = extractXG(apiData);
            assert.strictEqual(result.xg_home, 2.5);
            assert.strictEqual(result.xg_away, 1.3);
            assert.strictEqual(result.hasXG, true);
        });

        it('应正确提取 xG 数据 (方式2: 嵌套结构)', () => {
            const apiData = {
                content: {
                    stats: {
                        Periods: {
                            All: {
                                stats: [{
                                    title: 'Top stats',
                                    stats: [{
                                        key: 'expected_goals',
                                        stats: [1.8, 0.9]
                                    }]
                                }]
                            }
                        }
                    }
                }
            };

            const result = extractXG(apiData);
            assert.strictEqual(result.xg_home, 1.8);
            assert.strictEqual(result.xg_away, 0.9);
            assert.strictEqual(result.hasXG, true);
        });

        it('应处理空数据', () => {
            const result = extractXG(null);
            assert.strictEqual(result.xg_home, null);
            assert.strictEqual(result.xg_away, null);
            assert.strictEqual(result.hasXG, false);
        });

        it('应处理缺少 stats 的数据', () => {
            const apiData = { content: {} };
            const result = extractXG(apiData);
            assert.strictEqual(result.hasXG, false);
        });

        it('应处理字符串数字', () => {
            const apiData = {
                content: {
                    stats: {
                        Periods: {
                            All: {
                                stats: [{
                                    title: 'xG',
                                    stats: ['2.5', '1.3']
                                }]
                            }
                        }
                    }
                }
            };

            const result = extractXG(apiData);
            assert.strictEqual(result.xg_home, 2.5);
            assert.strictEqual(result.xg_away, 1.3);
        });
    });

    describe('extractPossession', () => {
        it('应正确提取控球率 (百分比格式)', () => {
            const apiData = {
                content: {
                    stats: {
                        Periods: {
                            All: {
                                stats: [{
                                    title: 'Ball possession',
                                    stats: [{
                                        key: 'possession',
                                        stats: ['65%', '35%']
                                    }]
                                }]
                            }
                        }
                    }
                }
            };

            const result = extractPossession(apiData);
            assert.strictEqual(result.possession_home, 0.65);
            assert.strictEqual(result.possession_away, 0.35);
            assert.strictEqual(result.hasPossession, true);
        });

        it('应正确提取控球率 (小数格式)', () => {
            const apiData = {
                content: {
                    stats: {
                        Periods: {
                            All: {
                                stats: [{
                                    title: 'Possession',
                                    stats: [{
                                        key: 'ball_possession',
                                        stats: [0.55, 0.45]
                                    }]
                                }]
                            }
                        }
                    }
                }
            };

            const result = extractPossession(apiData);
            assert.strictEqual(result.possession_home, 0.55);
            assert.strictEqual(result.possession_away, 0.45);
        });

        it('应处理空数据', () => {
            const result = extractPossession(null);
            assert.strictEqual(result.hasPossession, false);
        });
    });

    describe('extractAllStats', () => {
        it('应同时提取 xG 和控球率', () => {
            const apiData = {
                content: {
                    stats: {
                        Periods: {
                            All: {
                                stats: [
                                    {
                                        title: 'Expected Goals',
                                        stats: [2.0, 1.0]
                                    },
                                    {
                                        title: 'Ball possession',
                                        stats: [{
                                            key: 'possession',
                                            stats: ['60%', '40%']
                                        }]
                                    }
                                ]
                            }
                        }
                    }
                }
            };

            const result = extractAllStats(apiData);
            assert.strictEqual(result.xg_home, 2.0);
            assert.strictEqual(result.xg_away, 1.0);
            assert.strictEqual(result.possession_home, 0.6);
            assert.strictEqual(result.possession_away, 0.4);
            assert.strictEqual(result.hasAnyStats, true);
        });
    });

    describe('validateXG', () => {
        it('应验证有效的 xG 数据', () => {
            const result = validateXG(2.5, 1.3);
            assert.strictEqual(result.valid, true);
            assert.deepStrictEqual(result.warnings, []);
        });

        it('应检测负数 xG', () => {
            const result = validateXG(-1, 0.5);
            assert.strictEqual(result.valid, false);
            assert.ok(result.warnings.some(w => w.includes('负数')));
        });

        it('应检测异常高的 xG', () => {
            const result = validateXG(15, 1);
            assert.strictEqual(result.valid, false);
            assert.ok(result.warnings.some(w => w.includes('异常高')));
        });

        it('应处理 null 值', () => {
            const result = validateXG(null, null);
            assert.strictEqual(result.valid, true);
            assert.ok(result.warnings.some(w => w.includes('缺失')));
        });
    });
});
