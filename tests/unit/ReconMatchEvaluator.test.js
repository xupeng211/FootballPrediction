'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconMatchEvaluator } = require('../../src/infrastructure/recon/services/ReconMatchEvaluator');

describe('ReconMatchEvaluator', () => {
  it('应正确判定候选主客反转方向', () => {
    const evaluator = new ReconMatchEvaluator({
      parser: {
        calculateSimilarity(left, right) {
          return String(left || '').toLowerCase().trim() === String(right || '').toLowerCase().trim() ? 1 : 0;
        }
      },
      logger: { info() {}, warn() {}, error() {} }
    });

    const orientation = evaluator.evaluateCandidateOrientation({
      homeTeam: 'Spurs',
      awayTeam: 'Wolves'
    }, {
      home_team: 'Wolves',
      away_team: 'Spurs'
    });

    assert.strictEqual(orientation.directMatch, false);
    assert.strictEqual(orientation.swappedMatch, true);
    assert.strictEqual(orientation.isReversed, true);
    assert.strictEqual(orientation.directScore, 0);
    assert.strictEqual(orientation.swappedScore, 1);
  });

  it('应按队名与日期加权选择更优候选', () => {
    const evaluator = new ReconMatchEvaluator({
      parser: {
        calculateSimilarity(left, right) {
          return String(left || '').toLowerCase().trim() === String(right || '').toLowerCase().trim() ? 1 : 0;
        }
      },
      logger: { info() {}, warn() {}, error() {} }
    });

    const l1Match = {
      home_team: 'Bayern Munich',
      away_team: 'RB Leipzig',
      match_date: '2025-08-22T18:30:00.000Z'
    };
    const wrongDateCandidate = {
      hash: 'wrong-date',
      url: 'oddsportal://wrong-date',
      homeTeam: 'Bayern Munich',
      awayTeam: 'RB Leipzig',
      matchDate: '2025-09-12T18:30:00.000Z'
    };
    const correctDateCandidate = {
      hash: 'correct-date',
      url: 'oddsportal://correct-date',
      homeTeam: 'Bayern Munich',
      awayTeam: 'RB Leipzig',
      matchDate: '2025-08-22T18:30:00.000Z'
    };

    const best = evaluator.findBestCandidate(l1Match, [wrongDateCandidate, correctDateCandidate]);

    assert.ok(best, '应找到最佳候选');
    assert.strictEqual(best.candidate.hash, 'correct-date');
    assert.ok(best.confidence > 0.95, `期望加权后置信度 > 0.95，实际 ${best.confidence}`);
    assert.strictEqual(best.method, 'exact');
  });
});
