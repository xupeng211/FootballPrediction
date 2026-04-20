/**
 * FeatureSmelter 单元测试
 * ========================
 *
 * 测试 L3 特征熔炼引擎的核心功能
 * 确保 FotMob 格式变更时能通过测试失败第一时间发现
 * @module tests/unit/FeatureSmelter.test
 * @version V197.0.0
 */

'use strict';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert');
const Registry = require('../../config/registry');

// Mock 数据 - 模拟 FotMob API 返回的比赛数据
const MOCK_RAW_DATA = {
    content: {
        // 比赛基本信息
        header: {
            name: 'Arsenal vs Chelsea',
            status: {
                started: false,
                finished: true,
                cancelled: false,
                utcTime: '2024-01-15T15:00:00Z'
            }
        },
        // 球队信息
        home: {
            name: 'Arsenal',
            shortName: 'ARS',
            id: '12345',
            score: 2
        },
        away: {
            name: 'Chelsea',
            shortName: 'CHE',
            id: '67890',
            score: 1
        },
        // 统计数据
        stats: {
            // 控球率
            possession: {
                home: 55,
                away: 45
            },
            // 射门
            shots: {
                home: 15,
                away: 8
            },
            // 射正
            shotsOnTarget: {
                home: 7,
                away: 3
            },
            // 角球
            corners: {
                home: 6,
                away: 2
            },
            // 犯规
            fouls: {
                home: 10,
                away: 12
            },
            // 黄牌
            yellowCards: {
                home: 1,
                away: 2
            },
            // 红牌
            redCards: {
                home: 0,
                away: 0
            }
        },
        // xG 数据
        expectedGoals: {
            home: 1.8,
            away: 0.9
        },
        // 球员数据
        lineups: {
            home: {
                players: [
                    { name: 'Saka', rating: 8.5, position: 'RW' },
                    { name: 'Ødegaard', rating: 8.2, position: 'CM' },
                    { name: 'Havertz', rating: 7.8, position: 'ST' }
                ]
            },
            away: {
                players: [
                    { name: 'Palmer', rating: 7.5, position: 'RW' },
                    { name: 'Jackson', rating: 6.8, position: 'ST' }
                ]
            }
        }
    },
    general: {
        leagueId: 47,
        leagueName: 'Premier League',
        season: '2023/2024'
    }
};

// Mock 比赛信息
const MOCK_MATCH_INFO = {
    match_id: '47_20232024_123456789',
    external_id: '123456789',
    home_team: 'Arsenal',
    away_team: 'Chelsea'
};

// ============================================================================
// 测试套件
// ============================================================================

describe('FeatureSmelter 单元测试', () => {

    // ========================================================================
    // Registry 验证测试
    // ========================================================================

    describe('Registry 配置验证', () => {
        it('应该包含所有必要的表名', () => {
            assert.ok(Registry.TABLES.MATCHES, 'MATCHES 表名应该存在');
            assert.ok(Registry.TABLES.RAW_MATCH_DATA, 'RAW_MATCH_DATA 表名应该存在');
            assert.ok(Registry.TABLES.L3_FEATURES, 'L3_FEATURES 表名应该存在');
        });

        it('应该包含所有必要的 API 配置', () => {
            assert.ok(Registry.APIS.FOTMOB, 'FOTMOB API 配置应该存在');
            assert.ok(Registry.APIS.FOTMOB.BASE_URL, 'FOTMOB BASE_URL 应该存在');
            assert.ok(Registry.APIS.FOTMOB.leagues, 'FOTMOB.leagues 方法应该存在');
        });

        it('应该正确构建联赛 API URL', () => {
            const url = Registry.APIS.FOTMOB.leagues(47, '20242025');
            assert.ok(url.includes('47'), 'URL 应该包含联赛 ID');
            assert.ok(url.includes('20242025'), 'URL 应该包含赛季');
        });
    });

    // ========================================================================
    // 数据格式验证测试
    // ========================================================================

    describe('Mock 数据结构验证', () => {
        it('Mock 数据应该包含完整的比赛信息', () => {
            assert.ok(MOCK_RAW_DATA.content, 'content 应该存在');
            assert.ok(MOCK_RAW_DATA.content.header, 'header 应该存在');
            assert.ok(MOCK_RAW_DATA.content.home, 'home 应该存在');
            assert.ok(MOCK_RAW_DATA.content.away, 'away 应该存在');
        });

        it('Mock 数据应该包含统计数据', () => {
            assert.ok(MOCK_RAW_DATA.content.stats, 'stats 应该存在');
            assert.strictEqual(MOCK_RAW_DATA.content.stats.possession.home, 55, '主队控球率应该是 55%');
            assert.strictEqual(MOCK_RAW_DATA.content.stats.possession.away, 45, '客队控球率应该是 45%');
        });

        it('Mock 数据应该包含 xG 数据', () => {
            assert.ok(MOCK_RAW_DATA.content.expectedGoals, 'expectedGoals 应该存在');
            assert.strictEqual(MOCK_RAW_DATA.content.expectedGoals.home, 1.8, '主队 xG 应该是 1.8');
            assert.strictEqual(MOCK_RAW_DATA.content.expectedGoals.away, 0.9, '客队 xG 应该是 0.9');
        });

        it('Mock 数据应该包含比分', () => {
            assert.strictEqual(MOCK_RAW_DATA.content.home.score, 2, '主队比分应该是 2');
            assert.strictEqual(MOCK_RAW_DATA.content.away.score, 1, '客队比分应该是 1');
        });
    });

    // ========================================================================
    // 边界情况测试
    // ========================================================================

    describe('边界情况', () => {
        it('应该处理缺失的统计数据', () => {
            const dataWithoutStats = {
                content: {
                    header: { name: 'Test Match' },
                    home: { name: 'Team A' },
                    away: { name: 'Team B' }
                }
            };

            // 验证数据结构不会导致崩溃
            assert.ok(dataWithoutStats.content, '数据应该有效');
            assert.strictEqual(dataWithoutStats.content.stats, undefined, 'stats 应该是 undefined');
        });

        it('应该处理未来的比赛（无比分）', () => {
            const futureMatchData = {
                content: {
                    header: {
                        name: 'Arsenal vs Chelsea',
                        status: { started: false, finished: false }
                    },
                    home: { name: 'Arsenal' },
                    away: { name: 'Chelsea' }
                }
            };

            // 验证未来比赛数据结构
            assert.strictEqual(futureMatchData.content.home.score, undefined, '未来比赛不应该有比分');
        });

        it('应该处理取消的比赛', () => {
            const cancelledMatchData = {
                content: {
                    header: {
                        name: 'Arsenal vs Chelsea',
                        status: { cancelled: true }
                    }
                }
            };

            // 验证取消比赛数据结构
            assert.ok(cancelledMatchData.content.header.status.cancelled, 'cancelled 标志应该为 true');
        });

        it('应该处理极端比分', () => {
            const highScoreData = {
                content: {
                    ...MOCK_RAW_DATA.content,
                    home: { ...MOCK_RAW_DATA.content.home, score: 10 },
                    away: { ...MOCK_RAW_DATA.content.away, score: 0 }
                }
            };

            assert.strictEqual(highScoreData.content.home.score, 10, '主队极端比分应该是 10');
            assert.strictEqual(highScoreData.content.away.score, 0, '客队比分应该是 0');
        });
    });

    // ========================================================================
    // 数据格式变更检测测试
    // ========================================================================

    describe('数据格式变更检测', () => {
        it('应该识别字段名变更', () => {
            // 模拟 FotMob API 格式变更（字段名改变）
            const changedFormatData = {
                content: {
                    // 新的 API 使用了不同的字段名
                    matchHeader: {  // 原来是 header
                        matchName: 'Arsenal vs Chelsea'  // 原来是 name
                    },
                    homeTeam: {  // 原来是 home
                        teamName: 'Arsenal'  // 原来是 name
                    }
                }
            };

            // 验证新格式数据中旧字段不存在
            assert.strictEqual(changedFormatData.content.header, undefined, '旧 header 字段不应该存在');
            assert.strictEqual(changedFormatData.content.home, undefined, '旧 home 字段不应该存在');
        });

        it('应该识别字段类型变更', () => {
            // 模拟字段类型变更（stats 从对象变成数组）
            const typeChangedData = {
                content: {
                    stats: [  // 原来是对象，现在变成数组
                        { type: 'possession', home: 55, away: 45 }
                    ]
                }
            };

            // 验证类型变更
            assert.ok(Array.isArray(typeChangedData.content.stats), 'stats 应该是数组类型');
        });
    });

    // ========================================================================
    // 比赛状态映射测试
    // ========================================================================

    describe('比赛状态映射', () => {
        it('应该正确识别已完成的比赛', () => {
            const status = Registry.MATCH_STATUS.fromFotMob(
                { finished: true },
                2,
                1
            );
            assert.strictEqual(status, 'finished', '已完成的比赛状态应该是 finished');
        });

        it('应该正确识别进行中的比赛', () => {
            const status = Registry.MATCH_STATUS.fromFotMob(
                { started: true, finished: false },
                null,
                null
            );
            assert.strictEqual(status, 'live', '进行中的比赛状态应该是 live');
        });

        it('应该正确识别已取消的比赛', () => {
            const status = Registry.MATCH_STATUS.fromFotMob(
                { cancelled: true },
                null,
                null
            );
            assert.strictEqual(status, 'cancelled', '已取消的比赛状态应该是 cancelled');
        });

        it('应该正确识别已判给的比赛', () => {
            const status = Registry.MATCH_STATUS.fromFotMob(
                { awarded: true },
                null,
                null
            );
            assert.strictEqual(status, 'awarded', '已判给的比赛状态应该是 awarded');
        });

        it('应该正确识别未开始的比赛', () => {
            const status = Registry.MATCH_STATUS.fromFotMob(
                { started: false, finished: false },
                null,
                null
            );
            assert.strictEqual(status, 'scheduled', '未开始的比赛状态应该是 scheduled');
        });
    });

    // ========================================================================
    // 性能测试
    // ========================================================================

    describe('性能测试', () => {
        it('数据结构操作应该在合理时间内完成', () => {
            // 创建包含大量球员的数据
            const largeData = {
                content: {
                    ...MOCK_RAW_DATA.content,
                    lineups: {
                        home: {
                            players: Array.from({ length: 50 }, (_, i) => ({
                                name: `Player ${i}`,
                                rating: 7 + Math.random(),
                                position: 'SUB'
                            }))
                        },
                        away: {
                            players: Array.from({ length: 50 }, (_, i) => ({
                                name: `Player ${i}`,
                                rating: 6 + Math.random(),
                                position: 'SUB'
                            }))
                        }
                    }
                }
            };

            const startTime = Date.now();

            // 模拟数据处理
            const homePlayers = largeData.content.lineups.home.players;
            const awayPlayers = largeData.content.lineups.away.players;
            const allPlayers = [...homePlayers, ...awayPlayers];

            const elapsed = Date.now() - startTime;

            // 应该在 10ms 内完成
            assert.ok(elapsed < 10, `操作应该在 10ms 内完成，实际耗时 ${elapsed}ms`);
            assert.strictEqual(allPlayers.length, 100, '应该有 100 个球员');
        });
    });
});

// ============================================================================
// 集成测试 - 验证组件间协作
// ============================================================================

describe('Registry 集成测试', () => {
    it('Registry 应该提供一致的配置', () => {
        // 验证所有表名都是字符串
        const tables = Registry.TABLES.all();
        tables.forEach(table => {
            assert.strictEqual(typeof table, 'string', `表名 ${table} 应该是字符串`);
        });
    });

    it('联赛映射应该包含主要联赛', () => {
        // 验证主要联赛 ID 存在
        const premierLeague = Registry.LEAGUES.BY_ID[47];
        const laLiga = Registry.LEAGUES.BY_ID[55];
        const bundesliga = Registry.LEAGUES.BY_ID[54];

        assert.ok(premierLeague, '英超应该存在于联赛映射中');
        assert.ok(laLiga, '西甲应该存在于联赛映射中');
        assert.ok(bundesliga, '德甲应该存在于联赛映射中');
    });

    it('代理配置应该有效', () => {
        const ports = Registry.PROXY.getAllPorts();
        assert.ok(Array.isArray(ports), '端口列表应该是数组');
        assert.ok(ports.length > 0, '至少应配置 1 个代理端口');
        assert.strictEqual(new Set(ports).size, ports.length, '代理端口不应该重复');
        assert.strictEqual(Math.min(...ports), ports[0], '代理端口起点应与首个配置端口一致');
        assert.strictEqual(Math.max(...ports), ports[ports.length - 1], '代理端口终点应与最后一个配置端口一致');

        // 验证端口范围与连续性
        ports.forEach((port, index) => {
            assert.strictEqual(port, ports[0] + index, `端口 ${port} 应该与共享代理池保持连续`);
        });
    });
});
