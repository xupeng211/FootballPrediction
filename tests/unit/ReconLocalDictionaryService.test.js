'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const { reconLocalDictionaryService } = require('../../src/infrastructure/recon/services/ReconLocalDictionaryService');

function createService(overrides = {}) {
  return {
    ...reconLocalDictionaryService,
    matchEvaluator: {
      normalizeTeamName(teamName) {
        return String(teamName || '')
          .normalize('NFD')
          .replace(/[\u0300-\u036f]/g, '')
          .replace(/[^a-z0-9]+/gi, ' ')
          .trim()
          .toLowerCase();
      },
      isPlaceholderTeamName() {
        return false;
      }
    },
    ...overrides
  };
}

describe('ReconLocalDictionaryService', () => {
  it('应注入静态队名纠偏映射并优先返回修正后的 remote name', () => {
    const service = createService();
    const target = {
      leagueId: 223,
      dbSeason: '2025/2026',
      leagueDictionaryEntries: [
        { local_team_name: 'Yokohama F.Marinos', remote_name: 'Wrong Remote Name' }
      ]
    };

    const index = service._buildLocalDictionaryIndex(target);

    assert.equal(service._resolveLocalDictionaryRemoteName('Yokohama F.Marinos', index), 'Yokohama Marinos');
    assert.equal(service._resolveLocalDictionaryRemoteName('Gremio', index), 'Grêmio');
    assert.equal(service._resolveLocalDictionaryRemoteName('Atletico Mg', index), 'Atlético Mineiro');
    assert.equal(service._resolveLocalDictionaryRemoteName('Flamengo', index), 'Flamengo RJ');
    assert.equal(service._resolveLocalDictionaryRemoteName('Vasco Da Gama', index), 'Vasco');
    assert.equal(service._resolveLocalDictionaryRemoteName('Santos FC', index), 'Santos');
    assert.equal(service._resolveLocalDictionaryRemoteName('Real Zaragoza', index), 'Zaragoza');
  });

  it('应使用静态纠偏映射构建本地字典候选', () => {
    const service = createService();
    const target = {
      leagueId: 268,
      dbSeason: '2025/2026',
      leagueDictionaryEntries: []
    };

    const candidate = service._buildLocalDictionaryCandidate({
      match_id: 'match-1',
      home_team: 'Gremio',
      away_team: 'Atletico Mg',
      match_date: '2026-04-20T12:00:00.000Z'
    }, target);

    assert.equal(candidate.homeTeam, 'Grêmio');
    assert.equal(candidate.awayTeam, 'Atlético Mineiro');
    assert.match(candidate.url, /Gr%C3%AAmio/);
    assert.match(candidate.url, /Atl%C3%A9tico%20Mineiro/);
  });
});
