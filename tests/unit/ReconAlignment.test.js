'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconParser } = require('../../src/infrastructure/recon/ReconParser');
const { Normalizer } = require('../../src/utils/Normalizer');

const silentLogger = {
  info() {},
  warn() {},
  error() {},
  debug() {}
};

describe('ReconAlignment - L1/L2 标准化大一统', () => {
  it('应将 Bayern 与 Bayern Munchen 对齐到 L1 的 Bayern Munich', () => {
    const parser = new ReconParser({
      logger: silentLogger,
      config: {
        teamSlugs: ['bayern-munich', 'rb-leipzig', 'koln', 'monchengladbach']
      }
    });

    const canonical = Normalizer.normalizeTeamName('Bayern Munich');

    assert.strictEqual(parser.findTeamMatch('Bayern'), canonical);
    assert.strictEqual(parser.findTeamMatch('Bayern Munchen'), canonical);
    assert.strictEqual(parser.findTeamMatch('bayern-munich'), canonical);
  });

  it('应将带重音和俱乐部前缀的德甲变体对齐到统一标准名', () => {
    const parser = new ReconParser({
      logger: silentLogger,
      config: {
        teamSlugs: ['koln', 'monchengladbach', 'bayern-munich']
      }
    });

    assert.strictEqual(
      parser.findTeamMatch('1. FC Köln'),
      Normalizer.normalizeTeamName('Koln')
    );
    assert.strictEqual(
      parser.findTeamMatch("M'Gladbach"),
      Normalizer.normalizeTeamName('Borussia Monchengladbach')
    );

    const extracted = parser.extractTeamsFromSlug('1-fc-koln-bayern-munchen');
    assert.deepStrictEqual(extracted, {
      homeTeam: Normalizer.normalizeTeamName('Koln'),
      awayTeam: Normalizer.normalizeTeamName('Bayern Munich')
    });
  });

  it('应将英冠缩写变体对齐到统一标准名', () => {
    const parser = new ReconParser({
      logger: silentLogger,
      config: {
        teamSlugs: [
          'queens-park-rangers',
          'west-bromwich-albion',
          'sheffield-united',
          'ipswich'
        ]
      }
    });

    assert.strictEqual(
      parser.findTeamMatch('QPR'),
      Normalizer.normalizeTeamName('Queens Park Rangers')
    );
    assert.strictEqual(
      parser.findTeamMatch('WBA'),
      Normalizer.normalizeTeamName('West Bromwich Albion')
    );
    assert.strictEqual(
      parser.findTeamMatch('Sheff Utd'),
      Normalizer.normalizeTeamName('Sheffield United')
    );

    const extracted = parser.extractTeamsFromSlug('sheff-utd-qpr');
    assert.deepStrictEqual(extracted, {
      homeTeam: Normalizer.normalizeTeamName('Sheffield United'),
      awayTeam: Normalizer.normalizeTeamName('Queens Park Rangers')
    });
  });

  it('应在相似度计算前先走中央标准化，避免 Wolves/Spurs/Man City 被误判', () => {
    const parser = new ReconParser({
      logger: silentLogger,
      config: {
        teamSlugs: [
          'wolverhampton-wanderers',
          'tottenham-hotspur',
          'manchester-city'
        ]
      }
    });

    assert.ok(
      parser.calculateSimilarity('Wolves', 'Wolverhampton Wanderers') >= 0.95
    );
    assert.ok(
      parser.calculateSimilarity('Spurs', 'Tottenham Hotspur') >= 0.95
    );
    assert.ok(
      parser.calculateSimilarity('Man City', 'Manchester City') >= 0.95
    );
  });
});
