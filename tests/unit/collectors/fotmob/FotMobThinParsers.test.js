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
