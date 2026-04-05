'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { reconMatchExtractor } = require('../../src/infrastructure/recon/services/ReconMatchExtractor');

describe('ReconMatchExtractor', () => {
  it('应优先使用 home-name/away-name 而不是数字 participant id', () => {
    const extractor = {
      baseUrl: 'https://www.oddsportal.com',
      extractMaxDepth: 5,
      ...reconMatchExtractor
    };

    const match = extractor.normalizeMatchObject({
      home: 26648917,
      away: 26648919,
      'home-name': 'Inter Miami',
      'away-name': 'Vancouver Whitecaps',
      encodeEventId: 'YkvQVd5d',
      url: '/football/h2h/inter-miami-0AheRyBg/vancouver-whitecaps-K2dlua5N/#YkvQVd5d',
      'date-start-timestamp': 1765049400
    }, 'pure_protocol_archive:xbsqV0go');

    assert.ok(match);
    assert.strictEqual(match.homeTeam, 'Inter Miami');
    assert.strictEqual(match.awayTeam, 'Vancouver Whitecaps');
    assert.strictEqual(match.hash, 'YkvQVd5d');
  });
});
