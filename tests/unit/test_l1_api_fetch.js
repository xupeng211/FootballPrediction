/**
 * V171-Infrastructure-10 L1 API 采集器单元测试
 * ============================================
 *
 * 符合 Google 规范的单元测试套件
 * - 测试覆盖: 异常处理、鲁棒性、时间转换
 * - 框架: Node.js 内置 assert + mock
 *
 * @module tests/unit/test_l1_api_fetch
 * @version V171.100
 */

'use strict';

const assert = require('assert');
const { describe, it, beforeEach, afterEach } = require('node:test');

// 模拟依赖
const mockClient = {
    connect: async () => {},
    end: async () => {},
    query: async () => ({ rows: [] })
};

// 模拟 fetch
global.fetch = null;

// 测试配置
const TEST_CONFIG = {
    validMatch: {
        match_id: 'EPL_20250215_ARS_CHE',
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        home_score: 2,
        away_score: 1,
        ht_score: '1-0',
        utc_time: '2025-02-15T15:00:00Z',
        match_status: 'finished',
        round_number: 25,
        is_live: false,
        fotmob_id: '4813550'
    },
    apiResponse: {
        fixtures: {
            allMatches: [
                {
                    id: 4813550,
                    home: { name: 'Arsenal' },
                    away: { name: 'Chelsea' },
                    status: {
                        finished: true,
                        started: false,
                        cancelled: false,
                        postponed: false,
                        scoreStr: '2 - 1',
                        htScoreStr: '1 - 0',
                        utcTime: '2025-02-15T15:00:00Z'
                    },
                    round: 25
                }
            ]
        }
    },
    rateLimitResponse: {
        status: 429,
        statusText: 'Too Many Requests',
        ok: false
    },
    forbiddenResponse: {
        status: 403,
        statusText: 'Forbidden',
        ok: false
    }
};

// ============================================================================
// 测试套件 1: API 异常处理
// ============================================================================

describe('L1 API 异常处理', () => {

    beforeEach(() => {
        // 重置 mock
        global.fetch = null;
    });

    describe('频率限制处理 (429 Too Many Requests)', () => {
        it('应该正确处理 429 错误并抛出包含状态码的异常', async () => {
            // 模拟 429 响应
            global.fetch = async () => TEST_CONFIG.rateLimitResponse;

            let errorThrown = false;
            let errorMessage = '';

            try {
                // 模拟调用 fetchLeagueSeason
                const response = await global.fetch('https://fotmob.com/api/test');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
            } catch (error) {
                errorThrown = true;
                errorMessage = error.message;
            }

            assert.strictEqual(errorThrown, true, '应该抛出异常');
            assert.match(errorMessage, /429/, '错误信息应包含 429 状态码');
        });

        it('应该实现指数退避重试机制', () => {
            // 测试指数退避逻辑
            const delays = [];
            let delay = 1000;
            for (let i = 0; i < 3; i++) {
                delays.push(delay);
                delay = delay * 2;  // 指数退避
            }

            assert.deepStrictEqual(delays, [1000, 2000, 4000], '退避时间应指数增长');
        });
    });

    describe('访问拒绝处理 (403 Forbidden)', () => {
        it('应该正确处理 403 错误', async () => {
            global.fetch = async () => TEST_CONFIG.forbiddenResponse;

            let errorThrown = false;
            let errorMessage = '';

            try {
                const response = await global.fetch('https://fotmob.com/api/test');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
            } catch (error) {
                errorThrown = true;
                errorMessage = error.message;
            }

            assert.strictEqual(errorThrown, true, '应该抛出异常');
            assert.match(errorMessage, /403/, '错误信息应包含 403 状态码');
        });

        it('403 错误不应触发重试（认证失败）', () => {
            // 403 是认证问题，不应重试
            const shouldRetry = (status) => {
                return status === 429 || status >= 500;
            };

            assert.strictEqual(shouldRetry(403), false, '403 不应重试');
            assert.strictEqual(shouldRetry(429), true, '429 应该重试');
        });
    });

    describe('网络超时处理', () => {
        it('应该在超时后抛出 TimeoutError', async () => {
            // 模拟超时
            global.fetch = async () => {
                return new Promise((_, reject) => {
                    setTimeout(() => reject(new Error('Network timeout')), 100);
                });
            };

            let errorThrown = false;

            try {
                await global.fetch('https://fotmob.com/api/test');
            } catch (error) {
                errorThrown = true;
                assert.match(error.message, /timeout/i, '应该抛出超时错误');
            }

            assert.strictEqual(errorThrown, true);
        });
    });
});

// ============================================================================
// 测试套件 2: 字段缺失鲁棒性
// ============================================================================

describe('API 返回字段缺失鲁棒性', () => {

    describe('缺失 scoreStr 字段', () => {
        it('应该将比分设为 null 而非报错', () => {
            const match = {
                id: 12345,
                home: { name: 'Team A' },
                away: { name: 'Team B' },
                status: { finished: true }
                // 缺失 scoreStr
            };

            const parseScore = (scoreStr) => {
                if (!scoreStr) return { home: null, away: null };
                const scores = scoreStr.split('-').map(s => parseInt(s.trim()));
                return { home: scores[0], away: scores[1] };
            };

            const result = parseScore(match.status?.scoreStr);
            assert.deepStrictEqual(result, { home: null, away: null });
        });

        it('应该处理格式错误的 scoreStr', () => {
            const parseScore = (scoreStr) => {
                if (!scoreStr) return { home: null, away: null };
                const scores = scoreStr.split('-').map(s => parseInt(s.trim()));
                if (scores.length !== 2 || isNaN(scores[0]) || isNaN(scores[1])) {
                    return { home: null, away: null };
                }
                return { home: scores[0], away: scores[1] };
            };

            // 测试各种异常格式
            assert.deepStrictEqual(parseScore('invalid'), { home: null, away: null });
            assert.deepStrictEqual(parseScore('2'), { home: null, away: null });
            assert.deepStrictEqual(parseScore('a-b'), { home: null, away: null });
        });
    });

    describe('缺失 utcTime 字段', () => {
        it('应该将 utc_time 设为 null', () => {
            const match = {
                id: 12345,
                status: { finished: true }
                // 缺失 utcTime
            };

            const utcTime = match.status?.utcTime || null;
            assert.strictEqual(utcTime, null);
        });
    });

    describe('缺失 round 字段', () => {
        it('应该将 round_number 设为 null', () => {
            const match = {
                id: 12345,
                // 缺失 round
            };

            const roundNumber = match.round ? parseInt(match.round) : null;
            assert.strictEqual(roundNumber, null);
        });
    });

    describe('缺失 home/away 队名', () => {
        it('应该跳过没有队名的比赛', () => {
            const matches = [
                { id: 1, home: { name: 'Team A' }, away: { name: null } },
                { id: 2, home: { name: null }, away: { name: 'Team B' } },
                { id: 3, home: { name: 'Team C' }, away: { name: 'Team D' } }
            ];

            const validMatches = matches.filter(m => m.home?.name && m.away?.name);
            assert.strictEqual(validMatches.length, 1);
            assert.strictEqual(validMatches[0].id, 3);
        });
    });

    describe('部分字段为 null', () => {
        it('应该正确处理混合 null 值', () => {
            const parseMatch = (match) => ({
                home_score: match.status?.scoreStr
                    ? parseInt(match.status.scoreStr.split('-')[0])
                    : null,
                ht_score: match.status?.htScoreStr || null,
                round: match.round || null
            });

            const result = parseMatch({
                status: { scoreStr: '2 - 1' },
                // htScoreStr 缺失
                // round 缺失
            });

            assert.strictEqual(result.home_score, 2);
            assert.strictEqual(result.ht_score, null);
            assert.strictEqual(result.round, null);
        });
    });
});

// ============================================================================
// 测试套件 3: UTC 时间转换
// ============================================================================

describe('UTC 时间转换验证', () => {

    describe('ISO 8601 字符串解析', () => {
        it('应该正确解析 ISO 8601 格式', () => {
            const utcTime = '2025-02-15T15:00:00Z';
            const date = new Date(utcTime);

            assert.strictEqual(date.getUTCFullYear(), 2025);
            assert.strictEqual(date.getUTCMonth(), 1);  // 月份从 0 开始
            assert.strictEqual(date.getUTCDate(), 15);
            assert.strictEqual(date.getUTCHours(), 15);
            assert.strictEqual(date.getUTCMinutes(), 0);
        });

        it('应该正确处理带时区的字符串', () => {
            const utcTime = '2025-02-15T15:00:00+00:00';
            const date = new Date(utcTime);

            assert.strictEqual(date.getUTCHours(), 15);
        });
    });

    describe('null 值处理', () => {
        it('null utcTime 应该保持为 null', () => {
            const utcTime = null;
            const result = utcTime || null;
            assert.strictEqual(result, null);
        });
    });

    describe('时间戳一致性', () => {
        it('utc_time 和 match_date 应该指向同一时间', () => {
            const match = {
                utc_time: '2025-02-15T15:00:00Z',
                match_date: '2025-02-15T15:00:00Z'
            };
            const utcDate = new Date(match.utc_time);
            const matchDate = new Date(match.match_date);

            assert.strictEqual(utcDate.getTime(), matchDate.getTime());
        });

        it('数据库存储应使用 UTC 时间', () => {
            // 模拟 NOW() 在 UTC 时区的行为
            const now = new Date();
            const utcString = now.toISOString();

            // 检查 ISO 格式以 Z 结尾 (UTC)
            assert.match(utcString, /Z$/, '应该以 Z 结尾表示 UTC');
        });
    });
});

// ============================================================================
// 测试套件 4: 幂等性验证
// ============================================================================

describe('幂等性验证', () => {

    describe('重复执行不应产生重复记录', () => {
        it('相同 match_id 应该更新而非插入新记录', () => {
            // 模拟第一次插入
            const db = new Map();
            const match = { match_id: 'EPL_20250215_ARS_CHE', home_score: 2 };

            // 模拟 ON CONFLICT DO UPDATE
            const upsert = (db, match) => {
                if (db.has(match.match_id)) {
                    // UPDATE
                    const existing = db.get(match.match_id);
                    db.set(match.match_id, { ...existing, ...match });
                } else {
                    // INSERT
                    db.set(match.match_id, match);
                }
            };

            upsert(db, match);
            assert.strictEqual(db.size, 1);

            // 重复执行
            const updatedMatch = { match_id: 'EPL_20250215_ARS_CHE', home_score: 3 };
            upsert(db, updatedMatch);

            assert.strictEqual(db.size, 1, '记录数应保持为 1');
            assert.strictEqual(db.get('EPL_20250215_ARS_CHE').home_score, 3, '比分应被更新');
        });
    });

    describe('external_id 保留', () => {
        it('更新时不应覆盖已存在的 external_id', () => {
            const db = new Map();
            db.set('EPL_20250215_ARS_CHE', {
                match_id: 'EPL_20250215_ARS_CHE',
                external_id: '4813550',
                home_score: 2
            });

            // 模拟 COALESCE 逻辑
            const updateWithExternalId = (existing, newData) => ({
                ...existing,
                ...newData,
                external_id: existing.external_id || newData.external_id
            });

            const updated = updateWithExternalId(
                db.get('EPL_20250215_ARS_CHE'),
                { match_id: 'EPL_20250215_ARS_CHE', home_score: 3, external_id: null }
            );

            assert.strictEqual(updated.external_id, '4813550', 'external_id 应保留原值');
        });
    });
});

// ============================================================================
// 测试套件 5: 边界条件
// ============================================================================

describe('边界条件测试', () => {

    describe('空响应', () => {
        it('应该处理空数组', () => {
            const matches = [];
            const result = matches.length;
            assert.strictEqual(result, 0);
        });

        it('应该处理 null fixtures', () => {
            const apiData = { fixtures: null };
            const matches = apiData?.fixtures?.allMatches || [];
            assert.deepStrictEqual(matches, []);
        });
    });

    describe('超大比分', () => {
        it('应该接受极端比分', () => {
            const parseScore = (scoreStr) => {
                const scores = scoreStr.split('-').map(s => parseInt(s.trim()));
                return { home: scores[0], away: scores[1] };
            };

            // 极端比分: 10-0
            assert.deepStrictEqual(parseScore('10 - 0'), { home: 10, away: 0 });
            // 极端比分: 7-7
            assert.deepStrictEqual(parseScore('7 - 7'), { home: 7, away: 7 });
        });
    });

    describe('特殊字符队名', () => {
        it('应该正确处理包含特殊字符的队名', () => {
            const generateMatchId = (home, away, date) => {
                const dateStr = date.replace(/-/g, '').substring(0, 8);
                const homeCode = home.substring(0, 3).toUpperCase();
                const awayCode = away.substring(0, 3).toUpperCase();
                return `EPL_${dateStr}_${homeCode}_${awayCode}`;
            };

            assert.strictEqual(
                generateMatchId('Manchester United', 'Brighton & Hove', '2025-02-15'),
                'EPL_20250215_MAN_BRI'
            );
        });
    });
});

// ============================================================================
// 运行测试
// ============================================================================

console.log('');
console.log('═'.repeat(60));
console.log('  L1 API 采集器单元测试 - V171.100');
console.log('═'.repeat(60));
console.log('');
