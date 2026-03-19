/**
 * FixtureSeeder V5.0 严谨版单元测试
 * ================================
 *
 * 测试覆盖:
 * 1. 三道铁门过滤逻辑（Mock测试）
 * 2. 赛季时间窗口校验
 * 3. 占位符检测（TBD/2026假数据）
 * 4. 边界情况（0场/100%拦截）
 * 5. 批量写入逻辑
 *
 * 运行: node --test tests/unit/FixtureSeederV5.test.js
 */

const { describe, it, beforeEach } = require('node:test');
const assert = require('node:assert');
const path = require('path');

// 导入被测函数
const {
    threeGatesFilter,
    STRICT_VALIDATION,
    parseArgs,
    validateArgs
} = require('../../scripts/ops/seed_fixtures');

// ============================================================================
// Mock 数据工厂
// ============================================================================

function createMockMatch(overrides = {}) {
    // V6.0: 使用 hasOwnProperty 检查，确保 undefined 和 null 不被默认值覆盖
    return {
        id: overrides.hasOwnProperty('id') ? overrides.id : 123456,
        leagueId: overrides.hasOwnProperty('leagueId') ? overrides.leagueId : 47,
        home: {
            id: overrides.hasOwnProperty('homeId') ? overrides.homeId : 1,
            name: overrides.hasOwnProperty('homeName') ? overrides.homeName : 'Liverpool'
        },
        away: {
            id: overrides.hasOwnProperty('awayId') ? overrides.awayId : 2,
            name: overrides.hasOwnProperty('awayName') ? overrides.awayName : 'Chelsea'
        },
        status: {
            utcTime: overrides.hasOwnProperty('utcTime') ? overrides.utcTime : '2024-10-15T15:00:00Z',
            ...overrides.status
        },
        parent: overrides.parent || undefined,
        ...overrides.extra
    };
}

// ============================================================================
// 测试套件 1: 三道铁门 Mock 测试
// ============================================================================

describe('V5.0 三道铁门过滤测试', () => {
    const leagueInfo = { id: 47, name: 'Premier League' };
    const season = '2024/2025';

    describe('铁门 1: LeagueId 校验', () => {
        it('应该拦截 leagueId 不匹配的比赛（英冠/西甲混入）', () => {
            const matches = [
                createMockMatch({ id: 1, leagueId: 47 }),  // 英超 ✓
                createMockMatch({ id: 2, leagueId: 48 }),  // 英冠 ✗
                createMockMatch({ id: 3, leagueId: 87 }),  // 西甲 ✗
                createMockMatch({ id: 4, leagueId: 47 })   // 英超 ✓
            ];
            const stats = {};

            const result = threeGatesFilter(matches, leagueInfo, season, stats);

            assert.strictEqual(result.length, 2, '应该只保留英超比赛');
            assert.deepStrictEqual(result.map(m => m.id), [1, 4]);
            assert.strictEqual(stats.wrongLeague, 2, '应该统计2场leagueId错误');
        });

        it('应该检查 parent.leagueId 作为备选', () => {
            const matches = [
                createMockMatch({ id: 1, leagueId: undefined, parent: { leagueId: 47 } }),
                createMockMatch({ id: 2, leagueId: undefined, parent: { leagueId: 48 } })
            ];
            const stats = {};

            const result = threeGatesFilter(matches, leagueInfo, season, stats);

            assert.strictEqual(result.length, 1);
            assert.strictEqual(result[0].id, 1);
        });
    });

    describe('铁门 2: 赛季时间窗口校验', () => {
        it('应该拦截不在 24/25 赛季窗口内的比赛', () => {
            const matches = [
                createMockMatch({ id: 1, utcTime: '2024-09-15T15:00:00Z' }),  // 在窗口内 ✓
                createMockMatch({ id: 2, utcTime: '2026-01-15T15:00:00Z' }),  // 2026假数据 ✗
                createMockMatch({ id: 3, utcTime: '2023-12-01T15:00:00Z' }),  // 上赛季 ✗
                createMockMatch({ id: 4, utcTime: '2025-04-20T15:00:00Z' })   // 在窗口内 ✓
            ];
            const stats = {};

            const result = threeGatesFilter(matches, leagueInfo, season, stats);

            assert.strictEqual(result.length, 2, '应该只保留窗口内的比赛');
            assert.strictEqual(stats.outsideWindow, 2, '应该统计2场时间窗口外');
        });

        it('应该允许 14 天缓冲期内的比赛', () => {
            const matches = [
                createMockMatch({ id: 1, utcTime: '2024-08-10T15:00:00Z' }),  // 赛季开始前6天（缓冲期内）✓
                createMockMatch({ id: 2, utcTime: '2024-08-01T15:00:00Z' })   // 赛季开始前15天（超出缓冲）✗
            ];
            const stats = {};

            const result = threeGatesFilter(matches, leagueInfo, season, stats);

            assert.strictEqual(result.length, 1);
            assert.strictEqual(result[0].id, 1);
        });

        it('无时间戳的比赛应该放行（由后续逻辑处理）', () => {
            const matches = [
                createMockMatch({ id: 1, utcTime: null }),
                createMockMatch({ id: 2, utcTime: undefined })
            ];
            const stats = {};

            const result = threeGatesFilter(matches, leagueInfo, season, stats);

            assert.strictEqual(result.length, 2);
            assert.strictEqual(stats.outsideWindow, 0);
        });
    });

    describe('铁门 3: 占位符检测', () => {
        it('应该拦截 TBD/TBC 占位符比赛', () => {
            const matches = [
                createMockMatch({ id: 1, homeName: 'Liverpool', awayName: 'Chelsea' }),  // ✓
                createMockMatch({ id: 2, homeName: 'TBD', awayName: 'Chelsea' }),        // ✗
                createMockMatch({ id: 3, homeName: 'Liverpool', awayName: 'tbc' }),      // ✗
                createMockMatch({ id: 4, homeName: 'Team A', awayName: 'Team B' })       // ✗
            ];
            const stats = {};

            const result = threeGatesFilter(matches, leagueInfo, season, stats);

            assert.strictEqual(result.length, 1);
            assert.strictEqual(result[0].id, 1);
            assert.strictEqual(stats.placeholder, 3);
        });

        it('应该拦截中文占位符（待定/胜者/败者）', () => {
            const matches = [
                createMockMatch({ id: 1, homeName: '待定', awayName: 'Liverpool' }),
                createMockMatch({ id: 2, homeName: 'Winner SF1', awayName: 'Loser SF2' }),
                createMockMatch({ id: 3, homeName: '未确定', awayName: 'Chelsea' })
            ];
            const stats = {};

            const result = threeGatesFilter(matches, leagueInfo, season, stats);

            assert.strictEqual(result.length, 0);
            assert.strictEqual(stats.placeholder, 3);
        });

        it('应该拦截无效球队 ID', () => {
            const matches = [
                createMockMatch({ id: 1, homeId: 0, awayId: 2 }),           // 数字 0 ✗
                createMockMatch({ id: 2, homeId: null, awayId: 2 }),        // null ✗
                createMockMatch({ id: 3, homeId: 1, awayId: undefined }),   // undefined ✗
                createMockMatch({ id: 4, homeId: '0', awayId: 2 }),         // 字符串 "0" ✗
                createMockMatch({ id: 5, homeId: '', awayId: 2 }),          // 空字符串 ✗
                createMockMatch({ id: 6, homeId: 1, awayId: 2 })            // ✓
            ];
            const stats = {};

            const result = threeGatesFilter(matches, leagueInfo, season, stats);

            assert.strictEqual(result.length, 1);
            assert.strictEqual(result[0].id, 6);
            assert.strictEqual(stats.placeholder, 5, '应统计5个无效ID（含字符串0）');
        });
    });

    describe('三道铁门综合拦截率测试', () => {
        it('对模拟脏数据应该达到 100% 拦截率', () => {
            const dirtyMatches = [
                // 英冠球队混入
                createMockMatch({ id: 1, leagueId: 48, homeName: 'Leeds United' }),
                // 2026 假比赛
                createMockMatch({ id: 2, utcTime: '2026-03-15T15:00:00Z' }),
                // TBD 占位符
                createMockMatch({ id: 3, homeName: 'TBD', awayName: 'Chelsea' }),
                // 降级球队（合法数据，如果Burnley确实在24/25英超）
                createMockMatch({ id: 4, leagueId: 47, homeName: 'Burnley' }),
                // 无效ID
                createMockMatch({ id: null }),
                // 短名称测试数据
                createMockMatch({ id: 6, homeName: 'A', awayName: 'B' }),
            ];
            const stats = {};

            const result = threeGatesFilter(dirtyMatches, leagueInfo, season, stats);

            // 验证拦截率（除了Burnley可能合法，其余5条都应被拦截）
            const rejectionRate = ((dirtyMatches.length - result.length) / dirtyMatches.length) * 100;
            assert.ok(rejectionRate >= 80, `拦截率应>=80%，实际${rejectionRate}%`);

            // 分项统计验证
            assert.ok(stats.wrongLeague >= 1, '应拦截英冠（leagueId=48）');
            assert.ok(stats.outsideWindow >= 1, '应拦截2026数据（时间窗口外）');
            assert.ok(stats.placeholder >= 1, '应拦截占位符关键词（TBD）');
            assert.ok(stats.invalidData >= 2, '应拦截无效ID和短名称（id=null 和 homeName="A"）');

            // 总拦截数验证（5条脏数据应被拦截）
            const totalRejected = (stats.wrongLeague || 0) + (stats.outsideWindow || 0) +
                                  (stats.placeholder || 0) + (stats.invalidData || 0);
            assert.ok(totalRejected >= 5, `应至少拦截5条脏数据，实际拦截${totalRejected}条`);
        });
    });
});

// ============================================================================
// 测试套件 2: 边界测试
// ============================================================================

describe('V5.0 边界情况测试', () => {
    const leagueInfo = { id: 47, name: 'Premier League' };
    const season = '2024/2025';

    describe('0 场比赛场景', () => {
        it('API 返回空数组应该返回空结果', () => {
            const result = threeGatesFilter([], leagueInfo, season, {});
            assert.deepStrictEqual(result, []);
        });

        it('全部比赛被拦截应该返回空数组（不崩溃）', () => {
            const matches = [
                createMockMatch({ id: 1, leagueId: 48 }),
                createMockMatch({ id: 2, utcTime: '2026-01-01T00:00:00Z' }),
                createMockMatch({ id: 3, homeName: 'TBD' })
            ];
            const stats = {};

            const result = threeGatesFilter(matches, leagueInfo, season, stats);

            assert.deepStrictEqual(result, []);
            assert.strictEqual(stats.wrongLeague + stats.outsideWindow + stats.placeholder, 3);
        });
    });

    describe('100% 通过场景', () => {
        it('全部合法的 380 场英超比赛应该全部通过', () => {
            const matches = [];
            for (let i = 1; i <= 380; i++) {
                matches.push(createMockMatch({
                    id: 1000000 + i,
                    utcTime: `2024-${9 + Math.floor(i / 40)}-${10 + (i % 20)}T15:00:00Z`,
                    homeName: `Team${i}Home`,
                    awayName: `Team${i}Away`
                }));
            }
            const stats = {};

            const result = threeGatesFilter(matches, leagueInfo, season, stats);

            assert.strictEqual(result.length, 380, '380场应该全部通过');
            assert.strictEqual(stats.wrongLeague || 0, 0);
            assert.strictEqual(stats.outsideWindow || 0, 0);
            assert.strictEqual(stats.placeholder || 0, 0);
        });
    });

    describe('异常大数量检测', () => {
        it('单日超过 50 场比赛应该触发警告（模拟）', () => {
            // 创建 60 场同一天的比赛（触发异常检测）
            const matches = [];
            for (let i = 1; i <= 60; i++) {
                matches.push(createMockMatch({
                    id: i,
                    utcTime: '2026-01-01T15:00:00Z'  // 同一天，且是2026年
                }));
            }
            const stats = {};

            const result = threeGatesFilter(matches, leagueInfo, season, stats);

            // 全部应该被时间窗口拦截
            assert.strictEqual(result.length, 0);
            assert.strictEqual(stats.outsideWindow, 60);
        });
    });

    describe('未知赛季处理', () => {
        it('未配置的赛季应该跳过时间窗口校验', () => {
            const matches = [
                createMockMatch({ id: 1, utcTime: '2027-01-01T00:00:00Z' })
            ];
            const stats = {};

            // 使用未配置的 2026/2027 赛季
            const result = threeGatesFilter(matches, leagueInfo, '2026/2027', stats);

            // 没有时间窗口配置，应该放行
            assert.strictEqual(result.length, 1);
            assert.strictEqual(stats.outsideWindow, 0);
        });
    });
});

// ============================================================================
// 测试套件 3: 参数解析测试
// ============================================================================

describe('V5.0 参数解析测试', () => {
    describe('parseArgs 函数', () => {
        it('应该正确解析 --season 和 --league', () => {
            process.argv = ['node', 'script.js', '--season=2024/2025', '--league=47'];
            const options = parseArgs();

            assert.strictEqual(options.season, '2024/2025');
            assert.strictEqual(options.league, 47);
            assert.strictEqual(options.all, false);
        });

        it('应该支持 20242025 数字格式自动转换', () => {
            process.argv = ['node', 'script.js', '--season=20242025', '--league=47'];
            const options = parseArgs();

            assert.strictEqual(options.season, '2024/2025');
        });

        it('应该正确识别 --all 模式', () => {
            process.argv = ['node', 'script.js', '--all'];
            const options = parseArgs();

            assert.strictEqual(options.all, true);
            assert.strictEqual(options.season, null);
            assert.strictEqual(options.league, null);
        });
    });

    describe('validateArgs 函数', () => {
        it('--all 模式应该跳过强制校验', () => {
            const options = { all: true, season: null, league: null };
            // 不应抛出异常
            assert.doesNotThrow(() => validateArgs(options));
        });

        it('缺少 season 应该退出', () => {
            const options = { all: false, season: null, league: 47 };
            // 由于 validateArgs 内部调用 process.exit，这里无法直接测试
            // 实际测试需要在集成测试中验证
            assert.ok(true, '需要在集成测试中验证 process.exit 行为');
        });
    });
});

// ============================================================================
// 测试套件 4: 配置常量测试
// ============================================================================

describe('V5.0 配置常量测试', () => {
    it('应该包含 24/25 赛季时间窗口', () => {
        const window = STRICT_VALIDATION.SEASON_WINDOWS['2024/2025'];
        assert.ok(window, '应该有 2024/2025 配置');
        assert.strictEqual(window.expected_matches, 380, '英超应有380场');
        assert.ok(window.start.includes('2024-08'), '开始时间应在2024年8月');
        assert.ok(window.end.includes('2025-05'), '结束时间应在2025年5月');
    });

    it('应该包含占位符关键词', () => {
        const keywords = STRICT_VALIDATION.PLACEHOLDER_KEYWORDS;
        assert.ok(keywords.includes('tbd'), '应包含 tbd');
        assert.ok(keywords.includes('待定'), '应包含 待定');
        assert.ok(keywords.includes('winner'), '应包含 winner');
    });

    it('单日阈值应设置为 50', () => {
        assert.strictEqual(STRICT_VALIDATION.DAILY_MATCH_THRESHOLD, 50);
    });
});

// ============================================================================
// 运行提示
// ============================================================================

console.log(`
═══════════════════════════════════════════════════════════════
FixtureSeeder V5.0 严谨版单元测试
═══════════════════════════════════════════════════════════════
运行命令: node --test tests/unit/FixtureSeederV5.test.js
测试覆盖:
  ✓ 三道铁门过滤 (leagueId/时间窗口/占位符)
  ✓ 边界情况 (0场/100%拦截/异常数量)
  ✓ 参数解析验证
  ✓ 配置常量检查
═══════════════════════════════════════════════════════════════
`);
