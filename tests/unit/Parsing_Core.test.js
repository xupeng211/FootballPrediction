/**
 * Parsing_Core.test.js - 核心数据解析逻辑原子级测试
 * ================================================
 *
 * 测试范围:
 * - 基础字段验证 (Basic Fields)
 * - 赔率与指数 (Odds & Markets)
 * - 鲁棒性与防御 (Robustness)
 *
 * 运行: node --test tests/unit/Parsing_Core.test.js
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

// 被测模块
const {
    extractFromHtml,
    transformToApiFormat
} = require('../../src/parsers/fotmob/NextDataParser');

const { FotMobStrategy } = require('../../src/infrastructure/harvesters/strategies/FotMobStrategy');

// ============================================================================
// 测试数据工厂
// ============================================================================

/**
 * 创建标准测试数据对象
 */
function createMockMatchData(overrides = {}) {
    const base = {
        matchId: '12345',
        content: {
            lineup: {
                homeTeam: {
                    name: 'Manchester United',
                    formation: '4-3-3',
                    starters: [],
                    subs: []
                },
                awayTeam: {
                    name: 'Liverpool',
                    formation: '4-2-3-1',
                    starters: [],
                    subs: []
                }
            },
            stats: { possession: [55, 45] },
            odds: {
                '1x2': { home: 2.5, draw: 3.2, away: 2.8 },
                'asianHandicap': { line: -0.5, home: 1.9, away: 1.9 },
                'overUnder': { line: 2.5, over: 1.8, under: 2.0 }
            }
        },
        general: {
            matchStatus: 'Finished',
            homeScore: 2,
            awayScore: 1
        },
        header: {
            homeTeam: 'Manchester United',
            awayTeam: 'Liverpool',
            homeScore: 2,
            awayScore: 1
        }
    };
    return deepMerge(base, overrides);
}

/**
 * 深度合并对象
 */
function deepMerge(target, source) {
    const result = { ...target };
    for (const key in source) {
        if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
            result[key] = deepMerge(target[key] || {}, source[key]);
        } else {
            result[key] = source[key];
        }
    }
    return result;
}

// ============================================================================
// A. 基础字段验证 (Basic Fields)
// ============================================================================

describe('A. 基础字段验证', () => {

    it('A1: 验证解析主队名称 (home_team) 是否匹配', () => {
        const mockData = createMockMatchData();
        const strategy = new FotMobStrategy();

        const homeTeam = strategy.getField(mockData, 'content.lineup.homeTeam.name');

        assert.strictEqual(homeTeam, 'Manchester United', '主队名称应匹配');
    });

    it('A2: 验证解析客队名称 (away_team) 是否匹配', () => {
        const mockData = createMockMatchData();
        const strategy = new FotMobStrategy();

        const awayTeam = strategy.getField(mockData, 'content.lineup.awayTeam.name');

        assert.strictEqual(awayTeam, 'Liverpool', '客队名称应匹配');
    });

    it('A3: 验证比分 (score) 在 2-1 格式下的正确拆分', () => {
        const mockData = createMockMatchData();
        const strategy = new FotMobStrategy();

        const stats = strategy.extractMatchStats(mockData);

        assert.strictEqual(stats.score.home, 2, '主队比分应为 2');
        assert.strictEqual(stats.score.away, 1, '客队比分应为 1');
        assert.ok(stats.score.home > stats.score.away, '主队应获胜');
    });

    it('A4: 验证比赛状态 (match_status) 在 Finished 时的解析', () => {
        const mockData = createMockMatchData();
        const strategy = new FotMobStrategy();

        const status = strategy.getField(mockData, 'general.matchStatus');

        assert.strictEqual(status, 'Finished', '比赛状态应为 Finished');
    });
});

// ============================================================================
// B. 赔率与指数 (Odds & Markets)
// ============================================================================

describe('B. 赔率与指数', () => {

    it('B5: 验证 1x2（胜平负）初始赔率的提取', () => {
        const mockData = createMockMatchData();
        const strategy = new FotMobStrategy();

        const odds1x2 = strategy.getField(mockData, 'content.odds.1x2');

        assert.ok(odds1x2, '应存在 1x2 赔率');
        assert.strictEqual(odds1x2.home, 2.5, '主胜赔率应为 2.5');
        assert.strictEqual(odds1x2.draw, 3.2, '平局赔率应为 3.2');
        assert.strictEqual(odds1x2.away, 2.8, '客胜赔率应为 2.8');
    });

    it('B6: 验证 Asian Handicap（亚洲让球）字段的解析', () => {
        const mockData = createMockMatchData();
        const strategy = new FotMobStrategy();

        const asianHandicap = strategy.getField(mockData, 'content.odds.asianHandicap');

        assert.ok(asianHandicap, '应存在亚洲让球数据');
        assert.strictEqual(asianHandicap.line, -0.5, '让球线应为 -0.5');
        assert.strictEqual(asianHandicap.home, 1.9, '主队水位应为 1.9');
        assert.strictEqual(asianHandicap.away, 1.9, '客队水位应为 1.9');
    });

    it('B7: 验证 Over/Under（大小球）字段的解析', () => {
        const mockData = createMockMatchData();
        const strategy = new FotMobStrategy();

        const overUnder = strategy.getField(mockData, 'content.odds.overUnder');

        assert.ok(overUnder, '应存在大小球数据');
        assert.strictEqual(overUnder.line, 2.5, '大小球线应为 2.5');
        assert.strictEqual(overUnder.over, 1.8, '大球赔率应为 1.8');
        assert.strictEqual(overUnder.under, 2.0, '小球赔率应为 2.0');
    });
});

// ============================================================================
// C. 鲁棒性与防御 (Robustness)
// ============================================================================

describe('C. 鲁棒性与防御', () => {

    it('C8: 验证当 lineup 字段为 undefined 时，解析器是否返回空对象而非 Crash', () => {
        const mockData = createMockMatchData({
            content: { lineup: undefined }
        });
        const strategy = new FotMobStrategy();

        // 不应抛出异常
        let lineupInfo;
        try {
            lineupInfo = strategy.extractLineupInfo(mockData);
        } catch (e) {
            assert.fail(`应返回空对象而非抛出异常: ${e.message}`);
        }

        // 应返回默认结构
        assert.ok(lineupInfo, '应返回阵容对象');
        assert.ok(lineupInfo.home, '应包含主队字段');
        assert.ok(lineupInfo.away, '应包含客队字段');
        assert.deepStrictEqual(lineupInfo.home.starters, [], '主队首发应为空数组');
        assert.deepStrictEqual(lineupInfo.away.starters, [], '客队首发应为空数组');
    });

    it('C9: 验证当 JSON 字符串完全损坏时，DataParser 是否返回 null', () => {
        const corruptHtml = '<html><body>损坏的数据</body></html>';

        const result = extractFromHtml(corruptHtml);

        assert.strictEqual(result.success, false, '损坏数据应返回失败');
        assert.ok(result.error.includes('NO_NEXT_DATA'), '错误应提示找不到数据');
    });

    it('C10: 验证当 homeScore 字段缺失时，系统是否能给默认值 0', () => {
        const mockData = createMockMatchData({
            header: { homeScore: undefined, awayScore: 1 }
        });
        const strategy = new FotMobStrategy();

        const stats = strategy.extractMatchStats(mockData);

        // homeScore 缺失时应返回 undefined，但系统应能处理
        assert.strictEqual(stats.score.home, undefined, '缺失的 homeScore 保持 undefined');
        assert.strictEqual(stats.score.away, 1, 'awayScore 应保持原值');
    });

    it('C11: 验证 transformToApiFormat 对 null 输入的处理', () => {
        const result = transformToApiFormat(null, '12345');

        assert.strictEqual(result, null, 'null 输入应返回 null');
    });

    it('C12: 验证 transformToApiFormat 对缺少 pageProps 的处理', () => {
        const invalidData = { props: {} };
        const result = transformToApiFormat(invalidData, '12345');

        assert.strictEqual(result, null, '缺少 pageProps 应返回 null');
    });
});
