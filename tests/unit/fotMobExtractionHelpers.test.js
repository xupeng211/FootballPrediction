'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  extractPrimaryLeagueData
} = require('../../src/infrastructure/shared/helpers/fotMobExtractionHelpers');

test('extractPrimaryLeagueData 应只提取与目标 leagueId 匹配的 fallback 数据', () => {
  const logs = [];
  const logger = {
    info(message) {
      logs.push(message);
    }
  };
  const pageProps = {
    fallback: {
      'https://www.fotmob.com/api/data/leagues?id=47&season=20242025': {
        fixtures: [{ id: 'wrong-league' }]
      },
      'https://www.fotmob.com/api/data/leagues?id=54&season=20242025': {
        fixtures: [{ id: 'target-league' }, { id: 'target-league-2' }]
      }
    }
  };

  const result = extractPrimaryLeagueData(
    pageProps,
    54,
    '2024/2025',
    (data) => Array.isArray(data?.fixtures) ? data.fixtures.length : 0,
    logger
  );

  assert.equal(result.matchCount, 2);
  assert.deepEqual(result.data, {
    fixtures: [{ id: 'target-league' }, { id: 'target-league-2' }]
  });
  assert.equal(logs.length, 1);
  assert.match(logs[0], /id=54/);
});

test('extractPrimaryLeagueData 在 fallback 无匹配 leagueId 时应回退到 pageProps fixtures', () => {
  const pageProps = {
    fallback: {
      'https://www.fotmob.com/api/data/leagues?id=47&season=20242025': {
        fixtures: [{ id: 'wrong-league' }]
      }
    },
    fixtures: [{ id: 'page-props-1' }, { id: 'page-props-2' }],
    marker: 'page-props-fallback'
  };

  const result = extractPrimaryLeagueData(
    pageProps,
    54,
    '2024/2025',
    (data) => Array.isArray(data?.fixtures) ? data.fixtures.length : 0,
    { info() {} }
  );

  assert.equal(result.matchCount, 2);
  assert.equal(result.data.leagueId, 54);
  assert.equal(result.data.season, '2024/2025');
  assert.equal(result.data.marker, 'page-props-fallback');
});
