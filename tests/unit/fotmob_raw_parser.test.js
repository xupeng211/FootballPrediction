/**
 * FotMobRawParser 单元测试
 * ========================
 *
 * 测试 fotmob_live_v1 raw payload parser。
 * 使用最小 inline mock 数据，不提交完整 raw。
 *
 * lifecycle: permanent
 */

'use strict';

const { test, describe } = require('node:test');
const assert = require('node:assert/strict');

const { parseFotMobRaw, _internals } = require('../../src/parsers/fotmob/FotMobRawParser');

// ---------------------------------------------------------------------------
// 最小 mock payload 构建器（不包含完整 raw data）
// ---------------------------------------------------------------------------

/**
 * 构建合法的 fotmob_live_v1 最小 payload。
 * 只包含 contract 定义的必选字段和部分可选字段。
 */
function buildMinimalPayload(overrides = {}) {
  return {
    _meta: { fetchedAt: '2026-06-10T12:00:00Z', hash: 'abc123' },
    matchId: '4830507',
    general: {
      matchId: 4830507,
      homeTeam: { id: 85, name: 'Paris Saint-Germain', shortName: 'PSG' },
      awayTeam: { id: 96, name: 'Angers', shortName: 'ANG' },
      leagueId: 47,
      leagueName: 'Ligue 1',
      leagueRoundName: 'Round 1',
      matchRound: 'Round 1',
      matchTimeUTC: '2026-06-10T19:00:00.000Z',
      started: true,
      finished: true,
    },
    header: {
      teams: [
        { id: 85, name: 'Paris Saint-Germain', score: 2, imageUrl: 'https://...', pageUrl: 'https://...' },
        { id: 96, name: 'Angers', score: 1, imageUrl: 'https://...', pageUrl: 'https://...' },
      ],
      status: {
        started: true,
        finished: true,
        cancelled: false,
        scoreStr: '2-1',
        utcTime: '2026-06-10T19:00:00.000Z',
        halfs: { homeTeamGoals1: 1, awayTeamGoals1: 0, homeTeamGoals2: 1, awayTeamGoals2: 1 },
        reason: {},
      },
      events: {
        homeTeamGoals: 2,
        awayTeamGoals: 1,
        homeTeamRedCards: 0,
        awayTeamRedCards: 0,
      },
    },
    content: {
      stats: {
        Periods: {
          All: {
            stats: [
              {
                key: 'expected_goals',
                title: 'Expected Goals',
                stats: [
                  { key: 'homeValue', value: 1.8 },
                  { key: 'awayValue', value: 0.6 },
                ],
              },
              {
                key: 'possession_percentage',
                title: 'Possession %',
                stats: [
                  { key: 'homeValue', value: 62 },
                  { key: 'awayValue', value: 38 },
                ],
              },
            ],
          },
          FirstHalf: {
            stats: [
              {
                key: 'expected_goals',
                title: 'Expected Goals',
                stats: [
                  { key: 'homeValue', value: 0.9 },
                  { key: 'awayValue', value: 0.2 },
                ],
              },
            ],
          },
          SecondHalf: {
            stats: [
              {
                key: 'expected_goals',
                title: 'Expected Goals',
                stats: [
                  { key: 'homeValue', value: 0.9 },
                  { key: 'awayValue', value: 0.4 },
                ],
              },
            ],
          },
        },
      },
      lineup: {
        homeTeam: {
          id: 85,
          name: 'Paris Saint-Germain',
          formation: '4-3-3',
          starters: [
            {
              id: 1001,
              name: { fullName: 'Kylian Mbappé', firstName: 'Kylian', lastName: 'Mbappé' },
              position: 'FW',
              shirtNumber: 7,
              rating: 8.5,
            },
            {
              id: 1002,
              name: { fullName: 'Ousmane Dembélé', firstName: 'Ousmane', lastName: 'Dembélé' },
              position: 'FW',
              shirtNumber: 10,
              rating: 7.8,
            },
          ],
          subs: [
            {
              id: 1003,
              name: { fullName: 'Gonçalo Ramos', firstName: 'Gonçalo', lastName: 'Ramos' },
              position: 'FW',
              shirtNumber: 9,
              rating: 6.5,
            },
          ],
          coach: { id: 5001, name: 'Luis Enrique' },
          rating: 7.2,
          averageStarterAge: 25.3,
          totalStarterMarketValue: '€950M',
          unavailable: [],
        },
        awayTeam: {
          id: 96,
          name: 'Angers',
          formation: '5-4-1',
          starters: [
            {
              id: 2001,
              name: { fullName: 'Himad Abdelli', firstName: 'Himad', lastName: 'Abdelli' },
              position: 'MF',
              shirtNumber: 10,
              rating: 6.8,
            },
          ],
          subs: [],
          coach: { id: 5002, name: 'Alexandre Dujeux' },
          rating: 6.4,
          averageStarterAge: 26.1,
          totalStarterMarketValue: '€45M',
          unavailable: [],
        },
      },
      matchFacts: {
        events: {
          events: [
            {
              id: 1,
              type: 'Goal',
              minute: 23,
              teamId: 85,
              playerId: 1001,
              playerName: 'Kylian Mbappé',
              assistPlayerId: 1002,
              outcome: 'goal',
            },
            {
              id: 2,
              type: 'Goal',
              minute: 67,
              teamId: 96,
              playerId: 2001,
              playerName: 'Himad Abdelli',
              assistPlayerId: null,
              outcome: 'goal',
            },
            {
              id: 3,
              type: 'Goal',
              minute: 82,
              teamId: 85,
              playerId: 1002,
              playerName: 'Ousmane Dembélé',
              assistPlayerId: null,
              outcome: 'goal',
            },
          ],
          ongoing: null,
          eventTypes: [
            { id: 1, name: 'Goal' },
            { id: 2, name: 'Card' },
          ],
          penaltyShootoutEvents: [],
        },
      },
      shotmap: {
        shots: [
          { id: 1, x: 0.85, y: 0.5, teamId: 85, playerId: 1001, minute: 23 },
          { id: 2, x: 0.15, y: 0.4, teamId: 96, playerId: 2001, minute: 67 },
        ],
      },
      playerStats: {
        '1001': { shots: 5, goals: 1 },
        '2001': { shots: 2, goals: 1 },
      },
      table: {},
      h2h: { matches: [], summary: {} },
    },
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// 整体成功解析
// ---------------------------------------------------------------------------

test('parseFotMobRaw 应成功解析完整的最小有效 payload', () => {
  const payload = buildMinimalPayload();
  const result = parseFotMobRaw(payload, '4830507');

  assert.equal(result.ok, true, `解析应成功: ${result.error}`);
  assert.ok(result.data, '应有 data 字段');

  // match
  assert.equal(result.data.match.matchId, '4830507');
  assert.equal(result.data.match.externalId, '4830507');
  assert.equal(result.data.match.leagueId, '47');
  assert.equal(result.data.match.leagueName, 'Ligue 1');
  assert.equal(result.data.match.matchRound, 'Round 1');
  assert.equal(result.data.match.started, true);
  assert.equal(result.data.match.finished, true);
  assert.equal(result.data.match.cancelled, false);

  // homeTeam
  assert.equal(result.data.homeTeam.id, 85);
  assert.equal(result.data.homeTeam.name, 'Paris Saint-Germain');
  assert.equal(result.data.homeTeam.score, 2);
  assert.equal(result.data.homeTeam.formation, '4-3-3');

  // awayTeam
  assert.equal(result.data.awayTeam.id, 96);
  assert.equal(result.data.awayTeam.name, 'Angers');
  assert.equal(result.data.awayTeam.score, 1);
  assert.equal(result.data.awayTeam.formation, '5-4-1');

  // meta
  assert.equal(result.data.meta.dataVersion, 'fotmob_live_v1');
  assert.equal(result.data.meta.hashStrategy, 'stable_raw_payload_v1');
  assert.equal(result.data.meta.parserVersion, '1.0.0');
});

// ---------------------------------------------------------------------------
// Stats: Periods-aware 遍历
// ---------------------------------------------------------------------------

test('stats 应进行 Periods-aware 遍历并输出扁平数组', () => {
  const payload = buildMinimalPayload();
  const result = parseFotMobRaw(payload, '4830507');

  assert.ok(result.ok);
  assert.ok(Array.isArray(result.data.stats));
  assert.ok(result.data.stats.length > 0, 'stats 不应为空');

  // 验证每条 stat 包含 period 字段
  for (const stat of result.data.stats) {
    assert.ok(['All', 'FirstHalf', 'SecondHalf'].includes(stat.period),
      `period 应为 All/FirstHalf/SecondHalf，实际: ${stat.period}`);
    assert.ok(typeof stat.key === 'string', 'stat.key 应为字符串');
    assert.ok('homeValue' in stat, '应包含 homeValue');
    assert.ok('awayValue' in stat, '应包含 awayValue');
  }

  // All period 应包含 expected_goals
  const allXg = result.data.stats.find(s => s.period === 'All' && s.key === 'expected_goals');
  assert.ok(allXg, 'All period 应包含 expected_goals');
  assert.equal(allXg.homeValue, 1.8);
  assert.equal(allXg.awayValue, 0.6);

  // 应有 FirstHalf 和 SecondHalf 的数据
  const fhStats = result.data.stats.filter(s => s.period === 'FirstHalf');
  const shStats = result.data.stats.filter(s => s.period === 'SecondHalf');
  assert.ok(fhStats.length > 0, '应有 FirstHalf stats');
  assert.ok(shStats.length > 0, '应有 SecondHalf stats');
});

// ---------------------------------------------------------------------------
// Events: content.matchFacts.events.events[]
// ---------------------------------------------------------------------------

test('events 应从 content.matchFacts.events.events[] 读取事件时间线', () => {
  const payload = buildMinimalPayload();
  const result = parseFotMobRaw(payload, '4830507');

  assert.ok(result.ok);
  assert.ok(Array.isArray(result.data.events));
  assert.equal(result.data.events.length, 3, '应解析 3 个事件');

  // 第一个事件：Mbappé 进球
  const goal = result.data.events[0];
  assert.equal(goal.id, 1);
  assert.equal(goal.type, 'Goal');
  assert.equal(goal.minute, 23);
  assert.equal(goal.teamId, 85);
  assert.equal(goal.playerId, 1001);
  assert.equal(goal.playerName, 'Kylian Mbappé');
  assert.equal(goal.assistPlayerId, 1002);
});

// ---------------------------------------------------------------------------
// Lineup 解析
// ---------------------------------------------------------------------------

test('lineup 应正确解析主客队阵容', () => {
  const payload = buildMinimalPayload();
  const result = parseFotMobRaw(payload, '4830507');

  assert.ok(result.ok);

  // home lineup
  assert.ok(Array.isArray(result.data.lineup.home.starters));
  assert.equal(result.data.lineup.home.starters.length, 2);
  assert.equal(result.data.lineup.home.starters[0].name, 'Kylian Mbappé');
  assert.equal(result.data.lineup.home.starters[0].position, 'FW');
  assert.equal(result.data.lineup.home.starters[0].rating, 8.5);
  assert.equal(result.data.lineup.home.subs.length, 1);
  assert.equal(result.data.lineup.home.coach.name, 'Luis Enrique');

  // away lineup
  assert.equal(result.data.lineup.away.starters.length, 1);
  assert.equal(result.data.lineup.away.subs.length, 0);
});

// ---------------------------------------------------------------------------
// Shotmap
// ---------------------------------------------------------------------------

test('shotmap 应提取 shots 数组', () => {
  const payload = buildMinimalPayload();
  const result = parseFotMobRaw(payload, '4830507');

  assert.ok(result.ok);
  assert.ok(result.data.shotmap, '应有 shotmap');
  assert.ok(Array.isArray(result.data.shotmap.shots));
  assert.equal(result.data.shotmap.shots.length, 2);
});

// ---------------------------------------------------------------------------
// PlayerStats
// ---------------------------------------------------------------------------

test('playerStats 应提取 content.playerStats', () => {
  const payload = buildMinimalPayload();
  const result = parseFotMobRaw(payload, '4830507');

  assert.ok(result.ok);
  assert.ok(typeof result.data.playerStats === 'object');
  assert.ok('1001' in result.data.playerStats);
});

// ---------------------------------------------------------------------------
// contract §7 缺失字段行为
// ---------------------------------------------------------------------------

test('缺失 general 应返回 MISSING_REQUIRED_SECTION', () => {
  const result = parseFotMobRaw({ header: {}, content: {} }, 'test');
  assert.equal(result.ok, false);
  assert.ok(result.error.includes('MISSING_REQUIRED_SECTION:general'));
});

test('缺失 header 应返回 MISSING_REQUIRED_SECTION', () => {
  const result = parseFotMobRaw({ general: { homeTeam: {}, awayTeam: {}, matchId: 1 }, content: {} }, 'test');
  assert.equal(result.ok, false);
  assert.ok(result.error.includes('MISSING_REQUIRED_SECTION:header'));
});

test('缺失 content 应返回 MISSING_REQUIRED_SECTION', () => {
  const result = parseFotMobRaw({ general: { homeTeam: {}, awayTeam: {}, matchId: 1 }, header: {} }, 'test');
  assert.equal(result.ok, false);
  assert.ok(result.error.includes('MISSING_REQUIRED_SECTION:content'));
});

test('缺失 homeTeam 应返回 MISSING_TEAM_IDENTITY', () => {
  const result = parseFotMobRaw({
    matchId: '1',
    general: { matchId: 1, awayTeam: { id: 2, name: 'Away' } },
    header: {},
    content: {},
  }, 'test');
  assert.equal(result.ok, false);
  assert.equal(result.error, 'MISSING_TEAM_IDENTITY');
});

test('缺失 awayTeam 应返回 MISSING_TEAM_IDENTITY', () => {
  const result = parseFotMobRaw({
    matchId: '1',
    general: { matchId: 1, homeTeam: { id: 1, name: 'Home' } },
    header: {},
    content: {},
  }, 'test');
  assert.equal(result.ok, false);
  assert.equal(result.error, 'MISSING_TEAM_IDENTITY');
});

test('缺失 matchId 应返回 INVALID_MATCH_ID', () => {
  const result = parseFotMobRaw({
    matchId: null,
    general: { homeTeam: { id: 1 }, awayTeam: { id: 2 } },
    header: {},
    content: {},
  }, 'test');
  assert.equal(result.ok, false);
  assert.equal(result.error, 'INVALID_MATCH_ID');
});

test('非数字 matchId 应返回 INVALID_MATCH_ID', () => {
  const result = parseFotMobRaw({
    matchId: 'not-a-number',
    general: { homeTeam: { id: 1 }, awayTeam: { id: 2 } },
    header: {},
    content: {},
  }, 'test');
  assert.equal(result.ok, false);
  assert.equal(result.error, 'INVALID_MATCH_ID');
});

test('null 输入应返回 error', () => {
  const result = parseFotMobRaw(null, 'test');
  assert.equal(result.ok, false);
  assert.ok(result.error.includes('INVALID_INPUT'));
});

test('非对象输入应返回 error', () => {
  const result = parseFotMobRaw('string', 'test');
  assert.equal(result.ok, false);
  assert.ok(result.error.includes('INVALID_INPUT'));
});

// ---------------------------------------------------------------------------
// optional 字段缺失 → 空容器 / null
// ---------------------------------------------------------------------------

test('content.stats 缺失应返回空 stats 数组', () => {
  const payload = buildMinimalPayload();
  delete payload.content.stats;
  const result = parseFotMobRaw(payload, '4830507');

  assert.ok(result.ok);
  assert.ok(Array.isArray(result.data.stats));
  assert.equal(result.data.stats.length, 0);
});

test('content.stats.Periods 缺失应返回空 stats 数组', () => {
  const payload = buildMinimalPayload();
  payload.content.stats = { someOther: true };
  const result = parseFotMobRaw(payload, '4830507');

  assert.ok(result.ok);
  assert.ok(Array.isArray(result.data.stats));
  assert.equal(result.data.stats.length, 0);
});

test('content.lineup 缺失应返回空阵容结构', () => {
  const payload = buildMinimalPayload();
  delete payload.content.lineup;
  const result = parseFotMobRaw(payload, '4830507');

  assert.ok(result.ok);
  assert.ok(Array.isArray(result.data.lineup.home.starters));
  assert.equal(result.data.lineup.home.starters.length, 0);
  assert.ok(Array.isArray(result.data.lineup.away.subs));
  assert.equal(result.data.lineup.away.subs.length, 0);
  assert.ok(typeof result.data.lineup.home.coach === 'object');
});

test('content.matchFacts.events 缺失应返回空 events 数组', () => {
  const payload = buildMinimalPayload();
  delete payload.content.matchFacts.events;
  const result = parseFotMobRaw(payload, '4830507');

  assert.ok(result.ok);
  assert.ok(Array.isArray(result.data.events));
  assert.equal(result.data.events.length, 0);
});

test('content.matchFacts.events.events 缺失应返回空 events 数组', () => {
  const payload = buildMinimalPayload();
  delete payload.content.matchFacts.events.events;
  const result = parseFotMobRaw(payload, '4830507');

  assert.ok(result.ok);
  assert.ok(Array.isArray(result.data.events));
  assert.equal(result.data.events.length, 0);
});

test('content.shotmap 缺失应返回空 shots 数组', () => {
  const payload = buildMinimalPayload();
  delete payload.content.shotmap;
  const result = parseFotMobRaw(payload, '4830507');

  assert.ok(result.ok);
  assert.ok(Array.isArray(result.data.shotmap.shots));
  assert.equal(result.data.shotmap.shots.length, 0);
});

test('content.playerStats 缺失应返回空对象', () => {
  const payload = buildMinimalPayload();
  delete payload.content.playerStats;
  const result = parseFotMobRaw(payload, '4830507');

  assert.ok(result.ok);
  assert.equal(typeof result.data.playerStats, 'object');
  assert.equal(Object.keys(result.data.playerStats).length, 0);
});

// ---------------------------------------------------------------------------
// 边界情况
// ---------------------------------------------------------------------------

test('空 stats 数组不应崩溃', () => {
  const payload = buildMinimalPayload();
  payload.content.stats.Periods.All.stats = [];
  payload.content.stats.Periods.FirstHalf.stats = [];
  payload.content.stats.Periods.SecondHalf.stats = [];

  const result = parseFotMobRaw(payload, '4830507');
  assert.ok(result.ok);
  assert.equal(result.data.stats.length, 0);
});

test('nil 值 score 应返回 null', () => {
  const payload = buildMinimalPayload();
  payload.header.teams[0].score = null;
  payload.header.teams[1].score = null;

  const result = parseFotMobRaw(payload, '4830507');
  assert.ok(result.ok);
  assert.equal(result.data.homeTeam.score, null);
  assert.equal(result.data.awayTeam.score, null);
});

test('空 matchFacts 下 events 应返回空数组', () => {
  const payload = buildMinimalPayload();
  payload.content.matchFacts = {};

  const result = parseFotMobRaw(payload, '4830507');
  assert.ok(result.ok);
  assert.equal(result.data.events.length, 0);
});

// ---------------------------------------------------------------------------
// 内部辅助函数
// ---------------------------------------------------------------------------

test('firstValue 应返回第一个非空值', () => {
  const { firstValue } = _internals;
  assert.equal(firstValue([null, undefined, '', 'found']), 'found');
  assert.equal(firstValue([null, undefined, '']), null);
  assert.equal(firstValue([0, 'fallback']), 0, '0 不应被视为空');
  assert.equal(firstValue([false, 'fallback']), false, 'false 不应被视为空');
});

test('safeGet 应安全获取深层属性', () => {
  const { safeGet } = _internals;
  const obj = { a: { b: { c: 42 } } };
  assert.equal(safeGet(obj, 'a', 'b', 'c'), 42);
  assert.equal(safeGet(obj, 'a', 'x', 'y'), undefined);
  assert.equal(safeGet(null, 'a', 'b'), undefined);
  assert.equal(safeGet(obj), obj);
});

// ---------------------------------------------------------------------------
// 确定性
// ---------------------------------------------------------------------------

test('parseFotMobRaw 应对相同输入产生相同输出', () => {
  const payload = buildMinimalPayload();
  const r1 = parseFotMobRaw(payload, '4830507');
  const r2 = parseFotMobRaw(payload, '4830507');

  assert.ok(r1.ok && r2.ok);
  assert.deepStrictEqual(r1.data, r2.data);
});

// ---------------------------------------------------------------------------
// 不抛异常
// ---------------------------------------------------------------------------

test('parseFotMobRaw 在任何异常输入下不应抛出异常', () => {
  const badInputs = [
    null,
    undefined,
    'string',
    42,
    [],
    {},
    { general: null, header: null, content: null },
  ];

  for (const input of badInputs) {
    let threw = false;
    try {
      parseFotMobRaw(input);
    } catch (_e) {
      threw = true;
    }
    assert.equal(threw, false, `输入 ${JSON.stringify(input)} 不应导致异常`);
  }
});

// ---------------------------------------------------------------------------
// contract: matchFacts.events vs header.events 不混淆
// ---------------------------------------------------------------------------

test('不应混淆 header.events（score summary）和 content.matchFacts.events.events（时间线）', () => {
  const payload = buildMinimalPayload();
  // header.events 是 aggregate score summary
  payload.header.events = {
    homeTeamGoals: 5,
    awayTeamGoals: 0,
    homeTeamRedCards: 1,
    awayTeamRedCards: 2,
  };

  const result = parseFotMobRaw(payload, '4830507');
  assert.ok(result.ok);
  // events 数组来自 content.matchFacts.events.events，不是 header.events
  assert.equal(result.data.events.length, 3);
  // 事件是 timeline 条目（Goal/Goal/Goal），不是 score summary
  assert.equal(result.data.events[0].type, 'Goal');
  assert.equal(result.data.events[0].minute, 23);
});

// ---------------------------------------------------------------------------
// preReview/postReview variance（record 39）
// ---------------------------------------------------------------------------

test('content.matchFacts 中存在额外键 preReview/postReview 时不应崩溃', () => {
  const payload = buildMinimalPayload();
  payload.content.matchFacts.preReview = { someData: true };
  payload.content.matchFacts.postReview = { otherData: true };

  const result = parseFotMobRaw(payload, '4830507');
  assert.ok(result.ok);
  // 仍能正确解析 events
  assert.equal(result.data.events.length, 3);
});

// ---------------------------------------------------------------------------
// 特定 period key 缺失 → 跳过该 period
// ---------------------------------------------------------------------------

test('Periods 中缺少某个 period key 时应跳过该 period', () => {
  const payload = buildMinimalPayload();
  delete payload.content.stats.Periods.FirstHalf;
  // SecondHalf 也为 null
  payload.content.stats.Periods.SecondHalf = null;

  const result = parseFotMobRaw(payload, '4830507');
  assert.ok(result.ok);
  // 只有 All period 的数据
  const allStats = result.data.stats.filter(s => s.period === 'All');
  const fhStats = result.data.stats.filter(s => s.period === 'FirstHalf');
  const shStats = result.data.stats.filter(s => s.period === 'SecondHalf');

  assert.ok(allStats.length > 0, 'All period 应有数据');
  assert.equal(fhStats.length, 0, 'FirstHalf 应被跳过');
  assert.equal(shStats.length, 0, 'SecondHalf 应被跳过');
});
