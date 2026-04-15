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

  it('应将 ±2 小时内的开球抖动视为满分时间窗口', () => {
    const evaluator = new ReconMatchEvaluator({
      parser: {
        calculateSimilarity(left, right) {
          return String(left || '').toLowerCase().trim() === String(right || '').toLowerCase().trim() ? 1 : 0;
        }
      },
      logger: { info() {}, warn() {}, error() {} }
    });

    const best = evaluator.findBestCandidate({
      home_team: 'Arsenal',
      away_team: 'Chelsea',
      match_date: '2025-08-22T18:30:00.000Z'
    }, [
      {
        hash: 'kickoff-buffer',
        url: 'oddsportal://kickoff-buffer',
        homeTeam: 'Arsenal',
        awayTeam: 'Chelsea',
        matchDate: '2025-08-22T20:15:00.000Z'
      }
    ]);

    assert.ok(best, '应找到候选');
    assert.equal(best.dateConfidence, 1);
    assert.equal(best.dateDeltaMs, 105 * 60 * 1000);
    assert.ok(best.confidence > 0.95, `期望时间抖动 2 小时内仍保持高置信度，实际 ${best.confidence}`);
  });

  it('应压低单边队名相似但另一边错误的假高分候选', () => {
    const evaluator = new ReconMatchEvaluator({
      parser: {
        calculateSimilarity(left, right) {
          const normalize = (value) => String(value || '')
            .toLowerCase()
            .replace(/\butd\b/g, 'united')
            .replace(/[^a-z]+/g, ' ')
            .trim();
          const normalizedLeft = normalize(left);
          const normalizedRight = normalize(right);
          if (normalizedLeft === normalizedRight) {
            return 1;
          }
          if (normalizedLeft.includes(normalizedRight) || normalizedRight.includes(normalizedLeft)) {
            return 0.8;
          }
          if (normalizedLeft.startsWith('manchester') && normalizedRight.startsWith('manchester')) {
            return 0.6;
          }
          return 0;
        }
      },
      logger: { info() {}, warn() {}, error() {} }
    });

    const best = evaluator.findBestCandidate({
      home_team: 'Newcastle United',
      away_team: 'Manchester City',
      match_date: '2025-11-22T17:30:00.000Z'
    }, [
      {
        hash: 'false-positive',
        url: 'oddsportal://false-positive',
        homeTeam: 'Newcastle Utd',
        awayTeam: 'Manchester Utd',
        matchDate: '2025-11-22T17:30:00.000Z'
      }
    ]);

    assert.ok(best, '应返回最佳候选以便记录证据');
    assert.ok(best.selectedAverageScore >= 0.79, `期望平均分仍暴露“像”，实际 ${best.selectedAverageScore}`);
    assert.ok(best.selectedMinScore < 0.7, `期望弱侧队名分数被识别，实际 ${best.selectedMinScore}`);
    assert.ok(best.confidence < 0.75, `期望候选被压到阈值下方，实际 ${best.confidence}`);
  });

  it('应对青年队与成年队身份冲突执行一票否决', () => {
    const evaluator = new ReconMatchEvaluator({
      parser: {
        calculateSimilarity() {
          return 0.99;
        }
      },
      logger: { info() {}, warn() {}, error() {} }
    });

    const l1Match = {
      home_team: 'Barcelona',
      away_team: 'Real Madrid',
      match_date: '2026-04-05T18:00:00.000Z'
    };
    const candidate = {
      hash: 'identity-conflict',
      url: 'https://www.oddsportal.com/football/spain/test/barcelona-u19-real-madrid-identity-conflict/',
      homeTeam: 'Barcelona U19',
      awayTeam: 'Real Madrid',
      matchDate: '2026-04-05T18:00:00.000Z'
    };

    const orientation = evaluator.evaluateCandidateOrientation(candidate, l1Match);
    const best = evaluator.findBestCandidate(l1Match, [candidate]);

    assert.equal(orientation.directIdentityConflict, true);
    assert.equal(orientation.directScore, 0);
    assert.equal(orientation.directMatch, false);
    assert.ok(best, '应仍返回候选以保留证据');
    assert.equal(best.confidence, 0);
    assert.equal(evaluator.isStrictMatch(candidate, l1Match), false);
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

  it('应在联赛字典命中时将短名候选直接锁定为 1.0', () => {
    const evaluator = new ReconMatchEvaluator({
      logger: { info() {}, warn() {}, error() {} }
    });

    evaluator.setLeagueDictionaryEntries(140, [
      {
        remote_name: 'Dep La Coruna',
        local_team_id: '9783',
        local_team_name: 'Deportivo La Coruna'
      },
      {
        remote_name: 'Gijon',
        local_team_id: '9869',
        local_team_name: 'Sporting Gijon'
      }
    ]);

    const best = evaluator.findBestCandidate({
      home_team: 'Deportivo La Coruna',
      away_team: 'Sporting Gijon',
      match_date: '2026-04-05T18:00:00.000Z'
    }, [
      {
        hash: 'dict-lock',
        url: 'https://www.oddsportal.com/football/h2h/dep-la-coruna-Q51ZzMS6/gijon-69w4Rb2d/#23spHYrm',
        homeTeam: 'Dep La Coruna',
        awayTeam: 'Gijon',
        matchDate: '2026-01-01T00:00:00.000Z'
      }
    ]);

    assert.ok(best, '应命中字典候选');
    assert.equal(best.method, 'dictionary');
    assert.equal(best.confidence, 1);
    assert.equal(best.isReversed, false);
  });

  it('应允许占位赛程在主客完全一致时完成本地精确匹配', () => {
    const evaluator = new ReconMatchEvaluator({
      logger: { info() {}, warn() {}, error() {} }
    });

    const best = evaluator.findBestCandidate({
      home_team: 'Winner Sf 1',
      away_team: 'Winner Sf 2',
      match_date: '2026-05-10T18:00:00.000Z'
    }, [
      {
        hash: 'winner-placeholder',
        url: 'dictionary://recon/141/2025%2F2026/Winner%20Sf%201/Winner%20Sf%202/141_20252026_4935324',
        homeTeam: 'Winner SF 1',
        awayTeam: 'Winner SF 2',
        matchDate: '2026-05-10T18:00:00.000Z'
      }
    ]);

    assert.ok(best, '应命中占位赛程候选');
    assert.equal(best.method, 'exact');
    assert.equal(best.confidence, 1);
    assert.equal(best.isReversed, false);
  });

  it('131 联赛开启 dictionary string_contains 后应将 Argentina 与 Argentina (C) 锁定为 1.0', () => {
    const evaluator = new ReconMatchEvaluator({
      logger: { info() {}, warn() {}, error() {} },
      dictionaryStringContainsLeagueIds: [131]
    });

    evaluator.setLeagueDictionaryEntries(131, [
      {
        remote_name: 'Argentina',
        local_team_id: '6706',
        local_team_name: 'Argentina (C)'
      },
      {
        remote_name: 'Brazil',
        local_team_id: '8256',
        local_team_name: 'Brazil (C)'
      }
    ]);

    const best = evaluator.findBestCandidate({
      home_team: 'Argentina',
      away_team: 'Brazil',
      match_date: '2026-06-10T18:00:00.000Z'
    }, [
      {
        hash: 'copa-contains-lock',
        url: 'https://www.oddsportal.com/football/south-america/copa-america-2025-2026/argentina-brazil-copa-contains-lock/',
        homeTeam: 'Argentina',
        awayTeam: 'Brazil',
        matchDate: '2026-06-10T18:00:00.000Z'
      }
    ]);

    assert.ok(best, '应命中字典候选');
    assert.equal(best.method, 'dictionary');
    assert.equal(best.confidence, 1);
  });

  it('181 联赛应将地名简称与俱乐部前缀视为同队', () => {
    const evaluator = new ReconMatchEvaluator({
      logger: { info() {}, warn() {}, error() {} },
      placeNameEquivalentLeagueIds: [181]
    });

    evaluator.setLeagueDictionaryEntries(181, []);

    const best = evaluator.findBestCandidate({
      home_team: 'AS Saint-Priest',
      away_team: 'FC Saint Etienne',
      match_date: '2025-10-25T17:00:00.000Z'
    }, [
      {
        hash: 'coupe-place-lock',
        url: 'https://www.oddsportal.com/football/france/coupe-de-france/saint-priest-st-etienne-coupe-place-lock/',
        homeTeam: 'Saint-Priest',
        awayTeam: 'St Etienne',
        matchDate: '2025-10-25T17:00:00.000Z'
      }
    ]);

    assert.ok(best, '应命中法国杯简称候选');
    assert.equal(best.method, 'exact');
    assert.equal(best.confidence, 1);
  });
});
