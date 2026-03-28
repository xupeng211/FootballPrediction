'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconMirrorManager } = require('../../src/infrastructure/recon/services/ReconMirrorManager');
const { ReconMatchEvaluator } = require('../../src/infrastructure/recon/services/ReconMatchEvaluator');

function createEvaluator() {
  return new ReconMatchEvaluator({
    parser: {
      calculateSimilarity(left, right) {
        return String(left || '').toLowerCase().trim() === String(right || '').toLowerCase().trim() ? 1 : 0;
      }
    },
    logger: { info() {}, warn() {}, error() {} }
  });
}

describe('ReconMirrorManager', () => {
  it('应基于主队-客队-比赛日复合键直接命中 season mirror', () => {
    const evaluator = createEvaluator();
    const mirrorManager = new ReconMirrorManager({ evaluator });
    evaluator.setMirrorManager(mirrorManager);

    const l1Match = {
      home_team: 'Leeds United',
      away_team: 'Burnley',
      match_date: '2025-08-12T19:00:00.000Z'
    };
    const candidates = [{
      hash: 'season-mirror-hash',
      url: 'oddsportal://championship/leeds-burnley',
      homeTeam: 'Leeds United',
      awayTeam: 'Burnley',
      matchDate: '2025-08-12T19:00:00.000Z'
    }];

    const mirror = mirrorManager.buildSeasonMirror(candidates);
    const best = mirrorManager.findMirrorCandidate(l1Match, mirror);

    assert.ok(mirror.size >= 2, '正向与反向复合键都应入镜像');
    assert.ok(best, 'season mirror 应直接返回候选');
    assert.strictEqual(best.method, 'season_mirror');
    assert.strictEqual(best.candidate.hash, 'season-mirror-hash');
    assert.strictEqual(best.isReversed, false);
    assert.strictEqual(best.confidence, 1);
  });

  it('应在镜像候选主客反转时返回 isReversed=true', () => {
    const evaluator = createEvaluator();
    const mirrorManager = new ReconMirrorManager({ evaluator });
    evaluator.setMirrorManager(mirrorManager);

    const l1Match = {
      home_team: 'Wolves',
      away_team: 'Spurs',
      match_date: '2025-08-16T14:00:00.000Z'
    };
    const candidates = [{
      hash: 'reverse-hash',
      url: 'oddsportal://wolves-vs-spurs',
      homeTeam: 'Spurs',
      awayTeam: 'Wolves',
      matchDate: '2025-08-16T14:00:00.000Z'
    }];

    const mirror = mirrorManager.buildSeasonMirror(candidates);
    const best = mirrorManager.findMirrorCandidate(l1Match, mirror);

    assert.ok(best, 'season mirror 应返回反向候选');
    assert.strictEqual(best.candidate.hash, 'reverse-hash');
    assert.strictEqual(best.isReversed, true);
    assert.strictEqual(best.confidence, 1);
  });
});
