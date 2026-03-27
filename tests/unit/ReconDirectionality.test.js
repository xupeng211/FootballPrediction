'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { ReconStitcher } = require('../../src/infrastructure/recon/ReconStitcher');
const { ReconParser } = require('../../src/infrastructure/recon/ReconParser');

test('ReconStitcher 应在 hash lock 中把数字队伍 ID 回退为 URL slug 队名', async () => {
  const savedMappings = [];
  const stitcher = new ReconStitcher({
    repository: {
      async saveOddsPortalMapping(mapping) {
        savedMappings.push(mapping);
        return { success: true };
      }
    },
    logger: { info() {}, warn() {}, error() {} },
    parser: new ReconParser({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'stitcher-slug-fallback'
    }),
    enableLocking: false
  });

  const result = await stitcher.stitchWithHashLock([{
    hash: 'hCfJZyrH',
    url: 'https://www.oddsportal.com/football/europe/champions-league/benfica-qarabag-agdam-hCfJZyrH/',
    homeTeam: 25545813,
    awayTeam: 25545815
  }], [{
    match_id: '42_20252026_4947188',
    home_team: 'Benfica',
    away_team: 'Qarabag Fk'
  }], '2025-2026', { name: 'Champions League' });

  assert.equal(result.inserted, 1);
  assert.equal(savedMappings.length, 1);
  assert.equal(savedMappings[0].home_team, 'Benfica');
  assert.equal(savedMappings[0].away_team, 'Qarabag Fk');
});

test('ReconStitcher 应在 hash lock 中容忍对象型队名而不触发 toLowerCase 崩溃', async () => {
  const savedMappings = [];
  const stitcher = new ReconStitcher({
    repository: {
      async saveOddsPortalMapping(mapping) {
        savedMappings.push(mapping);
        return { success: true };
      }
    },
    logger: { info() {}, warn() {}, error() {} },
    parser: new ReconParser({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'stitcher-object-team'
    }),
    enableLocking: false
  });

  stitcher._resolveWebMatchTeams = (match) => match;

  const result = await stitcher.stitchWithHashLock([{
    hash: 'objTeamHash1',
    url: 'https://www.oddsportal.com/football/europe/champions-league/benfica-qarabag-agdam-objTeam1/',
    homeTeam: { toString: () => 'Benfica' },
    awayTeam: { toString: () => 'Qarabag Fk' }
  }], [{
    match_id: '42_20252026_4947188',
    home_team: 'Benfica',
    away_team: 'Qarabag Fk'
  }], '2025-2026', { name: 'Champions League' });

  assert.equal(result.inserted, 1);
  assert.equal(savedMappings.length, 1);
  assert.equal(savedMappings[0].match_id, '42_20252026_4947188');
});
