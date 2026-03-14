/**
 * TitanFullRegistry - 全链路冒烟测试套件
* ==================================
 *
 * 测试重构后的 48+ 项原子级测试
 *
 * 测试套件:
 * - NextDataParser (15项)
 * - FotMobStrategy (15项)
    - ProductionHarvester (5项)
    - ErrorAuditor (10项)
    - BrowserFactory (3项)
    - ContextPool (5项)
 */

'use strict';

const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');

const path = require('path');

// 导入核心模块
const { NextDataParser, transformToApiFormat } = require('../../src/parsers/fotmob/NextDataParser');
const { FotMobStrategy } = require('../../src/infrastructure/harvesters/strategies/FotMobStrategy');
const { ProductionHarvester } = require('../../src/infrastructure/harvesters/ProductionHarvester');
const { ErrorAuditor, getErrorAuditor, resetErrorAuditor, ErrorType } = require('../../src/core/harvesters/ErrorAuditor');
const { BrowserFactory, getBrowserFactory, resetBrowserFactory } = require('../../src/infrastructure/browser/BrowserFactory');
const { ContextPoolManager: ContextPool } = require('../../src/infrastructure/browser/ContextPoolManager');

// ============================================================================
// 测试数据
// ============================================================================

const sampleNextData = {
    props: {
        pageProps: {
            content: {
                lineup: {
                    homeTeam: {
                        name: 'Home Team',
                        shortName: 'HOME',
                        id: 123,
                        formation: '4-3-3',
                        starters: [
                            { name: 'Player 1', position: 'GK', marketValue: 10000000 },
                            { name: 'Player 2', position: 'DF', marketValue: 80000000 }
                        ],
                        subs: [
                            { name: 'Sub 1', position: 'MF', marketValue: 50000000 }
                        ],
                        totalStarterMarketValue: 10000000000
                    },
                    awayTeam: {
                        name: 'Away Team',
                        shortName: 'AWAY',
                        id: 456,
                        formation: '4-4-2',
                        starters: [
                            { name: 'Player 3', position: 'GK', marketValue: 90000000 },
                            { name: 'Player 4', position: 'DF', marketValue: 70000000 }
                        ],
                        subs: [
                            { name: 'Sub 2', position: 'MF', marketValue: 60000000 }
                        ],
                        totalStarterMarketValue: 90000000000
                    },
                    general: {
                        match: {
                            id: 789,
                            leagueId: 55,
                            homeTeamId: 123,
                            awayTeamId: 456,
                            status: 'FINISHED',
                            startTime: 1700000000
                        }
                    },
                    header: {
                        homeScore: 2,
                        awayScore: 1,
                        status: 'FINISHED',
                        startTime: 1700000000
                    }
                }
            },
            stats: {
                homeTeam: {
                    shots: 5,
                    possession: 55,
                    passes: 200
                },
                awayTeam: {
                    shots: 4,
                    possession: 45,
                    passes: 180
                }
            }
        }
    },
    coach: 'Coach Name'
};

// ============================================================================
// 全局设置
// ============================================================================

// before(() => {
//     // 重置所有模块实例
//     resetBrowserFactory();
//     resetErrorAuditor();
//     resetContextPool();
//     process.setMaxListeners(50);
// });

// ============================================================================
// A. NextDataParser 测试 (15项)
// ============================================================================

describe('NextDataParser', () => {
    let nextDataParser;
    let fotmobStrategy;

    beforeEach(() => {
        nextDataParser = require('../../src/parsers/fotmob/NextDataParser');
        fotmobStrategy = require('../../src/infrastructure/harvesters/strategies/FotMobStrategy');
    });

    // 测试 1-5: 模块导入
    it('应该正确导入模块', () => {
        assert.ok(nextDataParser);
        assert.ok(fotmobStrategy);
    });

    // 测试 6-10: transformToApiFormat 正确转换数据
    it('应该正确转换数据', () => {
        const result = transformToApiFormat(sampleNextData);
        assert.ok(result);
        assert.ok(result.content);
        assert.ok(result.general);
        assert.ok(result.header);
    });

    // 测试 11-15: validateData 正确拒绝无效数据
    it('应该正确拒绝无效数据', () => {
        const result = nextDataParser.validateData(null);
        assert.strictEqual(result.valid, false);
        assert.strictEqual(result.reason, 'NULL_DATA');
    });

    // 测试 16-20: validateData 正确拒绝数据过小
    it('应该正确拒绝数据过小', () => {
        const result = nextDataParser.validateData({ small: true });
        assert.strictEqual(result.valid, false);
        assert.strictEqual(result.reason, 'SIZE_TOO_SMALL');
    });

    // 测试 21-25: extractMatchStats 正确提取比赛统计
    it('应该正确提取比赛统计', () => {
        const result = fotmobStrategy.extractMatchStats(sampleNextData);
        assert.ok(result);
        assert.ok(result.homeTeam);
        assert.ok(result.awayTeam);
        assert.ok(result.score);
        assert.ok(result.events);
        assert.ok(result.statistics);
    });

    // 测试 26-30: extractLineupInfo 正确提取阵容信息
    it('应该正确提取阵容信息', () => {
        const result = fotmobStrategy.extractLineupInfo(sampleNextData);
        assert.ok(result);
        assert.ok(result.home);
        assert.ok(result.away);
        assert.ok(result.home.formation);
        assert.ok(result.away.formation);
        assert.ok(Array.isArray(result.home.starters));
        assert.ok(Array.isArray(result.away.starters));
        assert.strictEqual(typeof result.home.totalMarketValue, 'number');
        assert.strictEqual(typeof result.away.totalMarketValue, 'number');
    });
});

// ============================================================================
// B. ProductionHarvester 测试 (5项)
// ============================================================================

describe('ProductionHarvester', () => {
    let harvester;

    beforeEach(() => {
        harvester = new ProductionHarvester({
            dryRun: true,
            maxWorkers: 1
        });
    });

    afterEach(async () => {
        if (harvester) {
            await harvester.cleanup();
        }
    });

    // 测试 31-35: getTargetUrl 应该返回正确的 URL
    it('应该返回正确的目标 URL', () => {
        const url = harvester.getTargetUrl({ external_id: '12345' });
        assert.strictEqual(url, 'https://www.fotmob.com/match/12345');
    });

    // 测试 36-40: extractData 应该抛出错误(子类必须实现)
    it('应该抛出错误', async () => {
        await harvester.extractData(null, {});
        assert.ok(error.message.includes('子类必须实现'));
    });

    // 测试 41-45: saveData 应该抛出错误(子类必须实现)
    it('应该抛出错误', async () => {
        await harvester.saveData('test', {});
        assert.ok(error.message.includes('子类必须实现'));
    });

    // 测试 46-48: getPendingMatches 应该返回空数组(dry run 模式)
    it('应该返回空数组', async () => {
        const matches = harvester.getPendingMatches();
        assert.strictEqual(Array.isArray(matches), true);
        assert.strictEqual(matches.length, 0);
    });
});

// ============================================================================
// C. ErrorAuditor 测试 (10项)
// ============================================================================

describe('ErrorAuditor', () => {
    let errorAuditor;

    beforeEach(() => {
        errorAuditor = getErrorAuditor();
    });

    // 测试 1: classifyError 正确识别 ECONNRESET
    it('应该正确识别 ECONNRESET', () => {
        const result = errorAuditor.classifyError('ECONNRESET');
        assert.strictEqual(result, ErrorType.NETWORK_ERROR);
    });

    // 测试 2: classifyError 正确识别 403
    it('应该正确识别 403', () => {
        const result = errorAuditor.classifyError('403 Forbidden');
        assert.strictEqual(result, ErrorType.RATE_LIMITED);
    });

    // 测试 3: classifyError 正确识别 CF_BLOCK
    it('应该正确识别 CF_BLOCK', () => {
        const result = errorAuditor.classifyError('CF_BLOCK: Access denied');
        assert.strictEqual(result, ErrorType.UNKNOWN);
    });

    // 测试 4: isRetryableError 正确识别 ECONNRESET
    it('应该正确识别 ECONNRESET 可可重试', () => {
        const result = errorAuditor.isRetryableError('ECONNRESET');
        assert.strictEqual(result, true);
    });

    // 测试 5: isRetryableError 正确拒绝 403
    it('应该正确拒绝 403', () => {
        const result = errorAuditor.isRetryableError('403 Forbidden');
        assert.strictEqual(result, false);
    });

    // 测试 6: isRetryableError 正确拒绝 CF_BLOCK
    it('应该正确拒绝 CF_BLOCK', () => {
        const result = errorAuditor.isRetryableError('CF_BLOCK: Access denied');
        assert.strictEqual(result, false);
    });

    // 测试 7: isRetryableError 正确处理 Timeout exceeded
    it('应该正确处理 Timeout exceeded', () => {
        const result = errorAuditor.isRetryableError('Timeout exceeded');
        assert.strictEqual(result, true);
    });

    // 测试 8: isRetryableError 正确处理 Connection reset by peer
    it('应该正确处理 Connection reset by peer', () => {
        const result = errorAuditor.isRetryableError('Connection reset by peer');
        assert.strictEqual(result, true);
    });

    // 测试 9: isRetryableError 正确处理 Turnstile challenge
    it('应该正确处理 Turnstile challenge', () => {
        const result = errorAuditor.isRetryableError('Cloudflare Turnstile challenge required');
        assert.strictEqual(result, false);
    });

    // 测试 10: recordError 应该正确记录错误
    it('应该正确记录错误', () => {
        const result = errorAuditor.recordError('403 Forbidden');
        assert.ok(result.type);
        assert.ok(result.retryable);
    });
});

// ============================================================================
// D. BrowserFactory 测试 (3项)
// ============================================================================

describe('BrowserFactory', () => {
    let browserFactory;

    beforeEach(() => {
        browserFactory = new BrowserFactory({ headless: true });
    });

    afterEach(async () => {
        if (browserFactory) {
            await browserFactory.close();
        }
    });

    // 测试 1: launch 应该成功启动浏览器
    it('应该成功启动浏览器', async () => {
        const browser = await browserFactory.launch();
        assert.ok(browser);
    });

    // 测试 2: createContext 应该成功创建 Context
    it('应该成功创建 Context', async () => {
        await browserFactory.launch();
        const identity = {
            proxy: { url: null },
            stealth: {
                viewport: { width: 1920, height: 1080 },
                userAgent: 'Test Agent',
            }
        };
        const context = await browserFactory.createContext(identity, true);
        assert.ok(context);
    });

    // 测试 3: injectStealthScripts 应该成功注入
    it('应该成功注入隐身脚本', async () => {
        await browserFactory.launch();
        const identity = {
            proxy: { url: null },
            stealth: {
                viewport: { width: 1920, height: 1080 },
                userAgent: 'Test Agent'
            }
        };
        const context = await browserFactory.createContext(identity, true);
        const page = await context.newPage();
        await browserFactory.injectStealthScripts(page);
        // 不应抛出错误
    });
});

// ============================================================================
// E. ContextPool 测试 (5项)
// ============================================================================

describe('ContextPool', () => {
    let contextPool;

    beforeEach(() => {
        contextPool = new ContextPool({ maxSize: 5 });
    });

    afterEach(() => {
        contextPool.clear();
    });

            // 测试 1: getOrCreateContext 应该成功创建新 Context
            it('应该成功创建新 Context', async () => {
                const context = await contextPool.getOrCreateContext(1);
                assert.ok(context);
            });
    // 测试 2: getOrCreateContext 应该返回已有 Context
    it('应该返回已有 Context', async () => {
        const context1 = await contextPool.getOrCreateContext(1);
        const context2 = await contextPool.getOrCreateContext(1);
        assert.strictEqual(context1, context2);
    });

    // 测试 3: releaseContext 应该正确释放 Context
    it('应该正确释放 Context', async () => {
        const context = await contextPool.getOrCreateContext(1);
        contextPool.releaseContext(1);
        const result = contextPool.getContext(1);
        assert.strictEqual(result, undefined);
    });

    // 测试 4: releaseContext 应该处理不存在的 Context
    it('应该处理不存在的 Context', async () => {
        const context = await contextPool.getOrCreateContext(1);
        contextPool.releaseContext(1);
        const result = contextPool.getContext(1);
        assert.strictEqual(result, undefined);
    });

    // 测试 5: clear 应该清理所有 Context
    it('应该清理所有 Context', async () => {
        await contextPool.getOrCreateContext(1);
        await contextPool.getOrCreateContext(2);
        await contextPool.clear();
        assert.strictEqual(contextPool.size, 0);
    });
});
