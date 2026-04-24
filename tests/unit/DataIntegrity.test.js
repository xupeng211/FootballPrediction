/**
 * 数据完整性测试套件
 * ======================
 *
 * 测试数据解析和验证逻辑
 * 禁止 Mock 环境， */

'use strict';

const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

// 模块路径
const NEXT_DATA_PARSER_PATH = path.resolve(__dirname, '../../src/parsers/fotmob/NextDataParser');
const FOTMOB_STRATEGY_PATH = path.resolve(__dirname, '../../src/infrastructure/harvesters/strategies/FotMobStrategy');

// ============================================================================
// 测试套件
// ============================================================================

describe('数据完整性测试套件', () => {
    let nextDataParser;
    let fotmobStrategy;
    let tempDir;

    beforeEach(async () => {
        // 创建临时目录
        tempDir = path.join(__dirname, 'temp_test_data');
        if (!fs.existsSync(tempDir)) {
            fs.mkdirSync(tempDir, { recursive: true });
        }
    });

    afterEach(async () => {
        // 清理临时目录
        if (fs.existsSync(tempDir)) {
                fs.rmSync(tempDir, { recursive: true });
        }
    });

    // ========================================================================
    // NextDataParser 测试
    // ========================================================================

    describe('NextDataParser', () => {
        beforeEach(() => {
                nextDataParser = require(NEXT_DATA_PARSER_PATH);
        });

        it('应该正确导出模块', () => {
                assert.strictEqual(typeof nextDataParser, 'object');
                assert.strictEqual(typeof nextDataParser.extractNextData, 'function');
                assert.strictEqual(typeof nextDataParser.extractFromHtml, 'function');
            assert.strictEqual(typeof nextDataParser.transformToApiFormat, 'function');
        });

        it('extractFromHtml 应该处理空输入', () => {
                const result = nextDataParser.extractFromHtml(null);
                assert.strictEqual(result.success, false);
                assert.ok(result.error.includes('INVALID_INPUT'));
            });

        it('extractFromHtml 应该处理空字符串', () => {
                const result = nextDataParser.extractFromHtml('');
                assert.strictEqual(result.success, false);
                assert.ok(result.error.includes('INVALID_INPUT'));
            });

        it('extractFromHtml 应该处理无 NEXT_DATA 的 HTML', () => {
                const html = '<html><body><p>Test</p></body></html>';
                const result = nextDataParser.extractFromHtml(html);
                assert.strictEqual(result.success, false);
                assert.ok(result.error.includes('NO_NEXT_DATA'));
            });

        it('extractFromHtml 应该正确解析有效 NEXT_DATA', () => {
                const html = '<script id="__NEXT_DATA__" type="application/json">{"test": "value"}</script>';
                const result = nextDataParser.extractFromHtml(html);
                assert.strictEqual(result.success, true);
                assert.deepStrictEqual(result.data, { test: 'value' });
            });

        it('extractFromHtml 应该处理无效 JSON', () => {
                const html = '<script id="__NEXT_DATA__" type="application/json">{invalid json}</script>';
                const result = nextDataParser.extractFromHtml(html);
                assert.strictEqual(result.success, false);
                assert.ok(result.error.includes('PARSE_ERROR'));
            });

        it('transformToApiFormat 应该正确转换数据', () => {
                const input = {
                    props: {
                        pageProps: {
                            content: { test: 'value' },
                            general: {},
                            header: {}
                        }
                    }
                };
                const result = nextDataParser.transformToApiFormat(input);
                assert.ok(result);
                assert.ok(result.content);
            });

        it('transformToApiFormat 应该处理空输入', () => {
                const result = nextDataParser.transformToApiFormat(null);
                assert.strictEqual(result, null);
            });
    });

    // ========================================================================
    // FotMobStrategy 测试
    // ========================================================================

    describe('FotMobStrategy', () => {
        beforeEach(() => {
                const { FotMobStrategy } = require(FOTMOB_STRATEGY_PATH);
                fotmobStrategy = new FotMobStrategy();
            });

        it('应该正确导出模块', () => {
                assert.strictEqual(typeof fotmobStrategy, 'object');
                assert.strictEqual(typeof fotmobStrategy.getTargetUrl, 'function');
                assert.strictEqual(typeof fotmobStrategy.setupRequestInterception, 'function');
                assert.strictEqual(typeof fotmobStrategy.extractData, 'function');
            });

        it('getTargetUrl 应该返回正确的 URL', () => {
                const match = { external_id: '12345' };
                const url = fotmobStrategy.getTargetUrl(match);
                assert.strictEqual(url, 'https://www.fotmob.com/match/12345');
            });

        it('getTargetUrl 应优先使用 L1 提供的历史 pageUrl', () => {
                const match = {
                    external_id: '12345',
                    pageUrl: '/matches/fulham-vs-manchester-united/3cqww9#4506263'
                };
                const url = fotmobStrategy.getTargetUrl(match);
                assert.strictEqual(url, 'https://www.fotmob.com/matches/fulham-vs-manchester-united/3cqww9#4506263');
            });

        it('_buildCookieHeader 应正确拼接 Cookie 头', () => {
                const header = fotmobStrategy._buildCookieHeader([
                    { name: 'session', value: 'abc' },
                    { name: 'locale', value: 'zh-Hans' }
                ]);
                assert.strictEqual(header, 'session=abc; locale=zh-Hans');
            });

        it('_normalizeSessionCookie 应兼容 no_restriction sameSite', () => {
                const cookie = fotmobStrategy._normalizeSessionCookie({
                    name: 'session',
                    value: 'abc',
                    domain: '.fotmob.com',
                    sameSite: 'no_restriction',
                    secure: true
                });
                assert.strictEqual(cookie.sameSite, 'None');
            });

        it('fetchDataDirect 应优先返回 API 数据且保留统一结构', async () => {
                const { FotMobStrategy } = require(FOTMOB_STRATEGY_PATH);
                const strategy = new FotMobStrategy({
                    apiClient: {
                        setSessionManager() {},
                        async fetchMatchDetails() {
                            return {
                                general: { matchId: '12345' },
                                content: { stats: {}, lineup: {} },
                                header: {},
                                padding: 'x'.repeat(1200)
                            };
                        }
                    }
                });

                const result = await strategy.fetchDataDirect({ external_id: '12345' });
                assert.ok(result.content);
                assert.ok(result.general);
                assert.ok(result.header);
            });

        it('fetchDataDirect 在 403 时应标记浏览器回退', async () => {
                const { FotMobStrategy } = require(FOTMOB_STRATEGY_PATH);
                const strategy = new FotMobStrategy({
                    apiClient: {
                        setSessionManager() {},
                        async fetchMatchDetails() {
                            const error = new Error('HTTP_403');
                            error.statusCode = 403;
                            throw error;
                        }
                    }
                });

                await assert.rejects(
                    strategy.fetchDataDirect({ external_id: '12345' }),
                    (error) => error && error.fallbackToBrowser === true
                );
            });

        it('validateData 应该验证有效数据', () => {
                const data = {
                    content: { lineup: {}, stats: {} },
                    general: {},
                    header: {},
                    padding: 'x'.repeat(1200)
                };
                const result = fotmobStrategy.validateData(data);
                assert.strictEqual(result.valid, true);
            });

        it('validateData 应该拒绝无效数据', () => {
                const result = fotmobStrategy.validateData(null);
                assert.strictEqual(result.valid, false);
                assert.ok(result.reason.includes('NULL_DATA'));
            });

        it('validateData 应该拒绝数据过小', () => {
                const data = { small: true };
                const result = fotmobStrategy.validateData(data);
                assert.strictEqual(result.valid, false);
                assert.ok(result.reason.includes('SIZE_TOO_SMALL'));
            });

        it('_normalizeData 应该添加必要字段', () => {
                const data = { test: 'value' };
                const result = fotmobStrategy._normalizeData(data);
                assert.ok(result._source);
                assert.ok(result._extractedAt);
            });

        it('getDataQualityReport 应该返回质量报告', () => {
                const data = {
                    content: {
                        lineup: { homeTeam: {}, awayTeam: {} },
                        stats: {}
                    },
                    general: {},
                    header: {}
                };
                const report = fotmobStrategy.getDataQualityReport(data);
                assert.ok(report.score > 50);
            });

        it('getField 应该正确获取嵌套字段', () => {
                const data = {
                    content: {
                        lineup: {
                            homeTeam: { name: 'Team A' }
                        }
                    }
                };
                const result = fotmobStrategy.getField(data, 'content.lineup.homeTeam.name');
                assert.strictEqual(result, 'Team A');
            });

        it('extractMatchStats 应该提取比赛统计', () => {
                const data = {
                    content: {
                        lineup: {
                            homeTeam: { name: 'Home' },
                            awayTeam: { name: 'Away' }
                        },
                        stats: { possession: 60 },
                        header: {
                            homeScore: 2,
                            awayScore: 1
                        }
                    },
                    general: {}
                };
                const stats = fotmobStrategy.extractMatchStats(data);
                assert.strictEqual(stats.homeTeam.name, 'Home');
                assert.strictEqual(stats.awayTeam.name, 'Away');
            });
    });

    // ========================================================================
    // ProductionHarvester 测试
    // ========================================================================

    describe('ProductionHarvester', () => {
        let ProductionHarvester;
        let harvester;

        beforeEach(() => {
                ProductionHarvester = require('../../src/infrastructure/harvesters/ProductionHarvester');
                harvester = new ProductionHarvester({
                    dryRun: true,
                    maxWorkers: 1
                });
            });

        afterEach(async () => {
                if (harvester) {
                    try {
                    await harvester.cleanup();
                    } catch (e) {
                        // 忽略清理错误
                    }
                }
            });

        it('应该正确初始化', () => {
                assert.ok(harvester.config);
                assert.ok(harvester.stats);
                assert.strictEqual(harvester.config.dryRun, true);
            });

        it('getTargetUrl 应该抛出错误', () => {
                assert.throws(
                    () => harvester.getTargetUrl({}),
                    /子类必须实现/
                );
            });

        it('extractData 应该抛出错误', async () => {
                await assert.rejects(
                    harvester.extractData(null, null),
                    /子类必须实现/
                );
            });

        it('saveData 应该抛出错误', async () => {
                await assert.rejects(
                    harvester.saveData('test', {}),
                    /子类必须实现/
                );
            });

        it('getPendingMatches 应该返回待收割比赛', async () => {
                // Mock 数据
                const result = await harvester.getPendingMatches();
                assert.ok(Array.isArray(result));
            });

        it('_isRetryableError 应该正确委托给 ErrorAuditor', () => {
                const error = new Error('ECONNRESET');
                const result = harvester._isRetryableError(error);
                assert.strictEqual(typeof result, 'boolean');
            });

        it('_classifyError 应该正确委托给 ErrorAuditor', () => {
                const errorType = harvester._classifyError('timeout');
                assert.strictEqual(typeof errorType, 'string');
            });
    });
});
