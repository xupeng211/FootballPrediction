'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');

const { LeagueParser } = require('../../../../src/parsers/fotmob/LeagueParser');
const { MatchParser } = require('../../../../src/parsers/fotmob/MatchParser');
const { MatchStatsParser } = require('../../../../src/parsers/fotmob/MatchStatsParser');
const { PlayerParser } = require('../../../../src/parsers/fotmob/PlayerParser');
const { TeamParser } = require('../../../../src/parsers/fotmob/TeamParser');

test('FotMob thin parsers 应提供清晰实体边界并复用原始结构', () => {
  const raw = {
    matchId: '4506745',
    general: {
      matchId: '4506745',
      homeTeam: { id: 1, name: 'Arsenal', score: 2 },
      awayTeam: { id: 2, name: 'Chelsea', score: 1 },
      status: 'Finished'
    },
    content: {
      stats: {
        Periods: {
          All: {
            stats: [
              { title: 'Expected Goals', stats: ['1.4', '0.8'] }
            ]
          }
        }
      },
      lineup: {
        home: { starters: [{ id: 10, name: 'Home Player', rating: 7.1 }] },
        away: { starters: [{ id: 20, name: 'Away Player', rating: 6.8 }] }
      }
    }
  };

  const teams = new TeamParser().parseTeams(raw);
  const match = new MatchParser().parseMatch(raw);
  const players = new PlayerParser().parsePlayers(raw);
  const stats = new MatchStatsParser().parseStats(raw);

  assert.equal(teams.length, 2);
  assert.equal(teams[0].name, 'Arsenal');
  assert.equal(match.matchId, '4506745');
  assert.equal(match.teams.length, 2);
  assert.equal(players.length, 2);
  assert.equal(stats.xg.xg_home, 1.4);
});

test('TeamParser 在 homeTeam 缺失时应过滤 null 并保留有效 awayTeam', () => {
  const raw = {
    general: {
      homeTeam: null,
      awayTeam: { id: 2, name: 'Chelsea', score: 1 }
    }
  };

  const teams = new TeamParser().parseTeams(raw);

  assert.equal(teams.length, 1);
  assert.equal(teams[0].side, 'away');
  assert.equal(teams[0].name, 'Chelsea');
  assert.equal(teams[0].score, 1);
});

test('LeagueParser 应从 __NEXT_DATA__ HTML 中抽取联赛边界对象', () => {
  const nextData = {
    props: {
      pageProps: {
        content: {
          id: 47,
          name: 'Premier League',
          season: '2024/2025'
        }
      }
    }
  };
  const html = `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify(nextData)}</script>`;
  const result = new LeagueParser().parseFromHtml(html, { leagueId: 47 });

  assert.equal(result.success, true);
  assert.equal(result.data.leagueId, 47);
  assert.equal(result.data.name, 'Premier League');
});

test('PlayerParser 在空 lineup 时应安全返回空数组', () => {
  const raw = {
    matchId: '4506745',
    general: {
      homeTeam: { name: 'Arsenal' },
      awayTeam: { name: 'Chelsea' }
    }
    // no content, no lineup
  };

  const players = new PlayerParser().parsePlayers(raw);

  assert.ok(Array.isArray(players));
  assert.equal(players.length, 0);
});

test('PlayerParser bench/substitutes extraction — 应从 lineup 中提取替补球员并分配正确的 side', () => {
  const raw = {
    matchId: '4506745',
    content: {
      lineup: {
        home: {
          starters: [{ id: 10, name: 'Home Starter', rating: 7.1 }],
          substitutes: [
            { id: 11, name: 'Home Substitute', rating: 6.0 },
            { id: 12, name: 'Home Unrated Sub' }
          ]
        },
        away: {
          starters: [{ id: 20, name: 'Away Starter', rating: 6.8 }],
          substitutes: [
            { id: 21, name: 'Away Substitute', rating: 5.5 }
          ]
        }
      }
    }
  };

  const players = new PlayerParser().parsePlayers(raw);

  // 2 starters + 3 substitutes = 5 total
  assert.equal(players.length, 5);

  // All substitutes present with correct side
  const subs = players.filter(p => p.name && p.name.toLowerCase().includes('sub'));
  assert.equal(subs.length, 3);

  const homeSub = players.find(p => p.name === 'Home Substitute');
  assert.equal(homeSub.side, 'home');
  assert.equal(homeSub.id, 11);
  assert.equal(homeSub.rating, 6.0);

  const awaySub = players.find(p => p.name === 'Away Substitute');
  assert.equal(awaySub.side, 'away');
  assert.equal(awaySub.id, 21);
  assert.equal(awaySub.rating, 5.5);

  // Unrated substitute should have null rating, not NaN
  const unrated = players.find(p => p.name === 'Home Unrated Sub');
  assert.equal(unrated.rating, null);
});

test('PlayerParser bench alias — 应从 lineup 中提取 bench 替补球员并分配正确的 side', () => {
  const raw = {
    matchId: '4506745',
    content: {
      lineup: {
        home: {
          starters: [{ id: 10, name: 'Home Starter', rating: 7.1 }],
          bench: [
            { id: 11, name: 'Home Bench Player', rating: 6.0 }
          ]
        },
        away: {
          starters: [{ id: 20, name: 'Away Starter', rating: 6.8 }],
          bench: [
            { id: 21, name: 'Away Bench Player', rating: 5.5 }
          ]
        }
      }
    }
  };

  const players = new PlayerParser().parsePlayers(raw);

  // 2 starters + 2 bench = 4 total
  assert.equal(players.length, 4);

  const homeBench = players.find(p => p.name === 'Home Bench Player');
  assert.equal(homeBench.side, 'home');
  assert.equal(homeBench.id, 11);
  assert.equal(homeBench.rating, 6.0);

  const awayBench = players.find(p => p.name === 'Away Bench Player');
  assert.equal(awayBench.side, 'away');
  assert.equal(awayBench.id, 21);
  assert.equal(awayBench.rating, 5.5);
});

test('MatchStatsParser 在缺少 xG 数据时应安全返回 null 不抛异常', () => {
  // Extremely minimal input — no content.stats at all
  const raw = { matchId: '4506745' };

  const result = new MatchStatsParser().parseStats(raw);

  // xG fields are null when no stat data exists
  assert.equal(result.xg.xg_home, null);
  assert.equal(result.xg.xg_away, null);
  assert.equal(result.xg.hasAnyStats, false);
  // stats array should be empty but no error
  assert.ok(Array.isArray(result.stats));
  assert.equal(result.stats.length, 0);
});
