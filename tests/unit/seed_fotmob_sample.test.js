'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const assert = require('node:assert/strict');

const {
  extractCandidate,
  loadCandidates
} = require('../../scripts/ops/seed_fotmob_sample');

function createFotMobSample(matchId, overrides = {}) {
  const {
    leagueId = 47,
    leagueName = 'Premier League',
    round = '1',
    matchDate = '2025-08-16T14:00:00.000Z',
    homeTeam = 'Arsenal',
    awayTeam = 'Chelsea',
    finished = false,
    started = false
  } = overrides;

  return {
    raw_data: {
      general: {
        matchId,
        leagueId,
        leagueName,
        matchRound: round,
        matchTimeUTCDateTime: matchDate,
        homeTeam: { name: homeTeam },
        awayTeam: { name: awayTeam },
        finished,
        started
      },
      header: {
        teams: [
          { name: homeTeam },
          { name: awayTeam }
        ],
        status: {
          utcTime: matchDate,
          finished,
          started
        }
      }
    }
  };
}

test('extractCandidate 应强制使用 JSON 内部的 general.matchId', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'seed-fotmob-candidate-'));

  try {
    const filePath = path.join(tempDir, '47_20252026_9999999.json');
    fs.writeFileSync(filePath, JSON.stringify(createFotMobSample('1234567')), 'utf8');

    const candidate = extractCandidate(filePath);

    assert.equal(candidate.matchId, '1234567');
    assert.equal(candidate.externalId, '1234567');
    assert.equal(candidate.fileMatchId, '9999999');
    assert.equal(candidate.fileNameMatchesMatchId, false);
    assert.equal(candidate.leagueName, 'Premier League');
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
});

test('loadCandidates 应支持递归扫描、联赛过滤并按 internal matchId 去重', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'seed-fotmob-load-'));

  try {
    const e0Dir = path.join(tempDir, 'E0');
    const sp1Dir = path.join(tempDir, 'SP1');
    const cupDir = path.join(tempDir, 'CUP');
    fs.mkdirSync(e0Dir, { recursive: true });
    fs.mkdirSync(sp1Dir, { recursive: true });
    fs.mkdirSync(cupDir, { recursive: true });

    const duplicatePayload = JSON.stringify(createFotMobSample('1111111'));
    fs.writeFileSync(path.join(e0Dir, '47_20252026_8888888.json'), duplicatePayload, 'utf8');
    fs.writeFileSync(path.join(e0Dir, '47_20252026_1111111.json'), duplicatePayload, 'utf8');
    fs.writeFileSync(
      path.join(sp1Dir, '87_20252026_2222222.json'),
      JSON.stringify(createFotMobSample('2222222', {
        leagueId: 87,
        leagueName: 'La Liga',
        round: '2',
        homeTeam: 'Barcelona',
        awayTeam: 'Real Madrid'
      })),
      'utf8'
    );
    fs.writeFileSync(
      path.join(cupDir, '900613_20252026_3333333.json'),
      JSON.stringify(createFotMobSample('3333333', {
        leagueId: 900613,
        leagueName: 'Coppa Italia',
        round: '3',
        homeTeam: 'Roma',
        awayTeam: 'Milan'
      })),
      'utf8'
    );

    const result = loadCandidates({
      sourceDir: tempDir,
      recursive: true,
      allowedLeagueIds: [47, 87]
    });

    assert.equal(result.stats.scannedFiles, 4);
    assert.equal(result.stats.parsedFiles, 4);
    assert.equal(result.stats.filteredCandidates, 3);
    assert.equal(result.stats.excludedByLeagueId, 1);
    assert.equal(result.stats.uniqueMatchIds, 2);
    assert.equal(result.stats.filenameMismatches, 1);
    assert.equal(result.stats.duplicateMatchIds, 1);
    assert.equal(result.stats.duplicateCandidates, 1);
    assert.equal(result.errors.length, 0);

    const deduped = result.candidates.find((candidate) => candidate.matchId === '1111111');
    assert.ok(deduped);
    assert.equal(deduped.fileNameMatchesMatchId, true);
    assert.equal(result.candidates.find((candidate) => candidate.matchId === '2222222')?.leagueName, 'La Liga');
    assert.equal(result.candidates.length, 2);
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
});
