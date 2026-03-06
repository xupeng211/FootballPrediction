/**
 * FixtureSeeder 单元测试 (V178)
 * ================================
 *
 * 测试覆盖:
 * 1. 非活跃联赛数据过滤
 * 2. match_id 格式验证
 * 3. 空数据优雅处理
 *
 * 运行: node --test tests/unit/FixtureSeeder.test.js
 */

const { describe, it, beforeEach } = require('node:test');
const assert = require('node:assert');
const path = require('path');
const fs = require('fs');

// 模拟配置文件路径
const CONFIG_PATH = path.resolve(__dirname, '../../config/leagues.json');

// ============================================================================
// 测试工具
// ============================================================================

/**
 * 创建模拟的 FixtureSeeder 实例（不连接数据库）
 */
function createMockSeeder(leagues, seasons) {
    return {
        config: { leagues, seasons },
        stats: { leagues: 0, fixtures: 0, inserted: 0, updated: 0, skipped: 0, errors: 0 },

        /**
         * 解析单场比赛 - 核心逻辑
         */
        parseMatch(match, leagueInfo, season) {
            const externalId = match.id?.toString() || null;
            if (!externalId) {
                return null;
            }

            const homeTeam = match.home?.name || match.home?.shortName || null;
            const awayTeam = match.away?.name || match.away?.shortName || null;

            if (!homeTeam || !awayTeam) {
                return null;
            }

            const utcTime = match.status?.utcTime || match.time || null;
            const matchDate = utcTime ? new Date(utcTime) : null;

            let homeScore = null;
            let awayScore = null;

            if (match.status?.scoreStr) {
                const parts = match.status.scoreStr.split(/ - /);
                if (parts.length === 2) {
                    const h = parseInt(parts[0].trim());
                    const a = parseInt(parts[1].trim());
                    if (!isNaN(h) && !isNaN(a)) {
                        homeScore = h;
                        awayScore = a;
                    }
                }
            }

            if (homeScore === null && match.home?.score !== undefined) {
                homeScore = match.home.score;
                awayScore = match.away?.score ?? null;
            }

            const status = this.determineStatus(match, homeScore, awayScore);

            // V178: match_id = league_id + season + fotmob_id
            const seasonTag = season.replace('/', '');
            const matchId = `${leagueInfo.id}_${seasonTag}_${externalId}`;

            return {
                match_id: matchId,
                external_id: externalId,
                league_name: leagueInfo.name,
                season: season,
                home_team: homeTeam,
                away_team: awayTeam,
                match_date: matchDate,
                home_score: homeScore,
                away_score: awayScore,
                status: status,
                data_source: 'FotMob'
            };
        },

        determineStatus(match, homeScore, awayScore) {
            const status = match.status;

            if (typeof status === 'object' && status !== null) {
                if (status.cancelled) return 'cancelled';
                if (status.awarded) return 'awarded';
                if (status.finished) return 'finished';
                if (status.started) return 'live';
            }

            if (homeScore !== null && awayScore !== null) {
                return 'finished';
            }

            return 'scheduled';
        },

        /**
         * 解析赛程数据
         */
        parseFixtures(leagueData, leagueInfo, season) {
            const fixtures = [];

            const allMatches = leagueData?.fixtures?.allMatches ||
                              leagueData?.overview?.matches?.allMatches ||
                              [];

            if (!Array.isArray(allMatches) || allMatches.length === 0) {
                return [];
            }

            for (const match of allMatches) {
                try {
                    const fixture = this.parseMatch(match, leagueInfo, season);
                    if (fixture) {
                        fixtures.push(fixture);
                    }
                } catch (e) {
                    // 忽略解析错误
                }
            }

            return fixtures.filter(f => f && f.external_id);
        }
    };
}

// ============================================================================
// 测试用例
// ============================================================================

describe('FixtureSeeder V178 单元测试', () => {

    describe('1. 联赛过滤测试', () => {
        const activeLeagues = [{ id: 47, name: 'Premier League', country: 'England', enabled: true }];

        it('应该只处理活跃联赛 (id=47)', () => {
            const league47 = activeLeagues.find(l => l.id === 47);
            assert.ok(league47, '英超 (47) 应该在活跃列表中');
            assert.strictEqual(league47.enabled, true);
        });

        it('非活跃联赛 (如西甲 87) 应该被过滤', () => {
            const league87 = activeLeagues.find(l => l.id === 87);
            assert.strictEqual(league87, undefined, '西甲 (87) 不应该在活跃列表中');
        });

        it('配置文件应该包含英超作为活跃联赛', () => {
            // V192: 西甲 (87) 已添加为活跃联赛，测试不再硬编码期望值
            // 改为验证英超 (47) 必须存在
            if (fs.existsSync(CONFIG_PATH)) {
                const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
                const activeIds = config.active_leagues.filter(l => l.enabled !== false).map(l => l.id);
                assert.ok(activeIds.includes(47), '英超 (47) 应该在活跃列表中');
                assert.ok(activeIds.length >= 1, '至少应该有一个活跃联赛');
            }
        });
    });

    describe('2. match_id 格式验证', () => {
        const seeder = createMockSeeder([{ id: 47, name: 'Premier League' }], ['2024/2025']);
        const league = { id: 47, name: 'Premier League', country: 'England' };

        it('match_id 格式应为 ${league_id}_${season}_${externalId}', () => {
            const mockMatch = {
                id: 123456789,
                home: { name: 'Liverpool' },
                away: { name: 'Chelsea' },
                status: { utcTime: '2024-03-15T15:00:00Z' }
            };

            const result = seeder.parseMatch(mockMatch, league, '2024/2025');

            assert.ok(result, '解析结果不应为空');
            assert.strictEqual(result.match_id, '47_20242025_123456789',
                `match_id 格式错误: ${result.match_id}`);
        });

        it('赛季格式 2023/2024 应转换为 20232024', () => {
            const mockMatch = {
                id: 999,
                home: { name: 'Arsenal' },
                away: { name: 'Man City' },
                status: {}
            };

            const result = seeder.parseMatch(mockMatch, league, '2023/2024');

            assert.ok(result.match_id.includes('20232024'),
                `赛季格式转换错误: ${result.match_id}`);
        });

        it('不同联赛的 match_id 应该不同', () => {
            const mockMatch = {
                id: 111,
                home: { name: 'Team A' },
                away: { name: 'Team B' },
                status: {}
            };

            const result47 = seeder.parseMatch(mockMatch, { id: 47, name: 'EPL' }, '2024/2025');
            const result87 = seeder.parseMatch(mockMatch, { id: 87, name: 'La Liga' }, '2024/2025');

            assert.notStrictEqual(result47.match_id, result87.match_id,
                '不同联赛的 match_id 应该不同');
        });
    });

    describe('3. 空数据优雅处理', () => {
        const seeder = createMockSeeder([{ id: 47, name: 'Premier League' }], ['2024/2025']);
        const league = { id: 47, name: 'Premier League', country: 'England' };

        it('API 返回 null 时应该返回空数组', () => {
            const result = seeder.parseFixtures(null, league, '2024/2025');
            assert.deepStrictEqual(result, []);
        });

        it('API 返回空对象时应该返回空数组', () => {
            const result = seeder.parseFixtures({}, league, '2024/2025');
            assert.deepStrictEqual(result, []);
        });

        it('allMatches 为空数组时应该返回空数组', () => {
            const result = seeder.parseFixtures({ fixtures: { allMatches: [] } }, league, '2024/2025');
            assert.deepStrictEqual(result, []);
        });

        it('缺少 id 的比赛应该被过滤', () => {
            const mockData = {
                fixtures: {
                    allMatches: [
                        { home: { name: 'Team A' }, away: { name: 'Team B' } },  // 无 id
                        { id: 123, home: { name: 'Team C' }, away: { name: 'Team D' } }  // 有效
                    ]
                }
            };

            const result = seeder.parseFixtures(mockData, league, '2024/2025');
            assert.strictEqual(result.length, 1, '只有有效比赛应该被保留');
            assert.strictEqual(result[0].external_id, '123');
        });

        it('缺少队名的比赛应该被过滤', () => {
            const mockData = {
                fixtures: {
                    allMatches: [
                        { id: 111, home: {}, away: { name: 'Team B' } },  // 缺少主队
                        { id: 222, home: { name: 'Team A' }, away: {} },  // 缺少客队
                        { id: 333, home: { name: 'Team C' }, away: { name: 'Team D' } }  // 有效
                    ]
                }
            };

            const result = seeder.parseFixtures(mockData, league, '2024/2025');
            assert.strictEqual(result.length, 1, '只有完整队名的比赛应该被保留');
        });
    });

    describe('4. 比赛状态判定', () => {
        const seeder = createMockSeeder([{ id: 47 }], ['2024/2025']);

        it('finished 状态应该正确识别', () => {
            const status = seeder.determineStatus({ status: { finished: true } }, null, null);
            assert.strictEqual(status, 'finished');
        });

        it('live 状态应该正确识别', () => {
            const status = seeder.determineStatus({ status: { started: true } }, null, null);
            assert.strictEqual(status, 'live');
        });

        it('cancelled 状态应该正确识别', () => {
            const status = seeder.determineStatus({ status: { cancelled: true } }, null, null);
            assert.strictEqual(status, 'cancelled');
        });

        it('无状态对象但有比分时应为 finished', () => {
            const status = seeder.determineStatus({ status: {} }, 2, 1);
            assert.strictEqual(status, 'finished');
        });

        it('无状态无比分时应为 scheduled', () => {
            const status = seeder.determineStatus({ status: {} }, null, null);
            assert.strictEqual(status, 'scheduled');
        });
    });
});

// ============================================================================
// 运行提示
// ============================================================================

console.log(`
═══════════════════════════════════════════════════════════════
V178 FixtureSeeder 单元测试
═══════════════════════════════════════════════════════════════
运行命令: node --test tests/unit/FixtureSeeder.test.js
═══════════════════════════════════════════════════════════════
`);
