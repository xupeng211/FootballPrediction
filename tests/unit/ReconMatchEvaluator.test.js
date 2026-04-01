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

  it('应识别世界杯淘汰赛与附加赛占位符，且不误伤真实队名', () => {
    const evaluator = new ReconMatchEvaluator({
      logger: { info() {}, warn() {}, error() {} }
    });

    assert.strictEqual(evaluator.isPlaceholderTeamName('1e'), true);
    assert.strictEqual(evaluator.isPlaceholderTeamName('3abcdf'), true);
    assert.strictEqual(evaluator.isPlaceholderTeamName('1b 3efgij'), true);
    assert.strictEqual(evaluator.isPlaceholderTeamName('European Play Off D'), true);
    assert.strictEqual(evaluator.isPlaceholderTeamName('Winner Qf 1'), true);
    assert.strictEqual(evaluator.isPlaceholderTeamName('South Korea'), false);
    assert.strictEqual(evaluator.isPlaceholderTeamName('1 Fc Koln'), false);
  });

  it('应从 h2h URL 中回推出文本队名并完成匹配评分', () => {
    const evaluator = new ReconMatchEvaluator({
      parser: {
        calculateSimilarity(left, right) {
          const normalize = (value) => String(value || '')
            .toLowerCase()
            .replace(/\butd\b/g, 'united')
            .trim();
          return normalize(left) === normalize(right) ? 1 : 0;
        }
      },
      logger: { info() {}, warn() {}, error() {} }
    });

    const l1Match = {
      home_team: 'Manchester City',
      away_team: 'Newcastle United',
      match_date: '2026-02-21T20:00:00.000Z'
    };
    const candidate = {
      hash: 'h2h-man-city-newcastle',
      url: 'https://www.oddsportal.com/football/h2h/manchester-city-Wtn9Stg0/newcastle-utd-p6ahwuwJ/#QwtIRNsf',
      homeTeam: 24480525,
      awayTeam: 24480527,
      matchDate: '2026-02-21T20:00:00.000Z'
    };

    const resolved = evaluator.resolveCandidateTeams(candidate, l1Match);
    const best = evaluator.findBestCandidate(l1Match, [candidate]);

    assert.equal(resolved.homeTeam, 'Manchester City');
    assert.equal(resolved.awayTeam, 'Newcastle United');
    assert.ok(best, '应找到 h2h URL 候选');
    assert.ok(best.confidence > 0.45, `期望 h2h 候选分值超过 0.45，实际 ${best.confidence}`);
  });
});
